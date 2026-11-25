# Progress

**Last updated:** 2026-11-18 · **Branch:** `feedback-update` (pushed; not merged into `master`; pushing `master` redeploys the website) · **Hand-in:** 27 November 2026

## Exploration and source links (18 November, late)

| Asked for | Done |
| --- | --- |
| Interactive exploration for every analysis | A new Explore page, and in every section of the Folktales and Parables pages an interaction (DECISIONS.md U13), including shuffles you run yourself (U14) and a TF-IDF/embeddings switch everywhere. |
| Links to read pairs of folktales | Every folktale links to its Ashliman Folktexts page, every parable to its source; any two texts can be read side by side with both links (U15). |

Checked: `python -m reimagine.run --stage site`; `uv run pytest` (all pass, including new checks that the browser shuffles reproduce the published NMI and that 98% of typed tales link to their page); `tests/browser/site_check.py` on all five pages at desktop and phone width, using every control once (no console errors, no sideways scrolling).

## AI-assist folder, clean-up, no hand validation, four-page website (18 November, night)

| Asked for | Done |
| --- | --- |
| AI-assistant files in one folder | `ai-assist/` holds DECISIONS.md, PROGRESS.md and AI_METHODS.md. `SOURCES.md` merged into the README; `LIMITATIONS.md` moved to `report/` (discussion material). Only README.md and LICENSE_NOTES.md stay at the top (U7). |
| Clean the repo | `outputs/` folded into `results/corpus_audit/`; `scripts/` (one-off drafting script) removed; process notes ("feedback update, step N") removed from code and settings; `tests/test_feedback_update.py` renamed `tests/test_checks.py`; dead local intermediate files of the old pipeline deleted; `.gitignore` simplified (U8). |
| Remove the hand validation | Hand-label template, the two-coder agreement module (Cohen's κ), the segmentation hand check, `labeling/`, Figure 3c and every mention in the report and the site removed (U9). |
| Remove unused data sources | Only `aft.csv`, `atu_df.csv` and the licence and attribution records stay; `atu_seq.csv`, `tmi.csv`, `atu_combos.csv`, Natural Earth, Crossref, the data dictionary and two documentation files are gone (U10). |
| Separate pages per analysis | Overview (the combination: three steps, the main figure, every check, the answer), Folktales (parts 1 and 2, seven sections), Parables (part 3, six sections), Methods & sources (every method with its course week) (U11, U12). |

Checked: the full pipeline ran from `data` to `figures` (exit 0; every `results/` table byte-identical to before), then `--stage site`; `uv run pytest` passes; `npm run build`; `tests/browser/site_check.py` on all four pages at desktop and phone width, with each page's controls used once.

## Tidy-up and one-story website (18 November, evening)

| Asked for | Done |
| --- | --- |
| Remove everything redundant | The old type-against-place website pipeline, its outputs and pages, 141 screenshots, logs, superseded figures, old planning documents, `audits/`, `legacy/`, another project's proposal, unused code and web dependencies (DECISIONS.md U1). Git history keeps all of it. |
| One project name | reIMAGINE everywhere: the package is `reimagine` (`python -m reimagine.run`), with the kept data-preparation and core code in `reimagine/core/` (U2, U3). |
| A concise website that tells a story | One page, six chapters, each "what we did, why, what we found", with interactions: recolour the map, a tale-type guessing game, read any parable beside its nearest folktale, rings on the map per tradition, switch the robustness checks on and watch which traditions still stand, then the answer and what cannot be answered (U4). Plus one Methods & sources page. All numbers come from `data/site/story.json` (U5). |

Checked: `uv run pytest` (67 pass), `python -m reimagine.run --stage figures site`, `npm run build`, and `tests/browser/site_check.py` on both pages at desktop and phone width with every interaction exercised (no console errors, no sideways scrolling).

## Feedback update (started 18 November)

Unfinished from the earlier tasks: the three decisions under "Needs your decision" and the tasks under "Work that only you can do" below. Blocked: nothing.

| Step | State |
| --- | --- |
| 1 Calibration not circular | Done. No retelling or near-copy in the pool (highest cosine TF-IDF 0.380, embeddings 0.894); assertion in every stage; no number changed (DECISIONS.md T1). |
| 2 Headline: parables against the same-translation baseline | Done (`reimagine/headline.py`, stage `headline`). TF-IDF: Buddhist, Taoist and Jewish parables are closer to folktales than their baseline (permutation p ≤ 0.02); Christian (p = 0.07) and Sufi (p = 0.18) are not. Embeddings: Christian, Buddhist, Sufi closer. The old "king, prince, princess" lean of four traditions is mostly shared with their own baseline; against it, Christian parables lean to C3 (money, husband, woman; +17 points), Sufi to C2 (fox, wolf, lion; +11), Taoist to C4 (+5). Outputs `results/headline_*.csv`. RESULTS.md is rewritten in step 9. |
| 3 Length confound | Done (`reimagine/length.py`, stage `length`). Baselines are length-matched (Mann-Whitney p ≥ 0.29). Every tradition's parables are *less* folktale-like than folktale excerpts of the same length (TF-IDF −0.04 to −0.06; embeddings −0.05 to −0.18): the gap to folklore is not a length effect. Closeness rises with length (TF-IDF +0.020 per log word). At equal length, parables beat their baseline for Buddhist and Taoist (p < 0.001), Christian borderline (p = 0.05), Jewish and Sufi not. The tradition order at equal length puts Christian first (τ = 0.8 with the raw order). |
| 4 Vocabulary against narrative | Done (`reimagine/vocab.py`, stage `vocab`; spaCy in group `paper`). With nouns masked, recall@10 0.69 → 0.47 (chance 0.055). Headline with nouns masked: Buddhist and Taoist hold, Christian becomes significant (p = 0.001), Jewish is lost (p = 0.13), Sufi none. Archaic pronouns (thou, thee, thy) are among the top match drivers of Buddhist, Jewish and Sufi texts: translation register. Template has `driver_terms` (no labels were filled). |
| 5 Network robustness | Done (`reimagine/network.py`, stage `network`). 12 graphs (densities 5–15%, kNN 5/10/20, both representations): tale type beats its shuffles and beats region in all 12; partitions differ (NMI 0.33–0.62 with the canonical one; 7 to 27 communities). Backbone drawn: disparity filter on the complete similarity graph, α = 0.01 (2,495 edges). Community table, degree and clustering against nulls, archetypal tales written. |
| 6 Collection and translator | Done (same stage). Collection known for 1,284 tales, translator for only 168. Type survives shuffles within collection (NMI 0.396 against 0.245); **region mostly does not** (0.091 against 0.086): the geography signal is largely the source collection. Three translator/editor formulae found and masked; the masked map keeps the type result. No tradition sends more than 12% of its links to one collection. |
| 7 Figures around one headline | Done (`reimagine/figures.py`, `reimagine/robustness.py`). Figures 1–3, S1, S2, captions, Table 1. |
| 8 Website (reIMAGINE) | Done, then rebuilt as one story (see the tidy-up above). Not deployed: `master` was not pushed. |
| 9 Ready for the report | Done. In `report/` (tracked since your commit `a2dcce9`): `RESULTS.md` in paper order, `numbers.tex` (every number as a macro), `table1.tex`, `captions.md`, `short_update.md`. The paper itself was not written. |

**Commits.** Steps 1–4 and your commit `a2dcce9` ("update") are on `origin/feedback-update`. Everything since (the tidy-up and this round) is uncommitted, for you to review and commit.

### What holds and what does not

- **Holds everywhere:** Buddhist parables are closer to folktales than their own translation's non-story text under every check (both representations, length control, nouns masked, names masked, hubs removed). The method finds known parallels (recall@10 0.69; 0.47 with nouns masked; chance 0.055). Tale type organises the map more than region in every graph, and beyond the source collection.
- **Holds mostly:** Taoist parables are closer than their baseline in every check except embeddings. Christian parables lean toward C3 (money, husband, woman) against their baseline.
- **Does not hold across representations:** the Christian, Jewish and Sufi verdicts. Christian is closer with embeddings and with nouns masked, not with plain TF-IDF; Jewish only with plain TF-IDF (its resemblance rests on shared nouns); Sufi only with embeddings.
- **Revised from 11 November:** the lean of four traditions toward the "king, prince, princess" community is shared by their own baseline, so it belongs to the translations. Region's NMI with the communities is mostly source collection.
- **Never in question:** every tradition's parables are less folktale-like than folktale excerpts of the same length.

### Left for the report

1. Decide on N1–N4 (DECISIONS.md), in particular N4 (editor's notes inside some folktale texts).
2. To deploy the site: commit, merge `feedback-update` into `master` and push; the workflow builds the site from `data/site/story.json`.

## Before the feedback update (11 November)

**State:** all five phases are done. `python -m reimagine.run --stage all` regenerates every table, the four figures and `results/RESULTS.md` on the full data; the 60 tests pass. The calibration gate of 14 November is already passed.

## Needs your decision

1. **sacred-texts.com terms of use.** The site's terms ask users not to scrape it; its `robots.txt` allows all paths. Four of the five traditions were collected from it on 11 November (313 pages at one request per second, plus about 250 during exploration) before I read the terms. Downloading is now off unless you pass `--fetch`. Decide whether to keep the source, ask the site, or replace it. Details: DECISIONS.md N1, README.md "Data sources".
2. **"1,498 versions with ATU type and place" is not what the corpus holds.** 1,493 have one ATU type; 1,133 have a mapped place and region. The type-versus-region test therefore runs on 1,123 of the 1,462 folktales. The proposal text should be corrected (DECISIONS.md N2).
3. **28 further versions from religious collections stay on the map** (found by the wider screen of 11 November; the spec fixes the calibration set at 36). Say if you want them removed or a sensitivity run (DECISIONS.md N3).

Blocked sources: none. Every page answered with HTTP 200 (`data/raw/parables/fetch_log.csv`).

## Work that only you can do

| Task | File | Then |
| --- | --- | --- |
| Review the Gospel verse ranges and the Lotus Sutra anchors | `data/mappings/parables/christian_refs.yaml`, `buddhist_lotus_refs.yaml` | Rerun from `--stage parables` |
| Check the five Jātaka numbers I assigned from titles | `data/mappings/calibration_set.csv`, column `known_story_basis` | Rerun from `--stage parables` if one is wrong |

## Done, by phase

| Phase | Result |
| --- | --- |
| 0 Audit | AUDIT.md (removed in the tidy-up; in the git history) |
| 1 Restructure, Part A | Lesson study moved to `legacy/`. New package `reimagine/`. Map of 1,462 folktales for TF-IDF and embeddings |
| 2 Parables | 281 parables (Christian 40, Buddhist 81, Jewish 50, Sufi 60, Taoist 50) and 168 baseline passages in `data/processed/parables.csv` |
| 3 Part B, calibration | Ranking, baselines, placement; gate passed |
| 4 Checks | Second method, length, hubness, masking, hand-label template, `reimagine/agreement.py` |
| 5 Figures, report | `figures/fig1`–`fig4` (PDF, PNG), `results/RESULTS.md` |
| Optional | PageRank z-scores done. Not done: Burlingame's *Buddhist Legends*, a Hindu tradition, a run without the 28 further religious versions |

## Key numbers (full run of 2026-11-11; the current numbers are in `report/RESULTS.md`)

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
git checkout feedback-update
uv sync --group paper                                  # spaCy for the noun-masking check
uv run pytest                                          # 81 tests
uv run python -m reimagine.run --stage all --sample 100     # about 2 minutes; writes to results/_sample
uv run python -m reimagine.run --stage all                  # full run incl. site build; about 20 minutes with warm caches
cd web && npm run preview                              # then: python tests/browser/site_check.py http://localhost:4173/
```

Read in this order: this file, DECISIONS.md (both in `ai-assist/`), `report/RESULTS.md` (regenerate it with `--stage figures` if `report/` is empty). Settings are in `paper.yaml`. The raw source pages are in `data/raw/parables/` on this machine only (git-ignored); without them the `parables` stage keeps the committed `parables.csv`. Node for the site build is found on PATH or in `.tools/node-*`.

## Possible next steps

1. Settle the three decisions above.
2. If wanted: rerun without the 28 further religious versions; add Burlingame; add purposive Zhuangzi parables (Cook Ding, the butterfly dream).
3. Merge `feedback-update` into `master` when the paper numbers are final.
