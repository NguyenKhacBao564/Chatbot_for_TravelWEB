# Execution Plan

Last updated: 2026-04-23

## Quick Scan

- Current sprint goal: improve product behavior without breaking the deterministic core.
- Batch 1 cleanup/correctness is complete.
- Scope: next 1-2 implementation batches only.
- Non-goal: no full rewrite, no real DB integration in this sprint, no LLM-driven search logic.

## Sprint Goal

- Make the current runtime more useful before real DB integration lands.
- Keep cleanup gains from batch 1 stable.
- Move toward partial search and better repository realism next.

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
- Risks:
  - UX policy ambiguity
  - need to avoid weakening deterministic behavior
- Non-goals:
  - no DB integration yet
  - no ranking redesign yet

## Batch 3 — Repository Realism Upgrade

- Purpose:
  - reduce the gap between current JSON adapter and actual website data
- Likely files to touch:
  - `repositories/tour_repository.py`
  - `data/tours_sample.json` or a new adapter file
  - tests
- Acceptance criteria:
  - repository contract stays stable
  - runtime can operate on more realistic tour data
  - ranking/filter tests cover richer scenarios
- Risks:
  - external integration may still be blocked
  - larger fixture data may expose ranking issues
- Non-goals:
  - no major architectural split
  - no FAQ model change yet

## Intentionally Postponed

- real website DB/API repository integration
- FAQ embedding stack replacement
- session externalization
- evaluation harness
- observability work

These matter, but they are not the best next coding batch.

## Immediate Success Check

After the next batch, the repo should be in this state:

- chatbot can search with partial but still deterministic filters
- response contract still holds
- code remains ready for real repository integration

## Read This Next

1. `WORKLOG.md`
2. `ROADMAP.md`
3. `PROJECT_STATE.md`

