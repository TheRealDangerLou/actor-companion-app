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
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
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
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10MB")

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


@api_router.get("/export-pdf/{breakdown_id}")
async def export_pdf(breakdown_id: str):
    breakdown = await db.breakdowns.find_one({"id": breakdown_id}, {"_id": 0})
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")

    from fpdf import FPDF

    def safe(text):
        if not text:
            return ""
        # Handle unicode and limit text length for PDF rendering
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        # Limit line length to prevent rendering issues
        if len(safe_text) > 500:
            safe_text = safe_text[:500] + "..."
        return safe_text

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 12, safe("ACTOR'S COMPANION"), 0, 1, 'C')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, safe("Script Breakdown"), 0, 1, 'C')
    pdf.ln(8)

    # Character
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, safe(f"Character: {breakdown.get('character_name', 'Unknown')}"), 0, 1)
    pdf.ln(4)

    # Scene Summary
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("SCENE SUMMARY"), 0, 1)
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, safe(breakdown.get('scene_summary', '')))
    pdf.ln(4)

    # Objective
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("OBJECTIVE"), 0, 1)
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, safe(breakdown.get('character_objective', '')))
    pdf.ln(4)

    # Stakes
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("STAKES"), 0, 1)
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, safe(breakdown.get('stakes', '')))
    pdf.ln(6)

    # Beats
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("BEAT BREAKDOWN"), 0, 1)
    pdf.ln(2)
    for beat in breakdown.get('beats', []):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 7, safe(f"Beat {beat.get('beat_number', '')}: {beat.get('title', '')}"), 0, 1)
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 5, safe(f"[{beat.get('emotion', '')}] {beat.get('description', '')}"))
        pdf.set_font('Helvetica', 'I', 10)
        subtext_text = beat.get('subtext', '')
        if subtext_text:
            pdf.multi_cell(0, 5, safe(f"Subtext: \"{subtext_text}\""))
        pdf.ln(3)

    # Acting Takes
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("ACTING TAKES"), 0, 1)
    pdf.ln(2)
    takes = breakdown.get('acting_takes', {})
    for label, key in [("GROUNDED / NATURAL", "grounded"), ("BOLD / RISKY", "bold"), ("WILDCARD", "wildcard")]:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 7, safe(label), 0, 1)
        pdf.set_font('Helvetica', '', 10)
        take_text = takes.get(key, '')
        if take_text:
            pdf.multi_cell(0, 5, safe(take_text))
        pdf.ln(4)

    # Self-Tape Tips
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, safe("SELF-TAPE TIPS"), 0, 1)
    pdf.ln(2)
    tips = breakdown.get('self_tape_tips', {})
    for label, key in [("Framing", "framing"), ("Eyeline", "eyeline"), ("Tone & Energy", "tone_energy")]:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 7, safe(label), 0, 1)
        pdf.set_font('Helvetica', '', 10)
        tip_text = tips.get(key, '')
        if tip_text:
            pdf.multi_cell(0, 5, safe(tip_text))
        pdf.ln(2)

    pdf_bytes = pdf.output()
    char_name = safe(breakdown.get('character_name', 'breakdown')).replace(' ', '_')
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={char_name}_breakdown.pdf"}
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
