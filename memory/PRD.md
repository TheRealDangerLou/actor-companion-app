# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable and text-grounded.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)
- **PDF Rendering**: pymupdf (scanned PDFs → per-page OCR)

## What's Implemented

### Analysis Engine v3 (Behavioral, Text-Grounded)
- Observable-first principle: everything anchored in provable text
- Behavior + Effect per beat (replaces emotion labels)
- No emotional labels — only action verbs
- Deep mode: Tactical Arc, what they hide, layered subtext, physical life
- Acting takes: line-specific physical direction

### Full Script Mode
- Upload/paste a full screenplay or script
- **File upload support**: PDF, images (JPG, PNG, HEIC) — extracts text via OCR pipeline
- Enter character name → finds all scenes containing that character
- Scene detection: regex-based (INT./EXT.) with GPT fallback
- Character detection: ALL CAPS dialogue cues per scene
- Scene list: heading, preview, character badges, "YOUR SCENE" tags
- Select scenes individually or "Select All" for batch analysis
- **Per-scene analysis architecture** — each scene analyzed individually to avoid proxy timeouts
- **Progress indicator** — "Analyzing scene 2 of 5" with scene heading + stepped progress bar
- **Graceful degradation** — failed scenes get placeholders, rest continue
- ScriptOverview view: scene tabs, prev/next navigation, per-scene breakdowns

### "Go Deeper" (Re-analyze in Deep)
- Quick breakdowns show a "Go Deeper" CTA banner
- One-click re-analysis with Deep mode using stored original_text

### Voice Selection for Scene Reader
- 10 curated ElevenLabs voices (Rachel, Adam, Sarah, Daniel, Charlie, Charlotte, George, Dorothy, Sam, Thomas)
- Voice picker dropdown in Scene Reader controls
- Shows name, gender, accent, style for each voice

### Optional Clarification Toggles
- 8 quick-tap flags: Cold read, Comedic, Dramatic, I'm the antagonist, Callback, Self-tape, Chemistry read, Under-5
- Appended to analysis context as "Actor notes"

### Scene Reader (AI Voice Partner)
- Voice-responsive "Run Lines" with selected voice
- Single persistent audio element (iOS-safe), 30s timeout, graceful degradation

### Memorization Suite (4 modes)
- My Lines (speed drill), Line Run (rehearsal), Reader (teleprompter), Cue & Recall (testing)

### File Upload Pipeline
- Text PDFs: PyPDF2 fast path
- Scanned PDFs: pymupdf → per-page Vision OCR
- Images: HEIC→JPEG, resize, iOS MIME handling
- Standalone text extraction: POST /api/extract-text

## Key API Endpoints
- `POST /api/extract-text` — Extract text from PDF/image
- `POST /api/analyze/text` — Analyze text script (mode: quick/deep)
- `POST /api/analyze/image` — Analyze uploaded image/PDF
- `POST /api/parse-scenes` — Parse full script into scenes
- `POST /api/scripts/create` — Initialize script record
- `POST /api/analyze/scene` — Analyze single scene (linked to script)
- `GET /api/scripts/{script_id}` — Retrieve full script with breakdowns
- `GET /api/breakdowns` — List recent breakdowns
- `POST /api/tts/generate` — Generate TTS audio (accepts voice_id)
- `GET /api/tts/voices` — List 10 curated voices

## DB Schema
- **breakdowns**: `{id, original_text, mode, script_id?, scene_number?, scene_heading?, scene_summary, character_name, character_objective, stakes, beats[], acting_takes, memorization, self_tape_tips, created_at}`
- **scripts**: `{id, character_name, mode, scene_count, breakdown_ids[], created_at}`

## Prioritized Backlog
### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
- [ ] Memorization Timer
