# Decisions

Last updated: 2026-04-23

## Quick Scan

- Hybrid NLP + deterministic search is the chosen shape.
- Business truth must not come from LLM.
- Repository boundary stays even before real DB integration exists.
- Graceful degradation is accepted for local dev/test.
- Some decisions are explicitly temporary and should not be treated as final architecture.

## D-001 Hybrid NLP + Deterministic Search

- Status: Accepted
- Context: The system must interpret Vietnamese queries and return business-valid tour results.
- Choice: Keep NLP understanding separate from deterministic search/filtering.
- Consequences:
  - easier to test business logic
  - lower hallucination risk
  - more components to maintain

## D-002 Business Filtering Must Not Depend On LLM

- Status: Accepted
- Context: Tour matching is business-critical.
- Choice: Use normalized filters + deterministic `TourSearchService`.
- Consequences:
  - auditable search behavior
  - less flexible natural matching unless normalization improves

## D-003 Gemini Is Phrasing-Only

- Status: Accepted
- Context: Natural Vietnamese phrasing is useful, but not as a source of truth.
- Choice: Gemini may phrase prompts and FAQ answers, but may not decide matches.
- Consequences:
  - safer runtime behavior
  - system can fall back cleanly when Gemini is unavailable

## D-004 Keep Repository Boundary Before Real DB Integration

- Status: Accepted
- Context: The actual website tour data source is not in this repo yet.
- Choice: Keep `TourRepository` protocol + adapter-based access.
- Consequences:
  - future DB/API integration is cleaner
  - current repo still depends on placeholder sample data

## D-005 Graceful Runtime Degradation

- Status: Accepted
- Context: Local machines may not have all ML runtimes or artifacts.
- Choice:
  - PhoBERT -> rule fallback
  - VnCoreNLP -> alias fallback
  - Gemini -> deterministic fallback
  - FAISS FAQ -> disable if stack is missing
- Consequences:
  - easier local bootstrapping
  - behavior can vary across environments

## D-006 Structured ChatResponse Is The API Contract

- Status: Accepted
- Context: Frontend needs stable fields, not free-form blobs.
- Choice: Keep `status`, `message`, `entities`, `missing_fields`, `tours`, `faq_sources`.
- Consequences:
  - frontend integration is simpler
  - API contract changes should be deliberate

## D-007 Require All Three Search Fields Before Searching

- Status: Temporary
- Context: Current pipeline only searches after `location`, `time`, and `price` are all present.
- Choice: Keep strict gating for now.
- Consequences:
  - simpler logic today
  - weak UX
  - likely one of the next changes

## D-008 Fix Correctness Before Expanding Capability

- Status: Accepted and executed in batch 1
- Context: The repo had known correctness issues:
  - duplicate normalization flow
  - sentinel `"None"` handling
  - weak request validation
  - no reset endpoint
- Choice: prioritize cleanup/correctness before larger behavior changes like partial search.
- Consequences:
  - safer next refactors
  - product-level improvements were delayed slightly

## D-009 Local Browser Compatibility Is Baseline

- Status: Accepted
- Context: The backend is intended to be consumed by a frontend during local development.
- Choice: Keep local-dev CORS enabled as baseline API wiring.
- Consequences:
  - easier frontend integration in development
  - production origin policy still needs separate hardening

## Open Decisions

- Partial search policy:
  - require only `location`
  - or require `location + one optional field`
- Real tour data integration path:
  - SQL repository
  - backend API repository
  - another source
- Whether Gemini should remain enabled for missing-info/search-intro phrasing, or be reduced further in favor of deterministic strings
- FAQ retrieval upgrade:
  - keep current embedding stack
  - move to better multilingual/Vietnamese model
- Session state:
  - keep in-memory for local only
  - move to Redis/shared store for multi-worker usage

## Read This Next

1. `ROADMAP.md`
2. `EXECUTION_PLAN.md`
3. `WORKLOG.md`

