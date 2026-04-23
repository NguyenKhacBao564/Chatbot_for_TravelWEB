# Architecture

Last updated: 2026-04-23

## Quick Scan

- Request flow: FastAPI -> `TourRetrievalPipeline` -> NLP path -> business search or FAQ path -> `ChatResponse`.
- Gemini is a phrasing layer only.
- Deterministic business logic lives in `services/tour_search_service.py`.
- Tour data access is abstracted behind `repositories/tour_repository.py`.
- Biggest current coupling: one orchestrator still coordinates most runtime decisions.

## Request Lifecycle

1. `server.py` receives `POST /chat` with `query` and `user_id`.
2. `TourRetrievalPipeline.get_tour_response()` classifies intent.
3. Pipeline extracts raw entities from the query and current session:
   - location
   - time
   - price
4. `services/entity_normalizer.py` converts raw values into business filters:
   - `destination_normalized`
   - `date_start`
   - `date_end`
   - `price_min`
   - `price_max`
5. If required fields are missing, pipeline returns `status="missing_info"`.
6. If intent is `out_of_scope`, pipeline uses FAQ retrieval and returns `status="faq"`.
7. If entities are complete, pipeline builds `TourSearchFilters` and calls `TourSearchService.search()`.
8. Pipeline returns `ChatResponse` with:
   - `status`
   - `message`
   - `entities`
   - `missing_fields`
   - `tours`
   - `faq_sources`

## NLP Layer

- Intent:
  - primary path: PhoBERT classifier loaded from `training/phobert_intent_finetuned`
  - fallback path: rule-based intent inference from query content
- Entity extraction:
  - location: `extractors/extract_location.py`
  - time: `extractors/extract_time.py`
  - price: `extractors/extract_price.py`
- Normalization:
  - destination aliasing and slugging
  - date range conversion from normalized extractor output
  - price ceiling/range interpretation
- FAQ retrieval:
  - `pipelines/retrieval.py`
  - FAISS + metadata + embedding model

## Business Search Layer

- Repository:
  - `TourRepository` protocol defines read-only access
  - `JsonTourRepository` is the current adapter
- Search service:
  - exact normalized destination filter first
  - date window filter second
  - price min/max filter third
  - simple weighted ranking after filtering

Current ranking inputs:

- destination match
- date closeness
- price closeness
- optional `rating`
- optional `popularity`

## Gemini Boundary

Gemini is currently allowed to:

- phrase missing-info prompts
- phrase search result intro text
- rephrase FAQ answer text

Gemini is not supposed to:

- choose which tours match the query
- override deterministic filters
- invent business facts not present in repository/FAQ data

## Strengths

- Clear separation between NLP interpretation and business filtering.
- Structured response format is frontend-friendly.
- Repository abstraction makes future DB integration cleaner.
- Runtime degrades gracefully when some optional dependencies are missing.

## Weak Points

- `TourRetrievalPipeline` is still a broad orchestrator and holds multiple responsibilities.
- Missing-info policy is rigid: search waits for all fields instead of supporting partial search.
- Session storage is not externalized.
- FAQ and tour flows still share orchestration state rather than being isolated services.

## Technical Debt / Coupling

- Destination normalization depends on a small hardcoded alias map.
- FAQ retrieval threshold is a magic constant in `RetrievalPipeline`.
- Rule fallback behavior and PhoBERT behavior may drift over time.
- Search service assumes repository returns already-clean tour rows.

## Read This Next

1. `DATASET_AND_MODELS.md`
2. `DECISIONS.md`
3. Root `README.md`

