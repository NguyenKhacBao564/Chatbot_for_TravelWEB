# Architecture

Last updated: 2026-04-23

## Quick Scan

- Request flow: FastAPI -> `TourRetrievalPipeline` -> NLP path -> business search or FAQ path -> `ChatResponse`.
- Gemini is phrasing-only.
- Deterministic business logic lives in `services/tour_search_service.py`.
- Tour data access is abstracted behind `repositories/tour_repository.py`.
- Main technical debt: orchestration is centralized in one pipeline class.

## Runtime Flow

1. `server.py` receives `POST /chat` with `query` and `user_id`.
2. `TourRetrievalPipeline.get_tour_response()` classifies intent.
3. Pipeline extracts entities from query + session:
   - location
   - time
   - price
4. `services/entity_normalizer.py` converts extracted values into business filters.
5. If `location` is missing, or only `location` is known without `time` or `price`, pipeline returns `status="missing_info"`.
6. If intent is `out_of_scope`, pipeline routes into FAQ retrieval and returns `status="faq"`.
7. If `location` plus at least one optional filter is present, pipeline builds `TourSearchFilters` and calls `TourSearchService.search()`.
8. If search ran with one optional filter missing, pipeline returns `status="partial_search"` and keeps the missing optional field in `missing_fields`.
9. If search ran with all filters present, pipeline returns `status="success"` or `status="no_results"`.
10. Pipeline returns `ChatResponse`.

## Layer Responsibilities

### API Layer

- File: `server.py`
- Owns:
  - FastAPI app
  - endpoint wiring
  - pipeline singleton creation
  - request validation
  - local-dev CORS
- Current caveats:
  - validation is basic rather than business-aware
  - pipeline is still a module-level singleton
  - CORS policy is local-dev friendly, not production-specific

### NLP Layer

- Intent:
  - primary: PhoBERT classifier
  - fallback: heuristic inference
- Entity extraction:
  - location: VnCoreNLP or alias fallback
  - time: regex + relative date rules
  - price: deterministic parsing
- FAQ retrieval:
  - FAISS + metadata + embedding model

### Business Search Layer

- `TourRepository` protocol defines read-only tour access.
- `JsonTourRepository` is the current adapter.
- `TourSearchService` applies deterministic filtering and ranking.
- `missing_fields` now has two meanings that are both intentional:
  - search blocker for `missing_info`
  - optional-but-still-missing filter for `partial_search`

## Gemini Boundary

Allowed:

- phrasing missing-info prompts
- phrasing search intro text
- rephrasing FAQ answers

Not allowed:

- deciding which tours match the query
- overriding deterministic filters
- inventing business facts or tour attributes

## Verified Technical Debt

- `TourRetrievalPipeline` is still a God Object by responsibility count:
  - intent loading/inference
  - session handling
  - entity extraction
  - FAQ routing
  - tour search orchestration
  - response formatting
- Partial-search policy is encoded inside the pipeline rather than a smaller dedicated policy object.
- Session design is convenient for local dev but weak for shared runtime:
  - per-process memory
  - no lock
  - no cleanup job
- Session is intentionally preserved after `partial_search` and reset only after full `success`.
- Destination normalization is hardcoded and narrow.
- `extract_location()` only returns the first detected location and does not distinguish departure vs destination.
- FAQ threshold is still a hardcoded constant in `RetrievalPipeline`.
- `RetrievalPipeline.get_retrieved_context()` is now legacy-style helper logic; main flow uses `retrieve()`.

## Architecture Strengths

- Clear separation between NLP interpretation and business filtering.
- Structured response contract is already frontend-friendly.
- Repository boundary is in place before real DB integration.
- Graceful degradation keeps local dev/test possible.
- Partial search makes multi-turn collection usable without weakening deterministic search.

## Architecture Weaknesses

- Destination-only requests still cannot search until time or budget is known.
- FAQ and tour flows are still coordinated inside one class rather than smaller use-case services.
- Repo still lacks a real website-tour data integration path.

## Read This Next

1. `DATASET_AND_MODELS.md`
2. `DECISIONS.md`
3. `EXECUTION_PLAN.md`
