# Project State

Last updated: 2026-04-23

## Quick Scan

- Project: Vietnamese travel chatbot backend with hybrid NLP + deterministic tour search.
- API entrypoints: `GET /health`, `POST /chat`.
- Main orchestrator: `server.py` -> `pipelines/tour_pipeline.py` -> `ChatResponse`.
- Search works against structured tour data, but current repo only ships a JSON adapter with 6 sample tours.
- FAQ retrieval is separate from tour search and depends on FAISS artifacts plus `all-MiniLM-L6-v2`.
- Several components are optional at runtime:
  - PhoBERT intent -> rule fallback if model/deps are missing.
  - VnCoreNLP location extraction -> alias fallback if runtime/deps are missing.
  - Gemini phrasing -> deterministic fallback strings if `GOOGLE_API_KEY` or SDK is missing.
- Current search still requires all three fields before searching: `location`, `time`, `price`.

## What This Repo Is

- A backend-only prototype/refactor for a Vietnamese travel chatbot.
- The current goal is not open-domain chat.
- The useful path is:
  - detect user intent
  - extract/normalize search entities
  - run deterministic tour search
  - return structured results for a frontend

## Current State

- Implemented:
  - FastAPI app and structured `/chat` response
  - hybrid intent path: PhoBERT or rule fallback
  - extractors for location, time, price
  - entity normalization to business filters
  - FAQ retrieval with metadata
  - deterministic tour filtering/ranking
  - tests for API smoke, parsers, session isolation, tour search flow
- Present but not production-ready:
  - `JsonTourRepository` backed by `data/tours_sample.json`
  - in-memory session storage
  - small destination alias map
  - simple ranking heuristic

## What Is Real vs Mock

- Real in repo:
  - `data/processed/intent_merged.json`
  - `data/processed/faq_cleaned.json`
  - `faq_metadata.json`
  - FAISS index generation script
  - deterministic tour search code
- Mock / adapter / fallback:
  - website tour database integration is not present in this repo
  - `data/tours_sample.json` is only placeholder data
  - PhoBERT model artifact is expected locally, not shipped in repo
  - FAQ retrieval can be disabled if dependencies/artifacts are missing

## Main Technical Risks

- Search flow is blocked until all three fields are filled, which is stricter than many real chatbot UX flows.
- Tour repository is not connected to the actual website database yet.
- Session state is process-local only.
- FAQ retrieval uses a fixed distance threshold and a non-Vietnamese-specific embedding model.
- Alias-based destination fallback is narrow and will miss many place variants.

## Read This Next

1. `ARCHITECTURE.md`
2. `DATASET_AND_MODELS.md`
3. `DECISIONS.md`

## Related Files

- Root `README.md` for setup and human-facing architecture summary
- `REFACTOR_NOTES.md` for the recent backend refactor scope

