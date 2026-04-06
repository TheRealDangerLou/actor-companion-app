# Actor's Companion - PRD

## Problem Statement
Build a clean, fast web app called "Actor's Companion" where actors upload audition sides (text, image, PDF) and get a reliable tool to go from script to confident performance as fast as possible. Core user needs: understand the scene, learn lines reliably, rehearse hands-free, prep auditions and self-tapes quickly.

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI (Python) + MongoDB (Motor async)
- **AI**: GPT-5.2 via Emergent LLM Key (scene analysis only)
- **TTS**: ElevenLabs (SceneReader hands-free mode)
- **PDF**: pymupdf (OCR extraction)

## What's Implemented

### Phase 1: Script Cleaning Layer (Apr 2026) — COMPLETE
- **`clean_script_text()`** — deterministic pure function, zero GPT, zero credits
  - Strips page number lines (e.g., `"15."`)
  - Joins `(MORE)/(CONT'D)` page-break splits into single speech blocks
  - Fixes concatenated scene numbers (`"20INT."` → `"INT."`)
  - Normalizes whitespace (strips indentation, collapses blank lines)
  - Ensures blank lines before character names (fixes action-as-dialogue absorption)
  - Strips `(CONT'D)` from character names (preserves speaker attribution)
- **`cleaned_text` field** — stored on breakdown documents in MongoDB
  - Computed once, saved permanently
  - Becomes single source of truth for all downstream features
  - `get_script()` uses `cleaned_text` when available, falls back to `original_text`
- **Script Review Screen** (`ScriptReview.jsx`)
  - Opens automatically when loading any script
  - Shows cleaned text in preview mode with scene navigation tabs
  - **Editable** — user can manually correct any scene before confirming
  - Reset button restores auto-cleaned version
  - "Confirm All N Scenes" saves all cleaned text to MongoDB
  - "Review Script" button in ScriptOverview header for re-review
- **New API Endpoints:**
  - `POST /api/clean-text` — clean raw text (deterministic, zero cost)
  - `POST /api/clean-script` — clean all scenes of an existing script
  - `POST /api/save-cleaned-script` — batch save confirmed cleaned text
  - `POST /api/save-cleaned-text` — save single scene's cleaned text

### Parser & Trust Layer (Feb-Mar 2026)
- Deterministic `extract_character_lines()` — regex pattern matching, zero GPT
- `(MORE)/(CONT'D)` joins, `"I..."` false name prevention, action verb detection
- 16/16 regression tests passing

### Scene/Episode Ordering (Mar 2026)
- `get_script()` sorts breakdowns by `scene_number`

### Analysis Engine (Feb 2026)
- Per-scene GPT analysis: summary, objective, stakes, beats, acting takes
- Genre-aware (vertical/soap project type)
- Caching layer with SHA256 hash + 72-hour TTL

### Rehearsal Modes
- My Lines (read-through with blur ladder)
- Line Run (tap-to-reveal flashcard drill)
- Scene Reader (TTS reads cues, actor speaks lines)
- Cue & Recall
- Progressive memorization (4 blur levels)

### Script Management
- Upload: PDF, image, pasted text
- Scene splitting (INT./EXT./EPISODE markers)
- Character name extraction
- Parallel batch analysis
- My Scripts list with persistence

## Key API Endpoints
- `POST /api/clean-text` — deterministic cleaning (zero GPT)
- `POST /api/clean-script` — clean all scenes of a script
- `POST /api/save-cleaned-script` — batch save cleaned text
- `POST /api/save-cleaned-text` — save single scene cleaned text
- `POST /api/extract-text` — PDF/image OCR
- `POST /api/analyze/text` — analyze with caching
- `POST /api/analyze/scene` — analyze single scene
- `POST /api/parse-lines` — deterministic line extraction
- `GET /api/scripts/{id}` — full script with breakdowns (uses cleaned_text)
- `GET /api/scripts` — list scripts
- `POST /api/tts/generate` — TTS audio
- `GET /api/tts/voices` — voice list

## Prioritized Backlog

### P2 (Next)
- [ ] Full uninterrupted read-through (My Lines + cues across all scenes, play/pause/skip)
- [ ] Line learner refinements
- [ ] Audition prep tools
- [ ] Self-tape setup suggestions

### Frozen (Do Not Build)
- [ ] CD POV
- [ ] Take Comparison
- [ ] Auto voice suggestions
- [ ] Audition Tracker
- [ ] User accounts & auth

## Testing
- Phase 1: 27/27 tests passed (17 backend, 10 frontend) — iteration_24.json
- Parser: 16/16 regression tests
- Backend test file: `/app/backend/tests/test_script_cleaning.py`
