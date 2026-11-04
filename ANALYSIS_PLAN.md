# Analysis plan (frozen 2026-10-29, before any agreement statistic was computed)

This plan fixes the preprocessing, cohorts, graph construction, evaluation measures, permutation counts and sensitivity checks for **Once Upon a World**. The machine-readable values live in `config.yaml`. When this plan was frozen, the only things that had been examined were the raw-data audit, the cleaning, the provenance mapping and the cohort *sizes*. No similarity graph, community partition or label-agreement score existed. Later changes are allowed only to correct defects or justified limitations, and each one is logged in the change log at the end.

## 1. Question

* **Public:** Do folktales form communities primarily around their geographical origins or around recurring narrative motifs?
* **Operational:** Do communities in a folktale text-similarity network align more closely with recorded geographical provenance or with established tale types (ATU), and does the answer differ between lexical (TF–IDF) and semantic (MiniLM) representations?

Every possible answer is admissible: geography matters, type matters, both, neither, or the answer depends on the representation or setting.

## 2. Data and cohorts

The corpus is `aft.csv` from `j-hagedorn/trilogy`, pinned at commit `d57c2ce`. Each cohort records membership and exclusion reasons. They are exported in `data/processed/cohorts.csv` (per narrative) and `outputs/audit/inclusion_ledger.csv` (per record).

| Cohort | Definition | Size at freeze |
| --- | --- | --- |
| Raw records | rows of the pinned CSV | 1,518 |
| Usable records | not excluded as non-narrative (9 reviewed exclusions) | 1,509 |
| **Text cohort** | distinct cleaned narratives (11 exact-duplicate records merged) | 1,498 |
| **ATU cohort** | text cohort with one unambiguous ATU label (5 conflicts out) | 1,493 |
| **Joint cohort** | ATU cohort with a defensible place *and* UN M49 broad region (mapping confidence high/medium) | 1,133 |
| **Distance cohort** | joint cohort whose place has documented coordinates | 1,084 |
| Validation sample | stratified pairs from the joint cohort (§8) | 84 pairs planned |

The joint cohort covers 164 ATU types, 89 place labels and 13 broad regions. Its geography is dominated by Europe (809 of 1,133 tales), so it cannot support a global claim.

## 3. Text representations (input = cleaned narrative text only)

Titles, ATU labels, provenance, sources and notes are **never** part of model input.

**Lexical.** A single TF–IDF space is fitted on the text cohort and reused for every subset. Settings: NFKC normalisation, lowercase, negated contractions expanded (`n't` → `not`), letters-only tokens of two or more characters, and the scikit-learn English stopword list *minus* 13 negation words. Unigrams, `min_df = 2`, sublinear TF, smoothed IDF, L2 normalisation.

**Semantic.** `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243…`. The verified limit is 256 tokens including special tokens. Each tale is cut into non-overlapping chunks of at most 200 tokens (special tokens included), measured with the model's own tokenizer and packed from whole sentences. Over-long sentences are split at clause punctuation and then at word windows. A final remainder under 32 tokens joins the previous chunk when it fits. Every chunk is asserted to fit, so nothing is silently truncated. Chunk vectors are unit length (the model's Normalize module). The tale vector is the equal-weight mean of its chunk vectors, L2-normalised.

**Similarity.** Cosine similarity in the original feature spaces, kept at full precision. Graph layout and PCA coordinates are never used to compute similarities.

## 4. Networks

* One node per narrative and one undirected, cosine-weighted edge per selected pair. No self-loops and no duplicate edges.
* Edges are the strongest positive pairs up to target densities of 5%, **10% (primary)** and 15%. The edge count is m = round(d · n(n−1)/2).
* **Tie rule:** sort pairs by similarity rounded to 12 decimals (descending), then by the narrative-ID pair (ascending), and take the first m. If fewer than m positive pairs exist, the achieved density is reported.
* Graphs are built separately per cohort. The **primary comparison uses the joint cohort**, with lexical and semantic graphs on identical node sets. The text-cohort graph is exploratory only.
* Weighted Louvain (`networkx.community.louvain_communities`) with resolution 1. **Seed 42 is primary**; seeds 7 and 19 are stability checks. The output records weighted modularity, component count, isolates and community sizes. Stability is the NMI between seed partitions. Isolates are kept, and an isolate-free sensitivity is reported if any exist.
* **Modularity null:** 20 degree-preserving edge-swap shuffles (10 swaps per edge), with the original edge weights reassigned at random to the shuffled edges and Louvain rerun on each. This preserves n, m, the degree sequence and the multiset of weights. Modularity is reported as observed − null mean and as a z-score, never as "significant community structure" on its own.

## 5. Primary comparison: geography or story family?

All label systems use the **same joint-cohort node set and the same partition**.

| Label system | Categories at freeze |
| --- | --- |
| ATU type | 164 |
| Place (country / constituent nation / community / region) | 89 |
| UN M49 broad region | 13 |
| Bibliographic source key *(diagnostic only, not a research label)* | — |

Measures:

1. **NMI** between the Louvain partition and each label system, using scikit-learn's default arithmetic normalisation (week 4 formula).
2. **Attribute assortativity** on the unweighted graph (NetworkX definition; it ignores edge weights) and the **share of edges joining same-label tales** (unweighted).
3. **Label-shuffle reference:** 1,000 permutations of each label vector across the fixed node set, with seed 20261029. Category counts are preserved and the graph and partition never change. For each measure and label system the output records the reference mean, sd, 95th/99th percentiles, the excess (observed − mean), z, and a one-sided empirical p = (1 + #null ≥ observed)/(1 + N). These describe association beyond what label frequencies produce on this fixed graph. They do not remove dependence from shared sources, translators or ancestry.
4. **Top-10 neighbour check** in the original feature space, within the cohort. For each tale, the share of its 10 nearest tales that share each label, against the frequency baseline (n_label − 1)/(n − 1). The output is the corpus mean, a per-ATU-type summary and a per-region summary.

**Interpretation rule (fixed in advance).** For one representation at one setting, "tale type aligns more closely than geography" (or the reverse) is stated only when NMI excess, assortativity r and neighbour lift (rate ÷ baseline) all order the two label systems the same way. Otherwise the result is reported as mixed. Place and broad region are different resolutions and are reported side by side. A label system "shows association" when its observed NMI and assortativity both exceed every one of the 1,000 shuffles. The lexical and semantic conclusions are stated separately. The overall answer is called robust only if the ordering holds at all three densities and all three seeds.

## 6. Sensitivity checks (all on precomputed outputs and identical procedures)

| Check | Variation |
| --- | --- |
| Density | 5% / 10% / 15% |
| Louvain seed | 42 / 7 / 19 |
| Pooling (semantic) | token-length-weighted mean of chunk vectors |
| Chunk size (semantic) | ≤ 128 tokens |
| Names (lexical) | words capitalised in > 50% of uses treated as names and removed (course week 6 rule) |
| Near duplicates | keep one narrative per word-5-gram near-duplicate component (Jaccard ≥ 0.5) |
| Fragments | drop narratives flagged as suspected truncated starts |
| Region-balanced subset | at most 60 tales per broad region, sampled with seed 42; graphs rebuilt on the subset |
| Source dependence | top-10 neighbour check repeated excluding neighbours with the same bibliographic source key; NMI(partition, source key) reported as a diagnostic |
| Exploratory text cohort | communities on the 1,498-tale graph, descriptive only |

## 7. Geographic distance extension (distance cohort)

* Great-circle distance between representative points, computed with the haversine formula and R = 6371.0088 km. Points are Natural Earth label points, so tales recorded in the same country have distance 0.
* Descriptive curves: mean and quartiles of similarity per distance bin, shown for all pairs, same-ATU pairs and different-ATU pairs.
* **Spearman ρ** between distance and similarity over all eligible pairs.
* Reference: 1,000 permutations that move each tale's *whole* location as one unit (seed 4242). Pair distances are never shuffled independently.
* No ordinary p-values or confidence bands that assume independent pairs. Any visual sampling (6,000 pairs, seed 11) is disclosed, and statistics always use all pairs.

## 8. Human validation

The sample is stratified by semantic-similarity band (percentiles of all joint-cohort pairs: top 2%, 70th–90th, below 50th), same vs different ATU, and same vs different region. That gives 12 strata, each with 2 development and 5 final pairs (seed 7), and no tale appears in more than 2 pairs. Reviewers see texts blind to ATU, provenance, model and score. Five aspects are recorded separately. Agreement is reported as raw agreement with disagreement counts. Validation stays **pending** until real annotation files exist; no simulated or LLM labels are counted.

## 9. Not done (deliberately)

No MRQAP, causal inference, phylogenetics, classifier training, topic-model claims, or modularity "significance" without the shuffle null. Centrality is not used to rank tales. No acquisition date is treated as a historical date.

## Change log

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-29 | Plan frozen. | — |
| 2026-10-29 | Added an isolate-free sensitivity: NMI on non-isolated tales only, with permutations restricted to those tales. | The global threshold leaves 15 (lexical) and 114 (semantic) isolates at 10% density, and the brief requires isolate effects to be stated. Added before results were interpreted; the main measures are unchanged. |
| 2026-10-29 | Display backbone switched from the disparity filter (α = 0.05) to each tale's 5 strongest edges in the analysis graph. | At α ≤ 0.2 the disparity filter kept 0–42 edges, because weights in these thresholded similarity graphs are nearly uniform per node. This affects drawing only, never statistics. |
| 2026-10-30 | **Defect fixed:** the negation word “no” is now kept out of the stopword list as planned. All lexical results were recomputed. | YAML parses a bare `no` as boolean false, so “no” had silently stayed a stopword in the first run. Caught by `tests/test_pipeline.py`. The config value is now quoted, and `lexical.stopwords` asserts that every kept word is a string. |
| 2026-10-30 | The degree-preserving shuffle for the modularity null is implemented directly (same rule as `networkx.double_edge_swap`) rather than by calling NetworkX. All six nulls were recomputed with it. | NetworkX rebuilds a neighbour list for every attempt, which took hours per shuffle set on the hub-heavy semantic graphs. The rule is unchanged: links A–B and C–D become A–D and C–B, and self-loops and repeated edges are rejected. The degree sequence is asserted after every shuffle and covered by a unit test. |
