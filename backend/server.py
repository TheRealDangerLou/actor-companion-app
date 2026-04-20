from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
import json
import io
import re
import uuid
import hashlib
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from PIL import Image

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Register HEIC/HEIF support with Pillow
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    logging.info("HEIC/HEIF support registered")
except ImportError:
    logging.warning("pillow-heif not installed — HEIC uploads won't be converted")

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Serve uploaded files
from fastapi.staticfiles import StaticFiles
_upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(_upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")

# --- ElevenLabs TTS Setup ---
eleven_client = None
try:
    from elevenlabs import ElevenLabs, VoiceSettings
    elevenlabs_key = os.environ.get('ELEVENLABS_API_KEY')
    if elevenlabs_key:
        eleven_client = ElevenLabs(api_key=elevenlabs_key)
        logger.info("ElevenLabs TTS initialized")
    else:
        logger.info("ElevenLabs API key not set - TTS disabled")
except ImportError:
    logger.info("ElevenLabs SDK not installed - TTS disabled")

# --- Caching & Cost Control ---
CACHE_VERSION = "v1"  # Bump when prompts change to invalidate old cache
CACHE_TTL_HOURS = 72  # 3 days
SCENE_TEXT_HARD_CAP = 8000  # Max chars sent to GPT


def compute_cache_key(text: str, mode: str, character_name: str = "") -> str:
    """Deterministic cache key from normalized inputs."""
    normalized = f"{text.strip()[:SCENE_TEXT_HARD_CAP]}|{mode}|{character_name.strip().lower()}|{CACHE_VERSION}"
    return hashlib.sha256(normalized.encode()).hexdigest()


async def get_cached_breakdown(cache_key: str):
    """Return cached breakdown if exists and not expired."""
    cached = await db.breakdown_cache.find_one({"cache_key": cache_key}, {"_id": 0})
    if not cached:
        logger.info(f"[COST] CACHE MISS: {cache_key[:16]}")
        return None
    created = datetime.fromisoformat(cached["cached_at"])
    age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
    if age_hours > CACHE_TTL_HOURS:
        logger.info(f"[COST] CACHE EXPIRED ({age_hours:.1f}h): {cache_key[:16]}")
        await db.breakdown_cache.delete_one({"cache_key": cache_key})
        return None
    logger.info(f"[COST] CACHE HIT ({age_hours:.1f}h old, saved 1 GPT call): {cache_key[:16]}")
    return cached.get("result")


async def store_cached_breakdown(cache_key: str, result: dict, mode: str, char_name: str = ""):
    """Store breakdown in cache for future reuse."""
    doc = {
        "cache_key": cache_key,
        "result": result,
        "mode": mode,
        "character_name": char_name.strip().lower(),
        "cache_version": CACHE_VERSION,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.breakdown_cache.replace_one({"cache_key": cache_key}, doc, upsert=True)
    logger.info(f"[COST] CACHE STORED: {cache_key[:16]} (mode={mode})")


def estimate_cost(mode: str) -> float:
    """Rough per-scene cost estimate for a single GPT analysis call."""
    return 0.08 if mode == "deep" else 0.03



# --- Deterministic Script Cleaning (zero GPT) ---

def clean_script_text(raw_text: str) -> str:
    """Clean raw OCR/PDF-extracted text into standard screenplay format.
    
    Pure function: same input always produces same output.
    Zero GPT calls, zero credits, zero network.
    
    Handles: page numbers, (MORE)/(CONT'D) joins, concatenated scene numbers,
    missing blank lines before character names, trailing whitespace.
    """
    if not raw_text:
        return ""

    lines = raw_text.split("\n")
    
    # --- Pass 1: Strip page-number-only lines ---
    # Pattern: optional whitespace, digits, period, optional whitespace
    # e.g. "                                                         15. "
    cleaned = []
    for line in lines:
        if re.match(r'^\s*\d+\.\s*$', line):
            continue  # drop page number lines entirely
        cleaned.append(line)
    lines = cleaned

    # --- Pass 2: Join (MORE) / (CONT'D) page-break splits ---
    # Find (MORE) → remove it and the following SAME_NAME (CONT'D) header
    # so the dialogue before and after merge naturally
    joined = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        
        # Detect (MORE) marker
        if re.match(r'^\(MORE\)$', stripped, re.IGNORECASE):
            # Look ahead: skip blanks, find CHAR (CONT'D), skip it
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.search(r"\(CONT'?D\)", lines[j], re.IGNORECASE):
                # Skip both (MORE) and the CONT'D header
                i = j + 1
                continue
            # If no matching CONT'D found, keep the line as-is
        
        # Detect standalone CONT'D headers (without preceding MORE)
        # e.g. "FELIX (CONT'D)" → keep as "FELIX" (strip the tag, keep the name)
        contd_match = re.match(r'^([A-Z][A-Z\s\.\'\-]+?)\s*\(CONT\'?D\)\s*$', stripped, re.IGNORECASE)
        if contd_match:
            joined.append(contd_match.group(1).strip())
            i += 1
            continue
        
        joined.append(lines[i])
        i += 1
    lines = joined

    # --- Pass 3: Fix concatenated scene numbers in headings ---
    # "20INT. BAR - NIGHT" → "INT. BAR - NIGHT"
    # "13INT. ELLIE'S HOUSE" → "INT. ELLIE'S HOUSE"
    fixed = []
    for line in lines:
        s = line.strip()
        m = re.match(r'^(\d+)((?:INT|EXT|INT/EXT)\..*)$', s)
        if m:
            fixed.append(m.group(2))
        else:
            fixed.append(line.rstrip())
    lines = fixed

    # --- Pass 4: Normalize whitespace ---
    # Strip heavy indentation (common in PDF extraction)
    # Preserve relative indentation for parentheticals only
    normalized = []
    for line in lines:
        # Strip leading whitespace entirely — screenplay format doesn't need it
        # in our cleaned output
        normalized.append(line.strip())
    lines = normalized

    # --- Pass 5: Ensure blank lines before character names ---
    # In clean screenplay format, character names always have a blank line before them.
    # This is the key fix for the "action absorbed as dialogue" problem:
    # by guaranteeing structural separation, the parser can reliably detect boundaries.
    def looks_like_character_name(s):
        s = s.strip()
        if not s or len(s) > 60 or len(s) < 2:
            return False
        m = re.match(r'^([A-Z][A-Z\s\.\'\-]+?)(?:\s*\(.*?\))?\s*$', s)
        if not m:
            return False
        name = m.group(1).strip()
        if re.match(r'^(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|CUT\.|EPISODE|EP[\.\s]|CHAPTER|CONTINUED|END OF|THE END)', name):
            return False
        alpha_only = re.sub(r'[\s\.\'\-]', '', name)
        if len(alpha_only) < 2:
            return False
        return True

    spaced = []
    for idx, line in enumerate(lines):
        # If this line is a character name and previous line is non-blank
        if looks_like_character_name(line) and idx > 0 and lines[idx - 1].strip():
            spaced.append("")  # insert blank line
        spaced.append(line)
    lines = spaced

    # --- Pass 6: Collapse multiple blank lines to max 1 ---
    final = []
    prev_blank = False
    for line in lines:
        if not line.strip():
            if not prev_blank:
                final.append("")
            prev_blank = True
        else:
            final.append(line)
            prev_blank = False

    # Strip leading/trailing blank lines
    while final and not final[0].strip():
        final.pop(0)
    while final and not final[-1].strip():
        final.pop()

    return "\n".join(final)


# --- Deterministic Line Extraction (zero GPT) ---

def extract_character_lines(text: str, character_name: str) -> dict:
    """Extract character dialogue from raw script text using pattern matching.
    Returns {chunked_lines, cue_recall} — no GPT call, no credits.

    Strategy:
    1. Primary pass: Find CHARACTER NAME headers and collect dialogue until a stop signal
    2. Fallback pass: Scan for any missed lines using loose pattern matching
    """
    if not text or not character_name:
        return {"chunked_lines": [], "cue_recall": []}

    char_upper = character_name.strip().upper()
    lines = text.split("\n")

    def is_character_name(s):
        """Check if a line is a character name (ALL CAPS, short, possibly with parenthetical)."""
        s = s.strip()
        if not s or len(s) > 60 or len(s) < 2:
            return False
        m = re.match(r'^([A-Z][A-Z\s\.\'\-]+?)(?:\s*\(.*?\))?\s*$', s)
        if not m:
            return False
        name = m.group(1).strip()
        # Reject scene headings, transitions, page numbers
        if re.match(r'^(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE|EP[\.\s]|CHAPTER|CONTINUED|END OF|THE END)', name):
            return False
        # Reject single-letter "names" like "I..." or "A."
        alpha_only = re.sub(r'[\s\.\'\-]', '', name)
        if len(alpha_only) < 2:
            return False
        return True

    def extract_name(s):
        """Extract the speaker name from a character name line."""
        m = re.match(r'^([A-Z][A-Z\s\.\'\-]+?)(?:\s*\(.*?\))?\s*$', s.strip())
        return m.group(1).strip() if m else s.strip()

    def is_action_line(s):
        """Detect action/description lines that should stop dialogue collection.
        Used for inline detection (no blank line between dialogue and action)."""
        s = s.strip()
        if not s:
            return True
        # Page numbers: "8." or "9." or "                    8."
        if re.match(r'^\d+\.\s*$', s):
            return True
        # Starts with lowercase and is long — likely action/description
        # BUT exclude common dialogue continuation words
        if s[0].islower() and len(s) > 15:
            if not re.match(r'^(and |but |or |because |so |then |that |just |like |maybe |if |when |where |what |who |how |why |not |no |yes |the |this |it |to |for |in |on |at |my |your |his |her |our |you )', s, re.IGNORECASE):
                return True
        # Starts with a proper-case name followed by action verb or adverb+verb
        # e.g., "Ivy grabs...", "Felix enters.", "Ivy slowly begins to crawl"
        # Only match known character-name patterns (2+ letters, not common words)
        if re.match(r"^[A-Z][a-z]{2,}(?:'s)?\s+(?:\w+ly\s+)?(?:is|was|has|had|are|were|isn't|wasn't|can't|doesn't|didn't|enters|exits|turns|walks|grabs|runs|looks|sits|stands|goes|opens|closes|picks|pushes|shakes|approaches|whispers|freezes|shrugs|smiles|answers|laughs|cries|screams|sighs|nods|pauses|points|lets|let's|gets|takes|puts|pulls|drops|falls|stares|stops|starts|moves|leaves|steps|reaches|holds|throws|slaps|kisses|hugs|begins|crawls|climbs|covers|watches|groans|moans|gasps|snaps|winks|blinks|frowns|glares|leans|bends|kneels|lies|rolls|wraps|rubs|squeezes|pins|presses|lifts|raises|speaks|apologizes|apologises|stammers|stutters|mutters|mumbles|chuckles|giggles|wipes|twists|stumbles|trips|collapses|struggles|slowly|instantly|quietly|gently|quickly|suddenly)", s):
            # Exclude common dialogue starters that look like Name+verb
            first_word = s.split()[0] if s.split() else ""
            if first_word.lower() not in ('this', 'that', 'what', 'here', 'there', 'just', 'well', 'sure', 'fine', 'come', 'look', 'listen', 'stop', 'wait', 'maybe', 'never', 'always', 'enough', 'please'):
                return True
        # "We see...", "We hear...", "Close-up on...", "They..." — common action starts
        if re.match(r'^(We |They |Close-up |The camera |His |Her |Their )', s):
            return True
        return False

    def is_action_line_strict(s):
        """Stricter action detection for peek-ahead after blank lines.
        Only flags lines that are unambiguously stage direction.
        Dialogue continuations often start with He/She/They/We/lowercase — don't flag those."""
        s = s.strip()
        if not s:
            return True
        if re.match(r'^\d+\.\s*$', s):
            return True
        # Only flag: ProperName + physical action verb (no pronouns, no common words)
        # Must be a 2+ word proper name pattern followed directly by a physical verb
        if re.match(r"^[A-Z][a-z]{2,}(?:'s)?\s+(?:\w+ly\s+)?(?:enters|exits|turns|walks|grabs|runs|sits|stands|goes|opens|closes|picks|pushes|shakes|approaches|whispers|freezes|shrugs|smiles|laughs|cries|screams|sighs|nods|pauses|points|gets|takes|puts|pulls|drops|falls|stares|stops|starts|moves|leaves|steps|reaches|holds|throws|slaps|kisses|hugs|begins|crawls|climbs|covers|watches|groans|moans|gasps|snaps|winks|blinks|frowns|glares|leans|bends|kneels|lies|rolls|wraps|rubs|squeezes|pins|presses|lifts|raises|apologizes|apologises|stammers|stutters|mutters|mumbles|chuckles|giggles|wipes|twists|stumbles|trips|collapses|struggles|slowly|instantly|quietly|gently|quickly|suddenly)", s):
            first_word = s.split()[0] if s.split() else ""
            if first_word.lower() not in ('this', 'that', 'what', 'here', 'there', 'just', 'well', 'sure', 'fine', 'come', 'look', 'listen', 'stop', 'wait', 'maybe', 'never', 'always', 'enough', 'please', 'she', 'he', 'we', 'they', 'his', 'her', 'their', 'its', 'my', 'your', 'our', 'nothing', 'everything', 'everyone', 'someone', 'no', 'not'):
                return True
        # Narration pattern: His/Her/Their + 1-3 words + past-tense verb (clearly describing events, not dialogue)
        # e.g. "His whole world changed", "Her heart sank", "Their eyes met"
        if re.match(r'^(His|Her|Their|The)\s+(?:\w+\s+){0,3}\w*(ed|ank|oke|ell|ew|ung|ept|elt|ose|one|ent|ade|ook|ame)\b', s):
            return True
        # "Close-up on...", "The camera..." — unambiguous stage direction
        if re.match(r'^(Close-up |The camera )', s):
            return True
        return False

    # --- Primary pass: extract dialogue blocks ---
    dialogue_blocks = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if is_character_name(stripped):
            speaker = extract_name(stripped)
            dialogue_lines = []
            first_line = True
            after_blank_skip = False
            i += 1
            while i < len(lines):
                dl = lines[i].strip()
                # Empty line: peek ahead to check for dialogue continuation
                if not dl:
                    peek = i + 1
                    while peek < len(lines) and not lines[peek].strip():
                        peek += 1
                    if peek < len(lines):
                        next_content = lines[peek].strip()
                        # Same speaker with CONT'D after blank = page-break continuation (MORE/CONT'D)
                        if is_character_name(next_content):
                            nc_name = extract_name(next_content).upper()
                            if nc_name == speaker.upper() and re.search(r"CONT'?D", next_content, re.IGNORECASE):
                                i = peek + 1
                                after_blank_skip = True
                                continue
                            break
                        # Stop if heading or unambiguous action
                        if re.match(r'^\d*(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE\s|EP[\.\s])', next_content, re.IGNORECASE) or \
                           is_action_line_strict(next_content):
                            break
                        # Otherwise dialogue continues — skip blank line(s)
                        i = peek
                        after_blank_skip = True
                        continue
                    break
                # Another character name = end of this speaker's dialogue
                # UNLESS it's the same speaker with (CONT'D) — that's a page-break continuation
                if is_character_name(dl):
                    other_name = extract_name(dl).upper()
                    if other_name == speaker.upper() and re.search(r"CONT'?D", dl, re.IGNORECASE):
                        i += 1
                        continue
                    break
                # Scene heading
                if re.match(r'^\d*(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE\s|EP[\.\s])', dl, re.IGNORECASE):
                    break
                # Skip parentheticals like (beat), (pause)
                if re.match(r'^\(.*\)$', dl):
                    i += 1
                    after_blank_skip = True  # protect next line from action check (same as blank-line continuation)
                    continue
                # Page number embedded in line — skip before action check
                # Treat as structural boundary (like blank line)
                if re.match(r'^\d+\.\s*$', dl):
                    i += 1
                    after_blank_skip = True
                    continue
                # Action/description line = end of dialogue
                # Skip for first line (always dialogue) and lines reached via blank-line continuation
                # Also skip if previous dialogue line didn't end with sentence terminator (mid-sentence wrap)
                prev_ended_sentence = True
                if dialogue_lines:
                    prev_last_char = dialogue_lines[-1].rstrip()[-1:] if dialogue_lines[-1].rstrip() else ''
                    prev_ended_sentence = prev_last_char in '.!?"\u201d'
                if not first_line and not after_blank_skip and prev_ended_sentence and is_action_line(dl):
                    break
                dialogue_lines.append(dl)
                first_line = False
                after_blank_skip = False
                i += 1
            if dialogue_lines:
                dialogue_blocks.append({"speaker": speaker, "text": " ".join(dialogue_lines), "line_idx": i})
        else:
            i += 1

    # --- Fallback pass: scan for missed character lines ---
    # Look for the pattern: char name on one line, dialogue on next, that we might have missed
    found_texts = {b["text"] for b in dialogue_blocks if b["speaker"].upper() == char_upper or char_upper in b["speaker"].upper()}
    char_patterns = [char_upper, f"{char_upper} (", f"{char_upper}("]

    i = 0
    while i < len(lines):
        stripped = lines[i].strip().upper()
        # Check if this line contains the character name as a header
        matched = False
        for pat in char_patterns:
            if stripped.startswith(pat) and is_character_name(lines[i].strip()):
                matched = True
                break
        if matched:
            fb_speaker = extract_name(lines[i].strip()).upper()
            # Check if we already have this block
            # Collect the dialogue
            fallback_lines = []
            fb_first_line = True
            fb_after_blank = False
            j = i + 1
            while j < len(lines):
                dl = lines[j].strip()
                if not dl:
                    # Peek ahead for dialogue continuation
                    peek = j + 1
                    while peek < len(lines) and not lines[peek].strip():
                        peek += 1
                    if peek < len(lines):
                        next_content = lines[peek].strip()
                        # Same speaker with CONT'D = page-break continuation
                        if is_character_name(next_content):
                            nc_name = extract_name(next_content).upper()
                            if nc_name == fb_speaker and re.search(r"CONT'?D", next_content, re.IGNORECASE):
                                j = peek + 1
                                fb_after_blank = True
                                continue
                            break
                        if re.match(r'^\d*(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE\s|EP[\.\s])', next_content, re.IGNORECASE) or \
                           is_action_line_strict(next_content):
                            break
                        j = peek
                        fb_after_blank = True
                        continue
                    break
                if is_character_name(dl):
                    other_fb_name = extract_name(dl).upper()
                    if other_fb_name == fb_speaker and re.search(r"CONT'?D", dl, re.IGNORECASE):
                        j += 1
                        continue
                    break
                if re.match(r'^\d*(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE\s|EP[\.\s])', dl, re.IGNORECASE):
                    break
                if re.match(r'^\(.*\)$', dl) or re.match(r'^\d+\.\s*$', dl):
                    j += 1
                    fb_after_blank = True  # protect next line from action check
                    continue
                fb_prev_ended = True
                if fallback_lines:
                    fb_prev_last = fallback_lines[-1].rstrip()[-1:] if fallback_lines[-1].rstrip() else ''
                    fb_prev_ended = fb_prev_last in '.!?"\u201d'
                if not fb_first_line and not fb_after_blank and fb_prev_ended and is_action_line(dl):
                    break
                fallback_lines.append(dl)
                fb_first_line = False
                fb_after_blank = False
                j += 1
            if fallback_lines:
                fb_text = " ".join(fallback_lines)
                # Check if this text is already captured
                if fb_text not in found_texts:
                    # Find insertion point (maintain script order)
                    insert_idx = len(dialogue_blocks)
                    for di, db in enumerate(dialogue_blocks):
                        if db["line_idx"] > i:
                            insert_idx = di
                            break
                    dialogue_blocks.insert(insert_idx, {"speaker": extract_name(lines[i].strip()), "text": fb_text, "line_idx": j})
                    found_texts.add(fb_text)
                    logger.info(f"[PARSE] Fallback recovered line for {character_name}: '{fb_text[:50]}...'")
            i = j if fallback_lines else i + 1
        else:
            i += 1

    if not dialogue_blocks:
        return {"chunked_lines": [], "cue_recall": []}

    # Build cue_recall
    cue_recall = []
    for idx, block in enumerate(dialogue_blocks):
        if block["speaker"].upper() == char_upper or char_upper in block["speaker"].upper():
            if idx == 0:
                cue = "(Scene start)"
                cue_speaker = ""
            else:
                prev = dialogue_blocks[idx - 1]
                cue = f'{prev["speaker"]}: {prev["text"]}'
                cue_speaker = prev["speaker"].upper()
            cue_recall.append({
                "cue": cue,
                "your_line": block["text"],
                "cue_speaker": cue_speaker,
            })

    # Build chunked_lines
    char_lines = [b["text"] for b in dialogue_blocks if b["speaker"].upper() == char_upper or char_upper in b["speaker"].upper()]
    chunked_lines = []
    for ci in range(0, len(char_lines), 3):
        chunk = char_lines[ci:ci + 3]
        chunked_lines.append({
            "chunk_label": f"Chunk {ci // 3 + 1} ({len(chunk)} line{'s' if len(chunk) != 1 else ''})",
            "lines": "\n".join(chunk),
        })

    logger.info(f"[PARSE] Deterministic: {len(cue_recall)} lines for '{character_name}' (0 GPT calls)")
    return {"chunked_lines": chunked_lines, "cue_recall": cue_recall}


class ParseLinesRequest(BaseModel):
    text: str
    character_name: str


# --- Models ---
class AnalyzeTextRequest(BaseModel):
    text: str
    mode: Optional[str] = "quick"

class Beat(BaseModel):
    beat_number: int
    title: str
    description: str
    emotion: str
    subtext: str
    key_words: List[str] = []

class ActingTakes(BaseModel):
    grounded: str
    bold: str
    wildcard: str

class ChunkedLine(BaseModel):
    chunk_label: str
    lines: str

class CueRecall(BaseModel):
    cue: str
    your_line: str

class Memorization(BaseModel):
    chunked_lines: List[ChunkedLine]
    cue_recall: List[CueRecall]

class SelfTapeTips(BaseModel):
    framing: str
    eyeline: str
    tone_energy: str

class BreakdownResponse(BaseModel):
    id: str
    scene_summary: str
    character_name: str
    character_objective: str
    stakes: str
    beats: List[Beat]
    acting_takes: ActingTakes
    memorization: Memorization
    self_tape_tips: SelfTapeTips
    original_text: str
    created_at: str

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

class ParseScenesRequest(BaseModel):
    text: str
    character_name: str

class SceneInfo(BaseModel):
    scene_number: int
    heading: str
    preview: str
    characters: List[str]
    text: str
    has_character: bool

class BatchAnalyzeRequest(BaseModel):
    scenes: List[dict]  # [{scene_number, text, heading}]
    character_name: str
    mode: Optional[str] = "quick"

class SingleSceneRequest(BaseModel):
    script_id: str
    scene_number: int
    scene_heading: str
    text: str
    character_name: str
    mode: Optional[str] = "quick"
    prep_mode: Optional[str] = None  # "audition" | "booked" | "silent" | "study"
    project_type: Optional[str] = None  # "commercial" | "tvfilm" | "theatre" | "voiceover" | "vertical"

class CreateScriptRequest(BaseModel):
    character_name: str
    mode: Optional[str] = "quick"
    scene_count: int
    prep_mode: Optional[str] = None
    project_type: Optional[str] = None

class AdjustTakesRequest(BaseModel):
    adjustments: List[str]  # stacking list: ["tighten_pacing", "raise_stakes"]


class CheckCacheRequest(BaseModel):
    text: str
    mode: Optional[str] = "quick"
    character_name: Optional[str] = ""


class BatchCheckCacheRequest(BaseModel):
    scenes: List[dict]
    mode: Optional[str] = "quick"
    character_name: Optional[str] = ""


# --- Scene Parsing ---
def parse_scenes_regex(text: str) -> Optional[List[dict]]:
    """Split script text into scenes using standard screenplay markers, episode markers, or dividers."""
    # 1. Standard scene headers: INT./EXT./INT\/EXT./I/E.
    pattern = r'(?:^|\n)\s*((?:INT\.|EXT\.|INT/EXT\.|I/E\.)[\s\S]*?)(?=\n)'
    headers = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))

    if len(headers) < 2:
        # 2. Numbered scenes: "SCENE 1", "ACT TWO"
        pattern2 = r'(?:^|\n)\s*((?:SCENE\s+\d+|ACT\s+\w+)[\s\S]*?)(?=\n)'
        headers = list(re.finditer(pattern2, text, re.IGNORECASE | re.MULTILINE))

    if len(headers) < 2:
        # 3. Episode / chapter markers: "EPISODE 1", "EP 1", "EP. 1", "CHAPTER 1", "#1"
        pattern3 = r'(?:^|\n)\s*((?:EPISODE\s+\d+|EP\.?\s*\d+|CHAPTER\s+\d+|#\s*\d+)[\s\S]*?)(?=\n)'
        headers = list(re.finditer(pattern3, text, re.IGNORECASE | re.MULTILINE))

    if len(headers) < 2:
        return None  # Need GPT fallback

    scenes = []
    for i, match in enumerate(headers):
        start = match.start()
        end = headers[i + 1].start() if i < len(headers) - 1 else len(text)
        scene_text = text[start:end].strip()
        heading = match.group(1).strip()
        # Clean heading — take first line only
        heading = heading.split('\n')[0].strip()
        scenes.append({
            "scene_number": i + 1,
            "heading": heading,
            "text": scene_text,
        })

    return scenes


def detect_characters_in_scene(scene_text: str) -> List[str]:
    """Detect character names from screenplay dialogue cues (ALL CAPS names on their own line)."""
    lines = scene_text.split('\n')
    characters = set()
    skip_prefixes = ('INT', 'EXT', 'FADE', 'CUT TO', 'SCENE', 'ACT ', 'END ', 'CONTINUED', 'THE END', 'DISSOLVE')
    for line in lines:
        stripped = line.strip()
        # Character cue: mostly uppercase, possibly with (V.O.) (O.S.) (CONT'D)
        if not stripped or len(stripped) > 60:
            continue
        # Remove parentheticals
        name_clean = re.sub(r'\s*\(.*?\)\s*', '', stripped).strip()
        if not name_clean or len(name_clean) < 2:
            continue
        # Must be mostly uppercase letters/spaces
        if name_clean.isupper() and re.match(r'^[A-Z][A-Z\s\'./-]+$', name_clean):
            if not any(name_clean.startswith(p) for p in skip_prefixes):
                characters.add(name_clean)
    return sorted(characters)


def character_in_scene(scene_text: str, character_name: str) -> bool:
    """Check if a character appears in a scene (case-insensitive, checks dialogue cues and mentions)."""
    name_upper = character_name.upper().strip()
    characters = detect_characters_in_scene(scene_text)
    # Direct match in character cues
    for c in characters:
        if name_upper in c or c in name_upper:
            return True
    # Fallback: search in full text
    return bool(re.search(re.escape(character_name), scene_text, re.IGNORECASE))


SCENE_SPLIT_PROMPT = """You are a script parser. Given a full screenplay or script, split it into individual scenes.

RULES:
1. Each scene is a continuous block of action in one location/time.
2. A new scene starts when there's a clear change of location, time, or dramatic unit.
3. If there are INT./EXT. headers, use those as scene boundaries.
4. If there are no standard headers, identify natural scene breaks.

You MUST respond with valid JSON only. No markdown.

Return this exact structure:
{
  "scenes": [
    {
      "scene_number": 1,
      "heading": "Scene heading or brief location/context",
      "text": "Full text of this scene including dialogue and directions"
    }
  ]
}"""


# --- Prompts ---
QUICK_SYSTEM_PROMPT = """You are a working actor's script analyst. You break down audition sides into immediately playable notes. Everything you say must be PROVABLE from the text on the page.

RULES — read these before every response:
1. ONLY describe what is observable in the dialogue, stage directions, and character behavior ON THE PAGE.
2. Do NOT infer hidden emotions, guilt, shame, vulnerability, or backstory that isn't written.
3. If a character is cruel, play cruel. If they're dismissive, play dismissive. Do not soften or humanize beyond what the text supports.
4. Objectives must be ACTIVE VERBS describing what the character is doing TO the other person. Not feelings. Not states.
5. Beats track TACTIC SHIFTS — when the character changes what they're doing, not what they're talking about.
6. Subtext = what the line is doing tactically, not a therapy session about what they "really feel."
7. Acting takes must describe specific physical choices and line deliveries an actor can execute in 10 seconds.
8. NO emotional labels as descriptors. Not "cool contempt" or "authoritative satisfaction." Instead describe the BEHAVIOR: "dismisses her point without addressing it" or "reframes the situation to put himself in charge." Verbs, not adjectives.

You MUST respond with valid JSON only. No markdown.

{
  "scene_summary": "1-2 sentences. What is happening, what is at stake. Based only on what's written.",
  "character_name": "Name of the character the actor is reading for",
  "character_objective": "One active verb phrase: what are they trying to DO to the other person? e.g. 'To corner David into confessing' or 'To shut Sarah down before she can finish'",
  "stakes": "What happens if they fail at this objective? Stay concrete and text-based.",
  "beats": [
    {
      "beat_number": 1,
      "title": "Short title — name the tactic shift",
      "description": "What tactic is the character using HERE? What changed from the previous beat? Be specific about what they're DOING.",
      "behavior": "What the character is DOING in this beat — described as an action, not a feeling. e.g. 'Dismisses her explanation to stop her from building a case' or 'Cuts off her exit to maintain control of the conversation.'",
      "effect": "How this lands on the other person. What does it do to them? e.g. 'Forces her to defend instead of attack' or 'Takes away her option to leave.'",
      "subtext": "What this line/section is doing tactically. Not what they secretly feel — what the words are engineered to accomplish.",
      "key_words": ["word1", "word2"]
    }
  ],
  "acting_takes": {
    "grounded": "A naturalistic take. Specific physical direction: tempo, where tension lives in the body, breath. Reference specific lines. This should sound like a director's whisper, not a feeling description.",
    "bold": "A take that commits harder to what's on the page. If the character is aggressive, go MORE aggressive. If controlled, go ice cold. Specific line readings and physical choices.",
    "wildcard": "A surprising choice that's still TEXT-SUPPORTED. Not a different emotion — a different tactic for the same objective. Specific and committed."
  },
  "memorization": {
    "chunked_lines": [
      {"chunk_label": "Chunk 1: [context]", "lines": "Actual dialogue in breath groups (2-4 lines)"}
    ],
    "cue_recall": [
      {"cue": "Last thing said before your line", "your_line": "Your character's exact line"}
    ]
  },
  "self_tape_tips": {
    "framing": "Specific framing for this scene and why.",
    "eyeline": "Where to look and the tactical reason (not emotional reason).",
    "tone_energy": "Energy 1-10 with adjustments for this scene."
  }
}

Return ONLY valid JSON."""

DEEP_SYSTEM_PROMPT = """You are an elite scene analyst for working actors. You think like a director who trusts the text and doesn't invent psychology. Your job is to give actors a breakdown they can PERFORM — grounded in what's actually written.

CORE PRINCIPLE: Observable first, interpretation second.
- First: what is provably happening on the page (dialogue, actions, stage directions).
- Then: what this behavior reveals about tactics and objectives.
- NEVER: inferred guilt, shame, vulnerability, or emotional backstory that isn't in the text.

RULES — apply these to every field:
1. If a character is cruel, dominant, or manipulative ON THE PAGE — play that. Do not soften it, humanize it, or add hidden vulnerability that isn't written.
2. Objectives are ACTIVE VERBS about what the character is doing to the other person. "To punish," "to control," "to test," "to corner." NOT "to process feelings" or "to confront inner conflict."
3. Beats are TACTIC SHIFTS. A new beat starts when the character changes their method of pursuing the objective. Not when the topic changes.
4. Subtext describes what the line DOES, not what the character "really feels." A cruel line's subtext is what it's designed to accomplish — not hidden guilt.
5. Physical direction must be specific and executable. "Jaw tight, words clipped, weight forward" — not "a flicker of vulnerability."
6. If casting notes or context are provided, integrate them as constraints on your analysis — they tell you what the production wants, which should shape every choice.
7. NO emotional labels as descriptors. Not "cool contempt," "authoritative satisfaction," or "possessive command." Instead describe the BEHAVIOR: "dismisses her point without acknowledging it" or "physically blocks her exit." Use verbs that describe what the character DOES and how it LANDS on the other person.

You MUST respond with valid JSON only. No markdown.

{
  "scene_summary": "2-3 sentences. What is happening on the page? What is being fought over, risked, or decided? Text-based only.",
  "character_name": "Name of the character the actor is reading for",
  "character_objective": "Active verb phrase: what are they doing TO the other person through the entire scene? e.g. 'To dismantle Sarah's position until she has no ground left.' Must be provable from the dialogue.",
  "stakes": "What happens if they fail? Based on what's observable in the text — not inferred emotional consequences.",
  "emotional_arc": "Track what the character is DOING from first line to last. Not what they feel — what tactics they deploy, how those tactics escalate or shift, and what changes by the end. Describe in behavioral terms: 'starts by dismissing, escalates to reframing, ends by physically restraining.' No feeling words.",
  "what_they_hide": "What is the character actively working to keep OFF the table? This must be supported by the text — something they avoid saying, redirect away from, or refuse to acknowledge. If nothing is hidden, say 'Nothing — this character operates in the open.' Do NOT default to guilt/shame.",
  "beats": [
    {
      "beat_number": 1,
      "title": "Name the tactic, not the topic",
      "description": "What tactic is the character deploying? What changed from the previous beat? Be precise about the BEFORE and AFTER of this shift.",
      "behavior": "What the character is DOING in this beat — as an action verb. e.g. 'Dismisses her framing to deny her agency' or 'Grabs her arm to physically stop her from leaving.' NOT feeling labels like 'contempt' or 'frustration.'",
      "effect": "How this lands on the other person. What position does it put them in? e.g. 'Forces her onto the defensive' or 'Removes her ability to walk away.' Describe the tactical result.",
      "subtext_surface": "What the line appears to be saying.",
      "subtext_meaning": "What the line is tactically designed to DO to the other person.",
      "subtext_fear": "What happens if this tactic fails? What's the character trying to prevent? Must be text-supported. If nothing, say 'N/A.'",
      "key_words": ["word1", "word2"],
      "physical_life": "Specific body direction for this beat. Posture, breath, hands, weight, tension. Must be actable right now."
    }
  ],
  "acting_takes": {
    "grounded": "A naturalistic, text-faithful take. Direct the actor beat by beat: where to start, where to shift, where to land. Include tempo, physicality, breath, and specific line readings. Reference actual lines from the scene. Play what's written — if the character is hard, play hard.",
    "bold": "A take that commits even further to what the text supports. If the character dominates, go colder. If they charm, make it more dangerous. Specific physical commitments and line-level direction. NOT a softer version — a SHARPER one.",
    "wildcard": "A text-supported surprise. A different tactical read of the same objective that reframes how every line lands. e.g. 'What if he's already decided it's over, and every line is a formality?' Must be defensible from the page. Specific direction."
  },
  "memorization": {
    "chunked_lines": [
      {"chunk_label": "Chunk 1: [tactical context]", "lines": "2-4 lines of actual dialogue grouped by tactic"}
    ],
    "cue_recall": [
      {"cue": "Last thing said before your line", "your_line": "Your character's exact response"}
    ]
  },
  "self_tape_tips": {
    "framing": "Specific framing for this scene. What the camera needs to catch.",
    "eyeline": "Where to look, when to break, and the tactical reason for each.",
    "tone_energy": "Energy 1-10 with beat-by-beat adjustments. Where to start, peak, and land."
  }
}

Return ONLY valid JSON."""

REGENERATE_TAKES_PROMPT = """Acting coach. 3 NEW takes — specific, physical, immediately playable. No fluff.

Return ONLY valid JSON:
{
  "acting_takes": {
    "grounded": "Naturalistic: physicality, tempo, breath. Director's whisper.",
    "bold": "Pushes the scene — not louder, DIFFERENT. Specific anchor + physical life.",
    "wildcard": "Unexpected choice. Specific, committed, surprising."
  }
}"""


def parse_json_response(response_text):
    text = response_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError("Could not parse JSON from response")


async def analyze_with_gpt(text=None, image_base64=None, context=None, mode="quick"):
    """Core GPT call. mode='quick' truncates to ~2500 chars, mode='deep' allows ~8000. Returns (result_dict, raw_response_str)."""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise Exception("STAGE:gpt_init | LLM API key not configured in environment")

    is_deep = mode == "deep"
    max_chars = 8000 if is_deep else 2500
    system_prompt = DEEP_SYSTEM_PROMPT if is_deep else QUICK_SYSTEM_PROMPT

    if text and len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[...truncated — first ~{max_chars // 500} pages used]"
        logger.info(f"Truncated input text to {max_chars} chars (mode={mode})")

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
    except Exception as e:
        raise Exception(f"STAGE:gpt_init | Failed to create LLM chat: {e}")

    try:
        if image_base64:
            image_content = ImageContent(image_base64=image_base64)
            if is_deep:
                vision_prompt = "Extract ALL text from this audition sides image. Then provide a DEEP acting breakdown—focus on emotional truth, layered subtext, what the character hides, and the emotional arc across the scene. Include 'extracted_text' with the raw text."
            else:
                vision_prompt = "Extract ALL text from this audition sides image, then analyze it as a script. Provide the full acting breakdown. Also include a field 'extracted_text' with the raw text you read from the image."
            if context:
                vision_prompt = f"{context}\n{vision_prompt}"
            user_msg = UserMessage(
                text=vision_prompt,
                file_contents=[image_content]
            )
        else:
            if is_deep:
                prompt = f"Provide a DEEP acting breakdown of these audition sides. Focus on emotional truth, layered subtext, what the character is hiding, the emotional arc, and highly specific playable choices.\n\n{text}"
            else:
                prompt = f"Analyze these audition sides and provide a full acting breakdown:\n\n{text}"
            user_msg = UserMessage(text=prompt)
    except Exception as e:
        raise Exception(f"STAGE:gpt_message_build | Failed to build message: {e}")

    try:
        response = await chat.send_message(user_msg)
    except Exception as e:
        err_str = str(e).lower()
        if "budget" in err_str and "exceeded" in err_str:
            raise Exception("STAGE:gpt_call | LLM budget exceeded. Please add balance at Profile > Universal Key > Add Balance.")
        if "rate" in err_str and "limit" in err_str:
            raise Exception("STAGE:gpt_call | Rate limit reached. Please wait a moment and try again.")
        raise Exception(f"STAGE:gpt_call | GPT request failed: {e}")

    if not response or not response.strip():
        raise Exception("STAGE:gpt_call | GPT returned empty response")

    try:
        result = parse_json_response(response)
        return result, response
    except (ValueError, json.JSONDecodeError):
        raise Exception(f"STAGE:gpt_parse | Could not parse JSON from GPT response (first 300 chars): {response[:300]}")



# ============================================================
# PROJECT CRUD (Phase 1 — Audition-First MVP)
# ============================================================

class CreateProjectRequest(BaseModel):
    title: str
    role_name: Optional[str] = ""
    mode: str = "audition"  # "audition" | "booked"
    audition_date: Optional[str] = None
    audition_time: Optional[str] = None
    audition_format: Optional[str] = None  # "self-tape" | "in-person" | null


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    role_name: Optional[str] = None
    mode: Optional[str] = None
    audition_date: Optional[str] = None
    audition_time: Optional[str] = None
    audition_format: Optional[str] = None
    selected_character: Optional[str] = None


@api_router.post("/projects")
async def create_project(request: CreateProjectRequest):
    project = {
        "id": str(uuid.uuid4()),
        "title": request.title.strip(),
        "role_name": (request.role_name or "").strip(),
        "mode": request.mode,
        "selected_character": None,
        "audition_date": request.audition_date,
        "audition_time": request.audition_time,
        "audition_format": request.audition_format,
        "document_ids": [],
        "prep_output": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.projects.insert_one(project)
    project.pop("_id", None)
    return project


@api_router.get("/projects")
async def list_projects():
    cursor = db.projects.find({}, {"_id": 0}).sort("updated_at", -1)
    projects = await cursor.to_list(length=100)
    # Add document count for each project
    for p in projects:
        p["document_count"] = await db.documents.count_documents({"project_id": p["id"]})
    return projects


@api_router.get("/projects/{project_id}")
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Include documents
    docs = await db.documents.find({"project_id": project_id}, {"_id": 0}).to_list(length=50)
    project["documents"] = docs
    return project


@api_router.put("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    updates = {}
    for field in ["title", "role_name", "mode", "audition_date", "audition_time", "audition_format", "selected_character"]:
        val = getattr(request, field, None)
        if val is not None:
            updates[field] = val.strip() if isinstance(val, str) else val
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.projects.update_one({"id": project_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    return project


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Delete associated documents
    await db.documents.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id})
    return {"status": "deleted", "project_id": project_id}



# ============================================================
# DOCUMENT UPLOAD & MANAGEMENT (Phase 1 — Feature #2)
# ============================================================

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@api_router.post("/projects/{project_id}/documents")
async def upload_document(
    project_id: str,
    file: UploadFile = File(None),
    pasted_text: Optional[str] = Form(None),
    doc_type: Optional[str] = Form("unknown"),
):
    """Upload a document (PDF, image) or paste text. Extracts text and attaches to project."""
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check document limit
    existing_count = await db.documents.count_documents({"project_id": project_id})
    if existing_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 documents per project.")

    doc_id = str(uuid.uuid4())
    filename = ""
    file_url = ""
    original_text = ""
    extraction_method = ""

    if file and file.filename:
        # File upload path
        try:
            contents = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File must be under 20MB.")
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File is empty.")

        filename = file.filename or "unnamed"
        file_type = detect_file_type(file.content_type, file.filename, contents)

        # Save original file
        safe_name = f"{doc_id}_{filename.replace('/', '_')}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(file_path, "wb") as f:
            f.write(contents)
        file_url = f"/uploads/{safe_name}"

        # Extract text
        if file_type == "pdf":
            extraction_method = "pdf"
            try:
                from PyPDF2 import PdfReader
                pdf_reader = PdfReader(io.BytesIO(contents))
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        original_text += page_text + "\n"
                original_text = original_text.strip()
            except Exception as e:
                logger.error(f"[doc-upload] PDF text extraction failed: {e}")

            # Fallback to Vision OCR if text too short
            if len(original_text) < 30:
                extraction_method = "pdf_ocr"
                try:
                    page_images = pdf_pages_to_images(contents, max_pages=10, dpi=200)
                    api_key = os.environ.get('EMERGENT_LLM_KEY')
                    if api_key:
                        all_page_text = []
                        for page_num, page_jpeg in enumerate(page_images):
                            b64 = base64.b64encode(page_jpeg).decode('utf-8')
                            try:
                                ocr_chat = LlmChat(
                                    api_key=api_key,
                                    session_id=str(uuid.uuid4()),
                                    system_message="Extract ALL text from this image exactly as written. Preserve line breaks, character names, stage directions, and formatting. Return only the extracted text, nothing else."
                                ).with_model("openai", "gpt-5.2")
                                ocr_msg = UserMessage(
                                    text="Extract all text from this script page.",
                                    file_contents=[ImageContent(image_base64=b64)]
                                )
                                page_text = await asyncio.wait_for(ocr_chat.send_message(ocr_msg), timeout=60)
                                all_page_text.append(page_text.strip())
                            except Exception as e:
                                logger.warning(f"[doc-upload] Page {page_num+1} OCR failed: {e}")
                                all_page_text.append(f"[Page {page_num+1}: OCR failed]")
                        original_text = "\n\n".join(all_page_text)
                except Exception as e:
                    logger.error(f"[doc-upload] PDF OCR fallback failed: {e}")

        elif file_type == "image":
            extraction_method = "image_ocr"
            try:
                img_bytes = prepare_image_for_vision(contents)
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                api_key = os.environ.get('EMERGENT_LLM_KEY')
                if api_key:
                    ocr_chat = LlmChat(
                        api_key=api_key,
                        session_id=str(uuid.uuid4()),
                        system_message="Extract ALL text from this image exactly as written. Preserve line breaks, character names, stage directions, and formatting. Return only the extracted text, nothing else."
                    ).with_model("openai", "gpt-5.2")
                    ocr_msg = UserMessage(
                        text="Extract all text from this script page.",
                        file_contents=[ImageContent(image_base64=b64)]
                    )
                    original_text = await asyncio.wait_for(ocr_chat.send_message(ocr_msg), timeout=60)
                    original_text = original_text.strip()
            except Exception as e:
                logger.error(f"[doc-upload] Image OCR failed: {e}")
                raise HTTPException(status_code=500, detail=f"Could not extract text from image: {e}")
        else:
            # Try to read as plain text
            extraction_method = "text"
            try:
                original_text = contents.decode("utf-8").strip()
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF, image, or text file.")

    elif pasted_text and pasted_text.strip():
        # Pasted text path
        filename = "pasted_text.txt"
        original_text = pasted_text.strip()
        extraction_method = "paste"
    else:
        raise HTTPException(status_code=400, detail="Provide a file or pasted text.")

    # Validate we got text
    if len(original_text) < 5:
        raise HTTPException(status_code=400, detail="Could not extract enough text. Try a clearer file or paste the text manually.")

    # Validate doc_type
    valid_types = {"sides", "instructions", "wardrobe", "notes", "reference", "unknown"}
    if doc_type not in valid_types:
        doc_type = "unknown"

    # Create document record
    doc = {
        "id": doc_id,
        "project_id": project_id,
        "type": doc_type,
        "filename": filename,
        "original_text": original_text,
        "cleaned_text": None,
        "is_confirmed": False,
        "file_url": file_url,
        "extraction_method": extraction_method,
        "char_count": len(original_text),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)

    # Add document ID to project
    await db.projects.update_one(
        {"id": project_id},
        {
            "$push": {"document_ids": doc_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )

    logger.info(f"[doc-upload] Saved doc {doc_id[:12]} for project {project_id[:12]}: {filename}, {len(original_text)} chars, method={extraction_method}")
    return doc


@api_router.get("/projects/{project_id}/documents")
async def list_project_documents(project_id: str):
    """List all documents for a project."""
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    docs = await db.documents.find(
        {"project_id": project_id},
        {"_id": 0, "original_text": 0},  # Exclude large text from list
    ).to_list(length=50)
    return docs


@api_router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a single document with full text."""
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@api_router.put("/documents/{doc_id}/type")
async def update_document_type(doc_id: str, request: dict):
    """Update the document type (user override)."""
    new_type = request.get("type", "unknown")
    valid_types = {"sides", "instructions", "wardrobe", "notes", "reference", "unknown"}
    if new_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {', '.join(valid_types)}")
    result = await db.documents.update_one({"id": doc_id}, {"$set": {"type": new_type}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "ok", "type": new_type}


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and remove from project."""
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Remove from project's document_ids
    await db.projects.update_one(
        {"id": doc.get("project_id")},
        {
            "$pull": {"document_ids": doc_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    # Delete file if exists
    if doc.get("file_url"):
        file_path = os.path.join(UPLOAD_DIR, os.path.basename(doc["file_url"]))
        if os.path.exists(file_path):
            os.remove(file_path)
    await db.documents.delete_one({"id": doc_id})
    return {"status": "deleted", "doc_id": doc_id}




# --- Endpoints ---
@api_router.get("/")
async def root():
    return {"message": "Actor's Companion API"}


@api_router.get("/debug/pipeline")
async def debug_pipeline():
    """Test each stage of the analysis pipeline independently.
    Hit this from the browser to see exactly what's working and what isn't."""
    results = {}

    # 1. Check LLM key
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    results["llm_key"] = {"ok": bool(api_key), "value": f"{api_key[:8]}..." if api_key else "MISSING"}

    # 2. LLM readiness (no GPT call — saves credits)
    results["gpt_ready"] = {"ok": bool(api_key), "note": "Key present, no test call (cost savings)"}

    # 2b. Cache stats
    try:
        cache_count = await db.breakdown_cache.count_documents({})
        results["cache"] = {"ok": True, "cached_breakdowns": cache_count, "version": CACHE_VERSION, "ttl_hours": CACHE_TTL_HOURS}
    except Exception as e:
        results["cache"] = {"ok": False, "error": str(e)}

    # 3. Test MongoDB
    try:
        count = await db.breakdowns.count_documents({})
        results["mongodb"] = {"ok": True, "breakdown_count": count}
    except Exception as e:
        results["mongodb"] = {"ok": False, "error": str(e)}

    # 4. Test image processing
    try:
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (100, 100), (255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        results["image_processing"] = {"ok": True, "pillow_version": PILImage.__version__}
    except Exception as e:
        results["image_processing"] = {"ok": False, "error": str(e)}

    # 5. HEIC support
    try:
        from pillow_heif import register_heif_opener
        results["heic_support"] = {"ok": True}
    except ImportError:
        results["heic_support"] = {"ok": False, "error": "pillow-heif not installed"}

    # 6. PDF support
    try:
        from PyPDF2 import PdfReader
        results["pdf_text_support"] = {"ok": True}
    except ImportError:
        results["pdf_text_support"] = {"ok": False, "error": "PyPDF2 not installed"}

    # 7. PDF-to-image (scanned PDF) support
    try:
        import pymupdf
        results["pdf_image_support"] = {"ok": True, "pymupdf_version": pymupdf.version[0]}
    except ImportError:
        results["pdf_image_support"] = {"ok": False, "error": "pymupdf not installed"}

    all_ok = all(r.get("ok") for r in results.values())
    return {"all_ok": all_ok, "stages": results}


@api_router.post("/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    """Extract text from a PDF or image file without analyzing it. Used by Full Script mode."""
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 20MB.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    file_type = detect_file_type(file.content_type, file.filename, contents)
    logger.info(f"[extract-text] File: {file.filename}, type: {file_type}, size: {len(contents)/1024:.0f}KB")

    extracted_text = ""

    if file_type == "pdf":
        try:
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(io.BytesIO(contents))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            extracted_text = extracted_text.strip()
            logger.info(f"[extract-text] PDF text: {len(extracted_text)} chars, {len(pdf_reader.pages)} pages")
        except Exception as e:
            logger.error(f"[extract-text] PDF text extraction failed: {e}")

        if len(extracted_text) < 30:
            logger.info("[extract-text] PDF text too short, using Vision OCR")
            try:
                page_images = pdf_pages_to_images(contents, max_pages=10, dpi=200)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Could not process PDF: {e}")

            all_page_text = []
            api_key = os.environ.get('EMERGENT_LLM_KEY')
            if not api_key:
                raise HTTPException(status_code=500, detail="LLM API key not configured")

            for page_num, page_jpeg in enumerate(page_images):
                b64 = base64.b64encode(page_jpeg).decode('utf-8')
                try:
                    ocr_chat = LlmChat(
                        api_key=api_key,
                        session_id=str(uuid.uuid4()),
                        system_message="Extract ALL text from this image exactly as written. Preserve line breaks, character names, stage directions, and formatting. Return only the extracted text, nothing else."
                    ).with_model("openai", "gpt-5.2")
                    ocr_msg = UserMessage(
                        text="Extract all text from this script page.",
                        file_contents=[ImageContent(image_base64=b64)]
                    )
                    page_text = await asyncio.wait_for(ocr_chat.send_message(ocr_msg), timeout=60)
                    all_page_text.append(page_text.strip())
                    logger.info(f"[extract-text] Page {page_num+1} OCR: {len(page_text)} chars")
                except Exception as e:
                    logger.warning(f"[extract-text] Page {page_num+1} OCR failed: {e}")
                    all_page_text.append(f"[Page {page_num+1}: OCR failed]")

            extracted_text = "\n\n".join(all_page_text)

    elif file_type == "image":
        try:
            img_bytes = prepare_image_for_vision(contents)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image processing failed: {e}")

        b64 = base64.b64encode(img_bytes).decode('utf-8')
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="LLM API key not configured")

        try:
            ocr_chat = LlmChat(
                api_key=api_key,
                session_id=str(uuid.uuid4()),
                system_message="Extract ALL text from this image exactly as written. Preserve line breaks, character names, stage directions, and formatting. Return only the extracted text, nothing else."
            ).with_model("openai", "gpt-5.2")
            ocr_msg = UserMessage(
                text="Extract all text from this script page.",
                file_contents=[ImageContent(image_base64=b64)]
            )
            extracted_text = await asyncio.wait_for(ocr_chat.send_message(ocr_msg), timeout=60)
            extracted_text = extracted_text.strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed: {e}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF or image.")

    if len(extracted_text) < 10:
        raise HTTPException(status_code=400, detail="Could not extract enough text from this file. Try a clearer scan or paste the text manually.")

    logger.info(f"[extract-text] Complete: {len(extracted_text)} chars extracted")
    return {"text": extracted_text, "chars": len(extracted_text)}


@api_router.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    stages = []  # track what happened at each stage

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide at least a few lines of dialogue")

    mode = request.mode or "quick"
    input_text = request.text[:SCENE_TEXT_HARD_CAP] if len(request.text) > SCENE_TEXT_HARD_CAP else request.text
    if len(request.text) > SCENE_TEXT_HARD_CAP:
        logger.info(f"[COST] Text hard-capped: {len(request.text)} -> {SCENE_TEXT_HARD_CAP} chars")
    stages.append({"stage": "input_received", "ok": True, "chars": len(input_text), "mode": mode})
    logger.info(f"[analyze/text] Input: {len(input_text)} chars, mode={mode}")

    # Check cache first
    cache_key = compute_cache_key(input_text, mode)
    cached_result = await get_cached_breakdown(cache_key)
    if cached_result:
        stages.append({"stage": "cache_hit", "ok": True})
        breakdown_id = str(uuid.uuid4())
        doc = {
            "id": breakdown_id,
            "original_text": input_text,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "from_cache": True,
            **cached_result
        }
        await db.breakdowns.insert_one(doc)
        stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
        stages.append({"stage": "db_save", "ok": True})
        stored["_debug"] = {"stages": stages, "fallback": False, "cached": True}
        logger.info("[COST] Served from cache — 0 GPT calls, $0.00")
        return stored

    # GPT call with timeout (deep gets more time)
    logger.info(f"[COST] Cache miss — GPT call (est. ${estimate_cost(mode):.2f})")
    gpt_timeout = 120 if mode == "deep" else 90
    try:
        result, raw = await asyncio.wait_for(
            analyze_with_gpt(text=input_text, mode=mode),
            timeout=gpt_timeout
        )
        stages.append({"stage": "gpt_analysis", "ok": True})

        # Override GPT memorization with deterministic extraction if character found
        gpt_char = result.get("character_name", "")
        if gpt_char:
            det_mem = extract_character_lines(input_text, gpt_char)
            if det_mem["cue_recall"]:
                result["memorization"] = det_mem
                stages.append({"stage": "deterministic_lines", "ok": True, "lines": len(det_mem["cue_recall"])})
    except asyncio.TimeoutError:
        stages.append({"stage": "gpt_analysis", "ok": False, "error": "Timed out after 90s"})
        logger.error("[analyze/text] GPT timed out")
        return {
            "id": str(uuid.uuid4()),
            "original_text": input_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scene_summary": "Analysis timed out — text captured below.",
            "character_name": "Unknown",
            "character_objective": "", "stakes": "",
            "beats": [], "acting_takes": {"grounded": "", "bold": "", "wildcard": ""},
            "memorization": {"chunked_lines": [], "cue_recall": []},
            "self_tape_tips": {"framing": "", "eyeline": "", "tone_energy": ""},
            "_debug": {"stages": stages, "fallback": True, "reason": "timeout"}
        }
    except Exception as e:
        error_str = str(e)
        stages.append({"stage": "gpt_analysis", "ok": False, "error": error_str})
        logger.error(f"[analyze/text] GPT error: {error_str}")
        return {
            "id": str(uuid.uuid4()),
            "original_text": input_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scene_summary": "Analysis failed — your text was saved. See error details.",
            "character_name": "Unknown",
            "character_objective": "", "stakes": "",
            "beats": [], "acting_takes": {"grounded": "", "bold": "", "wildcard": ""},
            "memorization": {"chunked_lines": [], "cue_recall": []},
            "self_tape_tips": {"framing": "", "eyeline": "", "tone_energy": ""},
            "_debug": {"stages": stages, "fallback": True, "reason": error_str}
        }

    # Cache result for future reuse
    await store_cached_breakdown(cache_key, result, mode)
    logger.info(f"[COST] GPT call complete — 1 call, est. ${estimate_cost(mode):.2f}")

    # Save to DB
    breakdown_id = str(uuid.uuid4())
    doc = {
        "id": breakdown_id,
        "original_text": input_text,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **result
    }
    await db.breakdowns.insert_one(doc)
    stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    stages.append({"stage": "db_save", "ok": True})
    stored["_debug"] = {"stages": stages, "fallback": False}
    return stored


def prepare_image_for_vision(raw_bytes: bytes, filename: str = "") -> bytes:
    """Convert any image (including HEIC) to JPEG, resize if large.
    Returns JPEG bytes ready for base64 encoding."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception:
        raise ValueError("Could not open file as an image")

    # Convert to RGB (handles RGBA, HEIC palettes, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize if any dimension exceeds 2048px — keeps quality, reduces payload
    max_dim = 2048
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        logger.info(f"Resized image to {img.size}")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


def pdf_pages_to_images(pdf_bytes: bytes, max_pages: int = 5, dpi: int = 200) -> list[bytes]:
    """Render PDF pages to JPEG images using pymupdf.
    Returns a list of JPEG byte strings (one per page, up to max_pages)."""
    import pymupdf
    jpeg_list = []
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        page_count = min(len(doc), max_pages)
        logger.info(f"[pdf_to_images] Rendering {page_count}/{len(doc)} pages at {dpi}dpi")
        for i in range(page_count):
            page = doc[i]
            # Render at specified DPI
            zoom = dpi / 72
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # Resize if too large
            max_dim = 2048
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            jpeg_list.append(buf.getvalue())
            logger.info(f"[pdf_to_images] Page {i+1}: {len(jpeg_list[-1])/1024:.0f}KB")
        doc.close()
    except Exception as e:
        logger.error(f"[pdf_to_images] pymupdf render failed: {e}")
        raise ValueError(f"PDF rendering failed: {e}")
    if not jpeg_list:
        raise ValueError("PDF had no renderable pages")
    return jpeg_list


def detect_file_type(content_type: str, filename: str, raw_bytes: bytes) -> str:
    """Determine if a file is 'pdf', 'image', or 'unknown'.
    Handles iOS edge cases where content_type is empty or generic."""
    ct = (content_type or "").lower().strip()
    fn = (filename or "").lower().strip()

    # Explicit PDF
    if ct == "application/pdf" or fn.endswith(".pdf"):
        return "pdf"
    # PDF magic bytes
    if raw_bytes[:5] == b"%PDF-":
        return "pdf"

    # Explicit image MIME
    if ct.startswith("image/"):
        return "image"

    # Known image extensions
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".bmp", ".tiff", ".tif"}
    if any(fn.endswith(ext) for ext in image_exts):
        return "image"

    # iOS often sends application/octet-stream or empty type for camera photos
    if ct in ("", "application/octet-stream") and raw_bytes:
        # Try to open as image
        try:
            Image.open(io.BytesIO(raw_bytes))
            return "image"
        except Exception:
            pass

    return "unknown"


@api_router.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...), context: Optional[str] = Form(None), mode: Optional[str] = Form("quick")):
    stages = []
    mode = mode or "quick"

    # Stage 1: Read file
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"[analyze/image] File read error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    file_size_mb = len(contents) / (1024 * 1024)
    file_info = {"name": file.filename, "content_type": file.content_type, "size_mb": round(file_size_mb, 2), "bytes": len(contents), "mode": mode}
    stages.append({"stage": "file_received", "ok": True, **file_info})
    logger.info(f"[analyze/image] File received: {file_info}")

    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File is {file_size_mb:.1f}MB — must be under 20MB.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    context_prefix = ""
    if context and context.strip():
        context_prefix = f"[CONTEXT FOR ANALYSIS]\n{context.strip()}\n\n"

    # Stage 2: Detect file type
    file_type = detect_file_type(file.content_type, file.filename, contents)
    stages.append({"stage": "type_detection", "ok": True, "detected": file_type})
    logger.info(f"[analyze/image] Detected type: {file_type}")

    extracted_text = None

    # Stage 3a: PDF — extract text
    if file_type == "pdf":
        try:
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(io.BytesIO(contents))
            extracted_text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            extracted_text = extracted_text.strip()
            stages.append({"stage": "pdf_extract", "ok": True, "chars": len(extracted_text), "pages": len(pdf_reader.pages)})
            logger.info(f"[analyze/image] PDF extracted: {len(extracted_text)} chars, {len(pdf_reader.pages)} pages")
        except Exception as e:
            stages.append({"stage": "pdf_extract", "ok": False, "error": str(e)})
            logger.error(f"[analyze/image] PDF extract failed: {e}")
            return _fallback_response(None, stages, f"PDF read failed: {e}")

        if len(extracted_text) < 10:
            stages.append({"stage": "pdf_text_check", "ok": False, "error": "Too little text extracted, converting pages to images"})
            logger.info("[analyze/image] PDF text too short, rendering pages as images for vision OCR")
            try:
                page_images = pdf_pages_to_images(contents, max_pages=5, dpi=200)
                stages.append({"stage": "pdf_to_images", "ok": True, "pages_rendered": len(page_images), "total_kb": round(sum(len(p) for p in page_images) / 1024, 1)})
            except ValueError as e:
                stages.append({"stage": "pdf_to_images", "ok": False, "error": str(e)})
                return _fallback_response(None, stages, f"Scanned PDF could not be converted to images: {e}")

            # OCR each page via Vision, then concatenate text
            all_page_text = []
            for page_num, page_jpeg in enumerate(page_images):
                b64 = base64.b64encode(page_jpeg).decode('utf-8')
                try:
                    api_key = os.environ.get('EMERGENT_LLM_KEY')
                    ocr_chat = LlmChat(
                        api_key=api_key,
                        session_id=str(uuid.uuid4()),
                        system_message="Extract ALL text from this image exactly as written. Preserve line breaks, character names, stage directions, and formatting. Return only the extracted text, nothing else."
                    ).with_model("openai", "gpt-5.2")
                    ocr_msg = UserMessage(
                        text="Extract all text from this script page.",
                        file_contents=[ImageContent(image_base64=b64)]
                    )
                    page_text = await asyncio.wait_for(ocr_chat.send_message(ocr_msg), timeout=60)
                    all_page_text.append(page_text.strip())
                    logger.info(f"[analyze/image] Page {page_num+1} OCR: {len(page_text)} chars")
                except Exception as e:
                    logger.warning(f"[analyze/image] Page {page_num+1} OCR failed: {e}")
                    all_page_text.append(f"[Page {page_num+1}: OCR failed]")

            combined_text = "\n\n".join(all_page_text)
            stages.append({"stage": "ocr_complete", "ok": True, "total_chars": len(combined_text), "pages_ocrd": len(all_page_text)})
            logger.info(f"[analyze/image] OCR complete: {len(combined_text)} chars from {len(all_page_text)} pages")

            # Now analyze the combined OCR text
            full_text = context_prefix + combined_text if context_prefix else combined_text
            gpt_timeout = 120 if mode == "deep" else 90
            try:
                result, raw = await asyncio.wait_for(
                    analyze_with_gpt(text=full_text, mode=mode),
                    timeout=gpt_timeout
                )
                stages.append({"stage": "gpt_analysis", "ok": True})
            except asyncio.TimeoutError:
                stages.append({"stage": "gpt_analysis", "ok": False, "error": "Timed out"})
                return _fallback_response(combined_text, stages, "GPT timed out analyzing OCR text")
            except Exception as e:
                stages.append({"stage": "gpt_analysis", "ok": False, "error": str(e)})
                return _fallback_response(combined_text, stages, str(e))

            breakdown_id = str(uuid.uuid4())
            doc = {
                "id": breakdown_id,
                "original_text": combined_text,
                "mode": mode,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **result
            }
            await db.breakdowns.insert_one(doc)
            stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
            stages.append({"stage": "db_save", "ok": True})
            stored["_debug"] = {"stages": stages, "fallback": False}
            return stored
        else:
            # Text extraction worked — send to GPT
            full_text = context_prefix + extracted_text if context_prefix else extracted_text
            gpt_timeout = 120 if mode == "deep" else 90
            try:
                result, raw = await asyncio.wait_for(
                    analyze_with_gpt(text=full_text, mode=mode),
                    timeout=gpt_timeout
                )
                stages.append({"stage": "gpt_analysis", "ok": True})
            except asyncio.TimeoutError:
                stages.append({"stage": "gpt_analysis", "ok": False, "error": "Timed out after 90s"})
                return _fallback_response(extracted_text, stages, "GPT timed out on PDF text")
            except Exception as e:
                stages.append({"stage": "gpt_analysis", "ok": False, "error": str(e)})
                return _fallback_response(extracted_text, stages, str(e))

            breakdown_id = str(uuid.uuid4())
            doc = {
                "id": breakdown_id,
                "original_text": extracted_text,
                "mode": mode,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **result
            }
            await db.breakdowns.insert_one(doc)
            stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
            stages.append({"stage": "db_save", "ok": True})
            stored["_debug"] = {"stages": stages, "fallback": False}
            return stored

    # Stage 3b: Image — convert/compress then GPT Vision
    if file_type == "image":
        try:
            jpeg_bytes = prepare_image_for_vision(contents, file.filename)
            stages.append({"stage": "image_convert", "ok": True, "jpeg_kb": round(len(jpeg_bytes) / 1024, 1)})
            logger.info(f"[analyze/image] Image converted: {len(jpeg_bytes)/1024:.0f}KB JPEG")
        except ValueError as e:
            stages.append({"stage": "image_convert", "ok": False, "error": str(e)})
            logger.error(f"[analyze/image] Image conversion failed: {e}")
            return _fallback_response(None, stages, f"Image processing failed: {e}")

        base64_image = base64.b64encode(jpeg_bytes).decode('utf-8')
        gpt_timeout = 120 if mode == "deep" else 90
        try:
            result, raw = await asyncio.wait_for(
                analyze_with_gpt(image_base64=base64_image, context=context_prefix if context_prefix else None, mode=mode),
                timeout=gpt_timeout
            )
            stages.append({"stage": "gpt_vision", "ok": True})
        except asyncio.TimeoutError:
            stages.append({"stage": "gpt_vision", "ok": False, "error": "Timed out after 90s"})
            return _fallback_response(None, stages, "GPT Vision timed out")
        except Exception as e:
            stages.append({"stage": "gpt_vision", "ok": False, "error": str(e)})
            return _fallback_response(None, stages, str(e))

        breakdown_id = str(uuid.uuid4())
        original_text = result.pop("extracted_text", "Image analysis")
        doc = {
            "id": breakdown_id,
            "original_text": original_text,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **result
        }
        await db.breakdowns.insert_one(doc)
        stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
        stages.append({"stage": "db_save", "ok": True})
        stored["_debug"] = {"stages": stages, "fallback": False}
        return stored

    # Stage 3c: Unknown type
    stages.append({"stage": "type_detection", "ok": False, "error": f"Unrecognized type: {file.content_type}"})
    return _fallback_response(None, stages, f"Couldn't identify file type (received: {file.content_type or 'none'})")


def _fallback_response(extracted_text: str | None, stages: list, reason: str):
    """Return a partial response instead of a hard failure.
    Always includes debug stages so frontend can show what went wrong."""
    logger.warning(f"[fallback] {reason}")
    return {
        "id": str(uuid.uuid4()),
        "original_text": extracted_text or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scene_summary": f"Analysis incomplete — {reason.split('|')[-1].strip() if '|' in reason else reason}",
        "character_name": "Unknown",
        "character_objective": "", "stakes": "",
        "beats": [], "acting_takes": {"grounded": "", "bold": "", "wildcard": ""},
        "memorization": {"chunked_lines": [], "cue_recall": []},
        "self_tape_tips": {"framing": "", "eyeline": "", "tone_energy": ""},
        "_debug": {"stages": stages, "fallback": True, "reason": reason}
    }


@api_router.post("/regenerate-takes/{breakdown_id}")
async def regenerate_takes(breakdown_id: str):
    breakdown = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")

    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=REGENERATE_TAKES_PROMPT
    ).with_model("openai", "gpt-5.2")

    scene_excerpt = breakdown['original_text'][:3000]
    user_msg = UserMessage(
        text=f"Generate 3 new acting takes for:\n\n{scene_excerpt}"
    )
    response = await chat.send_message(user_msg)

    try:
        result = parse_json_response(response)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Failed to parse AI response")

    new_takes = result.get("acting_takes", {})
    await db.breakdowns.update_one(
        {"id": breakdown_id},
        {"$set": {"acting_takes": new_takes}}
    )
    updated = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    return updated


ADJUSTMENT_LABELS = {
    "tighten_pacing": "Tighten the pacing — make it faster, more urgent, cut the fat",
    "emotional_depth": "Add emotional depth — find the deeper undercurrent, let the vulnerability surface through behavior",
    "more_natural": "Make it more natural — less performed, more conversational, like they're not even acting",
    "raise_stakes": "Raise the stakes — this moment matters more than the actor thinks. Make every word count like it could change everything",
    "play_opposite": "Play the opposite — flip the obvious read. If the scene reads angry, play it calm. If sad, play it amused. Find the unexpected truth",
}

ADJUST_TAKES_PROMPT = """Refine these takes with the adjustments below. Stack all adjustments onto each take. Keep core identity (grounded/bold/wildcard). Be specific, physical, concise — director's whisper, not a lecture.

PREVIOUS TAKES:
{previous_takes}

ADJUSTMENTS:
{adjustments}

Return ONLY valid JSON:
{{
  "acting_takes": {{
    "grounded": "Refined direction with all adjustments",
    "bold": "Refined direction with all adjustments",
    "wildcard": "Refined direction with all adjustments"
  }}
}}"""


@api_router.post("/adjust-takes/{breakdown_id}")
async def adjust_takes(breakdown_id: str, request: AdjustTakesRequest):
    """Adjust acting takes based on stacking actor feedback."""
    breakdown = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")

    if not request.adjustments:
        raise HTTPException(status_code=400, detail="No adjustments provided")

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")

    # Build previous takes string
    takes = breakdown.get("acting_takes", {})
    prev_takes = f"Grounded: {takes.get('grounded', 'N/A')}\nBold: {takes.get('bold', 'N/A')}\nWildcard: {takes.get('wildcard', 'N/A')}"

    # Build adjustment descriptions
    adj_lines = []
    for i, adj_id in enumerate(request.adjustments, 1):
        label = ADJUSTMENT_LABELS.get(adj_id, adj_id)
        adj_lines.append(f"{i}. {label}")
    adjustments_text = "\n".join(adj_lines)

    prompt = ADJUST_TAKES_PROMPT.format(
        previous_takes=prev_takes,
        adjustments=adjustments_text,
    )

    logger.info(f"[adjust-takes] Breakdown {breakdown_id}, adjustments: {request.adjustments}")

    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=prompt
    ).with_model("openai", "gpt-5.2")

    user_msg = UserMessage(
        text=f"Here's the scene:\n\n{breakdown['original_text'][:3000]}\n\nRefine the takes with the adjustments above."
    )

    try:
        response = await asyncio.wait_for(chat.send_message(user_msg), timeout=60)
        result = parse_json_response(response)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Adjustment timed out. Try again.")
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Failed to parse adjusted takes")

    new_takes = result.get("acting_takes", {})
    # Store adjustment history
    history = breakdown.get("adjustment_history", [])
    history.append({
        "adjustments": request.adjustments,
        "previous_takes": takes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await db.breakdowns.update_one(
        {"id": breakdown_id},
        {"$set": {"acting_takes": new_takes, "adjustment_history": history}}
    )
    updated = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    return updated


@api_router.get("/breakdowns/{breakdown_id}")
async def get_breakdown(breakdown_id: str):
    breakdown = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return breakdown


@api_router.get("/breakdowns")
async def list_breakdowns():
    results = await db.breakdowns.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return results


# --- Full Script: Scene Parsing & Batch Analysis ---

@api_router.post("/parse-scenes")
async def parse_scenes(request: ParseScenesRequest):
    """Parse a full script into scenes and identify which ones contain the specified character."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Script text cannot be empty")
    if not request.character_name.strip():
        raise HTTPException(status_code=400, detail="Character name is required")

    character_name = request.character_name.strip()
    script_text = request.text.strip()
    logger.info(f"[parse-scenes] Parsing {len(script_text)} chars for character: {character_name}")

    # Step 1: Try regex-based scene splitting
    scenes = parse_scenes_regex(script_text)

    # Step 2: If regex fails, use GPT to split
    if not scenes:
        logger.info("[parse-scenes] Regex found <2 scenes, using GPT fallback")
        try:
            api_key = os.environ.get('EMERGENT_LLM_KEY')
            if not api_key:
                raise Exception("LLM API key not configured")

            # Truncate for GPT if very long
            gpt_text = script_text[:15000] if len(script_text) > 15000 else script_text

            chat = LlmChat(
                api_key=api_key,
                session_id=str(uuid.uuid4()),
                system_message=SCENE_SPLIT_PROMPT
            ).with_model("openai", "gpt-5.2")

            response = await asyncio.wait_for(
                chat.send_message(UserMessage(text=f"Split this script into scenes:\n\n{gpt_text}")),
                timeout=60
            )
            parsed = parse_json_response(response)
            scenes = parsed.get("scenes", [])
            # Ensure scene_number is set
            for i, s in enumerate(scenes):
                s.setdefault("scene_number", i + 1)
                s.setdefault("heading", f"Scene {i + 1}")
        except Exception as e:
            logger.error(f"[parse-scenes] GPT fallback failed: {e}")
            # Last resort: treat entire text as one scene
            scenes = [{
                "scene_number": 1,
                "heading": "Full Script",
                "text": script_text,
            }]

    # Step 3: Enrich each scene with character detection and preview
    enriched = []
    for scene in scenes:
        scene_text = scene.get("text", "")
        characters = detect_characters_in_scene(scene_text)
        has_char = character_in_scene(scene_text, character_name)

        # Generate preview: first 2 lines of dialogue or text, max 150 chars
        lines = [ln.strip() for ln in scene_text.split('\n') if ln.strip()]
        preview_lines = lines[1:4] if len(lines) > 1 else lines[:3]  # Skip heading
        preview = ' / '.join(preview_lines)[:150]

        enriched.append({
            "scene_number": scene.get("scene_number", 0),
            "heading": scene.get("heading", f"Scene {scene.get('scene_number', '?')}"),
            "preview": preview,
            "characters": characters,
            "text": scene_text,
            "has_character": has_char,
            "line_count": len(lines),
        })

    character_scenes = [s for s in enriched if s["has_character"]]
    logger.info(f"[parse-scenes] Found {len(enriched)} total scenes, {len(character_scenes)} with {character_name}")

    return {
        "total_scenes": len(enriched),
        "character_scenes_count": len(character_scenes),
        "character_name": character_name,
        "scenes": enriched,
    }


@api_router.post("/analyze/batch")
async def analyze_batch(request: BatchAnalyzeRequest):
    """Analyze multiple scenes from a full script. Returns all breakdowns linked by script_id."""
    if not request.scenes:
        raise HTTPException(status_code=400, detail="No scenes provided")
    if len(request.scenes) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 scenes per batch")

    character_name = request.character_name.strip()
    mode = request.mode or "quick"
    script_id = str(uuid.uuid4())
    logger.info(f"[analyze/batch] {len(request.scenes)} scenes, mode={mode}, character={character_name}, script_id={script_id}")

    breakdowns = []
    for i, scene in enumerate(request.scenes):
        scene_text = scene.get("text", "")
        scene_heading = scene.get("heading", f"Scene {scene.get('scene_number', i + 1)}")
        scene_number = scene.get("scene_number", i + 1)

        if not scene_text.strip():
            continue

        # Prepend character context so GPT focuses on the right character
        analysis_text = f"[CHARACTER TO ANALYZE: {character_name}]\n[SCENE: {scene_heading}]\n\n{scene_text}"

        logger.info(f"[analyze/batch] Analyzing scene {scene_number}/{len(request.scenes)}: {scene_heading}")

        try:
            gpt_timeout = 120 if mode == "deep" else 90
            result, raw = await asyncio.wait_for(
                analyze_with_gpt(text=analysis_text, mode=mode),
                timeout=gpt_timeout
            )

            breakdown_id = str(uuid.uuid4())
            doc = {
                "id": breakdown_id,
                "script_id": script_id,
                "scene_number": scene_number,
                "scene_heading": scene_heading,
                "original_text": scene_text,
                "mode": mode,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **result
            }
            await db.breakdowns.insert_one(doc)
            stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
            breakdowns.append(stored)

        except Exception as e:
            logger.error(f"[analyze/batch] Scene {scene_number} failed: {e}")
            # Add a placeholder so the user knows this scene failed
            breakdowns.append({
                "id": str(uuid.uuid4()),
                "script_id": script_id,
                "scene_number": scene_number,
                "scene_heading": scene_heading,
                "original_text": scene_text,
                "mode": mode,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "scene_summary": f"Analysis failed for this scene: {str(e)[:100]}",
                "character_name": character_name,
                "character_objective": "", "stakes": "",
                "beats": [], "acting_takes": {"grounded": "", "bold": "", "wildcard": ""},
                "memorization": {"chunked_lines": [], "cue_recall": []},
                "self_tape_tips": {"framing": "", "eyeline": "", "tone_energy": ""},
                "_debug": {"fallback": True, "reason": str(e)},
            })

    # Save script metadata
    script_doc = {
        "id": script_id,
        "character_name": character_name,
        "mode": mode,
        "scene_count": len(breakdowns),
        "breakdown_ids": [b["id"] for b in breakdowns],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.scripts.insert_one(script_doc)

    return {
        "script_id": script_id,
        "character_name": character_name,
        "mode": mode,
        "breakdowns": breakdowns,
    }


@api_router.get("/scripts")
async def list_scripts():
    """List recent scripts with metadata (no full breakdowns)."""
    scripts = await db.scripts.find({}, {"_id": 0}).sort("created_at", -1).to_list(20)
    for s in scripts:
        s["breakdown_count"] = len(s.get("breakdown_ids", []))
    return scripts


@api_router.get("/scripts/{script_id}")
async def get_script(script_id: str):
    """Retrieve a full script analysis with all its scene breakdowns."""
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    breakdown_ids = script.get("breakdown_ids", [])
    character_name = script.get("character_name", "")
    breakdowns = []
    for bid in breakdown_ids:
        b = await db.breakdowns.find_one({"id": bid}, {"_id": 0})
        if b:
            # Use cleaned_text if available, otherwise fall back to original_text
            parse_text = b.get("cleaned_text") or b.get("original_text", "")
            if character_name and parse_text:
                fresh_mem = extract_character_lines(parse_text, character_name)
                b["memorization"] = fresh_mem
            breakdowns.append(b)

    breakdowns.sort(key=lambda x: x.get("scene_number", 0))

    return {
        **script,
        "breakdowns": breakdowns,
    }


@api_router.post("/scripts/create")
async def create_script(request: CreateScriptRequest):
    """Initialize a script record before analyzing scenes one by one."""
    script_id = str(uuid.uuid4())
    doc = {
        "id": script_id,
        "character_name": request.character_name.strip(),
        "mode": request.mode or "quick",
        "scene_count": request.scene_count,
        "prep_mode": request.prep_mode,
        "project_type": request.project_type,
        "breakdown_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.scripts.insert_one(doc)
    logger.info(f"[scripts/create] Created script {script_id} for {request.character_name}, {request.scene_count} scenes")
    return {"script_id": script_id}


@api_router.post("/analyze/scene")
async def analyze_single_scene(request: SingleSceneRequest):
    """Analyze a single scene and link it to an existing script. Designed to avoid proxy timeouts."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Scene text cannot be empty")

    character_name = request.character_name.strip()
    mode = request.mode or "quick"

    # Hard cap scene text
    scene_text = request.text[:SCENE_TEXT_HARD_CAP] if len(request.text) > SCENE_TEXT_HARD_CAP else request.text
    if len(request.text) > SCENE_TEXT_HARD_CAP:
        logger.info(f"[COST] Scene #{request.scene_number} hard-capped: {len(request.text)} -> {SCENE_TEXT_HARD_CAP} chars")

    analysis_text = f"[CHARACTER TO ANALYZE: {character_name}]\n[SCENE: {request.scene_heading}]"
    if request.prep_mode:
        prep_labels = {"audition": "Audition prep", "booked": "Booked role / rehearsal", "silent": "Silent on-camera", "study": "General script study"}
        analysis_text += f"\n[PREP CONTEXT: {prep_labels.get(request.prep_mode, request.prep_mode)}]"
    if request.project_type:
        type_labels = {"commercial": "Commercial", "tvfilm": "TV / Film", "theatre": "Theatre", "voiceover": "Voiceover", "vertical": "Vertical drama / Soap-style series"}
        analysis_text += f"\n[PROJECT TYPE: {type_labels.get(request.project_type, request.project_type)}]"
        if request.project_type == "vertical":
            analysis_text += "\n[GENRE DIRECTION: This is a vertical short-form drama / soap. The acting style is HEIGHTENED — faster emotional turns, stronger reversals, clearer beat buttons (end-of-episode hooks). Performances should be decisive and dramatic, not subtle or understated. Physical choices should be bold and camera-conscious (tight framing, direct looks). Memorization chunks should be tight — this is fast-paced material with sharp exchanges.]"
    analysis_text += f"\n\n{scene_text}"

    logger.info(f"[analyze/scene] script={request.script_id}, scene #{request.scene_number}: {request.scene_heading}, mode={mode}")

    # Check cache (key includes character name for strict isolation)
    cache_key = compute_cache_key(scene_text, mode, character_name)
    cached_result = await get_cached_breakdown(cache_key)
    if cached_result:
        breakdown_id = str(uuid.uuid4())
        doc = {
            "id": breakdown_id,
            "script_id": request.script_id,
            "scene_number": request.scene_number,
            "scene_heading": request.scene_heading,
            "original_text": scene_text,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "from_cache": True,
            **cached_result
        }
        await db.breakdowns.insert_one(doc)
        stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
        await db.scripts.update_one(
            {"id": request.script_id},
            {"$push": {"breakdown_ids": breakdown_id}}
        )
        logger.info(f"[COST] Scene #{request.scene_number} CACHE HIT — 0 GPT calls, $0.00")
        return stored

    logger.info(f"[COST] Scene #{request.scene_number} CACHE MISS — GPT call (est. ${estimate_cost(mode):.2f})")
    try:
        gpt_timeout = 120 if mode == "deep" else 90
        result, raw = await asyncio.wait_for(
            analyze_with_gpt(text=analysis_text, mode=mode),
            timeout=gpt_timeout
        )

        # Override GPT memorization with deterministic extraction (exact lines, zero hallucination)
        det_mem = extract_character_lines(scene_text, character_name)
        if det_mem["cue_recall"]:
            result["memorization"] = det_mem

        # Cache for future reuse
        await store_cached_breakdown(cache_key, result, mode, character_name)

        breakdown_id = str(uuid.uuid4())
        doc = {
            "id": breakdown_id,
            "script_id": request.script_id,
            "scene_number": request.scene_number,
            "scene_heading": request.scene_heading,
            "original_text": scene_text,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **result
        }
        await db.breakdowns.insert_one(doc)
        stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})

        # Link to script
        await db.scripts.update_one(
            {"id": request.script_id},
            {"$push": {"breakdown_ids": breakdown_id}}
        )

        logger.info(f"[COST] Scene #{request.scene_number} done — 1 GPT call, est. ${estimate_cost(mode):.2f}")
        return stored

    except asyncio.TimeoutError:
        logger.error(f"[analyze/scene] Scene #{request.scene_number} timed out")
        raise HTTPException(status_code=504, detail=f"Scene #{request.scene_number} timed out. Try Quick mode.")
    except Exception as e:
        err_str = str(e)
        err_lower = err_str.lower()
        logger.error(f"[analyze/scene] Scene #{request.scene_number} failed: {err_str}")
        if "budget" in err_lower and "exceeded" in err_lower:
            raise HTTPException(status_code=402, detail="LLM budget exceeded. Go to Profile > Universal Key > Add Balance.")
        if "rate" in err_lower and "limit" in err_lower:
            raise HTTPException(status_code=429, detail="Rate limited. Wait a moment and retry.")
        if any(kw in err_lower for kw in ["serviceunavailable", "connection refused", "upstream connect error", "connection reset", "service_unavailable"]):
            raise HTTPException(status_code=503, detail="LLM service temporarily unavailable. Retry in a moment.")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {err_str[:200]}")


@api_router.post("/check-cache")
async def check_cache(request: CheckCacheRequest):
    """Check if a breakdown for this input is already cached."""
    cache_key = compute_cache_key(request.text, request.mode or "quick", request.character_name or "")
    cached = await get_cached_breakdown(cache_key)
    return {
        "cached": cached is not None,
        "cache_key": cache_key[:16],
        "estimated_cost": 0.0 if cached else estimate_cost(request.mode or "quick"),
    }


@api_router.post("/check-cache/batch")
async def check_cache_batch(request: BatchCheckCacheRequest):
    """Check cache status for multiple scenes before batch analysis."""
    mode = request.mode or "quick"
    char_name = request.character_name or ""
    cached_count = 0
    scene_results = []
    for scene in request.scenes:
        text = scene.get("text", "")
        cache_key = compute_cache_key(text, mode, char_name)
        cached = await get_cached_breakdown(cache_key)
        is_cached = cached is not None
        if is_cached:
            cached_count += 1
        scene_results.append({"scene_number": scene.get("scene_number", 0), "cached": is_cached})
    uncached = len(request.scenes) - cached_count
    return {
        "total": len(request.scenes),
        "cached": cached_count,
        "uncached": uncached,
        "estimated_cost": round(uncached * estimate_cost(mode), 2),
        "scenes": scene_results,
    }


@api_router.post("/parse-lines")
async def parse_lines(request: ParseLinesRequest):
    """Deterministic line extraction — zero GPT, zero credits."""
    result = extract_character_lines(request.text, request.character_name)
    return {
        "character_name": request.character_name,
        "line_count": len(result["cue_recall"]),
        "memorization": result,
    }



class CleanTextRequest(BaseModel):
    text: str


class CleanScriptRequest(BaseModel):
    script_id: str


class SaveCleanedTextRequest(BaseModel):
    script_id: str
    breakdown_id: str
    cleaned_text: str


@api_router.post("/clean-text")
async def clean_text_endpoint(request: CleanTextRequest):
    """Deterministic script cleaning — zero GPT, zero credits.
    Returns cleaned text for user review/edit."""
    cleaned = clean_script_text(request.text)
    return {"cleaned_text": cleaned}


@api_router.post("/clean-script")
async def clean_script_endpoint(request: CleanScriptRequest):
    """Clean all scenes of an existing script. Returns cleaned texts for review.
    Zero GPT, zero credits."""
    script = await db.scripts.find_one({"id": request.script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    breakdown_ids = script.get("breakdown_ids", [])
    scenes = []
    for bid in breakdown_ids:
        b = await db.breakdowns.find_one({"id": bid}, {"_id": 0, "id": 1, "original_text": 1, "scene_number": 1, "scene_heading": 1, "cleaned_text": 1})
        if b:
            raw = b.get("original_text", "")
            already_cleaned = b.get("cleaned_text", "")
            scenes.append({
                "breakdown_id": b["id"],
                "scene_number": b.get("scene_number", 0),
                "scene_heading": b.get("scene_heading", ""),
                "original_text": raw,
                "cleaned_text": already_cleaned or clean_script_text(raw),
                "has_saved_clean": bool(already_cleaned),
            })

    scenes.sort(key=lambda x: x.get("scene_number", 0))
    return {
        "script_id": request.script_id,
        "character_name": script.get("character_name", ""),
        "scene_count": len(scenes),
        "scenes": scenes,
    }


@api_router.post("/save-cleaned-text")
async def save_cleaned_text(request: SaveCleanedTextRequest):
    """Save user-confirmed cleaned text for a breakdown.
    This becomes the single source of truth for all downstream features."""
    result = await db.breakdowns.update_one(
        {"id": request.breakdown_id},
        {"$set": {"cleaned_text": request.cleaned_text}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    logger.info(f"[CLEAN] Saved cleaned_text for breakdown {request.breakdown_id[:16]}")
    return {"status": "ok", "breakdown_id": request.breakdown_id}


class SaveCleanedScriptRequest(BaseModel):
    script_id: str
    scenes: list


@api_router.post("/save-cleaned-script")
async def save_cleaned_script(request: SaveCleanedScriptRequest):
    """Batch save cleaned text for all scenes of a script."""
    script_id = request.script_id
    scenes = request.scenes
    if not script_id or not scenes:
        raise HTTPException(status_code=400, detail="script_id and scenes required")

    saved = 0
    for scene in scenes:
        bid = scene.get("breakdown_id") if isinstance(scene, dict) else None
        ct = scene.get("cleaned_text", "") if isinstance(scene, dict) else ""
        if not bid or not ct:
            continue
        await db.breakdowns.update_one(
            {"id": bid},
            {"$set": {"cleaned_text": ct}},
        )
        saved += 1

    logger.info(f"[CLEAN] Saved cleaned_text for {saved}/{len(scenes)} scenes of script {script_id}")
    return {"status": "ok", "saved": saved, "total": len(scenes)}



@api_router.post("/debug/parse-audit")
async def parse_audit(request: ParseLinesRequest):
    """Audit tool: shows raw text annotated with what the parser captured vs missed.
    Zero GPT. For validation only."""
    text = request.text
    character_name = request.character_name
    char_upper = character_name.strip().upper()

    # Get parser output
    result = extract_character_lines(text, character_name)
    cue_recall = result.get("cue_recall", [])
    extracted_lines = [cr["your_line"] for cr in cue_recall]

    # Build line-by-line annotation of the raw text
    lines = text.split("\n")
    annotations = []
    extracted_set = set(extracted_lines)

    # Also build a flat list of all dialogue blocks (all speakers) for context
    all_blocks = []
    # Re-parse to get all speakers' blocks
    import re as _re
    def _is_char(s):
        s = s.strip()
        if not s or len(s) > 60 or len(s) < 2:
            return False
        m = _re.match(r'^([A-Z][A-Z\s\.\'\-]+?)(?:\s*\(.*?\))?\s*$', s)
        if not m:
            return False
        name = m.group(1).strip()
        if _re.match(r'^(INT\.|EXT\.|INT/EXT\.|FADE|CUT TO|EPISODE|EP[\.\s]|CHAPTER|CONTINUED|END OF|THE END)', name):
            return False
        return True

    def _extract_name(s):
        m = _re.match(r'^([A-Z][A-Z\s\.\'\-]+?)(?:\s*\(.*?\))?\s*$', s.strip())
        return m.group(1).strip() if m else s.strip()

    # Annotate each line
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if _is_char(stripped):
            speaker = _extract_name(stripped)
            is_target = speaker.upper() == char_upper or char_upper in speaker.upper()
            annotations.append({
                "line_num": i + 1,
                "raw": raw,
                "type": "speaker",
                "speaker": speaker,
                "is_target_character": is_target,
            })
        elif stripped == "":
            annotations.append({"line_num": i + 1, "raw": raw, "type": "blank"})
        elif _re.match(r'^\d*(INT\.|EXT\.|INT/EXT\.)', stripped, _re.IGNORECASE):
            annotations.append({"line_num": i + 1, "raw": raw, "type": "heading"})
        elif _re.match(r'^\(.*\)$', stripped):
            annotations.append({"line_num": i + 1, "raw": raw, "type": "parenthetical"})
        else:
            # Check if this text appears in any extracted line
            found_in = None
            for idx, el in enumerate(extracted_lines):
                if stripped in el:
                    found_in = idx
                    break
            annotations.append({
                "line_num": i + 1,
                "raw": raw,
                "type": "captured" if found_in is not None else "uncaptured",
                "matched_line_index": found_in,
            })
        i += 1

    # Build mismatch summary
    uncaptured = [a for a in annotations if a["type"] == "uncaptured"]

    return {
        "character_name": character_name,
        "total_raw_lines": len(lines),
        "extracted_line_count": len(extracted_lines),
        "extracted_lines": extracted_lines,
        "uncaptured_count": len(uncaptured),
        "uncaptured_lines": [{"line_num": u["line_num"], "text": u["raw"].strip()} for u in uncaptured],
        "annotations": annotations,
    }



# Curated default voices — available with any ElevenLabs API key
DEFAULT_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "accent": "American", "style": "Calm, natural"},
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "accent": "American", "style": "Deep, narration"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah", "gender": "female", "accent": "American", "style": "Soft, warm"},
    {"voice_id": "cjVigY5qzO86Huf0OWal", "name": "Daniel", "gender": "male", "accent": "British", "style": "Authoritative"},
    {"voice_id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "gender": "male", "accent": "Australian", "style": "Casual, conversational"},
    {"voice_id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female", "accent": "English-Swedish", "style": "Dramatic, expressive"},
    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "gender": "male", "accent": "British", "style": "Raspy, warm"},
    {"voice_id": "ThT5KcBeYPX3keUQqHPh", "name": "Dorothy", "gender": "female", "accent": "British", "style": "Pleasant, clear"},
    {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "gender": "male", "accent": "American", "style": "Young, raspy"},
    {"voice_id": "GBv7mTt0atIp3Br8iCZE", "name": "Thomas", "gender": "male", "accent": "American", "style": "Calm, measured"},
]


@api_router.get("/tts/status")
async def tts_status():
    return {"available": eleven_client is not None}


@api_router.get("/tts/voices")
async def list_voices():
    if not eleven_client:
        return {"voices": [], "available": False}
    return {"voices": DEFAULT_VOICES, "available": True}


@api_router.post("/tts/generate")
async def tts_generate(request: TTSRequest):
    if not eleven_client:
        raise HTTPException(status_code=503, detail="Voice features require an ElevenLabs API key. Add ELEVENLABS_API_KEY to enable.")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        from elevenlabs import VoiceSettings as VS
        voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM"

        def _generate():
            audio_gen = eleven_client.text_to_speech.convert(
                text=request.text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                voice_settings=VS(stability=0.55, similarity_boost=0.7, style=0.15, use_speaker_boost=True)
            )
            data = b""
            for chunk in audio_gen:
                data += chunk
            return data

        audio_data = await asyncio.to_thread(_generate)
        audio_b64 = base64.b64encode(audio_data).decode()
        return {"audio_url": f"data:audio/mpeg;base64,{audio_b64}"}
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")


@api_router.get("/export-pdf/{breakdown_id}")
async def export_pdf(breakdown_id: str):
    breakdown = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")

    from fpdf import FPDF

    def safe(text):
        if not text:
            return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.add_page()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    def divider():
        pdf.set_draw_color(180, 180, 180)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.l_margin + w, y)
        pdf.ln(6)

    def section_label(text):
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(w, 5, safe(text.upper()), 0, 1)
        pdf.set_text_color(0, 0, 0)

    def section_body(text, font_style='', font_size=11, line_height=6):
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', font_style, font_size)
        pdf.multi_cell(w, line_height, safe(text))

    # --- Header ---
    char_name = breakdown.get('character_name', 'Unknown')
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(w, 10, safe(char_name.upper()), 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(w, 5, safe("Script Breakdown  |  Actor's Companion"), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    divider()

    # --- Scene Summary (one-liner) ---
    summary = breakdown.get('scene_summary', '')
    if summary:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5, safe(summary))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    # --- Objective & Stakes side by side concept (stacked for clean print) ---
    section_label("Objective")
    section_body(breakdown.get('character_objective', ''), 'B', 11, 6)
    pdf.ln(4)

    section_label("Stakes")
    section_body(breakdown.get('stakes', ''), '', 11, 6)
    pdf.ln(4)
    divider()

    # --- Beats ---
    section_label("Beat Breakdown")
    pdf.ln(2)
    for beat in breakdown.get('beats', []):
        # Beat header
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 10)
        beat_num = beat.get('beat_number', '')
        beat_title = beat.get('title', '')
        emotion = beat.get('emotion', '')
        pdf.multi_cell(w, 5, safe(f"{beat_num}. {beat_title}  [{emotion}]"))

        # Description
        desc = beat.get('description', '')
        if desc:
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(w - 4, 5, safe(desc))

        # Subtext — the key part
        subtext = beat.get('subtext', '')
        if subtext:
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(w - 4, 5, safe(f'"{subtext}"'))
            pdf.set_text_color(0, 0, 0)

        pdf.ln(3)

    divider()

    # --- Three Takes ---
    section_label("Your Takes")
    pdf.ln(2)
    takes = breakdown.get('acting_takes', {})
    for label, key in [("Grounded", "grounded"), ("Bold", "bold"), ("Wildcard", "wildcard")]:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(w, 5, safe(label.upper()), 0, 1)
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(w, 5, safe(takes.get(key, '')))
        pdf.ln(3)

    # --- Footer ---
    pdf.ln(4)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(150, 150, 150)
    pdf.set_x(pdf.l_margin)
    pdf.cell(w, 4, safe(f"Generated by Actor's Companion  |  {breakdown.get('created_at', '')[:10]}"), 0, 1, 'C')
    pdf.set_x(pdf.l_margin)
    pdf.cell(w, 4, safe("Co-produced by DangerLou Media"), 0, 1, 'C')

    pdf_bytes = pdf.output()
    filename = safe(char_name).replace(' ', '_').lower()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}_breakdown.pdf"}
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
