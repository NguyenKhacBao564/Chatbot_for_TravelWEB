# Dataset And Models

Last updated: 2026-04-23

## Quick Scan

- Intent dataset: `data/processed/intent_merged.json` with 11,904 samples.
- FAQ data: `data/processed/faq_cleaned.json` with 3,504 entries.
- FAQ metadata: `faq_metadata.json` with 3,504 indexed entries.
- Tour data in repo: `data/tours_sample.json` with 6 sample tours only.
- Main runtime models:
  - PhoBERT for intent
  - `all-MiniLM-L6-v2` for FAQ retrieval
  - rule-based extractors for time/price

## Intent Data

- File: `data/processed/intent_merged.json`
- Purpose: training data for intent classifier
- Observed size: 11,904 samples
- Current intent labels in code:
  - `find_tour_with_location`
  - `find_tour_with_time`
  - `find_tour_with_price`
  - `find_tour_with_location_and_time`
  - `find_tour_with_location_and_price`
  - `find_tour_with_time_and_price`
  - `find_with_all`
  - `out_of_scope`

Notes:

- Dataset generation scripts in `scripts/` indicate heavy synthetic / paraphrased generation.
- This is useful for bootstrap training, but distribution may differ from real user traffic.

## FAQ Data

- Source data: `data/processed/faq_cleaned.json`
- Metadata used at runtime: `faq_metadata.json`
- FAISS index file: `faq_index.faiss`
- Retrieval model in code: `SentenceTransformer("all-MiniLM-L6-v2")`

Notes:

- FAQ path is independent from tour search.
- Current retrieval returns metadata fields:
  - `question`
  - `answer`
  - `tags`
  - `score`
  - `source`

## Tour Data

- Current runtime source in repo: `data/tours_sample.json`
- Observed size: 6 tours
- Purpose: adapter data for `JsonTourRepository`
- Important limitation: this is not the website database

Current repo does not contain:

- SQL schema for tours
- ORM models
- API client for the website backend
- migration/config for production tour storage

## Runtime Artifacts

Required or effectively required for full behavior:

- `training/phobert_intent_finetuned/`
- `faq_metadata.json`
- `faq_index.faiss`

Can be regenerated:

- `faq_metadata.json`
- `faq_index.faiss`
- PhoBERT artifact, if training data + training environment are available

Fallback behavior if artifacts are missing:

- no PhoBERT -> rule-based intent
- no FAISS stack -> FAQ retrieval disabled
- no Gemini key/SDK -> deterministic response text fallback

## Model / Extractor Inventory

- Intent:
  - PhoBERT classifier from local artifact
- FAQ:
  - sentence-transformer `all-MiniLM-L6-v2`
- Location:
  - VnCoreNLP NER if available
  - alias fallback otherwise
- Time:
  - regex + relative-date rules
- Price:
  - rule-based numeric/unit parsing

## Known Limitations

- Intent dataset likely over-represents synthetic phrasing.
- FAQ embedding model is not specialized for Vietnamese.
- Time normalization handles month and exact date forms, but not rich natural ranges.
- Destination alias list is small and manually maintained.
- Tour sample data is too small to evaluate ranking quality seriously.
- Search currently assumes price is usually a ceiling, which is reasonable but not universally true.

## Read This Next

1. `DECISIONS.md`
2. `ROADMAP.md`
3. Root `README.md`

