# AI methods log

The course asks every project to record each place a model touched the results and how it was checked (`the-new-way.html#the-skill-underneath`).

## 1. Pretrained text encoder (measurement instrument)

- **What:** `sentence-transformers/all-MiniLM-L6-v2` (revision pinned) embeds ≤ 200-token passages; tale vectors are mean-pooled.
- **Touches:** semantic similarities, semantic graphs, communities, neighbour lists, passage matches, validation strata.
- **Checks done:**
  - Every chunk is asserted to fit the 256-token limit (no silent truncation).
  - Vectors are asserted finite and unit length.
  - Results are compared with a second method (TF–IDF) and with two pooling and chunking variants.
  - Exported vectors reproduce the pipeline scores (tests).
- **Check pending:** human validation of what high-similarity pairs share (Validation page; status *pending*).

## 2. Coding agent (Claude)

The agent wrote the pipeline and website code and made the documented judgement calls listed below. None of them was tuned to make the agreement results look stronger; the plan and settings were frozen before any agreement statistic existed (ANALYSIS_PLAN.md).

| Agent judgement | Where recorded | How it was checked | Still needed |
| --- | --- | --- | --- |
| Text cleaning rules and 40 per-record decisions | `analysis/clean.py`, `data/mappings/text_review.csv`, `outputs/audit/cleaning_log.csv` | Every trailing cut and residue was read; a leakage test ensures no classification or site text remains | Human spot-check of the review file |
| Provenance mapping (406 strings) | `data/mappings/provenance_map.csv`, `scripts/draft_provenance_map.py` | Row-by-row review; validation asserts (unknown stays unknown, coordinate ranges, authors never mapped to places) | Human review of every row (`review_status` column) |
| Opening and Story example pairs | `config.yaml` (`export.opening_pair`, `story_pairs`) | Chosen after reading best-matching passages; labelled as illustrations | — |
| Code correctness | `tests/` | 7 metric-equivalence tests (scikit-learn, NetworkX), 16 pipeline-output tests, 4 browser journeys | — |

Two defects were found by these checks and fixed:

1. YAML turned `no` into `false`, so "no" had stayed a stopword.
2. A slow NetworkX edge-swap was replaced with the same rule implemented directly.

Both are logged in ANALYSIS_PLAN.md.

## 3. Not used

- No LLM labels, summaries or motif annotations enter any analysis.
- No simulated reviewers.
- No generated images in charts: all figures are drawn from computed data.
