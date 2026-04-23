# Worklog

Last updated: 2026-04-23

## Quick Scan

- This file is append-only.
- Each entry should let a future AI understand the latest session in under 2 minutes.
- Prefer concrete facts over narrative.

## Entry Template

### YYYY-MM-DD - Short Session Title

- Session goal:
- Main changes:
- Files changed:
- Tests added/updated:
- Blockers / caveats:
- Next exact step:

## 2026-04-23 - Post-refactor baseline and AI memory docs

- Session goal:
  - capture the refactored backend shape and make the repo easier for future AI sessions to parse
- Main changes:
  - backend already moved to hybrid NLP + deterministic search
  - structured response contract established
  - AI-readable docs added under `docs/ai_context/`
- Files changed:
  - `server.py`
  - `pipelines/tour_pipeline.py`
  - `pipelines/retrieval.py`
  - `services/`
  - `repositories/`
  - `schemas/`
  - `tests/`
  - `docs/ai_context/`
- Tests added/updated:
  - API smoke tests
  - parser tests
  - tour search tests
  - session isolation tests
- Blockers / caveats:
  - no real tour repository yet
  - strict search gating still in place
  - some correctness issues remained in main flow
- Next exact step:
  - execute cleanup/correctness batch from `EXECUTION_PLAN.md`

## 2026-04-23 - Batch 1 cleanup and correctness

- Session goal:
  - refine the AI docs into an execution-ready source of truth
  - implement the first small cleanup/correctness batch
- Main changes:
  - absorbed key verified insights from `ampfeedback.md` into `docs/ai_context/`
  - added `EXECUTION_PLAN.md`
  - removed extractor sentinel `"None"` behavior from the main pipeline path
  - removed duplicate normalization in `TourRetrievalPipeline`
  - added stronger `/chat` request validation
  - added local-dev CORS config
  - added `POST /reset`
- Files changed:
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/ARCHITECTURE.md`
  - `docs/ai_context/DATASET_AND_MODELS.md`
  - `docs/ai_context/DECISIONS.md`
  - `docs/ai_context/ROADMAP.md`
  - `docs/ai_context/WORKLOG.md`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `server.py`
  - `pipelines/tour_pipeline.py`
  - `extractors/extract_location.py`
  - `extractors/extract_time.py`
  - `extractors/extract_price.py`
  - `services/entity_normalizer.py`
  - `tests/test_api.py`
  - `tests/test_extract_price.py`
  - `tests/test_extract_time.py`
- Tests added/updated:
  - validation tests for blank query and invalid `user_id`
  - reset endpoint test
  - local CORS header test
  - parser tests for real `None` behavior
  - full suite passes
- Blockers / caveats:
  - real tour repository is still missing
  - search still requires `location + time + price`
  - location extraction still collapses to the first detected place
- Next exact step:
  - implement partial search policy after deciding minimum required fields

## Read This Next

1. `EXECUTION_PLAN.md`
2. `PROJECT_STATE.md`
3. `ROADMAP.md`

