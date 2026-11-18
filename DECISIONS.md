# Decisions

Every judgement call made while building the paper pipeline (`python -m ouaw.run`), one line each. "Spec" is the task description of 11 November 2026. Settings live in `paper.yaml`; where a decision is a setting, change it there and rerun.

## Needs your decision

| # | Issue | What was done |
| --- | --- | --- |
| N1 | **sacred-texts.com terms.** Section 4 of the site's terms asks users "not to … scrape … the service outside its documented interfaces". Its `robots.txt` allows all paths. I checked only `robots.txt` before collecting. | 313 pages were downloaded on 11 November at one request per second (plus about 250 during exploration, repeated because I reset the cache once). Downloading is now off by default (`--fetch` switches it on). The texts are public-domain books of 1881–1907; the raw pages are not committed. You decide whether to keep this source, ask the site, or replace it (places to check for the same editions: Wikisource, Project Gutenberg, the Internet Archive; I did not verify which of them hold each book). |
| N2 | The spec says "1,498 versions with ATU type and place". 1,493 have one ATU type and 1,133 have a mapped place and region. | The map uses all 1,462 folktales. The type-versus-region test uses the 1,123 that carry both labels. The paper should state these numbers. |
| N3 | A wider screen on 11 November found 28 more versions from religious collections (Pauli, Luther's Table Talk, the Kangyur and others). | They stay on the map, because the spec fixes the calibration set at 36 and the map at 1,462. No sensitivity run without them was made. |
| N4 | **Editor's notes inside folktale texts** (found on 18 November, T18). Some cleaned texts end with D. L. Ashliman's notes, for example the Panchatantra note in 5 tales and remarks on Grimm editions in about 10. | The masking checks remove the formulaic parts and the type result survives them (Table 1). The cleaning was not changed, because that would change the map and every number. Decide whether to strip the notes in `analysis/clean.py` and rerun everything. |

## Feedback update (18 November 2026)

Judgement calls made while applying the feedback on the project (steps 1–9 of the update task). Numbering T1, T2, … in the order they were made.

| # | Decision | Why |
| --- | --- | --- |
| T1 | **Calibration is not circular; no number changed.** The 36 retellings were already outside the pool (`corpus.py` removes them before any map is built). New assertions: no calibration ID in the pool and no 5-word-shingle near-duplicate of one (checked in `load_corpus`, so in every stage), and no pool folktale with cosine above 0.9 to a retelling in either representation (checked in the `data` and `checks` stages). Highest cosines: TF-IDF 0.380, embeddings 0.894 (`results/calibration_exclusion.json`). | Spec step 1. The near-copy limit 0.9 is the same as the parable duplicate rule P3. |
| T2 | spaCy 3.8 and `en_core_web_sm` 3.8.0 are in a separate dependency group, `paper` (`uv sync --group paper`). | Only the noun-masking check needs them. The website deploy runs `uv sync --locked` and the tests; neither needs spaCy, and the noun-masking tests run on toy tagged tokens. |
| T3 | **Headline test.** Per tradition, the parable/baseline label is shuffled among that tradition's texts (1,000 times; `common.permute_within`); the text is the unit. "Closer than baseline" uses the one-sided p (parables closer), because the question is directional; the two-sided p is in the table too. The 95% interval resamples parables and baseline passages separately (10,000 draws). | Spec step 2. With the text as the unit, the 10 links of one parable are not treated as independent draws, the weakness of the old placement test (RESULTS.md, "Reading the placement test"). |
| T4 | The permutation p and the bootstrap interval can disagree near the edge (Jewish, TF-IDF: p = 0.020, interval −0.002 to +0.018). The verdict follows the permutation test; both are reported. | The spec names the permutation test as the test; the interval describes the size. |
| T5 | Community profile: each text's 10 nearest folktales, counted per canonical community of the same representation (TF-IDF map for TF-IDF and the noun-masked variant; embedding map for embeddings). Small communities (under 1% of the map) are one column. Cells are marked after Bonferroni correction over all tradition × community cells of a variant (50 for TF-IDF, 30 for embeddings). | Same partition as Part A and B. |
| T6 | **Type vote:** the ATU type with the largest summed cosine among a text's 10 nearest folktales; ties go to the type of the nearer folktale; folktales without one type do not vote. | "Voted ATU type" needed a definition. Summing cosines lets two moderately close versions of one type outvote a single closer tale. |
| T7 | Top source collection of a tradition = the collection with the largest share of the tradition's links, among links to folktales with a known collection; it is compared with that collection's share of the map and of the baseline's links. | Step 6.5. |
| T9 | **Length-matched excerpts.** For a text of n words, every folktale with at least 0.9 n words is eligible; 5 distinct eligible tales are drawn at random (seed in `paper.yaml`) and from each an excerpt of min(n, tale length) words is cut, starting at a random sentence start that leaves room. Excerpts are drawn for parables *and* baseline passages (2,245 in all; no text had fewer than 5 eligible tales). An excerpt's folk-closeness leaves out its own source tale and that tale's 5-word-shingle near-copies. The comparison is paired: a text's closeness minus the mean of its own 5 excerpts; median and bootstrap interval over texts. | Spec step 3. Sentence starts keep excerpts comparable to parables, which open at a sentence; near-copies are left out for the same reason as the source tale. The TF-IDF space stays the one fitted on all folktales (the source tale is in the IDF fit; effect negligible with 1,462 documents). |
| T10 | **Length regression:** closeness = slope × (log words − median parable log words) + one level per group, no intercept; groups = each tradition's parables, each tradition's baseline, folktale excerpts. Robust (HC1) standard errors, numpy. A second model on parables only (log words + tradition) answers whether the tradition order holds at equal length (Kendall τ with the raw order; same first and last). | Spec step 3.2. Levels at a common length are directly "closeness at equal length". |
| T11 | Baseline passages count as length-matched when a Mann-Whitney test of parable against baseline lengths gives p ≥ 0.05. All five traditions pass (p = 0.29 to 0.94; baseline medians 0.99 to 1.11 times the parable medians), so the matching was not changed. | Spec step 3.3. |
| T12 | **Noun masking:** tokens tagged NOUN or PROPN by spaCy `en_core_web_sm` are replaced by "[N]", which the TF-IDF tokenizer ignores (one letter); everything else stays. TF-IDF only: embeddings of noun-less text are not sentences the model was trained on. Neighbours are placed on the unmasked TF-IDF communities (the map stays the same). Raw closeness is not comparable between the two spaces (the masked vocabulary is smaller and commoner, so all cosines rise); the comparison is parables against baseline inside the masked space, and each tradition's percentile among folktales in each space. | Spec step 4.1. |
| T13 | A word counts as a noun when spaCy tags it NOUN or PROPN in at least half of its uses over all texts of the study (16,400 words). Match drivers: the 5 terms with the largest product of TF-IDF weights in a text's top-1 pair (unmasked TF-IDF); also the share of the whole cosine that comes from noun terms. | Spec step 4.2. |
| T14 | The hand-label template gets a `driver_terms` column: no coder value was filled and `labeling/hand_labels.csv` does not exist. From now on the `checks` stage leaves a template with filled values alone and writes `labeling/driver_terms_for_labelled_pairs.csv` instead. | Spec step 4.3. |
| T15 | **Type-vote accuracy** of the 36 retellings: share whose voted type (T6) is their own type. Chance: each query keeps its 10 cosines but its neighbours are 10 random folktales; 1,000 draws (mean and middle 95%). | Figure 3 needed a chance level for the vote. |
| T16 | **Edge-construction sweep:** densities 5%, 10%, 15% (existing builder) and symmetrised k-nearest-neighbour graphs, k = 5, 10, 20 (an edge if either tale is among the other's k most similar; ties to the lower index; positive cosines only). Density graphs reuse the Part A modularity nulls (100 shuffles at 10%, 20 otherwise); each kNN graph gets 20. Tale type, region and source collection are tested on the same 978 tales that carry all three labels, with 1,000 label shuffles. | Spec step 5.1; one node set keeps the three labels on the same scale. |
| T17 | **Within-collection null:** type and region labels shuffled only among tales of the same source collection (1,000 times). Tales without a collection are outside these tests; a collection with one tale never moves, which makes the null strict. | Spec step 6.3. |
| T18 | **Translator formulae** (`paper.yaml`, `masking.translator_formulae`): a scan for 5-word phrases in at least 3 tales with at least 60% of them in one collection found three formulae: the Panchatantra opening "In a certain place there lived" (5 tales), the Grimm header "Kinder- und Hausmärchen (Children's and Household Tales -- Grimms' Fairy Tales)" (4), and an editor's note on the Panchatantra (5 tales, 6 sentences). The other hits were shared plot phrases or near-copies of one tale. Added to the existing names-and-formulae masking, so every masked variant uses them. | Spec step 6.4. The scan also showed that some cleaned folktale texts end with the editor's notes; see N4. |
| T19 | Masked map: names, collection formulae and translator formulae masked in every folktale; TF-IDF refitted and embeddings recomputed on the masked texts; 10% graph; Louvain seed 42; the same label tests and nulls. | Spec step 6.4. |
| T20 | **Backbone for drawing:** the disparity filter keeps 73 (α = 0.05) and 22 (α = 0.01) edges of the thresholded 10% graph, whose weights are nearly uniform per tale, and 11,272 and 2,495 edges of the complete similarity graph. Figure 1 draws the complete graph's backbone at α = 0.01; at 0.05 the drawing was a hairball again. Positions stay those of ForceAtlas2 on the full 10% graph (A9); communities always come from the full graph. Embedding cosines are too uniform for any backbone (at most 2 edges), so Figure 1 uses TF-IDF. | Spec step 5.2. |
| T21 | **Structure against nulls:** the degree distribution against 20 random graphs G(n, m) of the same size; clustering (unweighted, and Onnela's weighted version, computed with dense matrices and checked against networkx in a test) against the first 20 shuffles of the Part A degree-preserving null (same seed and stream, so the same rewired graphs). TF-IDF clustering is far above a random graph of the same density but below the degree-preserving null: the hub-heavy degree sequence alone makes many triangles. Reported as found. | Spec step 5.3. |
| T22 | Community table: top words as in A5; "LDA topic" = the dominant topic most common among the community's tales, with its share; tale types, regions and source collections = the three most frequent with counts. | Spec step 5.3. |
| T23 | **Table 1 rule**, fixed in `ouaw/robustness.py` before the table was first computed: per tradition the headline is two verdicts, closer than baseline (one-sided permutation p < 0.05) and profile different from the baseline's (JSD permutation p < 0.05). A check holds "yes" if every comparable verdict agrees with the headline, "partly" if at least 60% agree, otherwise "no". Edge construction compares only the profile verdict (closeness needs no graph), on the five other partitions (communities under 1% grouped as in A4). Length compares only the closeness verdict (regression contrast at equal length, one-sided). Source collection: "yes" if tale type beats the within-collection null and no tradition sends more than 25% of its links to one collection. | Spec step 7 ("does the headline hold (yes/partly/no)") needed a rule. |
| T24 | "Home region" (spec step 7) is read as the recorded-region side of the map: no analysis of parables against a tradition's home region existed. Region stays in the Figure 1 inset, as the spec asks, and otherwise moves to Supplementary Figure S1, Section S1 of RESULTS.md and a supplementary table of the regions of each tradition's nearest folktales against its baseline (`results/headline_region_excess.csv`). | The only region analysis in the repository is type against region. |
| T25 | Figures follow a three-hue rule: the three largest communities in colour, the others grey with direct labels. Figure 2 shows the signed parable-minus-baseline excess as small multiples of bars (position, not colour, carries the value). Figures 2–4 of 11 November (`fig2_closeness`, `fig3_placement`, `fig4_calibration`) are superseded and no longer written; their old files are still in `figures/`. | Legibility; one headline figure. |
| T26 | **`report/numbers.tex`:** every number in `report/RESULTS.md`, `report/captions.md` and `report/short_update.md` passes through one registry (`report.Numbers`), which writes the macros (design settings such as the density and the number of shuffles too); a name must keep one value (asserted). Macro names are camel case with digits spelled out, because LaTeX command names cannot contain digits (`\recallTfidf`, `\headTfidfBuddhistDiff`, `\backboneAlphaZeroZeroOne`). `report/table1.tex` is Table 1 as a LaTeX tabular. | Spec step 9.2. |
| T27 | **Website:** renamed reIMAGINE with a storybook theme (IM Fell English, self-hosted via `@fontsource`); a new Overview page at `#/` reads `paper.json`; the earlier Story (type against place) moved to `#/story` as background; the Parables explorer now shows the parable-against-baseline test. No number on the site is typed by hand: results and settings come from `data/site/paper.json` and `parables.json`, built by the `site` stage from `results/`. The lesson study appears only as an "Earlier plan" note. The Validation page's pair rubric keeps its aspect "notable difference in outcome or moral": it compares two folktales, it is not lesson coding. | Spec step 8. |
| T28 | **Main-figure representation: TF-IDF**, the higher calibration recall@10 (0.69 against 0.61 for embeddings; unchanged by the step-1 check). Embeddings go to Supplementary Figure S2 and to Table 1. `figures.check_primary` refuses to draw if calibration ever favours the other representation. | Spec step 2 ("log the choice"); same rule as R3. |
| T29 | **Report material lives in `report/`, which is git-ignored:** `RESULTS.md`, `captions.md`, `short_update.md`, `numbers.tex`, `table1.tex`. Analysis tables stay in `results/`, figures in `figures/`, website data in `data/site/`. The earlier `results/RESULTS.md` moved to `report/`. | Rule of the authors (18 November): material for the final report is kept apart and not committed with the code, the analysis or the website. |
| T8 | **Source collection = the corpus's `source_key`** (author or editor of the cited book, as parsed by the existing cleaning stage): known for 1,284 of 1,462 folktales (564 collections; 55 with at least 5 tales cover 576 tales; 383 have one tale). The 178 "(no source)" tales are unknown. Recovering them from the notes was tried and dropped: only 10 notes hold a parsable reference. **Translator** = a "translated … by X" in the source or notes: stated for 168 tales only, so translator is not tested as a label of its own; it enters through the collection (a book has one translator) and through masking of translator formulae (step 6). | Step 6.1 ("log how many are missing"). |

## Structure

| # | Decision | Why |
| --- | --- | --- |
| S1 | New package `ouaw/` next to `analysis/`; the website pipeline (`python -m analysis`) is untouched. | Keeps the deployed site working and makes the one command `python -m ouaw.run --stage all`. |
| S2 | The paper pipeline's own settings are in `paper.yaml`. TF-IDF, embedding, density and seed settings are still read from `config.yaml`. | `config.yaml` is the frozen plan of the website run; its hash is part of that run's ID. |
| S3 | The lesson study moved to `legacy/lesson_study/`, mirroring its old paths. `config.yaml` and ANALYSIS_PLAN.md were returned to their committed state (the removed lines are in `legacy/` and in `git stash`). | Spec: keep it, take it out of the pipeline. |
| S4 | Work is on branch `parables-pipeline`. | Pushing `master` redeploys the site. |
| S5 | Development runs (`--sample N`) write to `results/_sample/` and `figures/_sample/` and never touch the full results. | A dev run must not overwrite numbers used in the paper. |
| S6 | New tests are unit tests on toy inputs (`tests/test_ouaw.py`). | The deploy workflow runs `pytest` on a fresh clone without the paper results. |

## Corpus

| # | Decision | Why |
| --- | --- | --- |
| C1 | Calibration set = the 36 versions found by the audit screen of 4 November, listed in `data/mappings/calibration_set.csv`. | Spec. The file is the single reviewable list. |
| C2 | The map keeps the 5 folktales with conflicting ATU labels and the 335 without a region, as nodes without that label. | They are folktales; only the label tests need labels. |
| C3 | `n_tokens` = whitespace-delimited words, for parables and folktales alike. | Same definition as the existing `n_words`. |

## Text representations

| # | Decision | Why |
| --- | --- | --- |
| R1 | TF-IDF vocabulary and IDF are fitted on the 1,462 folktales; every other text is projected. Words that no folktale uses are ignored. | Spec. Adding parables must not change the map. |
| R2 | The embedding cache stays in `data/interim/cache/` (per chunk, existing; per text, new), not `data/cache/`. | Reuses the existing cache, so no folktale was encoded again. |
| R3 | **Primary representation: TF-IDF.** Rule: the representation with the higher calibration recall@10. TF-IDF 0.69, embeddings 0.61. | `paper.yaml` held a placeholder until the gate. The first full Part B run and the gate ran in the same job, so the tradition medians were already printed when the choice was recorded; the choice follows the gate number alone. TF-IDF is also less tied to text length (Spearman 0.36 against 0.61) and less hub-prone. Both representations are reported everywhere. |
| R4 | Name masking uses the existing capitalised-word rule (course week 6) over all texts of the study, plus a list of collection formulae in `paper.yaml`. | spaCy is not installed. |
| R5 | Masked words are removed, not replaced by a visible token. | A token such as "X" is itself shared by every text with names. With "X", masked and unmasked embedding closeness correlated 0.77; with removal 0.88. For TF-IDF both give the same result. |

## Part A

| # | Decision | Why |
| --- | --- | --- |
| A1 | Louvain seeds 42, 7 and 19; the partition of seed 42 at 10% density is canonical. | The spec says "seed 0 = canonical"; the frozen configuration already uses these seeds with 42 first. |
| A2 | Modularity null: the repository's own edge-swap routine, 10 swaps per edge, weights reassigned at random; 100 shuffles at 10% density, 20 at 5% and 15%. | Same rule as `networkx.double_edge_swap`, which took hours here. Fewer shuffles at the other densities keep the run near 15 minutes. |
| A3 | Shuffles run in parallel processes, each with its own seeded random stream, and are cached per graph. | Results do not depend on the number of workers; reruns take 2 minutes. |
| A4 | Communities with fewer than 1% of the tales (isolates and tiny groups) are reported together as "small". | TF-IDF: 12 tales. Embeddings: 168 tales, 117 of them isolates. |
| A5 | Community labels are the words with the highest mean TF-IDF weight in the community relative to all tales, without name-like words. The course definition (community as one document) is in a second column. | With 5 to 9 large communities almost every word occurs in each, so the IDF over communities is 0 for the words that describe them. |
| A6 | LDA: k = number of communities with at least 1% of the tales; counts without stopwords and name-like words, words in at least 5 tales, 5,000 terms, 30 iterations, seed 0. | "k ≈ number of communities" in the spec. |
| A7 | Type versus region uses the map's partition restricted to the 1,123 tales with both labels and the edges among them. Tale type on all 1,457 typed tales is reported as well. | Both label systems are judged on the same tales. See N2. |
| A8 | The disparity filter at α = 0.05 keeps 73 of 106,799 edges (TF-IDF) and 0 (embeddings). The figure draws each tale's 5 strongest edges. | Edge weights in a thresholded similarity graph are nearly uniform per node. Drawing only. |
| A9 | Node positions come from ForceAtlas2 on the whole 10% graph (linear attraction, 300 iterations), not from the backbone. | The backbone's layout mixed the communities; the whole graph shows them. Drawing only. |
| A10 | PageRank z-scores are listed only for tales in the largest component with at least the median degree. | A tale with a few edges has almost no spread under the shuffles, so its z-score is huge and meaningless. |

## Parables

| # | Decision | Why |
| --- | --- | --- |
| P1 | Raw pages are cached compressed in `data/raw/parables/<tradition>/` and git-ignored; `fetch_log.csv` (URL, time, SHA-256) and `parables.csv` are committed. | Third-party page markup stays local; the texts are public domain. |
| P2 | Length limits: 40 to 3,000 tokens. | Shorter segments are cross-references; longer ones are epics (five Jātaka of 3,000 to 11,000 tokens were skipped). |
| P3 | A new story is dropped when it is a calibration version: same story number (Jātaka number; Masnavi book and story), same title, or TF-IDF cosine above 0.9. | Spec, plus the number where the corpus prints it. Five Jātaka numbers were identified by me from titles (marked in `calibration_set.csv`). Dropped: Jātaka 322 and 44; Masnavi II.13, IV.5, VI.7. |
| P4 | Where more stories qualify than the target, a seeded random draw of the target size is kept (Sufi 60 of 78, Taoist 50 of 115, Jātaka 72 of 547). | Targets in the spec; similar sizes per tradition. Set a target to `all` in `paper.yaml` to keep everything. |
| P5 | **Christian.** World English Bible (eBible.org, `engwebp`). 40 parables; verse ranges in `data/mappings/parables/christian_refs.yaml`; the longest of parallel tellings is kept. | Spec. |
| P6 | Christian ranges hold the story only (explanations such as Matthew 13:18–23 are left out). Mustard Seed with Leaven, and Hidden Treasure with Pearl, are one text each. John 10 and 15 are not included. | Each half of the two pairs is under 40 words; John's are discourses. Please review the YAML. |
| P7 | **Buddhist.** 72 Jātaka drawn at random from all 547 (Cowell edition), plus the 9 prose parables of the Lotus Sutra (Kern), cut where the speaker turns to the application. Burlingame was not collected. | Spec; Burlingame was optional. |
| P8 | Jātaka: the story of the past runs from the first paragraph that opens "Once on a time" (or a like formula) to the printed rule or the closing formula ("identified the Birth", "his lesson ended"). 1 of 72 could not be cut and is kept whole with a note. | Spec. |
| P9 | **Jewish.** Rapaport's book is a list of passages closed by a source reference; one passage is one item. Items that pass the story rule and have at least 60 tokens are the parables (50, all that qualify). | The target of 60 was not reached; lowering the length limit let sayings in. |
| P10 | The two retold legend cycles at the front of Rapaport's book (Alexander, Ashmedai) are not used. | They have no source references to cut them by. |
| P11 | **Sufi.** Per Masnavi story, the parable is Whinfield's prose summary; his translated couplets are the baseline. | The summary is the tale; the couplets are mostly the teaching hung on it. Some couplets are narrative, which makes the baseline a little too story-like (conservative). |
| P12 | **Taoist.** One numbered section of Legge's Zhuangzi is one item; books XXX and XXXI are undivided and are one item each. | Legge's own division. |
| P13 | Story rule for the Midrash and the Zhuangzi (`ouaw/parables/narrative.py`): enough past-tense action verbs, plus reported speech or a story opener; for the Midrash also little exegesis. It never looks at folktales. | Both sources mix stories with sayings. A rule that used similarity to folktales would bias the result. |
| P14 | The rule is strict. Of the proposal's three Zhuangzi examples, the butterfly dream and the useless tree pass it and Cook Ding does not. The random draw of 50 includes a useless-tree story (Book IV) but not the butterfly dream. | A looser rule let discursive sections in. Add purposive items in `taoist.py` if you want the famous ones. |
| P15 | Baseline passages: consecutive units of non-story text (verses, sayings, couplet lines), with lengths set to evenly spaced quantiles of the tradition's parable lengths and spread over the whole source. | Length matters for similarity, so length is matched first. |
| P16 | Where the source is too short, fewer passages are cut rather than shorter ones: Buddhist 24 (Dhammapada), Taoist 24 (Tao Te Ching); the others 40. | See P15. |
| P17 | Jewish baseline = Rapaport's short items without action or speech, and Pirqe Aboth (Taylor). Christian = Proverbs and the Epistles. | Spec. |
| P18 | No Hindu tradition. | Optional in the proposal. |

## Part B

| # | Decision | Why |
| --- | --- | --- |
| B1 | Folktale scale: each folktale's folk-closeness to all other folktales. A second value leaves out tales of its own type. | A folktale's nearest tales are often versions of the same tale; a parable has none. |
| B2 | Intervals: 10,000 bootstrap resamples of parables within a tradition, percentile method, seed 0. | Spec. |
| B3 | "Above the style baseline" = the 95% interval of (parable median minus baseline median) excludes 0. The share of parables above the baseline's 95th percentile is also given. | The proposal's "above this band" needed a definition. |
| B4 | Length adjustment: a parable's folk-closeness minus the median folk-closeness of folktales of the same length (15 quantile bins of log length, interpolated). | Closeness rises with length in both representations. |
| B5 | Placement null as in the spec (community labels shuffled over folktales, sizes kept), two-sided empirical p, Bonferroni over all cells for the asterisks in Figure 3. | Spec. |
| B6 | Added: Jensen–Shannon divergence between two traditions' link distributions against 1,000 shuffles of tradition labels over parables. | It answers "do traditions land in the same part?" with the parable as the unit; the label shuffle of B5 treats a parable's 10 links as independent. |
| B7 | Distinctive words: log-odds with a Dirichlet prior, closest against farthest quarter within a tradition. | Spec allows TF-IDF or log-odds. |
| B8 | `top_pairs.csv` holds the 5 highest top-1 cosines per representation, with the opening 30 words of both texts. | Spec. |

## Checks

| # | Decision | Why |
| --- | --- | --- |
| K1 | Gate rule: recall@10 is "clearly above chance" when its bootstrap 95% interval lies above the analytic chance rate and the chance of that many hits (Poisson-binomial) is below 0.001. | The spec's wording needed a number. Result: passed for both representations. |
| K2 | Hubs = the 10 folktales that occur most often in the parables' top-10 lists, per representation. | Spec. |
| K3 | The length check also reruns the ranking on parables of at least 100 tokens. | Short Gospel parables are the obvious risk. |
| K4 | The ranking is also rerun with k = 1 and k = 10 nearest folktales. | Shows that k = 5 is not doing the work. |
| K5 | Hand-label template: top-1 pair under the primary representation, 20 parables per tradition, seed 0, rows in mixed order, 120-word excerpts. The filled copy is `labeling/hand_labels.csv`. | The template is rewritten by every run; the filled file is not. |
| K6 | Precision: strict = "same_plot"; lenient = "same_plot" or "shared_motif"; both for each coder and for pairs where both agree. Weighted κ uses linear weights. | The four labels are ordered. |

## Figures

| # | Decision | Why |
| --- | --- | --- |
| F1 | Figure 2 has two panels, TF-IDF and embeddings, with the traditions in the same order. | Shows the second method next to the result. |
| F2 | Figure 1 names the communities in a legend, with short tags on the map. | Nine labels with words do not fit on the map. |
| F3 | Figure 3 is double-column when the map has more than 6 communities. | Ten columns. |
| F4 | Colours: three base hues, further colour-blind-safe hues for communities 4 to 9, one diverging blue–orange scale for Figure 3. Text is never in a series colour. | Legibility. |
