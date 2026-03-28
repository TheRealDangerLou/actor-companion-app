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
- **Debug Pipeline**: `/api/debug/pipeline` no longer makes GPT calls
- **Prompt Optimization**: REGENERATE_TAKES_PROMPT and ADJUST_TAKES_PROMPT reduced by ~60% token count
- **Scene Text Hard Cap**: 8000 chars max before any processing (SCENE_TEXT_HARD_CAP)
- **Text Truncation**: regenerate-takes now only sends first 3000 chars of scene text
- **Submission Guards**: isSubmitting state prevents duplicate button clicks
- **Scene-Level Error Reporting**: Backend categorizes errors into 402 (budget), 429 (rate limit), 503 (service unavailable), 504 (timeout), 500 (other)
- **Failed Scene Retry**: Red-flagged tabs for failed scenes, retry card with specific error type badge
- **GPT Timeout Reduced**: Lowered to 55s per scene to stay under proxy timeout

### Deterministic Line Extraction & Trust Layer (Feb-Mar 2026)
- **Deterministic Parser**: `extract_character_lines()` uses regex pattern matching to find CHARACTER NAME + dialogue blocks from raw script text. Zero GPT, zero credits, zero hallucination
- **Memorization Override**: Both `/api/analyze/scene` and `/api/analyze/text` override GPT's memorization data with deterministic extraction
- **`POST /api/parse-lines`**: Standalone endpoint for extracting lines without any analysis
- **3-Tab Scene View**: ScriptOverview now has My Lines | Full Scene | Breakdown tabs
- **Booked Role Default**: When prepMode is "booked", My Lines tab is the default view on load
- **Lines First Landing**: Prominent hero card with line count, instant "Memorize" and "Run Lines" buttons
- **Parser Edge Cases Fixed (Mar 2026)**:
  - `(MORE)` / `(CONT'D)` page-break splits correctly join into single continuous speech
  - `"I..."` no longer falsely flagged as single-letter character name
  - Action text after page number skips correctly detected and excluded
  - 12 additional action verbs added (apologizes, stammers, wipes, twists, etc.)
  - 16/16 regression tests passing

### Scene/Episode Ordering (P1 - Mar 2026)
- **Backend sort**: `get_script()` now sorts breakdowns by `scene_number` before returning
- Episodes display in correct ascending order in horizontal tab bar

### Genre-Aware Analysis (Feb 2026)
- **Vertical / Soap project type**: New option for vertical short-form drama and soap-style series
- **Episode Parser**: Scene splitter recognizes `EPISODE X`, `EP X`, `EP. X`, `CHAPTER X`, and `#X` markers
- **Genre Direction Injection**: When project_type is "vertical", GPT receives specific genre context

### Script Persistence & Performance (Feb 2026)
- **My Scripts List**: `GET /api/scripts` returns recent scripts with metadata
- **Script Loading**: Clicking a script loads all breakdowns via `GET /api/scripts/{id}` — zero GPT calls
- **Parallel Batching**: Full script analysis processes scenes in batches of 3 via Promise.all
- **Zero-Credit Rehearsal**: MemorizationMode has zero network calls. SceneReader only calls TTS endpoint

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
- Per-scene analysis with parallel batching

### Adjustment Loop (Performance Feedback)
- 5 adjustment options
- Adjustments stack (each builds on previous)
- Only acting takes regenerated (fast ~10s)

### Voice Selection for Scene Reader
- 10 curated ElevenLabs voices

### Memorization Suite (4 modes)
- My Lines, Line Run, Reader, Cue & Recall
- Progressive blur ladder (4 levels)
- End-of-scene prompts (Repeat/Harder/Done)

## Key API Endpoints
- `POST /api/extract-text` — Extract text from PDF/image
- `POST /api/analyze/text` — Analyze text script (with caching)
- `POST /api/analyze/scene` — Analyze single scene (with caching)
- `POST /api/adjust-takes/{id}` — Adjust acting takes with stacking feedback
- `POST /api/parse-scenes` — Parse full script into scenes
- `POST /api/parse-lines` — Deterministic line extraction (zero GPT)
- `POST /api/scripts/create` — Initialize script record
- `GET /api/scripts/{id}` — Retrieve full script with breakdowns (sorted by scene_number)
- `GET /api/scripts` — List recent scripts
- `POST /api/tts/generate` — TTS audio (accepts voice_id)
- `GET /api/tts/voices` — 10 curated voices
- `POST /api/check-cache` — Check if a breakdown is cached
- `POST /api/check-cache/batch` — Check cache status for multiple scenes
- `GET /api/debug/pipeline` — System health check (no GPT call)

## Prioritized Backlog
### P2 (Next)
- [ ] Cheapest useful continuous read-through (My Lines + cues, play/pause/skip, deterministic only)

### Frozen (Do Not Build)
- [ ] CD POV
- [ ] Take Comparison Tool
- [ ] Auto voice suggestions
- [ ] Audition Tracker
- [ ] User accounts & auth
- [ ] Memorization Timer

## Current Status
- **Parser**: Stable. P0 approved. 16/16 regression tests. (MORE)/(CONT'D) joins working.
- **Ordering**: P1 fixed. Episodes display in correct ascending order.
- **App**: Fully functional, no known bugs.
- **Priority**: P2 — Continuous read-through. Frozen features must not be touched.
