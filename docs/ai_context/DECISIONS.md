# Decisions

Last updated: 2026-04-23

## Quick Scan

- The repo has already chosen a hybrid architecture.
- Business truth is deterministic, not LLM-driven.
- Repository abstraction is intentional because website DB integration is still missing.
- Some runtime fallbacks are accepted temporarily to keep local development possible.

## D-001 Hybrid NLP + Deterministic Search

- Status: Accepted
- Context: The chatbot must both interpret Vietnamese user queries and return business-valid tour results.
- Choice: Keep a hybrid architecture: NLP for intent/entity understanding, deterministic service for tour filtering and ranking.
- Consequences:
  - simpler to reason about than end-to-end LLM orchestration
  - easier to test business logic
  - still requires maintaining NLP and search layers separately

## D-002 Business Filtering Must Not Depend On LLM

- Status: Accepted
- Context: Tour matching is business-critical and should be reproducible.
- Choice: Use `TourSearchService` + normalized filters for matching tours.
- Consequences:
  - business rules stay auditable
  - lower risk of hallucinated matches
  - search quality depends on normalized entities and repository quality

## D-003 Gemini Is For Phrasing Only

- Status: Accepted
- Context: The repo still wants natural Vietnamese responses, but not LLM-controlled business truth.
- Choice: Gemini may phrase:
  - missing-info prompts
  - search intro text
  - FAQ rephrasing
- Consequences:
  - safer use of LLM
  - system still works without Gemini
  - response tone can vary while business result stays stable

## D-004 Keep Tour Repository As An Adapter Boundary

- Status: Accepted
- Context: The actual website database is not present in this repo.
- Choice: Keep `TourRepository` protocol and current `JsonTourRepository` adapter separate from search logic.
- Consequences:
  - DB integration can be added without rewriting search service
  - current repo still runs with sample data
  - one more abstraction layer to maintain

## D-005 Graceful Runtime Degradation

- Status: Accepted
- Context: Local environments may not have all heavy ML dependencies or model artifacts installed.
- Choice: Use optional runtime behavior:
  - PhoBERT -> rule fallback
  - VnCoreNLP -> alias fallback
  - Gemini -> deterministic fallback
  - FAISS FAQ -> disabled if stack is missing
- Consequences:
  - easier local bootstrapping
  - easier isolated testing
  - behavior differs across environments if dependencies are inconsistent

## D-006 Structured ChatResponse Is The API Contract

- Status: Accepted
- Context: Frontend rendering needs stable fields, not free-form text blobs.
- Choice: Return `status`, `message`, `entities`, `missing_fields`, `tours`, `faq_sources`.
- Consequences:
  - frontend integration is cleaner
  - future changes should preserve or version this contract

## D-007 Require All Three Search Fields Before Searching

- Status: Temporary
- Context: Current pipeline asks for `location`, `time`, and `price` before calling tour search.
- Choice: Keep the stricter behavior for now.
- Consequences:
  - easier deterministic logic in the short term
  - weaker UX for partial-search cases
  - likely to be revisited soon

## Open Decisions

- How the real website tour database will be integrated
- Whether partial search should be allowed before all fields are known
- Whether FAQ retrieval should switch to a better Vietnamese/multilingual embedding stack
- Whether session state should move to Redis or another shared store

## Read This Next

1. `ROADMAP.md`
2. `WORKLOG.md`
3. `PROJECT_STATE.md`

