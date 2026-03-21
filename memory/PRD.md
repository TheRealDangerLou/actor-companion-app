# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)

## What's Implemented (March 2026)

### Guided Upload Flow
- 3-step stepper: (1) Choose input → (2) Input + Quick/Deep → (3) Context + Analyze
- Smooth transitions, lightweight, feels fast not like a form
- Recent breakdowns on Step 1 with DEEP badges

### Memorization Suite (4 modes)
- **My Lines** (default): Speed drill — one line at a time, large centered text, tap anywhere to advance, wraps at end. "show cue" button for context peek. Minimal UI, no distractions.
- **Line Run**: Structured rehearsal — cue → recall → reveal → Nailed/Peeked tracking → completion summary
- **Reader**: Chunked lines with navigation, hide/reveal, teleprompter mode
- **Cue & Recall**: All cue-line pairs with tap-to-reveal

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast prep, simple beats + subtext
- **Deep** (~30-60s): Emotional arc, what character hides, layered subtext (surface/meaning/fear), physical life per beat

### Stabilized Analysis Pipeline
- Stage-by-stage debug tracking, fallback mode, `/api/debug/pipeline`
- HEIC→JPEG, image resize, iOS MIME handling, detailed errors

### Breakdown Features
- Scene Summary, Objective, Stakes, Beat Breakdown, 3 Acting Takes
- Regenerate Takes, Share, PDF Export, Print, Scene Reader (ElevenLabs)

### UI/UX
- Dark "Black Box Theater" aesthetic, mobile-first, camera snap

## Prioritized Backlog
### P1
- [ ] "Re-analyze in Deep" button on Quick breakdowns
- [ ] Voice selection for Scene Reader

### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
