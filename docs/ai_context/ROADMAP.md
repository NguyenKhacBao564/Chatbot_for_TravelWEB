# Roadmap

Last updated: 2026-04-26

## Quick Scan

- Cleanup and partial-search batches are done.
- TravelWeb now has MSSQL demo tour data for chatbot testing.
- Strategic choice now is whether Python should stay orchestration-only for TravelWeb or gain its own direct DB adapter.
- Evaluation is the next quality gate once repository readiness is better.

## Now

### 1. Component Health Reporting

- Why it matters:
  - current `/health` does not expose degraded FAQ/model/repository components
- Expected impact: high
- Approximate effort: low to medium
- Dependencies:
  - keep checks lightweight and avoid slow model inference
- Success condition:
  - `/health` reports FAQ retrieval availability
  - `/health` reports intent model vs rule fallback
  - `/health` reports tour repository/search readiness

### 2. TravelWeb Contract Hardening

- Why it matters:
  - TravelWeb is the actual UI path for real DB tours
  - Python and Express can drift on `status`, `entities`, and message semantics
- Expected impact: high
- Approximate effort: medium
- Dependencies:
  - TravelWeb backend tests
  - a stable local MSSQL seed
- Success condition:
  - `faq` and `missing_info` never trigger DB queries
  - `partial_search`, `success`, and `no_results` are rendered consistently
  - DB query uses display `location` correctly and handles `price_min` vs `price_max`

### 3. Repository Readiness And Richer Python Fixtures

- Why it matters:
  - Python standalone still has only 6 JSON sample tours
  - this path is useful for backend-only tests but does not represent TravelWeb DB volume
- Expected impact: medium
- Approximate effort: medium
- Dependencies:
  - current repository contract stays stable
- Success condition:
  - Python fixture coverage mirrors key demo cases without pretending to be production DB
  - repository adapter remains swappable without changing pipeline/search code

### 4. Evaluation Harness For Intent, FAQ, And Search

- Why it matters:
  - current tests verify correctness, not model/search quality
- Expected impact: high
- Approximate effort: medium
- Dependencies:
  - small gold datasets
- Success condition:
  - repo contains repeatable evaluation scripts and baseline metrics

## Next

### 5. Better Destination Catalog / Normalization

- Why it matters:
  - current alias map is too small
- Expected impact: medium
- Approximate effort: low to medium
- Dependencies:
  - preferably real tour data or curated destination catalog
- Success condition:
  - normalization covers a much wider place set without hardcoding everything in Python

### 6. FAQ Retrieval Upgrade

- Why it matters:
  - current embedding choice and threshold are weakly justified
- Expected impact: medium
- Approximate effort: medium
- Dependencies:
  - FAQ evaluation harness
- Success condition:
  - model/threshold choice is backed by measured retrieval quality

## Later

### 7. Session Externalization

- Why it matters:
  - current in-memory state is per-process only
- Expected impact: medium
- Approximate effort: medium
- Dependencies:
  - deployment/runtime choice
- Success condition:
  - session behavior is stable across workers/restarts

### 8. Observability

- Why it matters:
  - debugging current hybrid path is still mostly manual
- Expected impact: medium
- Approximate effort: low to medium
- Dependencies:
  - logging/metrics approach
- Success condition:
  - request path, filters, and retrieval/search outcomes are visible in logs/metrics

## Intentionally Postponed

- vector search over tours
- LLM-driven business search
- major service decomposition

These are not the highest-leverage changes for the current repo state.

## Read This Next

1. `EXECUTION_PLAN.md`
2. `WORKLOG.md`
3. `PROJECT_STATE.md`
