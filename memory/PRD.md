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
- Upload/paste full screenplay (PDF, image, text)
- Character name → finds all scenes containing that character
- Scene detection: regex (INT./EXT.) + GPT fallback
- Prep Mode: Audition / Booked / Silent / Study
- Project Type: Commercial / TV-Film / Theatre / Voiceover
- Per-scene analysis (avoids proxy timeouts)
- **Budget-aware**: Detects 402 (budget) / 429 (rate limit), stops batch immediately, shows partial results
- Per-scene action bar with adaptive tools
- ScriptOverview with scene tabs

### Adjustment Loop (Performance Feedback)
- 5 adjustment options: Tighten pacing, Add depth, More natural, Raise stakes, Play the opposite
- Adjustments stack (each builds on previous)
- Only acting takes regenerated (fast ~10s)
- **Inline panel**: below acting takes in BreakdownView
- **Post-action card**: floating card after closing Scene Reader/Memorization
- Adjustment history stored per breakdown

### Voice Selection for Scene Reader
- 10 curated ElevenLabs voices
- Voice picker dropdown in Scene Reader

### Clarification Toggles
- 8 quick-tap flags: Cold read, Comedic, Dramatic, Antagonist, Callback, Self-tape, Chemistry read, Under-5

### Scene Reader (AI Voice Partner)
- Voice-responsive "Run Lines", iOS-safe, graceful degradation

### Memorization Suite (4 modes)
- My Lines, Line Run, Reader, Cue & Recall

## Key API Endpoints
- `POST /api/extract-text` — Extract text from PDF/image
- `POST /api/analyze/text` — Analyze text script
- `POST /api/analyze/scene` — Analyze single scene (with prep_mode, project_type)
- `POST /api/adjust-takes/{id}` — Adjust acting takes with stacking feedback
- `POST /api/parse-scenes` — Parse full script into scenes
- `POST /api/scripts/create` — Initialize script record
- `GET /api/scripts/{id}` — Retrieve full script with breakdowns
- `POST /api/tts/generate` — TTS audio (accepts voice_id)
- `GET /api/tts/voices` — 10 curated voices

## Prioritized Backlog
### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
- [ ] Memorization Timer
