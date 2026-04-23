# Roadmap

Last updated: 2026-04-23

## Quick Scan

- Cleanup batch is done.
- First priority now: replace placeholder tour data path with a real repository integration.
- Biggest product limitation after that: search is too strict and requires all three fields.
- Evaluation is the next quality gate once the runtime path is more realistic.

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

### 2. Partial Search

- Why it matters:
  - current UX is overly strict
  - many real users will provide only destination + one other constraint
- Expected impact: high
- Approximate effort: medium
- Dependencies:
  - cleanup batch completed
  - agreement on desired UX
- Success condition:
  - search runs when `location` is present and at least one optional filter exists
  - response clearly indicates missing optional filters

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

