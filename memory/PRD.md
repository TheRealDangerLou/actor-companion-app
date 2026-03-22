# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable and text-grounded.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)
- **PDF Rendering**: pymupdf (scanned PDFs → per-page OCR)

## What's Implemented (March 2026)

### Analysis Engine v3 (Behavioral, Text-Grounded)
- **Observable-first principle**: Everything anchored in provable text
- **Behavior + Effect** per beat: "What they do" + "How it lands" (replaces emotion labels)
- No emotional labels (guilt, shame, contempt, vulnerability) — only action verbs
- Objectives: active verbs describing what character does TO the other person
- Beats: tactic shifts, not topic or emotion changes
- Subtext: tactical function of lines, not hidden feelings
- "What They Hide": text-supported only, with "Nothing" as valid answer
- Antagonistic characters played as written — no softening
- Deep mode: Tactical Arc (not Emotional Arc), layered subtext (surface → what it does → if this fails)
- Acting takes: line-specific physical direction, bold = sharper not softer

### Full Script Mode (NEW - March 22, 2026)
- Upload/paste a full screenplay or script
- Enter character name → app finds all scenes containing that character
- Scene detection: regex-based (INT./EXT. headers) with GPT fallback for non-standard formats
- Character detection: identifies ALL CAPS dialogue cues per scene
- Scene list shows: heading, preview text, character badges, "YOUR SCENE" tags
- Select individual scenes or "Select All" for batch analysis
- One Quick/Deep mode choice applies to all selected scenes
- ScriptOverview view: scene tabs, prev/next navigation, per-scene breakdowns
- Each scene gets its own independent breakdown (memorization, takes, etc.)
- Scenes linked by script_id in the database

### "Go Deeper" (Re-analyze in Deep) - March 22, 2026
- Quick breakdowns show a "Go Deeper" CTA banner
- One-click re-analysis with Deep mode using the stored original_text
- Button auto-hides after upgrading to Deep (or on Deep breakdowns)

### Multi-Page Scanned PDF Support
- Up to 5 pages rendered via pymupdf at 200dpi
- Each page OCR'd independently via GPT Vision
- Text concatenated and sent to analysis engine
- Full stage tracking in _debug

### File Upload Pipeline
- Text PDFs: PyPDF2 fast path
- Scanned PDFs: pymupdf → per-page Vision OCR → analysis
- Images: HEIC→JPEG, resize, iOS MIME handling
- Fallback mode + stage-by-stage debug tracking

### Guided Upload Flow
- 3-step stepper for sides: (1) Choose input → (2) Input + Quick/Deep → (3) Context + Analyze
- 4-step stepper for full script: (1) Full Script → (2) Paste script → (3) Character name + Mode + Find Scenes → (4) Select scenes + Analyze

### Memorization Suite (4 modes)
- **My Lines**: Speed drill — tap-to-advance, large text
- **Line Run**: Structured rehearsal with Nailed/Peeked
- **Reader**: Chunked lines with teleprompter
- **Cue & Recall**: All pairs with tap-to-reveal

### Scene Reader (AI Voice Partner)
- Voice-responsive "Run Lines" mode via ElevenLabs TTS
- Single persistent audio element (iOS-safe)
- 30s safety timeout prevents hanging
- Graceful degradation to text+timer when voice fails
- Adjustable pause duration, skip, restart controls

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast tactic-based prep with behavior/effect per beat
- **Deep** (~30-60s): Full scene study with tactical arc, what they hide, layered subtext, physical life

## Key API Endpoints
- `POST /api/analyze/text` — Analyze text script (mode: quick/deep)
- `POST /api/analyze/image` — Analyze uploaded image/PDF
- `POST /api/parse-scenes` — Parse full script into scenes, detect characters
- `POST /api/analyze/batch` — Batch-analyze multiple scenes
- `GET /api/scripts/{script_id}` — Retrieve full script analysis
- `GET /api/breakdowns` — List recent breakdowns
- `GET /api/breakdowns/{id}` — Get single breakdown
- `POST /api/regenerate-takes/{id}` — Regenerate acting takes
- `POST /api/tts/generate` — Generate TTS audio
- `GET /api/tts/status` — Check TTS availability
- `GET /api/export-pdf/{id}` — Download PDF export
- `GET /api/debug/pipeline` — Health check all dependencies

## DB Schema
- **breakdowns**: `{id, original_text, mode, script_id?, scene_number?, scene_heading?, scene_summary, character_name, character_objective, stakes, beats[], acting_takes, memorization, self_tape_tips, created_at}`
- **scripts**: `{id, character_name, mode, scene_count, breakdown_ids[], created_at}`

## Prioritized Backlog
### P1
- [ ] Voice selection for Scene Reader (blocked by TTS voices endpoint returning 0)
- [ ] Optional clarification toggles (never required)

### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
- [ ] Memorization Timer
