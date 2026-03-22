# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text or image) and get an AI-powered professional acting breakdown that's immediately playable and text-grounded.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-5.2 via Emergent LLM Key (text analysis + image vision/OCR)
- **TTS**: ElevenLabs (live with paid key)
- **PDF Rendering**: pymupdf (scanned PDFs -> per-page OCR)

## What's Implemented

### Cost Optimization System (P0 - Feb 2026)
- **Caching Layer**: SHA256 hash of (text + mode + character_name + cache_version) -> MongoDB `breakdown_cache` collection
  - 72-hour TTL with automatic expiration
  - Cache versioning (bump `CACHE_VERSION` when prompts change)
  - `from_cache: true` flag on cached responses
  - Full cost logging: [COST] CACHE HIT/MISS on every request
- **Check-Cache Endpoints**: `POST /api/check-cache` and `POST /api/check-cache/batch` for frontend pre-flight cost estimation
- **Debug Pipeline**: `/api/debug/pipeline` no longer makes GPT calls — saves ~$0.03 per server restart
- **Prompt Optimization**: REGENERATE_TAKES_PROMPT and ADJUST_TAKES_PROMPT reduced by ~60% token count
- **Scene Text Hard Cap**: 8000 chars max before any processing (SCENE_TEXT_HARD_CAP)
- **Text Truncation**: regenerate-takes now only sends first 3000 chars of scene text
- **Frontend Cost Warnings**: Estimated cost display in Full Script step 4 ($0.03/quick, $0.08/deep per scene)
- **Deep Mode Warning**: Alert when Deep mode selected for Full Script (recommends Quick)
- **Submission Guards**: isSubmitting state prevents duplicate button clicks
- **Post-Run Cost Feedback**: Toast after batch shows "X scenes · Y from cache · Est. $Z"; single analysis shows "from cache — $0.00" when cached
- **Cost Summary Bar**: Subtle stat line in ScriptOverview header showing scene count, cache hit %, and estimated cost

### Analysis Engine v3 (Behavioral, Text-Grounded)
- Observable-first principle: everything anchored in provable text
- Behavior + Effect per beat (replaces emotion labels)
- Deep mode: Tactical Arc, what they hide, layered subtext, physical life

### Full Script Mode
- Upload/paste full screenplay (PDF, image, text)
- Character name -> finds all scenes containing that character
- Scene detection: regex (INT./EXT.) + GPT fallback
- Prep Mode: Audition / Booked / Silent / Study
- Project Type: Commercial / TV-Film / Theatre / Voiceover
- Per-scene analysis (avoids proxy timeouts)
- Budget-aware: Detects 402 (budget) / 429 (rate limit), stops batch immediately
- Per-scene action bar with adaptive tools
- ScriptOverview with scene tabs

### Adjustment Loop (Performance Feedback)
- 5 adjustment options: Tighten pacing, Add depth, More natural, Raise stakes, Play the opposite
- Adjustments stack (each builds on previous)
- Only acting takes regenerated (fast ~10s)
- Inline panel below acting takes in BreakdownView
- Post-action card: floating card after closing Scene Reader/Memorization
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
- `POST /api/analyze/text` — Analyze text script (with caching)
- `POST /api/analyze/scene` — Analyze single scene (with caching)
- `POST /api/adjust-takes/{id}` — Adjust acting takes with stacking feedback
- `POST /api/parse-scenes` — Parse full script into scenes
- `POST /api/scripts/create` — Initialize script record
- `GET /api/scripts/{id}` — Retrieve full script with breakdowns
- `POST /api/tts/generate` — TTS audio (accepts voice_id)
- `GET /api/tts/voices` — 10 curated voices
- `POST /api/check-cache` — Check if a breakdown is cached (single)
- `POST /api/check-cache/batch` — Check cache status for multiple scenes
- `GET /api/debug/pipeline` — System health check (no GPT call)

## Prioritized Backlog
### P2
- [ ] AI Scene Reader Phase 2 (tone/pacing)
- [ ] Take Comparison Tool
- [ ] Audition Tracker
- [ ] Casting Director POV
- [ ] User accounts & auth
- [ ] Memorization Timer
