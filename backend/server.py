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

# --- Models ---
class AnalyzeTextRequest(BaseModel):
    text: str

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

# --- Prompts ---
ANALYSIS_SYSTEM_PROMPT = """You are a top-tier acting coach and script analyst. Your job is to give actors an IMMEDIATELY PLAYABLE breakdown they can perform right after reading.

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.

{
  "scene_summary": "1-2 punchy sentences. What's happening, what's at stake.",
  "character_name": "Name of the character the actor is reading for (best guess if unclear)",
  "character_objective": "One clear, active objective using a strong verb. e.g. 'To force Sarah to admit the truth'",
  "stakes": "What happens if they fail? Make it visceral and personal.",
  "beats": [
    {
      "beat_number": 1,
      "title": "Short, evocative title",
      "description": "What shifts here. Be specific.",
      "emotion": "The dominant energy/feeling",
      "subtext": "What they're REALLY saying underneath the words. Write it as an inner monologue.",
      "key_words": ["word1", "word2"]
    }
  ],
  "acting_takes": {
    "grounded": "A grounded, naturalistic take. Specific physical and emotional direction the actor can do RIGHT NOW. Include tempo, physicality, breath. This should read like a director whispering in their ear.",
    "bold": "A bold, risky take that pushes the scene further. Specific choices that surprise. Not louder—DIFFERENT. Give them a clear physical life and emotional anchor.",
    "wildcard": "An unexpected choice nobody else will make. A genuine surprise for casting. Could be a tonal shift, an unusual rhythm, an against-the-grain read. Make it specific and committed."
  },
  "memorization": {
    "chunked_lines": [
      {"chunk_label": "Chunk 1: [brief context]", "lines": "The actual dialogue lines grouped in natural breath/thought groups (2-4 lines)"}
    ],
    "cue_recall": [
      {"cue": "The last thing said before your line (other character or stage direction)", "your_line": "Your character's exact response"}
    ]
  },
  "self_tape_tips": {
    "framing": "Specific framing for THIS scene. Close-up or mid? Why?",
    "eyeline": "Where to look and why. Be specific about the emotional reason.",
    "tone_energy": "The right energy level on a 1-10 scale with specific adjustments for this scene."
  }
}

RULES:
- Every word must be PLAYABLE. No academic analysis. No generic advice.
- Acting takes should feel like a director gave them specific notes they can perform in 30 seconds.
- Key_words are the 2-4 most important words in each beat that the actor should land on.
- Subtext should be written as the character's inner voice, not a description.
- Chunked lines must follow the actual dialogue from the script.
- Cue-recall must use actual lines from the scene.
- Be bold, specific, and practical.
- Return ONLY valid JSON."""

REGENERATE_TAKES_PROMPT = """You are a top-tier acting coach. Generate 3 COMPLETELY NEW acting takes for this scene. These must be genuinely different from typical choices—specific, physical, immediately playable.

Return ONLY valid JSON:
{
  "acting_takes": {
    "grounded": "Specific naturalistic direction. Include physicality, tempo, breath work. Like a director whispering in their ear before a take.",
    "bold": "A bold choice that pushes the scene. Not louder—DIFFERENT. Give specific emotional anchor and physical life.",
    "wildcard": "An unexpected choice nobody else will make. Specific, committed, surprising. Could flip the whole scene."
  }
}

Every word must be immediately performable. No fluff."""


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


async def analyze_with_gpt(text=None, image_base64=None, context=None):
    """Core GPT call. Truncates long text to ~2000 chars. Returns (result_dict, raw_response_str)."""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise Exception("STAGE:gpt_init | LLM API key not configured in environment")

    # Truncate text to ~2000 chars (roughly 1-2 pages) to keep GPT reliable
    if text and len(text) > 2500:
        text = text[:2500] + "\n\n[...truncated for analysis — first ~2 pages used]"
        logger.info("Truncated input text to 2500 chars")

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=ANALYSIS_SYSTEM_PROMPT
        ).with_model("openai", "gpt-5.2")
    except Exception as e:
        raise Exception(f"STAGE:gpt_init | Failed to create LLM chat: {e}")

    try:
        if image_base64:
            image_content = ImageContent(image_base64=image_base64)
            vision_prompt = "Extract ALL text from this audition sides image, then analyze it as a script. Provide the full acting breakdown. Also include a field 'extracted_text' with the raw text you read from the image."
            if context:
                vision_prompt = f"{context}\n{vision_prompt}"
            user_msg = UserMessage(
                text=vision_prompt,
                file_contents=[image_content]
            )
        else:
            user_msg = UserMessage(
                text=f"Analyze these audition sides and provide a full acting breakdown:\n\n{text}"
            )
    except Exception as e:
        raise Exception(f"STAGE:gpt_message_build | Failed to build message: {e}")

    try:
        response = await chat.send_message(user_msg)
    except Exception as e:
        raise Exception(f"STAGE:gpt_call | GPT request failed: {e}")

    if not response or not response.strip():
        raise Exception("STAGE:gpt_call | GPT returned empty response")

    try:
        result = parse_json_response(response)
        return result, response
    except (ValueError, json.JSONDecodeError):
        raise Exception(f"STAGE:gpt_parse | Could not parse JSON from GPT response (first 300 chars): {response[:300]}")


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

    # 2. Test GPT with a tiny fixed input
    if api_key:
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id="debug-test",
                system_message="Respond with exactly: {\"test\": \"ok\"}"
            ).with_model("openai", "gpt-5.2")
            raw = await asyncio.wait_for(
                chat.send_message(UserMessage(text="Say hello")),
                timeout=30
            )
            results["gpt_call"] = {"ok": True, "response_length": len(raw), "first_100": raw[:100]}
        except Exception as e:
            results["gpt_call"] = {"ok": False, "error": str(e)}
    else:
        results["gpt_call"] = {"ok": False, "error": "No API key"}

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
        results["pdf_support"] = {"ok": True}
    except ImportError:
        results["pdf_support"] = {"ok": False, "error": "PyPDF2 not installed"}

    all_ok = all(r.get("ok") for r in results.values())
    return {"all_ok": all_ok, "stages": results}


@api_router.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    stages = []  # track what happened at each stage

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide at least a few lines of dialogue")

    stages.append({"stage": "input_received", "ok": True, "chars": len(request.text)})
    logger.info(f"[analyze/text] Input: {len(request.text)} chars")

    # GPT call with timeout
    try:
        result, raw = await asyncio.wait_for(
            analyze_with_gpt(text=request.text),
            timeout=90
        )
        stages.append({"stage": "gpt_analysis", "ok": True})
    except asyncio.TimeoutError:
        stages.append({"stage": "gpt_analysis", "ok": False, "error": "Timed out after 90s"})
        logger.error("[analyze/text] GPT timed out")
        # Fallback: return the text with an error marker
        return {
            "id": str(uuid.uuid4()),
            "original_text": request.text,
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
        # Fallback: return text + error detail
        return {
            "id": str(uuid.uuid4()),
            "original_text": request.text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scene_summary": "Analysis failed — your text was saved. See error details.",
            "character_name": "Unknown",
            "character_objective": "", "stakes": "",
            "beats": [], "acting_takes": {"grounded": "", "bold": "", "wildcard": ""},
            "memorization": {"chunked_lines": [], "cue_recall": []},
            "self_tape_tips": {"framing": "", "eyeline": "", "tone_energy": ""},
            "_debug": {"stages": stages, "fallback": True, "reason": error_str}
        }

    # Save to DB
    breakdown_id = str(uuid.uuid4())
    doc = {
        "id": breakdown_id,
        "original_text": request.text,
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
async def analyze_image(file: UploadFile = File(...), context: Optional[str] = Form(None)):
    stages = []

    # Stage 1: Read file
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"[analyze/image] File read error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    file_size_mb = len(contents) / (1024 * 1024)
    file_info = {"name": file.filename, "content_type": file.content_type, "size_mb": round(file_size_mb, 2), "bytes": len(contents)}
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
            stages.append({"stage": "pdf_text_check", "ok": False, "error": "Too little text extracted, trying vision"})
            logger.info("[analyze/image] PDF text too short, falling back to vision OCR")
            try:
                jpeg_bytes = prepare_image_for_vision(contents, file.filename)
                file_type = "image"
                contents = jpeg_bytes
            except ValueError as e:
                stages.append({"stage": "pdf_to_image", "ok": False, "error": str(e)})
                return _fallback_response(None, stages, f"PDF had no readable text and couldn't be converted to image: {e}")
        else:
            # Text extraction worked — send to GPT
            full_text = context_prefix + extracted_text if context_prefix else extracted_text
            try:
                result, raw = await asyncio.wait_for(
                    analyze_with_gpt(text=full_text),
                    timeout=90
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
        try:
            result, raw = await asyncio.wait_for(
                analyze_with_gpt(image_base64=base64_image, context=context_prefix if context_prefix else None),
                timeout=90
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

    user_msg = UserMessage(
        text=f"Generate 3 new acting takes for:\n\n{breakdown['original_text']}"
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


@api_router.get("/tts/status")
async def tts_status():
    return {"available": eleven_client is not None}


@api_router.get("/tts/voices")
async def list_voices():
    if not eleven_client:
        return {"voices": [], "available": False}
    try:
        def _get():
            resp = eleven_client.voices.get_all()
            return [{"voice_id": v.voice_id, "name": v.name, "category": getattr(v, 'category', 'unknown')} for v in resp.voices[:15]]
        voices = await asyncio.to_thread(_get)
        return {"voices": voices, "available": True}
    except Exception as e:
        logger.error(f"Error fetching voices: {e}")
        return {"voices": [], "available": False}


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
