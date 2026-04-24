# Worklog

Last updated: 2026-04-25

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

## 2026-04-23 - Batch 2 partial search

- Session goal:
  - make tour search useful when users provide destination plus only one optional constraint
- Main changes:
  - changed search gating from `location + time + price` to `location + (time or price)`
  - added `status="partial_search"` to represent deterministic search with one missing optional filter
  - kept `missing_info` for missing destination or destination-only queries
  - preserved session state after `partial_search` and reset only after full `success`
  - updated message policy for missing location, destination-only, partial-search success, partial-search no-results, and full-search outcomes
- Files changed:
  - `pipelines/tour_pipeline.py`
  - `schemas/chat_response.py`
  - `tests/test_pipeline_sessions.py`
  - `README.md`
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/ARCHITECTURE.md`
  - `docs/ai_context/DECISIONS.md`
  - `docs/ai_context/ROADMAP.md`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `docs/ai_context/WORKLOG.md`
- Tests added/updated:
  - location-only gating
  - `location + time`
  - `location + price`
  - full search with all filters
  - time-only, price-only, and `time + price` without location
  - partial-search no-results
  - multi-turn session accumulation through partial search into full search
  - full suite passes
- Blockers / caveats:
  - no real website repository yet
  - destination-only search is still intentionally blocked
  - partial-search responses use the same `tours` field for both non-empty and empty results, so callers must inspect both `status` and `tours`
- Next exact step:
  - improve repository readiness and richer fixtures without guessing external DB/API details

## 2026-04-24 - Batch 3 knowledge routing and session guard

- Session goal:
  - stop FAQ-like destination queries from entering the tour-search session flow
  - reduce messaging instability on missing-info turns
- Main changes:
  - added deterministic knowledge-query guard before PhoBERT/fallback search routing
  - kept explicit tour queries with food/knowledge words in the tour-search path
  - prevented queries like `Đà Lạt có món gì` from writing `location` into session
  - reset session after full `no_results`, not only after `success`
  - made `missing_info` messages deterministic and removed Gemini calls from that path
- Files changed:
  - `pipelines/tour_pipeline.py`
  - `tests/test_pipeline_sessions.py`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/DECISIONS.md`
  - `docs/ai_context/WORKLOG.md`
- Tests added/updated:
  - destination food question routes to FAQ without polluting session
  - FAQ turn followed by budget fragment does not inherit destination
  - explicit tour query with food words still enters search flow
  - full `no_results` resets session
  - missing-info message path does not call Gemini
- Blockers / caveats:
  - knowledge guard is keyword-based and should be expanded with real logs
  - TravelWeb repo was not available in this workspace, so Express/UI contract remains unverified
- Next exact step:
  - verify TravelWeb backend/frontend status handling if the repo is added; otherwise continue repository readiness and richer fixture work

## 2026-04-25 - Batch 4 FAQ routing hardening and price false-positive fix

- Session goal:
  - fix verified UI failures where valid FAQ questions returned generic out-of-scope text or polluted tour-search state
- Main changes:
  - broadened deterministic FAQ candidate routing for recommendation/service/policy questions
  - added FAQ metadata lexical overlap scoring so broad service tags do not always return the first tag match
  - prevented short non-money quantities from being parsed as budgets
  - kept explicit tour-search queries in search mode
- Files changed:
  - `pipelines/tour_pipeline.py`
  - `extractors/extract_price.py`
  - `tests/test_pipeline_sessions.py`
  - `tests/test_extract_price.py`
  - `README.md`
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `docs/ai_context/WORKLOG.md`
- Tests added/updated:
  - cafe recommendation FAQ routing
  - pet policy FAQ routing with `tour` word present
  - wifi service FAQ fallback
  - child-ticket/age question does not parse `5` as budget
  - price parser accepts real money phrases and rejects age/person/day counts
- Verification:
  - `python -m pytest tests/test_extract_price.py tests/test_pipeline_sessions.py -q` -> 34 passed
  - `python -m pytest -q` -> 45 passed
  - Playwright UI on `http://localhost:3000`:
    - cafe query returned a concrete Hanoi cafe FAQ answer
    - child-ticket query returned age policy FAQ answer, not missing budget guidance
    - full Dalat search stayed in search path and returned TravelWeb `no_results` because MSSQL had no matching tour
- Blockers / caveats:
  - FAQ routing is still rule-based and should be evaluated with real query logs
  - TravelWeb DB contents can differ from Python sample tour data
  - `/health` still only returns a shallow status
- Next exact step:
  - implement component health/readiness reporting for `/health`

## Read This Next

1. `EXECUTION_PLAN.md`
2. `PROJECT_STATE.md`
3. `ROADMAP.md`
