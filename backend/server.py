from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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


async def analyze_with_gpt(text=None, image_base64=None):
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")

    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message=ANALYSIS_SYSTEM_PROMPT
    ).with_model("openai", "gpt-5.2")

    if image_base64:
        image_content = ImageContent(image_base64=image_base64)
        user_msg = UserMessage(
            text="Extract ALL text from this audition sides image, then analyze it as a script. Provide the full acting breakdown. Also include a field 'extracted_text' with the raw text you read from the image.",
            file_contents=[image_content]
        )
    else:
        user_msg = UserMessage(
            text=f"Analyze these audition sides and provide a full acting breakdown:\n\n{text}"
        )

    response = await chat.send_message(user_msg)
    try:
        result = parse_json_response(response)
        return result
    except (ValueError, json.JSONDecodeError):
        logger.error(f"Failed to parse GPT response: {response[:500]}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response. Please try again.")


# --- Endpoints ---
@api_router.get("/")
async def root():
    return {"message": "Actor's Companion API"}


@api_router.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide at least a few lines of dialogue")

    result = await analyze_with_gpt(text=request.text)
    breakdown_id = str(uuid.uuid4())
    doc = {
        "id": breakdown_id,
        "original_text": request.text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **result
    }
    await db.breakdowns.insert_one(doc)
    stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    return stored


@api_router.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 15MB")

    content_type = file.content_type or ""
    filename = (file.filename or "").lower()

    # PDF handling — extract text directly
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(io.BytesIO(contents))
            extracted_text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            extracted_text = extracted_text.strip()
            if len(extracted_text) < 10:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF. Try uploading an image of your sides instead.")
            result = await analyze_with_gpt(text=extracted_text)
            breakdown_id = str(uuid.uuid4())
            doc = {
                "id": breakdown_id,
                "original_text": extracted_text,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **result
            }
            await db.breakdowns.insert_one(doc)
            stored = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
            return stored
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise HTTPException(status_code=400, detail="Failed to read PDF. Try uploading an image instead.")

    # Image handling — accept all common image types including HEIC
    image_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/gif", "image/bmp", "image/tiff"}
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".bmp", ".tiff", ".tif"}
    is_image = content_type in image_types or any(filename.endswith(ext) for ext in image_extensions) or content_type.startswith("image/")

    if not is_image:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload an image (JPG, PNG, HEIC) or a PDF of your sides.")

    base64_image = base64.b64encode(contents).decode('utf-8')
    result = await analyze_with_gpt(image_base64=base64_image)

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
    return stored


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
