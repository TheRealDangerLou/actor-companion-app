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

### Analysis Engine (Tactic-Based, Text-Grounded)
- **Observable-first principle**: All analysis anchored in what's provable on the page
- No inferred guilt, shame, vulnerability, or backstory not written in the text
- Objectives use active verbs (what character DOES to the other person)
- Beats track tactic shifts, not topic changes or emotional labels
- Antagonistic characters played as written — no default softening/humanizing
- Subtext describes tactical function of lines, not hidden feelings
- Deep mode: layered subtext (surface → tactical meaning → what fails if tactic doesn't work)

### Multi-Page Scanned PDF Support
- Up to 5 pages rendered via pymupdf at 200dpi
- Each page OCR'd independently via GPT Vision
- Text concatenated and sent to analysis engine
- Full stage tracking: pdf_to_images → ocr_complete → gpt_analysis

### File Upload Pipeline (Fully Hardened)
- Text PDFs: PyPDF2 fast path
- Scanned PDFs: pymupdf → per-page Vision OCR → analysis
- Images: HEIC→JPEG, resize, iOS MIME handling
- Fallback mode + stage-by-stage debug tracking

### Guided Upload Flow
- 3-step stepper: (1) Choose input → (2) Input + Quick/Deep → (3) Context + Analyze

### Memorization Suite (4 modes)
- **My Lines**: Speed drill — tap-to-advance, large text, "show cue" peek
- **Line Run**: Structured rehearsal with Nailed/Peeked tracking
- **Reader**: Chunked lines with teleprompter mode
- **Cue & Recall**: All pairs with tap-to-reveal

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast tactic-based prep
- **Deep** (~30-60s): Full scene study with emotional arc, what they hide, layered subtext, physical life

### Breakdown Features
- Scene Summary, Objective, Stakes, Beat Breakdown, 3 Acting Takes
- Regenerate Takes, Share, PDF Export, Print, Scene Reader (ElevenLabs)

## Prioritized Backlog
### P1
- [ ] "Re-analyze in Deep" button on Quick breakdowns
- [ ] Voice selection for Scene Reader
- [ ] Optional clarification toggles (never required, default fast)

### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
