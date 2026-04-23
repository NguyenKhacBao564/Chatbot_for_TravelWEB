# Roadmap

Last updated: 2026-04-23

## Quick Scan

- Highest priority is replacing the JSON tour adapter with real website data access.
- Next biggest product issue is the rigid requirement to collect all three search fields before searching.
- Model/data quality work matters, but only after the business integration path is real.

## Now

### 1. Integrate The Real Website Tour Data Source

- Goal: replace `JsonTourRepository` with a repository backed by the actual website DB or backend API.
- Impact: high
- Difficulty: medium to high
- Depends on:
  - knowing the real data source
  - mapping fields into `schemas.tour_models.Tour`

### 2. Support Partial Search Before All Fields Are Present

- Goal: allow useful search when only some filters are known, especially `location + time` or `location + price`.
- Impact: high
- Difficulty: medium
- Depends on:
  - clear UX rules for missing fields
  - small refactor of `_missing_fields()` and search policy

### 3. Add Evaluation For Search And FAQ

- Goal: stop relying only on ad hoc manual checks.
- Impact: high
- Difficulty: medium
- Depends on:
  - a small gold set of real queries
  - expected tours / expected FAQ answers

## Next

### 4. Improve Destination Normalization And Slot Coverage

- Goal: expand alias coverage and reduce misses from spelling/variant forms.
- Impact: medium
- Difficulty: medium
- Depends on:
  - curated place alias list
  - maybe extracting destination catalog from real tour data

### 5. Revisit FAQ Retrieval Model And Threshold

- Goal: improve FAQ quality for Vietnamese queries.
- Impact: medium
- Difficulty: medium
- Depends on:
  - retrieval evaluation set
  - trying a better multilingual/Vietnamese embedding model

### 6. Separate Intent And Slot Policy More Explicitly

- Goal: reduce drift between classifier labels and actual business behavior.
- Impact: medium
- Difficulty: medium
- Depends on:
  - deciding whether some intents are redundant once partial search exists

## Later

### 7. Externalize Session Storage

- Goal: move from in-memory sessions to Redis or another shared store.
- Impact: medium
- Difficulty: medium
- Depends on:
  - deployment target
  - multi-worker or multi-instance requirements

### 8. Add Better Observability

- Goal: track intent path, extractor output, search filters, FAQ hit/miss, latency.
- Impact: medium
- Difficulty: low to medium
- Depends on:
  - deciding a logging/metrics stack

### 9. Tighten Dataset/Artifact Lifecycle

- Goal: make training/index regeneration less ad hoc.
- Impact: medium
- Difficulty: medium
- Depends on:
  - choosing where model artifacts live
  - deciding how to version data and index outputs

## Not Urgent Yet

- Complex semantic/vector search over tours
- End-to-end LLM orchestration for business search
- Aggressive microservice decomposition

Those would add complexity before the repo has a real tour data integration and a solid evaluation loop.

## Read This Next

1. `WORKLOG.md`
2. `DECISIONS.md`
3. `PROJECT_STATE.md`

