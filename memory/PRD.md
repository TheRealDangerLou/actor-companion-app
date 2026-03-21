# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)

## What's Implemented (March 2026)

### Quick / Deep Analysis Modes
- **Quick Mode** (~15-25s): Fast, surface-level prep. Simple beat subtext, basic acting direction. Default mode.
- **Deep Mode** (~30-60s): Full scene study. Includes:
  - Emotional Arc (character's journey from first line to last)
  - What They Hide (what truth the character is protecting)
  - Layered subtext per beat (surface / meaning / fear)
  - Physical life per beat (specific body direction)
  - More granular, playable acting takes with line-specific direction
- Mode toggle on upload page (Quick | Deep buttons)
- Different loading screens per mode with appropriate messaging
- DEEP badge in breakdown header when viewing deep analysis
- Deep-only cards (Emotional Arc, What They Hide) in BreakdownView
- Mode stored in DB with each breakdown

### Stabilized Analysis Pipeline
- Stage-by-stage debug tracking on every response (`_debug` object)
- Fallback mode: returns extracted text + partial breakdown instead of hard failure
- `/api/debug/pipeline` diagnostic endpoint
- Input truncation: Quick=2500 chars, Deep=8000 chars
- Detailed error messages surfaced to frontend

### File Upload (Hardened)
- HEIC→JPEG conversion, image resize (max 2048px)
- iOS edge case handling (empty MIME types, application/octet-stream)
- Smart file type detection (magic bytes + Pillow fallback)
- PDF text extraction with vision fallback for scanned PDFs

### Breakdown Features
- Scene Summary, Character Objective, Stakes
- Beat Breakdown with subtext + keyword highlights
- 3 Acting Takes (grounded/bold/wildcard)
- Regenerate Takes button
- Reader Mode (chunked lines + cue-based recall)
- Teleprompter Mode
- Scene Reader with ElevenLabs voice playback
- Share Breakdown (read-only URL)
- PDF Export + Browser Print
- Recent Breakdowns History

### UI/UX
- Dark "Black Box Theater" aesthetic
- Mobile-first (wake lock, swipe nav, safe area insets)
- Camera "Snap" for mobile uploads

## Prioritized Backlog
### P0
- [ ] User real-world testing on iPhone (Quick + Deep modes, all upload paths)

### P1
- [ ] Voice selection for Scene Reader
- [ ] AI Scene Reader Phase 2 (tone/pacing control)

### P2
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV layer
- [ ] User accounts & auth
