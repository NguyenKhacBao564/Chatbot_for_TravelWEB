# Decisions

Last updated: 2026-04-26

## Quick Scan

- Hybrid NLP + deterministic search is the chosen shape.
- Business truth must not come from LLM.
- Repository boundary stays even before real DB integration exists.
- Graceful degradation is accepted for local dev/test.
- Knowledge/FAQ-like queries are guarded before tour-search session mutation.
- Conversation context is separate from business search slots.
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

## D-007 Partial Search Requires `location + one optional field`

- Status: Accepted and executed in batch 2
- Context: Requiring `location`, `time`, and `price` before searching made the chatbot too rigid for normal travel queries.
- Choice:
  - keep `location` as the only hard requirement
  - run deterministic search when at least one of `time` or `price` is present
  - return `status="partial_search"` when search runs with one optional filter still missing
- Consequences:
  - better product usefulness in real conversations
  - frontend must handle `partial_search` explicitly
  - destination-only queries still do not search by design

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

## D-010 Keep Session After Missing/Partial Search, Reset After Terminal Full Search

- Status: Accepted and updated in batch 3
- Context: Users often provide destination first, then add time or budget in later turns.
- Choice:
  - keep session state after `missing_info` and `partial_search`
  - reset session after full `success`
  - also reset session after full `no_results`
- Consequences:
  - multi-turn narrowing works correctly
  - failed full searches do not trap later turns in stale filters
  - in-memory session state remains more important to runtime behavior
  - session bugs would have more visible user impact

## D-011 Guard Knowledge Queries Before Tour Search

- Status: Accepted and executed in batch 3
- Context: Queries like `Đà Lạt có món gì` contain a valid destination but are knowledge/FAQ requests, not tour-search requests.
- Choice:
  - detect common knowledge patterns such as food, weather, culture, festivals, and activities before entity extraction mutates session state
  - route these queries to FAQ/fallback response unless the query has explicit tour intent such as `tour`, `đặt tour`, `có tour`, `khởi hành`, or `lịch trình`
- Consequences:
  - prevents FAQ-like turns from polluting search session state
  - keeps deterministic behavior testable
  - keyword coverage must be expanded as real query logs expose misses

## D-012 Missing-Info Messages Are Deterministic

- Status: Accepted and executed in batch 3
- Context: Missing-info prompts do not need LLM phrasing and were adding latency plus output variability.
- Choice: Return deterministic fallback strings for `missing_info`.
- Consequences:
  - lower latency for common clarification turns
  - less chance that a clarification prompt sounds like a failed search
  - Gemini is still available for FAQ rephrasing and search intro phrasing

## D-013 Separate Conversation Context From Search Slots

- Status: Accepted and executed
- Context: FAQ turns like `Đà Lạt nên đi vào tháng mấy` should help later follow-up search, but must not pollute business search slots the way earlier FAQ/session bugs did.
- Choice:
  - keep `location/time/price` as search slots only
  - add lightweight `conversation_context` for `last_location`, `last_topic`, `last_mode`, and related follow-up hints
  - allow explicit search follow-ups to reuse recent FAQ location
  - keep FAQ follow-ups in FAQ mode when they do not contain search-request language
  - clear stale search slots when an explicit FAQ destination switches away from the active search destination
- Consequences:
  - multi-turn UX is better without reintroducing FAQ-to-search pollution
  - routing policy is more nuanced and needs regression tests
  - context remains in-memory and is not production-grade durable memory

## Open Decisions

- Real tour data integration path:
  - SQL repository
  - backend API repository
  - another source
- Whether Gemini should remain enabled for search-intro phrasing, or be reduced further in favor of deterministic strings
- FAQ retrieval upgrade:
  - keep current embedding stack
  - move to better multilingual/Vietnamese model
- Session state:
  - keep in-memory for local only
  - move to Redis/shared store for multi-worker usage
- Whether TravelWeb clear-chat should call Python `/reset` to clear backend context as well as frontend messages

## Read This Next

1. `ROADMAP.md`
2. `EXECUTION_PLAN.md`
3. `WORKLOG.md`
