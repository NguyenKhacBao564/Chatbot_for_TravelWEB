# Worklog

Last updated: 2026-04-26

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

## 2026-04-26 - TravelWeb demo tour data and DB contract fixes

- Session goal:
  - add enough real MSSQL tour data for chatbot demos
  - verify the real TravelWeb UI returns tour cards instead of false `no_results`
- Main changes:
  - added an idempotent TravelWeb SQL seed with 36 focused demo tours
  - seeded 12 tours each for Đà Lạt, Phú Yên, Huế across 2026-2027
  - fixed TravelWeb DB matching to prefer Vietnamese `location` over slug `destination_normalized`
  - fixed Express price mapping so `price_min`-only filters do not become exact-price filters
  - fixed Python price extractor so `năm 2026 trên 5tr` does not parse as `2026tr`
  - changed partial-search message mapping so DB results are not paired with stale no-results text
- Files changed:
  - `/Users/nguyen_bao/Documents/PTIT/Junior_2/cnpm/tour-booking-web/sql_chatbot_demo_tours_dalat_phuyen_hue.sql`
  - `/Users/nguyen_bao/Documents/PTIT/Junior_2/cnpm/tour-booking-web/backend/services/chatTourSearchService.js`
  - `/Users/nguyen_bao/Documents/PTIT/Junior_2/cnpm/tour-booking-web/backend/services/chatResponseMapper.js`
  - `/Users/nguyen_bao/Documents/PTIT/Junior_2/cnpm/tour-booking-web/backend/tests/chatIntegration.test.js`
  - `extractors/extract_price.py`
  - `tests/test_extract_price.py`
  - `README.md`
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/DATASET_AND_MODELS.md`
  - `docs/ai_context/ROADMAP.md`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `docs/ai_context/WORKLOG.md`
- Tests added/updated:
  - TravelWeb query builder prefers display location over slug
  - TravelWeb maps known slugs when display location is absent
  - TravelWeb preserves `price_min`-only filter semantics
  - Python price parser rejects false `2026tr` from `năm 2026 trên 5tr`
- Verification:
  - applied `sql_chatbot_demo_tours_dalat_phuyen_hue.sql` to MSSQL successfully
  - TravelWeb `npm test` -> 12 passed
  - Python `python -m pytest tests/test_extract_price.py tests/test_pipeline_sessions.py -q` -> 35 passed
  - Python `python -m pytest -q` -> 46 passed
  - direct Express API returned tours for Đà Lạt dưới 5tr, Đà Lạt trên 5tr, Phú Yên 2027 dưới 5tr, and Huế partial search
  - Playwright UI on `http://localhost:3000` showed tour cards for Đà Lạt dưới 5tr, Đà Lạt trên 5tr, and Huế partial search
- Blockers / caveats:
  - TravelWeb Git metadata is broken (`fatal: bad object HEAD`), so status/commit cannot be trusted there
  - Python standalone still uses `data/tours_sample.json` with 6 tours
  - console shows expected unauthenticated `401 /auth/user` on homepage when not logged in; it did not affect chatbot search
- Next exact step:
  - implement `/health` component readiness reporting in Python backend

## 2026-04-26 - Context location switch fix

- Session goal:
  - fix stale tour-search slots when user switches FAQ context from one destination to another
- Main changes:
  - when a FAQ/knowledge turn contains an explicit destination different from the active search slot, clear stale search slots
  - keep the newer `conversation_context.last_location` so the next explicit tour follow-up uses the new destination
  - added a regression test for Đà Lạt search context -> Huế food FAQ -> Huế tour follow-up
- Files changed:
  - `pipelines/tour_pipeline.py`
  - `tests/test_pipeline_sessions.py`
  - `docs/ai_context/ARCHITECTURE.md`
  - `docs/ai_context/DECISIONS.md`
  - `docs/ai_context/WORKLOG.md`
- Tests added/updated:
  - `test_faq_location_switch_clears_stale_search_slots`
- Verification:
  - `python -m pytest tests/test_pipeline_sessions.py -q` -> 33 passed
  - `python -m pytest -q` -> 52 passed
  - direct `/chat` API verified the final follow-up uses `destination_normalized="hue"`
  - Playwright UI verified the final follow-up renders Huế tour cards, not Đà Lạt cards
- Blockers / caveats:
  - context remains in-memory only
  - broader topic-switch policy may need more cases after real user testing
- Next exact step:
  - implement `/health` component readiness reporting in Python backend

## 2026-04-26 - Conversation context memory for multi-turn UX

- Session goal:
  - remember basic recent context for follow-up questions without reintroducing FAQ-to-search session pollution
- Main changes:
  - added separate `conversation_context` beside search slots in `SessionManager`
  - kept FAQ-derived destination/topic out of `location/time/price` business slots
  - allowed explicit search follow-ups to reuse recent FAQ location
  - kept FAQ follow-ups with season/time language in FAQ mode
  - made search-request phrases like `Tôi muốn đi...` override FAQ follow-up mode
  - boosted FAQ metadata ranking for season/month matches
  - removed stale `ampfeedback.md` after its useful findings had already been absorbed into project memory docs
- Files changed:
  - `pipelines/tour_pipeline.py`
  - `tests/test_pipeline_sessions.py`
  - `README.md`
  - `docs/ai_context/PROJECT_STATE.md`
  - `docs/ai_context/ARCHITECTURE.md`
  - `docs/ai_context/DECISIONS.md`
  - `docs/ai_context/ROADMAP.md`
  - `docs/ai_context/EXECUTION_PLAN.md`
  - `docs/ai_context/WORKLOG.md`
  - `ampfeedback.md`
- Tests added/updated:
  - FAQ location context seeds explicit tour follow-up
  - FAQ time/season follow-up stays in knowledge mode
  - search request after FAQ does not stay in knowledge mode
  - bare location reply completes active missing-location search
  - reset clears conversation context
- Verification:
  - `python -m pytest tests/test_pipeline_sessions.py -q` -> 32 passed
  - `python -m pytest -q` -> 51 passed
  - direct `/chat` API verified FAQ -> search and FAQ -> FAQ follow-up behavior
  - Playwright UI on `http://localhost:3000` verified:
    - `Đà Lạt nên đi vào tháng mấy` then `Có tour nào vào tháng 12 năm 2026 không` returns Đà Lạt tour cards
    - `đi đà lạt vào tháng 5 thì nên mặc gì` then `nhưng tháng 5 là mùa hè mà` stays FAQ and returns summer clothing guidance
    - `Tôi muốn đi tháng 12 năm 2026` then `Đà Lạt` returns Đà Lạt tour cards
- Blockers / caveats:
  - context is in-memory only and not shared across workers
  - TravelWeb clear-chat button appears to clear UI messages; backend reset behavior should be verified in TravelWeb contract batch
  - homepage still logs unauthenticated `401 /auth/user` when not logged in; it did not affect chatbot flow
- Next exact step:
  - implement `/health` component readiness reporting in Python backend

## Read This Next

1. `EXECUTION_PLAN.md`
2. `PROJECT_STATE.md`
3. `ROADMAP.md`
