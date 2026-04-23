# Worklog

Last updated: 2026-04-23

## Quick Scan

- This file is append-only.
- Purpose: preserve short session memory for future AI sessions.
- Keep entries factual: what changed, why, what to do next.

## Entry Template

### YYYY-MM-DD - Session title

- Main changes:
- Files touched:
- Why:
- Next useful step:

## 2026-04-23 - Post-refactor baseline and AI memory docs

- Main changes:
  - Backend has already been refactored into hybrid NLP + deterministic search.
  - Structured response contract is in place.
  - New AI-readable docs were added under `docs/ai_context/`.
- Files touched:
  - `server.py`
  - `pipelines/tour_pipeline.py`
  - `pipelines/retrieval.py`
  - `services/`
  - `repositories/`
  - `schemas/`
  - `tests/`
  - `docs/ai_context/`
- Why:
  - move the repo from prototype-only behavior toward a cleaner backend shape
  - make future AI sessions faster and less repetitive
- Next useful step:
  - integrate the real website tour data source
  - then relax the current “must have location + time + price” search gate

## Read This Next

1. `PROJECT_STATE.md`
2. `ROADMAP.md`
3. `DECISIONS.md`

