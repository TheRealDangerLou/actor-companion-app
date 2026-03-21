# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)
- **PDF Rendering**: pymupdf (for scanned PDFs → image conversion)

## What's Implemented (March 2026)

### File Upload Pipeline (Fully Hardened)
- **Text-based PDFs**: PyPDF2 extracts text → GPT text analysis (fast path)
- **Scanned/image-based PDFs**: PyPDF2 finds no text → pymupdf renders pages to JPEG at 200dpi → GPT Vision OCR → analysis
- **Images**: HEIC→JPEG conversion, resize to 2048px max, iOS MIME handling
- **Stage tracking**: Every response includes `_debug.stages` showing exactly what happened
- **Fallback mode**: Returns partial results + extracted text instead of hard failure
- **`/api/debug/pipeline`**: Tests LLM key, GPT, MongoDB, Pillow, HEIC, PyPDF2, pymupdf

### Guided Upload Flow
- 3-step stepper: (1) Choose input → (2) Input + Quick/Deep → (3) Context + Analyze
- Fast, lightweight, smooth transitions

### Memorization Suite (4 modes)
- **My Lines** (default): Speed drill — tap-to-advance, large centered text, "show cue" peek
- **Line Run**: Structured rehearsal with Nailed/Peeked tracking
- **Reader**: Chunked lines with teleprompter mode
- **Cue & Recall**: All pairs with tap-to-reveal

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast prep, simple beats + subtext
- **Deep** (~30-60s): Emotional arc, what character hides, layered subtext, physical life, director-level takes

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
