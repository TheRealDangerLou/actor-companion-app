# Actor's Companion - PRD

## Core Vision
Actor's Companion is a mobile-first actor command center that turns messy audition or production material into a crystal-clear prep path so the actor knows exactly what to do.

## Core User Needs
1. Understand the material
2. Know exactly what to do
3. Learn their lines
4. Rehearse efficiently
5. Execute the audition confidently

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui + framer-motion
- **Backend**: FastAPI (Python) + MongoDB (Motor async)
- **AI**: GPT-5.2 via Emergent LLM Key (prep generation only — 1 call per project)
- **PDF/OCR**: pymupdf
- **Design**: Mobile-first (390x844 primary viewport)

## Data Model
- **`projects`**: {id, title, role_name, mode, selected_character, audition_date/time/format, document_ids, prep_output, created_at, updated_at}
- **`documents`**: {id, project_id, type, filename, original_text, cleaned_text, is_confirmed, file_url, created_at}
- No separate `scenes` collection in Phase 1. Scenes derived from confirmed cleaned_text at document level.

## Product Modes
- **Audition Mode**: sides, instructions, wardrobe notes, quick breakdowns, line learning
- **Booked Role Mode**: full scripts, read-through, scene rehearsal, deeper work (Phase 2)

## Phase 1 Build Order (Audition-First MVP)

| # | Feature | Status | GPT? |
|---|---------|--------|------|
| 1 | Project CRUD | COMPLETE (19/19 tests) | No |
| 2 | Multi-document upload + OCR extraction | COMPLETE (29/29 tests) | No |
| 3 | Deterministic document classification + manual override | COMPLETE (33/33 tests) | No |
| 4 | Script cleaning + review/edit/confirm | COMPLETE (14/14 backend + full frontend flow) | No |
| 5 | Character detection + selection | COMPLETE (9/9 backend + full frontend flow, routing fix verified) | No |
| 6 | Line extraction + cue pair generation | COMPLETE (9/9 backend + full frontend flow) | No |
| 6.5 | Review My Lines (trust layer) | COMPLETE (8/8 backend + 18/18 frontend) | No |
| QC | Quick Coach (optional coaching panel) | COMPLETE (6/6 backend + 11/11 frontend) | Yes (1 cached GPT call) |
| CT | Content-type detection (script vs breakdown) | COMPLETE (10/10 backend + 5/5 frontend) | No |
| 7 | Prep Dashboard basics (At-a-Glance, Scenes/My Lines) | NOT STARTED | No |
| 8 | Read-Through | NOT STARTED | No |
| 9 | Export | NOT STARTED | No |
| 10 | Prep generation (wardrobe, self-tape, action items) | COMPLETE (5/5 backend + full frontend) | Yes (1 cached GPT call) |

## Document Types
- sides, instructions, wardrobe, notes, reference, unknown

## Intentionally Postponed
- Advanced rehearsal modes (blur ladder, memorization timer)
- TTS / Scene Reader / voice
- Deep analysis (beats, tactics, subtext)
- Take generation / adjustment
- Calendar integration / push reminders
- User accounts / auth
- Audition tracker / history
- CD POV / take comparison
- Offline PWA sync

## Key API Endpoints (Phase 1)
- `POST /api/projects` — create project
- `GET /api/projects` — list projects (includes document_count)
- `GET /api/projects/{id}` — get project with documents
- `PUT /api/projects/{id}` — update project
- `DELETE /api/projects/{id}` — delete project + documents
- `POST /api/projects/{id}/documents` — upload file or paste text
- `GET /api/projects/{id}/documents` — list documents (excludes text for performance)
- `GET /api/documents/{id}` — get single document with full text
- `PUT /api/documents/{id}/type` — change document type
- `DELETE /api/documents/{id}` — delete document
- `POST /api/documents/{id}/clean` — deterministic text cleaning
- `POST /api/projects/{id}/clean-all` — clean all docs in project
- `POST /api/documents/{id}/confirm` — confirm cleaned text (source of truth)
- `POST /api/projects/{id}/confirm-all` — batch confirm all docs

- `POST /api/projects/{id}/detect-characters` — scan confirmed docs for characters (ranked by frequency)
- `POST /api/projects/{id}/extract-lines` — extract lines + cue pairs grouped by scene for selected character
- `PUT /api/projects/{id}/reviewed-lines` — save user-edited line pairs
- `GET /api/projects/{id}/reviewed-lines` — retrieve saved reviewed lines
- `POST /api/projects/{id}/quick-coach` — generate/retrieve cached coaching notes (1 GPT call)
- `POST /api/projects/{id}/detect-content-type` — detect script vs breakdown
- `POST /api/projects/{id}/extract-breakdown` — extract labeled sections from casting breakdowns
- `POST /api/projects/{id}/prep-generation` — generate/retrieve cached prep (wardrobe, self-tape, actions)

## Implementation Rules
- One feature at a time
- Each feature validated end-to-end before next
- Mobile-first at every step
- No assumptions — everything testable
- confirmed cleaned_text is the ONLY source of truth for all downstream features

## Test Reports
- Feature #1 (Project CRUD): /app/test_reports/iteration_25.json — 19/19 passed
- Feature #2 (Document Upload): /app/test_reports/iteration_26.json — 29/29 passed
- Feature #3 (Classification): /app/test_reports/iteration_27.json — 33/33 passed
- Feature #4 (Clean/Review/Confirm): /app/test_reports/iteration_28.json — 14/14 backend + full frontend flow
- Feature #5 (Character Detection): /app/test_reports/iteration_29.json — 8/8 backend + full frontend flow
- Feature #5 bugfix (Routing loop + filtering): /app/test_reports/iteration_30.json
- Feature #6 (Line Extraction + Rehearsal): /app/test_reports/iteration_31.json — 9/9 backend + full frontend flow
- Feature #6.5 (Review My Lines): /app/test_reports/iteration_32.json — 8/8 backend + 18/18 frontend
- Quick Coach: /app/test_reports/iteration_33.json — 6/6 backend + 11/11 frontend
- Content-Type Detection: /app/test_reports/iteration_34.json — 10/10 backend + 5/5 frontend
- Prep Generation (#10): /app/test_reports/iteration_35.json — 5/5 backend + full frontend
