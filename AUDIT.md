# Audit of the repository before the parable pipeline (Phase 0, 2026-11-11)

No code was changed for this audit. It records what exists, what the new pipeline reuses, what moves to `legacy/`, the target layout and the phase plan. The earlier feasibility audit of 4 November is a different document: `audits/2026-11-04-full-feasibility/AUDIT.md`.

## 1. What exists

| Area | Files | State |
| --- | --- | --- |
| Data preparation | `analysis/fetch.py`, `clean.py`, `audit.py`, `cohorts.py` | Working. Produces `data/processed/narratives.parquet`: 1,498 cleaned narratives, pinned at trilogy commit `d57c2ce`. Present on disk. |
| Text representations | `analysis/lexical.py` (TF-IDF, negations kept, name masking by a capitalised-word rule), `analysis/semantic.py` (MiniLM, 200-token sentence-packed chunks, mean pooling, chunk cache keyed by model + text hash) | Working. The embedding cache for all 1,498 tales is on disk (`data/interim/cache/`). |
| Networks | `analysis/networks.py`: density-threshold edge selection with a tie rule, Louvain wrapper, modularity, degree-preserving edge swaps, disparity filter, k-strongest backbone, ForceAtlas2 layout | Working and unit-tested. |
| Label agreement | `analysis/metrics.py`: NMI, attribute assortativity, label-shuffle null, top-k neighbours | Working; tested against scikit-learn and NetworkX. |
| Website pipeline | `analysis/analyze.py`, `modnull.py`, `distance.py`, `validation.py`, `layouts.py`, `export.py`, `analysis/__main__.py` (`python -m analysis all`), `web/`, `.github/workflows/deploy-pages.yml` | Working (run `ouaw-20261111-ed9feb8a`; same content hash as the 30 October run). Builds its graphs on the *joint cohort* (1,133 tales with a type and a place), not on the folktale map the new spec asks for. |
| Lesson study (dropped) | `analysis/frame.py`, `analysis/aesop.py`, `scripts/coding.py`, `scripts/draft_framing_review.py`, `data/annotations/`, `data/mappings/framing_review.csv`, `data/processed/lesson_frame.csv`, `data/raw/aesop/`, `outputs/audit/lesson_frame*`, `config.yaml` sections `frame` and `lessons`, ANALYSIS_PLAN.md section 10 | All uncommitted. Not part of `python -m analysis all`. Only `scripts/coding.py` imports `analysis.aesop`; nothing imports `analysis.frame`. |
| Earlier feasibility audit | `audits/2026-11-04-full-feasibility/` | Committed, self-contained. Holds the pilot (`scripts/pilot_b.py`) and the list of 36 religious-collection versions. |
| Tests | `tests/test_metrics.py`, `test_common.py`, `test_export.py`, `test_pipeline.py`; browser journeys in `tests/browser/` | 34 tests pass. |

Environment: Python 3.11.9 in `.venv` (uv), numpy 2.4, pandas 3.1, scikit-learn 1.9, networkx 3.6, sentence-transformers 6.2, torch 2.15 (CPU), matplotlib 3.11. Not installed: spaCy, BeautifulSoup, lxml.

## 2. The 36 calibration versions

They were found by a metadata screen in `audits/2026-11-04-full-feasibility/scripts/annotation_frame.py` (regular expressions over provenance, source and title) and are listed in `audits/2026-11-04-full-feasibility/evidence/religious_collection_versions.csv`. The same 36 are the rows of `data/mappings/framing_review.csv` with `found_by = "audit screen 2026-11-04"`, where each also has a tradition and a collection. The counts match the spec: 18 Jātaka, 11 Gesta Romanorum, 4 Rumi, 2 Jacques de Vitry, 1 Talmud. All 36 have one unambiguous ATU type, and each type has between 1 and 24 other versions among the remaining folktales (median 6), so recall@10 is defined for every query.

The new pipeline reads the list from one reviewable file, `data/mappings/calibration_set.csv`, written once from those 36 rows.

## 3. Points where the repository and the spec differ

These are settled in DECISIONS.md. The first two affect what the paper can say.

1. **Place labels cover 1,127 of the 1,462 folktales, not all of them.** The corpus has 1,498 narratives; 1,493 have one unambiguous ATU type and 1,133 have a mapped place and region (the "joint cohort"). The existing type-versus-region test ran on a graph built from the joint cohort only. In the new structure the map is built from all 1,462 folktales, and the type-versus-region comparison is computed on the 1,123 map nodes that carry both labels, using the map's partition and the edges among those nodes. The website run's joint-cohort numbers are quoted next to it as a cross-check.
2. **A wider screen on 11 November found 28 more religious-collection versions** (Pauli, Luther's Table Talk, the Kangyur and others; `framing_review.csv` has 64 rows). The spec fixes the calibration set at 36 and the map at 1,462, so those 28 stay in the folktale map. A sensitivity run without them is listed as optional.
3. **Disparity filter.** At α = 0.05 it kept almost no edges on these graphs (0–42 edges at α ≤ 0.2; ANALYSIS_PLAN.md change log, 29 October), because edge weights in a thresholded similarity graph are nearly uniform per node. The new pipeline computes the α = 0.05 filter and reports how many edges it keeps; if that is too few to draw, the figure uses the documented fallback (each tale's 5 strongest edges). Drawing only.
4. **Seeds.** The frozen configuration uses Louvain seeds 42, 7 and 19 with 42 as primary. The spec says "seed 0 = canonical". The existing seeds are kept and the first one (42) is canonical.
5. **Modularity null.** The repository's own edge-swap routine (same rule as `networkx.double_edge_swap`, O(1) per attempt) is kept; the NetworkX function took hours per shuffle set on these graphs.
6. **Name masking.** spaCy is not installed, so the existing capitalised-word rule (course week 6) is reused, plus a list of collection formulae.
7. **Embedding cache location.** The existing cache lives in `data/interim/cache/`, not `data/cache/`. It is reused in place so that no folktale is re-embedded.

## 4. Sources for the parables (reachability checked 2026-11-11)

| Site | Result |
| --- | --- |
| sacred-texts.com | Reachable. `robots.txt` allows all paths. The site has been redesigned: old addresses such as `bud/j1/j1004.htm` redirect to `/book/<book>/<chapter>`, and the chapter text is in the served HTML (`<article data-slot="reader-content">`). Pages are about 400 KB each. |
| ebible.org (World English Bible) | Reachable (`engwebp_usfm.zip`, 2.9 MB). |
| gutenberg.org | Reachable. |

Raw pages are cached compressed under `data/raw/parables/<tradition>/` and are git-ignored (third-party page markup); the fetch log with URL, date and SHA-256 is committed, and so is `data/processed/parables.csv`.

## 5. Reuse, move, leave

| Decision | What |
| --- | --- |
| **Reuse unchanged** | `analysis/common.py`, `lexical.py` (`preprocess`, `stopwords`, `fit`, `name_like_words`), `semantic.py` (`Chunker`, `encode_cached`, `pool`), `networks.py`, `metrics.py`; the data stages `fetch`, `clean`, `audit`, `cohorts`. |
| **Leave working, do not extend** | The website pipeline (`python -m analysis all`), `web/`, the deploy workflow, the Validation page, `tests/`. |
| **Move to `legacy/`** | Everything in the "Lesson study" row of section 1, with the `frame` and `lessons` config sections and ANALYSIS_PLAN.md section 10. |
| **Dead code** | None found beyond the lesson study. |

## 6. Target layout

```text
analysis/              existing package: data stages, reusable core, website pipeline (unchanged)
ouaw/                  new package: the paper pipeline
  run.py               python -m ouaw.run --stage {data,parables,partA,partB,checks,figures,all} [--sample N]
  corpus.py            stage data: 1,462 folktales + 36 calibration versions from narratives.parquet
  parables/            stage parables: polite cached fetch, one extractor per tradition, baselines, parables.csv
  reps.py              TF-IDF fitted on the folktales; cached embeddings; masked variant
  part_a.py            map: graphs, Louvain, modularity null, community words, LDA, type vs region, PageRank, backbone
  part_b.py            ranking, folk_closeness, baselines, attachment, placement null, distinctive words
  checks.py            calibration gate, second method, length, hubness, hand-label template
  agreement.py         raw agreement, Cohen's kappa, confusion table, precision
  figures.py           fig1–fig4
  report.py            results/RESULTS.md
legacy/                lesson study (kept, not run)
results/               CSV tables and RESULTS.md      figures/   fig1–fig4 (PDF + PNG)
labeling/              segmentation_check.csv, hand_labels_template.csv
```

A second package next to `analysis/` keeps the website pipeline byte-for-byte untouched and makes the one command exactly `python -m ouaw.run --stage all`.

## 7. Phase plan

| Phase | Content | Priority |
| --- | --- | --- |
| 1 | Move the lesson study to `legacy/`; `ouaw` skeleton, `data` stage, representations, Part A on the 1,462 folktales | P0 |
| 2 | Parable collection for five traditions, baselines, `parables.csv`, segmentation check | P0 |
| 3 | Part B and the calibration gate | P0 |
| 4 | Checks: second method, length, hubness, masking, hand-label template, `agreement.py` | P1 |
| 5 | Figures 1–4, `results/RESULTS.md`, README | P1 |
| Optional | PageRank z-scores, Burlingame, sensitivity without the 28 further religious versions | P2 |

Each phase ends with the tests, a `--sample 100` run, an update of PROGRESS.md and a commit.
