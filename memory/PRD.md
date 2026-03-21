# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)

## What's Implemented (March 2026)

### Guided Upload Flow (Step-by-Step)
- **Step 1**: Choose input type — Paste Script / Upload File / Snap (mobile only)
- **Step 2**: Input area + Quick/Deep mode toggle + Continue button
- **Step 3**: Summary bar + optional context (character, project, casting notes) + Analyze button
- Progress indicator (3-segment bar), smooth AnimatePresence transitions, Back buttons
- Recent breakdowns visible on Step 1 only (not cluttering later steps)
- Feels fast, not like a form — minimal text, clear guidance

### Memorization Mode (Overhauled)
- **Line Run** (default tab): Sequential drill — cue shown, actor tries to recall, tap to reveal, mark Nailed/Peeked. Progress tracking with completion summary + Run Again.
- **Reader**: Chunked lines with navigation, hide/reveal toggle, teleprompter mode with tap zones
- **Cue & Recall**: All cue-line pairs displayed, each with tap-to-reveal. Clean visual separation between cue (dim) and actor's line (bright).

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast prep, simple beats + subtext
- **Deep** (~30-60s): Emotional arc, what character hides, layered subtext (surface/meaning/fear), physical life per beat, director-level acting takes

### Stabilized Analysis Pipeline
- Stage-by-stage debug tracking, fallback mode, `/api/debug/pipeline` diagnostic
- HEIC→JPEG, image resize, iOS MIME handling, detailed errors

### Breakdown Features
- Scene Summary, Objective, Stakes, Beat Breakdown, 3 Acting Takes
- Regenerate Takes, Share, PDF Export, Print
- Scene Reader with ElevenLabs voice playback

### UI/UX
- Dark "Black Box Theater" aesthetic, mobile-first
- Camera "Snap" for mobile, wake lock, swipe nav

## Prioritized Backlog
### P0
- [ ] User real-world testing on iPhone (guided flow + memorization + all upload paths)

### P1
- [ ] "My lines only" quick view in memorization
- [ ] "Re-analyze in Deep" button on Quick breakdowns
- [ ] Voice selection for Scene Reader

### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
