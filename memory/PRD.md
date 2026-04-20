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
| 3 | Deterministic document classification + manual override | NOT STARTED | No |
| 4 | Script cleaning + review/edit/confirm | NOT STARTED (reuse existing clean_script_text) | No |
| 5 | Character detection + selection | NOT STARTED | No |
| 6 | Line extraction + cue pair generation | NOT STARTED (reuse existing extract_character_lines) | No |
| 7 | Prep Dashboard basics (At-a-Glance, Scenes/My Lines) | NOT STARTED | No |
| 8 | Read-Through | NOT STARTED | No |
| 9 | Export | NOT STARTED | No |
| 10 | Prep generation (wardrobe, self-tape, action items) | NOT STARTED | Yes (1 call) |

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

## Implementation Rules
- One feature at a time
- Each feature validated end-to-end before next
- Mobile-first at every step
- No assumptions — everything testable
- confirmed cleaned_text is the ONLY source of truth for all downstream features

## Test Reports
- Feature #1 (Project CRUD): /app/test_reports/iteration_25.json — 19/19 passed
- Feature #2 (Document Upload): /app/test_reports/iteration_26.json — 29/29 passed
