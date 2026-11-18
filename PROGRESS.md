# Progress

**Last updated:** 2026-11-18 · **Branch:** `ta-feedback` (from `parables-site`; not merged; pushing `master` redeploys the website) · **Hand-in:** 27 November 2026

## TA feedback update (started 18 November)

Unfinished from the earlier tasks, carried over unchanged: the three decisions under "Needs your decision" and the four tasks under "Work that only you can do" below. Blocked: nothing.

| Step | State |
| --- | --- |
| 1 Calibration not circular | Done. No retelling or near-copy in the pool (highest cosine TF-IDF 0.380, embeddings 0.894); assertion in every stage; no number changed (DECISIONS.md T1). |
| 2 Headline: parables against the same-translation baseline | to do |
| 3 Length confound | to do |
| 4 Vocabulary against narrative | to do |
| 5 Network robustness | to do |
| 6 Collection and translator | to do |
| 7 Figures around one headline | to do |
| 8 Website (reIMAGINE) | to do |
| 9 Ready for the report | to do |

## Before the TA update (11 November)

**State:** all five phases are done. `python -m ouaw.run --stage all` regenerates every table, the four figures and `results/RESULTS.md` on the full data; the 60 tests pass. The calibration gate of 14 November is already passed.

## Needs your decision

1. **sacred-texts.com terms of use.** The site's terms ask users not to scrape it; its `robots.txt` allows all paths. Four of the five traditions were collected from it on 11 November (313 pages at one request per second, plus about 250 during exploration) before I read the terms. Downloading is now off unless you pass `--fetch`. Decide whether to keep the source, ask the site, or replace it. Details: DECISIONS.md N1, README.md "Data sources".
2. **"1,498 versions with ATU type and place" is not what the corpus holds.** 1,493 have one ATU type; 1,133 have a mapped place and region. The type-versus-region test therefore runs on 1,123 of the 1,462 folktales. The proposal text should be corrected (DECISIONS.md N2).
3. **28 further versions from religious collections stay on the map** (found by the wider screen of 11 November; the spec fixes the calibration set at 36). Say if you want them removed or a sensitivity run (DECISIONS.md N3).

Blocked sources: none. Every page answered with HTTP 200 (`data/raw/parables/fetch_log.csv`).

## Work that only you can do

| Task | File | Then |
| --- | --- | --- |
| Hand-check the segmentation of 20 parables per tradition | `labeling/segmentation_check.csv` (fill `segmentation_ok`, `comment`) | Tell me which rules to tighten, or edit the YAML files and rerun `--stage parables` |
| Review the Gospel verse ranges and the Lotus Sutra anchors | `data/mappings/parables/christian_refs.yaml`, `buddhist_lotus_refs.yaml` | Rerun from `--stage parables` |
| Label 100 top-1 pairs, two coders | copy `labeling/hand_labels_template.csv` to `labeling/hand_labels.csv` | `python -m ouaw.agreement`, then `python -m ouaw.run --stage figures` |
| Check the five Jātaka numbers I assigned from titles | `data/mappings/calibration_set.csv`, column `known_story_basis` | Rerun from `--stage parables` if one is wrong |

## Done, by phase

| Phase | Result |
| --- | --- |
| 0 Audit | AUDIT.md |
| 1 Restructure, Part A | Lesson study moved to `legacy/`. New package `ouaw/`. Map of 1,462 folktales for TF-IDF and embeddings |
| 2 Parables | 281 parables (Christian 40, Buddhist 81, Jewish 50, Sufi 60, Taoist 50) and 168 baseline passages in `data/processed/parables.csv` |
| 3 Part B, calibration | Ranking, baselines, placement; gate passed |
| 4 Checks | Second method, length, hubness, masking, hand-label template, `ouaw/agreement.py` |
| 5 Figures, report | `figures/fig1`–`fig4` (PDF, PNG), `results/RESULTS.md` |
| Optional | PageRank z-scores done. Not done: Burlingame's *Buddhist Legends*, a Hindu tradition, a run without the 28 further religious versions |

## Key numbers (full run of 2026-11-11; all in `results/RESULTS.md`)

TF-IDF is the primary representation (higher calibration recall); embeddings are the second method.

**Calibration gate: passed.** A same-type folktale is in the top 10 for 25 of the 36 religious retellings with TF-IDF (recall@10 0.69, 95% interval 0.53 to 0.83) and for 22 with embeddings (0.61, 0.44 to 0.78). Chance is 0.055.

**Part A.**

| | TF-IDF | Embeddings |
| --- | --- | --- |
| Edges at 10% density | 106,799 | 106,799 |
| Modularity (100 degree-preserving shuffles) | 0.138 (0.044 ± 0.001) | 0.186 (0.039 ± 0.001) |
| Communities with at least 1% of the tales | 9 (12 tales outside) | 5 (168 tales outside) |
| NMI between Louvain seeds | 0.64 to 0.78 | 0.85 to 0.88 |
| NMI with tale type (shuffle mean), n = 1,123 | 0.378 (0.149) | 0.367 (0.214) |
| NMI with region (shuffle mean), n = 1,123 | 0.087 (0.026) | 0.134 (0.099) |
| Assortativity: type, region | 0.024, 0.054 | 0.017, 0.032 |

Communities follow tale type more than region by NMI. Assortativity is higher for region, as in the website run.

**Part B.** Folk-closeness = mean cosine to the 5 nearest folktales.

| | TF-IDF median [95% CI] | Embeddings median [95% CI] |
| --- | --- | --- |
| Folktales to each other | 0.186 | 0.749 |
| Buddhist | 0.125 [0.116, 0.136] | 0.664 [0.630, 0.683] |
| Christian | 0.110 [0.105, 0.122] | 0.594 [0.569, 0.634] |
| Jewish | 0.109 [0.099, 0.113] | 0.546 [0.518, 0.584] |
| Sufi | 0.108 [0.103, 0.112] | 0.635 [0.610, 0.659] |
| Taoist | 0.101 [0.096, 0.106] | 0.543 [0.518, 0.567] |

- Every tradition is far less close to folktales than folktales are to each other (TF-IDF: 3rd to 11th percentile of folktales).
- Buddhist parables are the most folktale-like and Taoist the least in both representations; the middle three change order.
- Above non-story text of the same translation: Buddhist and Taoist (TF-IDF); Buddhist and Christian (embeddings). For the others the interval includes 0.
- Placement (TF-IDF): Buddhist, Taoist, Jewish and Sufi parables attach to the "king, prince, princess" community well above its share of the map (+32, +25, +21, +19 percentage points); Christian parables do not (+3).
- Traditions differ in where they land more than shuffled tradition labels do (mean divergence 0.051 bits against 0.013 ± 0.003), but the divergence is small.

**Checks.** TF-IDF and embeddings agree moderately on which parables are folktale-like (Spearman 0.58) and hardly on which folktales are nearest (mean Jaccard of the top-10 lists 0.09). Folk-closeness rises with length (Spearman 0.36 TF-IDF, 0.61 embeddings). Buddhist stays first under masking, hub removal, a length floor and k = 1 or 10; relative to folktales of the same length, Christian parables move to first.

## How to resume

```bash
git checkout parables-pipeline
uv sync
uv run pytest                                          # 60 tests
uv run python -m ouaw.run --stage all --sample 100     # 1 minute; writes to results/_sample
uv run python -m ouaw.run --stage all                  # full run; about 5 minutes with warm caches
```

Read in this order: this file, DECISIONS.md, `results/RESULTS.md`. Settings are in `paper.yaml`. The raw source pages are in `data/raw/parables/` on this machine only (git-ignored); without them the `parables` stage keeps the committed `parables.csv`.

## Possible next steps

1. Settle the three decisions above.
2. Fill the hand labels; Figure 4 and RESULTS.md pick them up.
3. If wanted: rerun without the 28 further religious versions; add Burlingame; add purposive Zhuangzi parables (Cook Ding, the butterfly dream).
4. Merge `parables-pipeline` into `master` when the paper numbers are final.
