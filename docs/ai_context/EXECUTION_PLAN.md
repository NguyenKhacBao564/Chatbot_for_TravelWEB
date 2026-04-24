# Execution Plan

Last updated: 2026-04-24

## Quick Scan

- Current sprint goal: improve product behavior without breaking the deterministic core.
- Batch 1 cleanup/correctness is complete.
- Batch 2 partial search is complete.
- Batch 3 routing/session guard is complete.
- Scope: next 1-2 implementation batches only.
- Non-goal: no full rewrite, no real DB integration in this sprint, no LLM-driven search logic.

## Sprint Goal

- Make the current runtime more useful before real DB integration lands.
- Keep cleanup gains from batch 1 stable.
- Keep partial search stable.
- Stop knowledge/FAQ-like queries from polluting tour-search session state.

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

## Batch 4 — TravelWeb Contract Verification

- Purpose:
  - verify how the Express backend and React UI consume `ChatResponse`
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
- Non-goals:
  - no guessed MSSQL integration without the actual repo

## Batch 5 — Repository Readiness And Richer Fixtures

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

## Batch 6 — Real Repository Integration When Source Details Exist

- Trigger:
  - concrete website DB or API access details are available
- Purpose:
  - replace or complement `JsonTourRepository` with a real adapter
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

- FAQ embedding stack replacement
- session externalization
- evaluation harness
- observability work

These matter, but they are not all actionable in the current repo state.

## Immediate Success Check

After batch 5, the repo should be in this state:

- partial-search behavior remains stable
- knowledge routing remains stable
- repository contract is still clean
- richer fixtures and tests make the next integration step safer

## Read This Next

1. `WORKLOG.md`
2. `ROADMAP.md`
3. `PROJECT_STATE.md`
