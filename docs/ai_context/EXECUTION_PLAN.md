# Execution Plan

Last updated: 2026-04-23

## Quick Scan

- Current sprint goal: improve product behavior without breaking the deterministic core.
- Batch 1 cleanup/correctness is complete.
- Batch 2 partial search is complete.
- Scope: next 1-2 implementation batches only.
- Non-goal: no full rewrite, no real DB integration in this sprint, no LLM-driven search logic.

## Sprint Goal

- Make the current runtime more useful before real DB integration lands.
- Keep cleanup gains from batch 1 stable.
- Keep partial search stable and improve repository realism without guessing unavailable external details.

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

## Batch 3 — Repository Readiness And Richer Fixtures

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

## Batch 4 — Real Repository Integration When Source Details Exist

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

After batch 3, the repo should be in this state:

- partial-search behavior remains stable
- repository contract is still clean
- richer fixtures and tests make the next integration step safer

## Read This Next

1. `WORKLOG.md`
2. `ROADMAP.md`
3. `PROJECT_STATE.md`
