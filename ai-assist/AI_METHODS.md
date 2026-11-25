# AI methods log

The course asks every project to record each place a model touched the results and how it was checked (`the-new-way.html#the-skill-underneath`).

## 1. Pretrained text encoder (measurement instrument)

- **What:** `sentence-transformers/all-MiniLM-L6-v2` (revision pinned) embeds ≤ 200-token passages; tale vectors are mean-pooled.
- **Touches:** the second representation: embedding similarities, the embedding map and its communities, folk-closeness and neighbours with embeddings, and the representation row of Table 1.
- **Checks done:**
  - Every chunk is asserted to fit the 256-token limit (no silent truncation).
  - Vectors are asserted finite and unit length.
  - Results are compared with a second method (TF–IDF), which is the primary one because it finds the held-out retellings' tale types more often (recall@10 0.69 against 0.61).
- **Reference set:** 36 religious retellings of known ATU tale type, held out of the folktale network; the instrument has to find a folktale of the same type among the 10 nearest (recall@10 0.69 for TF–IDF, chance 0.055). No hand labels of parable–folktale pairs were made (decision of the authors, 18 November; DECISIONS.md U9).

## 2. Coding agent (Claude)

The agent wrote the pipeline and website code and made the documented judgement calls listed below. None of them was tuned to make the agreement results look stronger; the text and graph settings were fixed on 29 October, before any agreement statistic existed, and every later judgement call is in DECISIONS.md (this folder).

| Agent judgement | Where recorded | How it was checked | Still needed |
| --- | --- | --- | --- |
| Text cleaning rules and 40 per-record decisions | `reimagine/core/clean.py`, `data/mappings/text_review.csv`, `results/corpus_audit/cleaning_log.csv` | Every trailing cut and residue was read; a leakage test ensures no classification or site text remains | Human spot-check of the review file |
| Provenance mapping (406 strings) | `data/mappings/provenance_map.csv` (rationale per row); drafted once by a script that is in the git history | Row-by-row review; validation asserts (unknown stays unknown, coordinate ranges, authors never mapped to places) | Human review of every row (`review_status` column) |
| Parable segmentation rules | `reimagine/parables/`, DECISIONS.md (P rows) | Unit tests on each rule; every tradition's counts read | Not checked by hand on a sample (decision of 18 November) |
| Code correctness | `tests/` | Unit tests: metric equivalence (scikit-learn, NetworkX), unit tests on toy inputs, checks on the data and the site's data file; a browser check of every page and interaction of the site | — |

Two defects were found by these checks and fixed:

1. YAML turned `no` into `false`, so "no" had stayed a stopword.
2. A slow NetworkX edge-swap was replaced with the same rule implemented directly.

Both were logged in the analysis plan's change log (removed in the tidy-up of 18 November; see the git history).

## 3. Not used

- No LLM labels, summaries or motif annotations enter any analysis.
- No simulated reviewers.
- No generated images in charts: all figures are drawn from computed data.
