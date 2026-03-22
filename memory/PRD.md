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
- Deep mode: Tactical Arc, what they hide, layered subtext, physical life

### Full Script Mode
- Upload/paste a full screenplay or script (PDF, image, or text)
- Enter character name → finds all scenes containing that character
- Scene detection: regex-based (INT./EXT.) with GPT fallback
- **Prep Mode Selection**: Audition / Booked role / Silent on-camera / Script study
- **Project Type**: Commercial / TV-Film / Theatre / Voiceover
- Per-scene analysis (avoids proxy timeouts)
- Progress indicator: "Analyzing scene 2 of 5"
- **Per-Scene Action Bar**: Run Lines, Memorize, Go Deeper, Share, Export PDF
- **Adaptive Tool Display**: Silent hides line tools, Booked leads with Memorize
- ScriptOverview with scene tabs + prev/next navigation

### "Go Deeper" (Re-analyze in Deep)
- Quick breakdowns show "Go Deeper" CTA
- Available per-scene in ScriptOverview action bar

### Voice Selection for Scene Reader
- 10 curated ElevenLabs voices
- Voice picker dropdown in Scene Reader controls

### Optional Clarification Toggles
- 8 quick-tap flags: Cold read, Comedic, Dramatic, Antagonist, Callback, Self-tape, Chemistry read, Under-5

### Scene Reader (AI Voice Partner)
- Voice-responsive "Run Lines" with selected voice
- iOS-safe audio, 30s timeout, graceful degradation

### Memorization Suite (4 modes)
- My Lines, Line Run, Reader, Cue & Recall

### File Upload Pipeline
- Text PDFs, scanned PDFs (pymupdf + Vision OCR), images (HEIC support)
- Standalone text extraction: POST /api/extract-text

## Key API Endpoints
- `POST /api/extract-text` — Extract text from PDF/image
- `POST /api/analyze/text` — Analyze text script
- `POST /api/analyze/image` — Analyze uploaded image/PDF
- `POST /api/parse-scenes` — Parse full script into scenes
- `POST /api/scripts/create` — Initialize script record
- `POST /api/analyze/scene` — Analyze single scene (with prep_mode, project_type)
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
