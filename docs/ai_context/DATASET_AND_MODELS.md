# Dataset And Models

Last updated: 2026-04-26

## Quick Scan

- Intent dataset: `data/processed/intent_merged.json` with 11,904 samples.
- FAQ dataset: `data/processed/faq_cleaned.json` with 3,504 entries.
- FAQ runtime metadata: `faq_metadata.json` with 3,504 entries.
- Tour runtime data in Python repo: `data/tours_sample.json` with 6 sample tours.
- Tour runtime data in TravelWeb demo: MSSQL seeded with focused Đà Lạt/Phú Yên/Huế tours.
- Main runtime models:
  - PhoBERT for intent
  - `all-MiniLM-L6-v2` for FAQ retrieval
  - rule-based extractors for time and price

## Intent Data

- File: `data/processed/intent_merged.json`
- Purpose: training data for PhoBERT intent classifier
- Current labels in runtime:
  - `find_tour_with_location`
  - `find_tour_with_time`
  - `find_tour_with_price`
  - `find_tour_with_location_and_time`
  - `find_tour_with_location_and_price`
  - `find_tour_with_time_and_price`
  - `find_with_all`
  - `out_of_scope`

### Important limitations

- Dataset generation scripts suggest heavy synthetic / paraphrased generation.
- The repo does not include an evaluation set proving these samples resemble real user traffic.
- Likely consequence:
  - PhoBERT may look acceptable on synthetic phrasing but still behave weakly on real traffic.

### Verified train-vs-inference mismatch

- Training script `training/phobert_intent_finetuned_train.py` segments text with VnCoreNLP before tokenization.
- Runtime inference in `pipelines/tour_pipeline.py` sends raw query text directly to tokenizer.
- Training and inference preprocessing are therefore not identical.

## FAQ Data

- Source data: `data/processed/faq_cleaned.json`
- Metadata used at runtime: `faq_metadata.json`
- FAISS index file: `faq_index.faiss`
- Retrieval model in code: `SentenceTransformer("all-MiniLM-L6-v2")`

### Important limitations

- `all-MiniLM-L6-v2` is not a Vietnamese-specific model.
- Current retrieval threshold is a fixed constant, not calibrated from an eval set.
- FAQ quality depends heavily on:
  - embedding choice
  - threshold choice
  - FAQ data cleanliness

## Tour Data

- Current runtime source: `data/tours_sample.json`
- Observed size: 6 tours
- Purpose: placeholder adapter data for `JsonTourRepository`

What this means:

- enough to prove the business-search shape
- not enough to judge ranking quality
- not a substitute for TravelWeb MSSQL integration

TravelWeb demo source:

- DB: MSSQL behind TravelWeb Express backend.
- Existing broad seed: `tour-booking-web/sql_future_tours_2026_2027.sql`
- Focused chatbot demo seed: `tour-booking-web/sql_chatbot_demo_tours_dalat_phuyen_hue.sql`
- Focused coverage:
  - 36 tours total
  - 12 tours for Đà Lạt
  - 12 tours for Phú Yên
  - 12 tours for Huế
  - date range: May 2026 through December 2027
  - varied adult prices below and above 5 million VND

Important integration note:

- Python emits both `location` and `destination_normalized`.
- TravelWeb MSSQL stores Vietnamese destination names like `Đà Lạt`, not slugs like `da-lat`.
- Express search should use display `location` for DB `LIKE` matching and keep slug as metadata/fallback only.

## Runtime Artifacts

Effectively required for full behavior:

- `training/phobert_intent_finetuned/`
- `faq_metadata.json`
- `faq_index.faiss`

Regenerable:

- `faq_metadata.json`
- `faq_index.faiss`
- PhoBERT artifact, if training environment is available

Fallback behavior:

- no PhoBERT -> rule-based intent
- no FAISS stack -> FAQ retrieval disabled
- no Gemini key/SDK -> deterministic phrasing fallback
- no VnCoreNLP -> alias-based location fallback

## Extractor Limitations

- Location:
  - current extractor returns only the first detected location
  - no explicit departure vs destination split
- Time:
  - handles exact day and month cases
  - does not support rich natural ranges well
  - now returns real `None` on miss in the main flow
- Price:
  - deterministic and testable
  - returns a single main value in extractor API
  - now returns real `None` on miss in the main flow
  - guarded against parsing `2026 tr` from phrases like `năm 2026 trên 5tr`
- Normalization:
  - alias map is small and hardcoded
  - no fuzzy matching yet

## Read This Next

1. `DECISIONS.md`
2. `ROADMAP.md`
3. `EXECUTION_PLAN.md`
