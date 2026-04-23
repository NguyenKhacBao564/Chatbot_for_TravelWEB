# Roadmap

Last updated: 2026-04-23

## Quick Scan

- Cleanup and partial-search batches are done.
- Strategic priority is still real tour repository integration.
- Practical next coding batch in this repo is not the same thing, because external DB/API details are still unavailable here.
- Evaluation is the next quality gate once repository readiness is better.

## Now

### 1. Real Tour Repository Integration

- Why it matters:
  - current search path is structurally correct but data-poor
  - `tours_sample.json` is not enough for realistic behavior
- Expected impact: very high
- Approximate effort: medium to high
- Dependencies:
  - identify real website DB or API
  - map source fields into `Tour`
- Success condition:
  - `JsonTourRepository` can be swapped for a real repository
  - `/chat` returns real tours from non-sample data
- Current reality:
  - this remains the strategic priority
  - it is blocked until concrete source details exist in or around the repo

### 2. Repository Readiness And Richer Tour Fixtures

- Why it matters:
  - real DB/API integration cannot be wired safely yet
  - current sample data is too small to expose ranking and normalization problems
- Expected impact: high
- Approximate effort: medium
- Dependencies:
  - current repository contract stays stable
- Success condition:
  - tests cover richer destination/date/price combinations
  - sample or fixture data exposes more realistic search behavior
  - repository adapter remains swappable without changing pipeline/search code

### 3. Evaluation Harness For Intent, FAQ, And Search

- Why it matters:
  - current tests verify correctness, not model/search quality
- Expected impact: high
- Approximate effort: medium
- Dependencies:
  - small gold datasets
- Success condition:
  - repo contains repeatable evaluation scripts and baseline metrics

## Next

### 4. Better Destination Catalog / Normalization

- Why it matters:
  - current alias map is too small
- Expected impact: medium
- Approximate effort: low to medium
- Dependencies:
  - preferably real tour data or curated destination catalog
- Success condition:
  - normalization covers a much wider place set without hardcoding everything in Python

### 5. FAQ Retrieval Upgrade

- Why it matters:
  - current embedding choice and threshold are weakly justified
- Expected impact: medium
- Approximate effort: medium
- Dependencies:
  - FAQ evaluation harness
- Success condition:
  - model/threshold choice is backed by measured retrieval quality

## Later

### 6. Session Externalization

- Why it matters:
  - current in-memory state is per-process only
- Expected impact: medium
- Approximate effort: medium
- Dependencies:
  - deployment/runtime choice
- Success condition:
  - session behavior is stable across workers/restarts

### 7. Observability

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
