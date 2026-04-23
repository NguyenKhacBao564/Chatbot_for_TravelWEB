# Project State

Last updated: 2026-04-23

## Quick Scan

- Project: Vietnamese travel chatbot backend.
- Direction is still correct: hybrid NLP + deterministic business search.
- API entrypoints today: `GET /health`, `POST /chat`, `POST /reset`.
- Main runtime path: `server.py` -> `TourRetrievalPipeline` -> structured `ChatResponse`.
- Tour search works, but only against a JSON adapter with 6 sample tours.
- Search now runs with `location + time`, `location + price`, or all three filters.
- FAQ retrieval is separate from tour search and depends on FAISS artifacts plus `all-MiniLM-L6-v2`.

## What Is Working Now

- Structured `/chat` response for frontend consumption.
- `/reset` endpoint for clearing per-user session state.
- Basic request validation on `/chat`.
- Local-development CORS configuration.
- Intent path:
  - PhoBERT if local artifact + runtime deps are available
  - rule fallback otherwise
- Entity extraction for location, time, and price.
- Entity normalization into:
  - `destination_normalized`
  - `date_start`
  - `date_end`
  - `price_min`
  - `price_max`
- Deterministic tour filtering/ranking in `TourSearchService`.
- Partial search with structured response:
  - `status="partial_search"` when one optional filter is still missing
  - `missing_fields` carries the missing optional filter
- FAQ retrieval with metadata when FAISS stack is available.
- Test suite covering API smoke, validation, parsers, reset flow, partial search flows, session isolation, and multi-turn search progression.

## What Is Fallback / Mock / Adapter

- `JsonTourRepository` backed by `data/tours_sample.json`
  - this is not the website database
  - current sample size is 6 tours only
- Gemini
  - phrasing only
  - deterministic fallback text is used if key or SDK is missing
- VnCoreNLP location extraction
  - alias fallback is used if VnCoreNLP is unavailable
- PhoBERT intent
  - rule fallback is used if model artifact or runtime deps are unavailable
- FAQ retrieval
  - disabled if FAISS/numpy/sentence-transformers are unavailable

## Known Code-Level Risks

- `TourRetrievalPipeline` is still a large orchestrator and remains the main coupling point.
- Session state is:
  - in-memory
  - per-process
  - unsynchronized
- Search still depends on `location` as the only hard requirement and will not run on destination-only queries.
- `extract_location()` still returns only the first detected location.
- Destination normalization is still based on a small hardcoded alias map.
- FAQ retrieval still uses:
  - a fixed threshold
  - a non-Vietnamese-specific embedding model

## Current Engineering Focus

- Strategic priority:
  - replace the JSON adapter with a real website repository when concrete DB/API details are available
- Practical next batch in this repo:
  - improve repository readiness without guessing external integration details
  - add better evaluation coverage for search and retrieval quality
  - expand destination normalization beyond the current alias map

## Read This Next

1. `EXECUTION_PLAN.md`
2. `ARCHITECTURE.md`
3. `DATASET_AND_MODELS.md`

## Related Files

- Root `README.md`
- `REFACTOR_NOTES.md`
- `ampfeedback.md`
