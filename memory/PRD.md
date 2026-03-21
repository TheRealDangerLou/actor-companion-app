# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (integration built, live with paid key)

## User Persona
Actors preparing for auditions who need fast, actionable breakdowns they can perform immediately. Primary use: mobile (iPhone), often while self-taping.

## What's Implemented (March 2026)

### Core Analysis Pipeline (Stabilized)
- Text analysis via GPT-5.2 with stage-by-stage tracking
- Image analysis via GPT-5.2 Vision (HEIC, JPEG, PNG, WebP supported)
- PDF text extraction via PyPDF2 with vision fallback for scanned PDFs
- Input truncation to ~2500 chars (1-2 pages) for reliable GPT responses
- Fallback mode: returns extracted text + partial breakdown instead of hard failure
- Detailed _debug object on every response (stages, fallback boolean, error reasons)
- `/api/debug/pipeline` diagnostic endpoint for stage-by-stage health checks
- HEIC-to-JPEG conversion via pillow-heif
- Image compression/resize (max 2048px) before Vision API
- iOS edge case handling (empty MIME types, application/octet-stream)

### Breakdown Features
- Scene Summary, Character Objective, Stakes
- Beat Breakdown with subtext + keyword highlights
- 3 Distinct Acting Takes (grounded/bold/wildcard)
- Regenerate Takes button
- Reader Mode (chunked lines + cue-based recall)
- Teleprompter Mode (full-screen, large text, tap zones)
- Scene Reader with ElevenLabs voice playback
- Share Breakdown (read-only URL)
- PDF Export + Browser Print
- Recent Breakdowns History on upload page

### UI/UX
- Dark "Black Box Theater" aesthetic
- Mobile-first design (wake lock, swipe nav, safe area insets)
- Camera "Snap" feature for mobile uploads
- File size display after selection
- Detailed error toasts (not generic "Analysis failed")
- Fallback banner in BreakdownView with expandable pipeline stages
- Console logging of _debug stages for debugging

## Prioritized Backlog
### P0 (User testing next)
- [ ] User real-world testing on iPhone (all upload paths: text, PDF, image, snap)
- [ ] Monitor fallback rate — if high, investigate LLM budget/quota

### P1
- [ ] Voice selection for Scene Reader (blocked on ElevenLabs voices_read permission)
- [ ] AI Scene Reader Phase 2 (tone/pacing control)

### P2
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV layer
- [ ] User accounts & auth
- [ ] Saved breakdowns dashboard
