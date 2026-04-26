# Execution Plan

Last updated: 2026-04-26

## Quick Scan

- Current sprint goal: improve product behavior without breaking the deterministic core.
- Batch 1 cleanup/correctness is complete.
- Batch 2 partial search is complete.
- Batch 3 routing/session guard is complete.
- Batch 4 FAQ routing hardening and price false-positive fix is complete.
- Batch 5 TravelWeb demo data and contract fixes are complete.
- Scope: next 1-2 implementation batches only.
- Non-goal: no full rewrite, no LLM-driven search logic.

## Sprint Goal

- Make the current runtime more useful with deterministic search and real TravelWeb demo data.
- Keep cleanup gains from batch 1 stable.
- Keep partial search stable.
- Stop knowledge/FAQ-like queries and non-money quantities from polluting tour-search session state.
- Keep Python standalone and TravelWeb MSSQL data paths clearly separated.

## Batch 1 — Cleanup And Correctness

- Status: Completed
- Result:
  - extractor sentinel `"None"` removed from the main flow
  - duplicate normalization removed from the main path
  - `/chat` validation improved
  - local-dev CORS added
  - `/reset` added
  - tests updated and passing

## Batch 2 — Partial Search

- Status: Completed
- Purpose:
  - make the chatbot useful before all optional fields are known
- Likely files to touch:
  - `pipelines/tour_pipeline.py`
  - `services/tour_search_service.py`
  - `schemas/chat_response.py`
  - tests
- Acceptance criteria:
  - search can run when `location` is present and at least one of `time` or `price` exists
  - response makes missing optional filters explicit
  - existing structured response contract remains usable
- Result:
  - `partial_search` status added to the main response contract
  - destination-only requests still return `missing_info`
  - session now survives `partial_search` and resets after full `success`
- Risks:
  - UX policy ambiguity
  - need to avoid weakening deterministic behavior
- Non-goals:
  - no DB integration yet
  - no ranking redesign yet

## Batch 3 — Knowledge Routing And Session Guard

- Status: Completed
- Purpose:
  - prevent destination-based FAQ/knowledge questions from being treated as tour searches
- Likely files touched:
  - `pipelines/tour_pipeline.py`
  - `tests/test_pipeline_sessions.py`
  - project memory docs
- Acceptance criteria:
  - `Đà Lạt có món gì` routes to FAQ/fallback knowledge response
  - FAQ-like destination queries do not write `location` into session
  - later budget/time fragments do not inherit destination from a FAQ turn
  - explicit tour queries with food words, such as `Có tour nào Đà Lạt ăn uống ngon không`, still enter search flow
  - full `no_results` resets session
- Result:
  - deterministic keyword guard now runs before model/fallback intent
  - missing-info messages no longer call Gemini
  - full `no_results` resets session state
- Risks:
  - keyword guard can miss unseen knowledge wording
  - hybrid queries still need product policy decisions over time
- Non-goals:
  - no FAQ embedding/model replacement
  - no TravelWeb integration changes

## Batch 4 — FAQ Routing Hardening And Price False Positives

- Status: Completed
- Purpose:
  - handle more valid travel FAQ/service phrasings without routing them into tour search
  - stop short non-money quantities from being treated as budgets
- Files touched:
  - `pipelines/tour_pipeline.py`
  - `extractors/extract_price.py`
  - `tests/test_pipeline_sessions.py`
  - `tests/test_extract_price.py`
  - docs/project memory
- Acceptance criteria:
  - `Hà Nội có những quán cà phê nổi tiếng nào nên ghé thăm?` returns FAQ/knowledge behavior
  - `Tôi có thể mang theo thú cưng khi đi tour không?` returns FAQ/policy behavior
  - `Tour có wifi trên xe không?` does not trigger tour search
  - `Trẻ em dưới 5 tuổi có phải mua vé không?` does not parse `5` as budget
  - explicit search query `Có tour nào Đà Lạt ăn uống ngon không` still enters search flow
  - Playwright UI verification on `localhost:3000` confirms the user-facing behavior
- Result:
  - broader deterministic FAQ candidate policy
  - metadata FAQ ranking now includes lightweight lexical overlap scoring
  - price extractor requires explicit money units/suffixes or large currency-like numbers
  - TravelWeb UI showed FAQ answers for cafe and child-ticket questions
  - TravelWeb UI showed `no_results` for full Dalat search because MSSQL had no matching tour, while Python sample search still returned results directly
- Non-goals:
  - no PhoBERT training
  - no real DB integration
  - no FAQ embedding replacement

## Batch 5 — TravelWeb Demo Data And Contract Fixes

- Status: Completed
- Purpose:
  - make chatbot demos return real TravelWeb DB tours instead of frequent `no_results`
  - fix contract mismatches between Python entities and TravelWeb MSSQL filters
- Files touched:
  - TravelWeb `sql_chatbot_demo_tours_dalat_phuyen_hue.sql`
  - TravelWeb `backend/services/chatTourSearchService.js`
  - TravelWeb `backend/services/chatResponseMapper.js`
  - TravelWeb `backend/tests/chatIntegration.test.js`
  - Python `extractors/extract_price.py`
  - Python `tests/test_extract_price.py`
  - docs/project memory
- Result:
  - added 36 focused idempotent demo tours to MSSQL
  - coverage is 12 tours each for Đà Lạt, Phú Yên, Huế
  - TravelWeb DB matching now uses Vietnamese `location` before slug `destination_normalized`
  - `price_min`-only filters no longer become exact price filters in Express
  - price extractor no longer parses `năm 2026 trên 5tr` as `2026tr`
  - partial-search messages now reflect DB results when DB returns tours
  - Playwright UI verified tour cards for Đà Lạt under 5tr, Đà Lạt over 5tr, and Huế partial search
- Non-goals:
  - no Python direct MSSQL repository adapter
  - no large TravelWeb refactor
  - no model training

## Batch 6 — Component Health Reporting

- Status: Next recommended batch
- Purpose:
  - make `/health` report degraded components instead of only `{"status":"ok"}`
- Likely files to touch:
  - `server.py`
  - `pipelines/tour_pipeline.py`
  - `tests/test_api.py`
- Acceptance criteria:
  - health reports FAQ retrieval availability
  - health reports intent model vs rule fallback
  - health reports tour search/repository availability
  - response stays lightweight and does not perform slow model inference
- Non-goals:
  - no external monitoring stack
  - no startup hard-fail for optional Gemini

## Batch 7 — TravelWeb Contract Verification

- Purpose:
  - keep verifying how the Express backend and React UI consume `ChatResponse`
- Trigger:
  - TravelWeb repo is available in the workspace
- Likely files to inspect/touch:
  - `backend/controller/chatController.js`
  - `backend/routes/chatRoutes.js`
  - frontend chatbot caller/component
  - backend DB query layer
- Acceptance criteria:
  - `faq` and `missing_info` do not trigger tour DB queries
  - `partial_search`, `success`, and `no_results` are rendered distinctly
  - DB query/filter mapping from `entities` is explicit and tested
  - no stale Python message contradicts DB tour results
- Non-goals:
  - no guessed MSSQL integration without the actual repo

## Batch 8 — Repository Readiness And Richer Fixtures

- Purpose:
  - reduce the gap between current JSON adapter behavior and realistic search scenarios
- Likely files to touch:
  - `repositories/tour_repository.py`
  - `data/tours_sample.json` or new test fixtures
  - destination normalization or fixture helpers
  - tests
- Acceptance criteria:
  - repository contract stays stable
  - runtime can operate on more realistic sample data
  - ranking/filter tests cover richer scenarios
- Success condition:
  - no code has to guess external DB/API details
  - fixture coverage is good enough to surface ranking and normalization issues locally
- Risks:
  - external integration may still be blocked
  - larger fixture data may expose ranking issues
- Non-goals:
  - no guessed DB integration
  - no FAQ model change yet

## Batch 9 — Python Real Repository Adapter If Needed

- Trigger:
  - Python backend must query a real source directly instead of letting TravelWeb own DB truth
- Purpose:
  - replace or complement `JsonTourRepository` with a real adapter only if product architecture needs it
- Likely files to touch:
  - `repositories/tour_repository.py` or a new repository adapter module
  - integration tests
  - config docs
- Acceptance criteria:
  - real data path is wired without changing deterministic search policy
  - mapping from source fields into `Tour` is explicit and tested
- Non-goals:
  - no business logic migration into LLM
  - no full backend rewrite

## Intentionally Postponed

- session externalization
- evaluation harness
- observability work
  - except lightweight `/health` component reporting

These matter, but they are not all actionable in the current repo state.

## Immediate Success Check

After batch 5, the repo should be in this state:

- partial-search behavior remains stable
- knowledge routing and price guards remain stable
- `/health` exposes component state without slowing normal startup
- repository contract is still clean

## Read This Next

1. `WORKLOG.md`
2. `ROADMAP.md`
3. `PROJECT_STATE.md`
