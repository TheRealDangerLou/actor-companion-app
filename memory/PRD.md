# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (integration built, awaiting API key)

## User Persona
Actors preparing for auditions who need fast, actionable breakdowns they can perform immediately. Primary use: mobile, often while self-taping.

## What's Implemented (March 2026)
- Core script analysis engine (text + image upload)
- Scene Summary, Character Objective, Stakes
- Beat Breakdown with subtext + keyword highlights
- 3 Distinct Acting Takes (grounded/bold/wildcard)
- Regenerate Takes button
- Reader Mode (chunked lines + cue-based recall)
- **Teleprompter Mode** — full-screen, large text, tap zones for hands-free
- Scene Reader (AI line runner) — text-only mode, ready for ElevenLabs voice
- Share Breakdown — clean read-only URL with CTA
- PDF Export
- Mobile-first optimizations (wake lock, swipe nav, safe area insets, auto-scroll)
- Dark "Black Box Theater" aesthetic

## Prioritized Backlog
### P0 (Next)
- [ ] Activate ElevenLabs voice (awaiting API key)
- [ ] Real-world audition testing & refinements

### P1
- [ ] AI Scene Reader with character voice distinction
- [ ] Self-tape recorder (one-tap from breakdown to recording)
- [ ] Audition tracker (organized submissions)

### P2
- [ ] Take comparison tool
- [ ] Casting Director POV layer
- [ ] Voice playback of actor's own lines
- [ ] History/saved breakdowns dashboard
- [ ] User accounts & auth
