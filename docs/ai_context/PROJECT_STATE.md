# Project State

Last updated: 2026-04-26

## Quick Scan

- Project: Vietnamese travel chatbot backend.
- Direction is still correct: hybrid NLP + deterministic business search.
- API entrypoints today: `GET /health`, `POST /chat`, `POST /reset`.
- Main runtime path: `server.py` -> `TourRetrievalPipeline` -> structured `ChatResponse`.
- Python standalone tour search still uses a JSON adapter with 6 sample tours.
- TravelWeb UI search now uses MSSQL seeded demo data for Đà Lạt, Phú Yên, Huế.
- Search now runs with `location + time`, `location + price`, or all three filters.
- FAQ-like knowledge/service queries are guarded before search/session mutation.
- Lightweight `conversation_context` now keeps recent FAQ/search context without polluting search slots.
- FAQ retrieval is separate from tour search and uses metadata keyword scoring before FAISS fallback.

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
- Deterministic knowledge guard:
  - examples like `Đà Lạt có món gì` route to FAQ/fallback response
  - examples like `Hà Nội có những quán cà phê...`, `Tour có wifi...`, `Trẻ em dưới 5 tuổi...` do not enter tour search
  - explicit tour queries with food words still enter tour-search flow
- Context-aware multi-turn behavior:
  - FAQ turns can remember `last_location` and `last_topic`
  - explicit search follow-ups can reuse the recent FAQ location
  - FAQ follow-ups with time/season language stay in FAQ mode
  - bare location replies can complete an active missing-location search
- Price extraction no longer treats short non-money quantities like ages, people counts, or day counts as budgets.
- Price extraction no longer treats the year before `trên` as a money unit, e.g. `năm 2026 trên 5tr`.
- Full `no_results` now resets session state.
- `missing_info` messages are deterministic and do not call Gemini.
- FAQ retrieval with metadata when FAISS stack is available.
- TravelWeb integration:
  - maps chatbot entities into MSSQL filters
  - prioritizes display `location` over slug `destination_normalized` for DB matching
  - returns DB tour cards in the React chatbot UI
- TravelWeb MSSQL demo data:
  - existing broad future-tour seed: `sql_future_tours_2026_2027.sql`
  - focused demo seed: `sql_chatbot_demo_tours_dalat_phuyen_hue.sql`
  - 36 focused demo tours, 12 each for Đà Lạt, Phú Yên, Huế
- Test suite covering API smoke, validation, parsers, reset flow, partial search flows, session isolation, and multi-turn search progression.

## What Is Fallback / Mock / Adapter

- `JsonTourRepository` backed by `data/tours_sample.json`
  - this is Python standalone data, not the TravelWeb MSSQL database
  - current sample size is 6 tours only
- Gemini
  - phrasing only
  - deterministic fallback text is used if key or SDK is missing
- VnCoreNLP location extraction
  - alias fallback is used if VnCoreNLP is unavailable
  - local runtime often depends on the alias fallback unless `vncorenlp` and Java setup are available
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
- `conversation_context` is also in-memory and should be treated as local-runtime memory, not durable user profile data.
- Search still depends on `location` as the only hard requirement and will not run on destination-only queries.
- `extract_location()` still returns only the first detected location.
- Destination normalization is still based on a small hardcoded alias map.
- Knowledge routing is still rule-based and can miss unseen FAQ phrasing, although it now has broader FAQ candidate handling.
- FAQ retrieval still uses:
  - a fixed threshold
  - deterministic metadata scoring plus a multilingual embedding fallback
- TravelWeb and Python still have separate tour data paths:
  - Python standalone uses `data/tours_sample.json`
  - TravelWeb UI uses MSSQL through Express
- TravelWeb repo in this workspace has a broken Git HEAD, so file tracking/commit status there cannot be trusted without fixing that repo metadata.

## Current Engineering Focus

- Practical next batch:
  - improve `/health` into component health/readiness reporting
  - keep TravelWeb/Python response contract tests current
  - verify whether TravelWeb clear-chat should call Python `/reset`
  - add evaluation coverage for search and retrieval quality
  - decide whether Python standalone should keep JSON-only mode or gain a real DB repository adapter

## Read This Next

1. `EXECUTION_PLAN.md`
2. `ARCHITECTURE.md`
3. `DATASET_AND_MODELS.md`

## Related Files

- Root `README.md`
- `REFACTOR_NOTES.md`
