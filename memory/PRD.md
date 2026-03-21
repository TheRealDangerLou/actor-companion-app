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
- 3-step stepper: (1) Choose input → (2) Input + Quick/Deep → (3) Context + Analyze

### Memorization Suite (4 modes)
- **My Lines**: Speed drill — tap-to-advance, large text
- **Line Run**: Structured rehearsal with Nailed/Peeked
- **Reader**: Chunked lines with teleprompter
- **Cue & Recall**: All pairs with tap-to-reveal

### Quick / Deep Analysis Modes
- **Quick** (~15-25s): Fast tactic-based prep with behavior/effect per beat
- **Deep** (~30-60s): Full scene study with tactical arc, what they hide, layered subtext, physical life

## Prioritized Backlog
### P1
- [ ] "Re-analyze in Deep" button on Quick breakdowns
- [ ] Voice selection for Scene Reader
- [ ] Optional clarification toggles (never required)

### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
