# Results

Written by `python -m ouaw.run --stage figures` on 2026-11-18. Every number is followed by the file that holds it and is also a LaTeX macro in `report/numbers.tex`. All statements describe these English translations and this corpus.

**Question.** Do parables from different religious traditions sit inside folktale communities more than non-story text from the same translations does, and which folktale communities and tale types do they land in?

*Motivation only, not tested:* "are parables just folktales with a moral attached?" Text similarity measures shared words and content; it says nothing about a moral, and no moral or lesson was coded.

**Primary representation: TF-IDF**, the representation with the higher calibration recall@10 (0.69 against 0.61 for embeddings) (`results/calibration.csv`). The other representation is reported next to it and in the robustness table.

## 1. Headline: where parables land, against non-story text of the same translation

- Design: 281 parables and 168 non-story passages cut from the same translations (Christian: World English Bible (eBible.org, engwebp); Buddhist: The Dhammapada (Sacred Books of the East 10); Jewish: Sayings of the Jewish Fathers (Pirqe Aboth) and Tales and Maxims from the Midrash; Sufi: Masnavi i Ma'navi, abridged; Taoist: The Tâo Teh King (Sacred Books of the East 39)) (`results/parables_summary.csv`). The baseline is length-matched in 5 of 5 traditions (Mann-Whitney p ≥ 0.29) (`results/length_matching.csv`). Folk-closeness of a text is its mean cosine to its 5 nearest of the 1,462 folktales. Every test shuffles the parable/baseline label within the tradition (1,000 times; the text is the unit); intervals are 10,000 bootstrap resamples (`results/headline_by_tradition.csv`).

### 1.1 Closer to folktales than the same translation's non-story text? (TF-IDF)

- Buddhist: parables 0.125, baseline 0.093; difference +0.032 (95% CI +0.015 to +0.046; permutation p < 0.001). 48% of the parables lie above the baseline's 95th percentile (shuffles: 8%; p < 0.001). (`results/headline_by_tradition.csv`)
- Taoist: parables 0.101, baseline 0.086; difference +0.015 (95% CI +0.008 to +0.021; permutation p < 0.001). 48% of the parables lie above the baseline's 95th percentile (shuffles: 9%; p < 0.001). (`results/headline_by_tradition.csv`)
- Jewish: parables 0.109, baseline 0.097; difference +0.011 (95% CI −0.002 to +0.018; permutation p = 0.020). 0% of the parables lie above the baseline's 95th percentile (shuffles: 7%; p = 1.000). The bootstrap interval includes 0. (`results/headline_by_tradition.csv`)
- Christian: parables 0.110, baseline 0.102; difference +0.008 (95% CI −0.007 to +0.023; permutation p = 0.072). 8% of the parables lie above the baseline's 95th percentile (shuffles: 7%; p = 0.493). (`results/headline_by_tradition.csv`)
- Sufi: parables 0.108, baseline 0.103; difference +0.005 (95% CI −0.009 to +0.016; permutation p = 0.177). 8% of the parables lie above the baseline's 95th percentile (shuffles: 7%; p = 0.420). (`results/headline_by_tradition.csv`)
- **Closer than their own baseline: Buddhist, Taoist and Jewish. Not closer: Christian and Sufi** (`results/headline_by_tradition.csv`).

### 1.2 Which folktale communities? (TF-IDF)

Each text's 10 nearest folktales are counted per community of the folklore map (Section 2). The profile of the parables is compared with the profile of their baseline (Jensen-Shannon divergence, same shuffles); cells are marked after Bonferroni correction over 50 tradition × community cells.

- Buddhist: the parables' profile does not differ from the baseline's (JSD 0.020 bits; shuffles 0.020; p = 0.457). Largest excess, not beyond the shuffles after correction: C2 (fox, wolf, lion) +3 points (p = 0.600). (`results/headline_community_excess.csv`)
- Taoist: the parables' profile differs from the baseline's (JSD 0.031 bits; shuffles 0.014; p = 0.010). Largest excess, not beyond the shuffles after correction: C4 (girl, door, house) +5 points (p = 0.008). (`results/headline_community_excess.csv`)
- Jewish: the parables' profile does not differ from the baseline's (JSD 0.010 bits; shuffles 0.012; p = 0.585). Largest excess, not beyond the shuffles after correction: C1 (king, prince, princess) +3 points (p = 0.478). (`results/headline_community_excess.csv`)
- Christian: the parables' profile differs from the baseline's (JSD 0.097 bits; shuffles 0.011; p < 0.001). Cells beyond the shuffles: C3 (money, husband, woman) +17 points (parables 26%, baseline 9%); C7 (parrot, thou, thee) −19 points (parables 2%, baseline 21%). (`results/headline_community_excess.csv`)
- Sufi: the parables' profile differs from the baseline's (JSD 0.043 bits; shuffles 0.014; p = 0.004). Largest excess, not beyond the shuffles after correction: C2 (fox, wolf, lion) +11 points (p = 0.008). (`results/headline_community_excess.csv`)
- The parables of Buddhist, Jewish, Sufi and Taoist link to C1 (king, prince, princess) far beyond its share of the map (+24 points on average), but so does their own baseline (+31 points): this lean belongs to the translations, not to the parables. (`results/headline_community_excess.csv`)

### 1.3 Which tale types?

The tale type voted by a text's 10 nearest folktales (largest summed cosine). Shares are of the tradition's parables or baseline passages.

- Buddhist: parables 502 The Wild Man (21%); 160 Grateful Animals, Ungrateful Man (7%); 91 Heart of Monkey as Medicine (7%). Baseline: 502 The Wild Man (21%) (`results/headline_atu_by_tradition.csv`).
- Taoist: parables 706 The Maiden without Hands (10%); 502 The Wild Man (8%); 545B Puss in Boots (8%). Baseline: 502 The Wild Man (29%) (`results/headline_atu_by_tradition.csv`).
- Jewish: parables 706 The Maiden without Hands (14%); 845 The Old Man and Death (8%); 980 The Ungrateful Son (6%). Baseline: 155 The Ungrateful Snake Returned to Captivity (18%) (`results/headline_atu_by_tradition.csv`).
- Christian: parables 650A Strong John (8%); 332 Godfather Death (8%); 981 Wisdom of Hidden Old Man Saves Kingdom (5%). Baseline: 777 The Wandering Jew (42%) (`results/headline_atu_by_tradition.csv`).
- Sufi: parables 706 The Maiden without Hands (20%); 332 Godfather Death (10%); 1423 The Enchanted Pear Tree (7%). Baseline: 706 The Maiden without Hands (35%) (`results/headline_atu_by_tradition.csv`).

### 1.4 Do the neighbours come from one source collection?

- No tradition's nearest folktales are dominated by one source collection (largest share 12%, Taoist: andrew lang, which holds 2.3% of the map and takes 7% of the baseline's links; threshold for "dominated": 25%) (`results/headline_by_tradition.csv`).
- Top collection per tradition: Buddhist andrew lang (10%); Taoist andrew lang (12%); Jewish gaster (5%); Christian wentworth webster (6%); Sufi jacob wilhelm grimm (5%).

### 1.5 What the resemblance consists of, tradition by tradition

- Buddhist: top-1 matches are carried by king, brahmin, thou, thee, thy; nouns give 69% of the top-1 cosine (baseline 51%). With nouns masked the parables are still closer than their baseline (+0.031; p < 0.001): the resemblance is more than a shared cast. (`results/match_drivers_by_tradition.csv`, `results/headline_by_tradition.csv`)
- Taoist: top-1 matches are carried by men, man, said, south, not; nouns give 55% of the top-1 cosine (baseline 55%). With nouns masked the parables are still closer than their baseline (+0.023; p < 0.001): the resemblance is more than a shared cast. (`results/match_drivers_by_tradition.csv`, `results/headline_by_tradition.csv`)
- Jewish: top-1 matches are carried by god, man, said, not, king; nouns give 81% of the top-1 cosine (baseline 70%). With nouns masked the parables are not closer than their baseline (+0.006; p = 0.126): the resemblance rests mostly on shared nouns. (`results/match_drivers_by_tradition.csv`, `results/headline_by_tradition.csv`)
- Christian: top-1 matches are carried by lord, said, not, servant, seed; nouns give 58% of the top-1 cosine (baseline 83%). With nouns masked the parables are closer than their baseline (+0.024; p < 0.001): the shared nouns of the baseline hid a resemblance in the rest of the wording. (`results/match_drivers_by_tradition.csv`, `results/headline_by_tradition.csv`)
- Sufi: top-1 matches are carried by god, lion, not, thou, king; nouns give 81% of the top-1 cosine (baseline 70%). With nouns masked the parables are not closer than their baseline (−0.005; p = 0.975): no resemblance beyond the baseline either way. (`results/match_drivers_by_tradition.csv`, `results/headline_by_tradition.csv`)
- Archaic pronouns (thou, thee, thy) are among the ten most frequent match drivers for Buddhist, Jewish and Sufi: part of what is matched is the register of the old translations, not the story (`results/match_drivers_by_tradition.csv`).

### 1.6 Second representation: embeddings

- With embeddings, parables are closer than their baseline for Buddhist, Christian and Sufi; not for Taoist and Jewish. Closer under both representations: Buddhist (`results/headline_by_tradition.csv`).
- Buddhist +0.101 (p < 0.001); Taoist +0.020 (p = 0.135); Jewish +0.032 (p = 0.096); Christian +0.104 (p < 0.001); Sufi +0.038 (p = 0.026) (`results/headline_by_tradition.csv`).

## 2. Supporting results: the map of world folklore

- Network (TF-IDF): 1,462 folktales; an edge for the top 10% of pairs by cosine (106,799 edges, cosine ≥ 0.096). Louvain (seed 42) finds 9 communities with at least 1% of the tales. Modularity 0.138 against 0.044 in 100 degree-preserving shuffles (z = 112); three seeds agree with NMI 0.64 to 0.78 (`results/network_robustness.csv`).

Communities of the TF-IDF map (`results/community_table.csv`):

| Community | Tales | Top words | LDA topic (share) | Dominant tale types | Regions | Source collections |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | 367 | king, prince, princess, daughter, queen, beautiful, palace, castle | king, not, said, princess, prince, daughter (47%) | 510B Peau d'asne (previously The Dress of Gold, of Silver, and of Stars [Cap o' Rushes]) (23); 545B Puss in Boots (17); 510A Cinderella (15) | Western Europe (66); Northern Europe (59); Southern Asia (47) | jacob wilhelm grimm (14); andrew lang (14); thomas frederick crane (9) |
| C2 | 317 | fox, wolf, lion, tail, tortoise, hare, jackal, race | said, not, fox, wolf, cat, bear (41%) | 275 The Race between Two Animals (previously The Race of the Fox and the Crayfish) (27); 155 The Ungrateful Snake Returned to Captivity (15); 20C The Animals Flee in Fear of the End of the World (12) | Northern Europe (69); Northern America (43); Southern Asia (31) | joel chandler harris (19); joseph jacobs (17); andrew lang (7) |
| C3 | 265 | money, husband, woman, wife, man, good, just, home | said, not, little, went, came, girl (31%) | 1540 The Student from Paradise (Paris) (15); 592 The Dance Among Thorns (12); 503 The Gifts of the Little People (11) | Northern Europe (97); Western Europe (54); Southern Europe (21) | jacob wilhelm grimm (18); joseph jacobs (10); thomas frederick crane (7) |
| C4 | 155 | girl, door, house, children, spinning, flax, sister, woman | said, not, little, went, came, girl (64%) | 480 The Kind and the Unkind Girls (previously The Spinning-Women by the Spring (13); 958E* Deep Sleep Brought on by a Robber (10); 327 The Children and the Ogre (10) | Northern Europe (55); Western Europe (34); Eastern Europe (19) | jacob wilhelm grimm (8); joseph jacobs (6); thomas frederick crane (5) |
| C5 | 121 | bridge, devil, shepherd, dream, dreamed, treasure, sheep, flute | devil, not, soldier, door, man, night (53%) | 1645 The Treasure at Home (18); 1191 Sacrifice on the Bridge (previously The Dog on the Bridge) (13); 670 The Man who Understands Animal Languages (previously The Animal Languages) (10) | Western Europe (42); Northern Europe (37); Southern Europe (11) | jacob wilhelm grimm (6); adalbert kuhn (4); karl haupt (3) |
| C6 | 116 | son, grandfather, father, man, death, child, old, merchant | said, man, not, no, old, went (57%) | 980 The Ungrateful Son (previously Ungrateful Son Reproved by Naive Actions of Own Son) (15); 332 Godfather Death (12); 779 Miscellaneous Divine Rewards and Punishments (10) | Western Europe (21); Southern Europe (14); Northern Europe (12) | jacob wilhelm grimm (5); thomas frederick crane (4); albert wesselski (4) |
| C7 | 59 | parrot, thou, thee, ship, thy, flying, eel, quoth | wife, not, husband, woman, no, good (37%) | 777 The Wandering Jew (26); 737 Who Will Be her Future Husband On New Year's Eve (Christmas Eve) a young woman foresees her future husband [D1825 (6); 237 The Talking Parrot (previously Magpie Tells why Sow is Muddy) (5) | Northern Europe (20); Western Europe (7); Western Asia (2) | book thousand nights night (4); hundred merry tales or (2); clouston (2) |
| C8 | 27 | grasshopper, ant, ants, rat, wind, elephant, summer, sun | said, man, not, no, old, went (52%) | 280A The Ant and the Cricket (previously The Ant and the Lazy Cricket) (7); 2031C The Mightiest Being as Husband for the Daughter (previously The Man Seeks the Greatest Being as a Husband for his Daughter) (7); 1317 The Blind Men and the Elephant (5) | Southern Asia (4); Western Europe (1); Eastern Asia (1) | cecil henry bompas (3); jean de la fontaine (3); ambrose bierce (2) |
| C9 | 23 | monkey, barber, monkeys, prize, razor, raja, birds, jackdaw | king, not, said, princess, prince, daughter (35%) | 782 Midas and the Donkey's Ears (3); 244 The Raven in Borrowed Feathers (3); 1586 The Man in Court for Killing a Fly (2) | Southern Asia (6); South-Eastern Asia (4); Northern Europe (2) | æsop fables (3); dean fansler (2); cecil henry bompas (1) |
| small | 12 | statement, members, childhood, honest, ring, vote, damned, scene | said, man, not, no, old, went (58%) | 173 Human and Animal Life Spans Are Readjusted (previously Men and Animals Readjust Span of Life) (2); 920E The Three Rings (2); 1430 The Man and his Wife Build Air Castles (1) | Northern Europe (3); Northern America (1); Southern Europe (1) | ambrose bierce (3); metamorphoses ovid (1); eric gustave geijer (1) |

- What the communities follow, on the 978 tales with type, region and source collection: tale type NMI 0.396 (label shuffles 0.159, largest 0.174; shuffles within collection 0.245, p < 0.001); region NMI 0.091 (label shuffles 0.030, largest 0.044; shuffles within collection 0.086, p = 0.019); source collection NMI 0.315 (label shuffles 0.284, largest 0.296) (`results/collection_confound.csv`).
- Attribute assortativity, which weighs every edge equally: tale type 0.029 (shuffles -0.002); region 0.056 (shuffles -0.002); source collection 0.005 (shuffles -0.002) (`results/collection_confound.csv`).
- Tale type beats the null that keeps every tale's source collection fixed (p < 0.001): the type signal is not just the style of a collection. Source collection itself is known for 1,284 of 1,462 tales (564 collections); a translator is named for only 168, too few to test on its own (`results/collection_metadata.json`).
- Built from texts with names and collection/translator formulae masked, the map keeps NMI 0.51 with the unmasked partition; tale type NMI 0.343 (within-collection shuffles 0.224; p < 0.001) (`results/collection_confound.csv`, `results/network_robustness.csv`).
- Degrees are far more unequal than in a random graph with the same number of edges (coefficient of variation 1.18 against 0.08; Gini 0.61 against 0.04; largest degree 724 against 185). Clustering is 0.56, far above a random graph of the same density (0.10), and below the 0.65 of degree-preserving shuffles (z = -46): the hub-heavy degree sequence alone produces even more triangles; weighted (Onnela) 0.07 against 0.08 (`results/network_structure.csv`).
- The most "archetypal" tales, more central by PageRank than their number of links predicts (z against the degree-preserving shuffles): “The Race (Parsons2)” (ATU 275, z = 39.0); “Keeping Pace” (ATU 275, z = 30.1); “The Wandering Jew (Scudder)” (ATU 777, z = 23.6); “Mr. Fox Goes a-Hunting, but Mr. Rabbit Bags the Game” (ATU 1, z = 23.0); “The Son Forgave His Father” (ATU 980, z = 20.7) (`results/network_archetypes.csv`).
- Backbone for drawing (disparity filter): at α = 0.05 it keeps 73 edges of the thresholded 10% graph and 11,272 of the complete similarity graph; at α = 0.01 it keeps 22 edges of the thresholded 10% graph and 2,495 of the complete similarity graph. The thresholded graph's weights are nearly uniform per tale, so almost nothing is significant there. Figure 1 draws the complete graph's backbone at α = 0.01: 2,495 edges touching 1,048 tales, 76% of them inside one community. Communities are always computed on the full 10% graph, never on a backbone (`results/network_backbone.csv`).
- Edge construction: across densities 5–15% and kNN graphs (k = 5, 10, 20), TF-IDF finds 7 to 27 communities; partitions share NMI 0.33 to 0.62 with the canonical one. In all 12 graphs of both representations, tale type is above its label shuffles (12 of 12) and above region in excess NMI (12 of 12) (`results/network_robustness.csv`).

## 3. Validity

- The calibration test is not circular: none of the 36 religious retellings, and no near-copy of one, is in the folktale pool; the highest cosine between a retelling and a pool folktale is 0.38 (TF-IDF); 0.89 (embeddings) (limit 0.90) (`results/calibration_exclusion.json`).
- TF-IDF: a same-type folktale is among the 10 nearest for 25 of 36 retellings (recall@10 0.69, 95% CI 0.53 to 0.83; chance 0.055, p < 0.001). The type voted by the 10 nearest is right for 13 (0.36; chance 0.006, 95% of random draws below 0.03) (`results/calibration.csv`).
- embeddings: a same-type folktale is among the 10 nearest for 22 of 36 retellings (recall@10 0.61, 95% CI 0.44 to 0.78; chance 0.055, p < 0.001). The type voted by the 10 nearest is right for 14 (0.39; chance 0.006, 95% of random draws below 0.03) (`results/calibration.csv`).
- TF-IDF with nouns masked: a same-type folktale is among the 10 nearest for 17 of 36 retellings (recall@10 0.47, 95% CI 0.31 to 0.64; chance 0.055, p < 0.001). The type voted by the 10 nearest is right for 9 (0.25; chance 0.006, 95% of random draws below 0.03) (`results/calibration.csv`).
- Hand labels: **pending.** `labeling/hand_labels_template.csv` holds the top-1 pair of 100 parables with the five terms that drive each match. Two coders fill `labeling/hand_labels.csv`; `python -m ouaw.agreement` then reports precision and Cohen's κ.

## 4. Robustness (Table 1)

The headline per tradition is two findings: parables closer to folktales than their baseline (one-sided permutation p < 0.05), and a community profile that differs from the baseline's. A check holds (yes) when every comparable verdict agrees with the headline, partly when at least 60% agree, otherwise no (`results/table1_robustness.csv`, `results/robustness_headline.csv`).

| Check | What changes | Headline holds | Verdicts agreeing | Key number |
| --- | --- | --- | --- | --- |
| Edge construction | densities 5% and 15%; kNN graphs, k = 5, 10, 20 (communities recomputed) | partly | 17 of 25 | profile verdicts agree in 17 of 25 tradition × partition cases; partitions share NMI 0.33–0.62 with the canonical one; tale type beats its label shuffles in 12 of 12 graphs and beats region in excess NMI in 12 of 12 |
| Representation | embeddings instead of TF-IDF | no | 4 of 10 | closer than baseline with embeddings: Christian, Buddhist, Sufi (headline: Buddhist, Jewish, Taoist); closer under both: Buddhist; Spearman of folk-closeness 0.58 |
| Length | parables against baseline at equal length (OLS on log words); length-matched folktale excerpts | partly | 3 of 5 | at equal length closer than baseline: Christian, Buddhist, Taoist; parables minus length-matched folktale excerpts -0.060 to -0.038 (all below); baselines length-matched in 5 of 5 traditions |
| Noun masking | nouns and proper nouns masked (spaCy), TF-IDF refitted | no | 4 of 10 | closer than baseline: Christian, Buddhist, Taoist (headline: Buddhist, Jewish, Taoist); recall@10 0.47 against 0.69 unmasked (chance 0.055) |
| Source collection | type and region shuffled within source collection; collections of the parables' neighbours | yes | 2 of 2 | type NMI 0.396 against 0.245 within collections (p < 0.001); region 0.091 against 0.086; at most 12% of a tradition's links go to one collection |
| Names and formulae masked | names, collection and translator formulae masked (TF-IDF refitted) | partly | 8 of 10 | closer than baseline: Christian, Buddhist, Taoist (headline: Buddhist, Jewish, Taoist); same top community for 3 of 3 traditions whose profile differs |
| Hubness | the 10 most frequent neighbours removed from the pool | partly | 9 of 10 | closer than baseline: Buddhist, Jewish, Taoist (headline: Buddhist, Jewish, Taoist); same top community for 3 of 3 traditions whose profile differs |

- Length: every tradition's parables are less folktale-like than folktale excerpts of the same length (median paired difference −0.060 to −0.038; 8% or fewer of a tradition's parables beat their own excerpts) (`results/length_control.csv`). Closeness rises with length (+0.020 per log word, p < 0.001); at equal length the order of the traditions is Christian > Buddhist > Jewish > Sufi > Taoist (raw: Buddhist > Christian > Jewish > Sufi > Taoist; Kendall τ 0.80) (`results/length_regression.csv`).
- Hubness: the 10 most frequent neighbours take 12% of all parable links (uniform 0.7%) (`results/checks_hubness.csv`).

## 5. Supplement

### S1. Recorded region

- Region is the weakest of the three labels: NMI 0.091 against 0.030 for label shuffles, below tale type in excess NMI in every edge construction (Supplementary Figure S1) (`results/network_robustness.csv`).
- Regions of the nearest folktales, parables against baseline: the largest excess per tradition is Buddhist Eastern Europe +4 points (p = 0.174); Taoist Northern Europe +8 points (p = 0.013); Jewish Southern Europe +4 points (p = 0.064); Christian Western Europe +13 points (p = 0.002); Sufi Southern Asia +9 points (p < 0.001) (`results/headline_region_excess.csv`).

### S2. Distance from folklore as a whole

- A folktale's folk-closeness to the other folktales has median 0.186. Tradition medians sit at the 11th (Buddhist), 3rd (Taoist), 4th (Jewish), 4th (Christian), 4th (Sufi) percentile of folktales (`results/partB_traditions.csv`, `results/partB_folktale_baseline.csv`).

## 6. What we can and cannot conclude

- Similarity has no direction: a parable close to a folktale did not necessarily borrow from it, or lend to it.
- Recording dates are not origin dates: a tale recorded in 1890 may be far older, so nothing here dates a story.
- Vocabulary is not narrative: TF-IDF matches shared words; the noun-masked check and the match drivers (1.5) show how much of each tradition's resemblance is a shared cast and how much is the rest of the wording, but neither measures plot structure.
- The corpus is 1,462 English folktale versions; 72% of those with a recorded region are European (`results/corpus_summary.json`). Each religious tradition is one or two English translations. Nothing here describes a religion or world folklore as a whole.
- The moral is not measured. Whether parables are folktales with a moral attached stays the motivation, not a result.

## Figures and tables

- `figures/fig1_map` (the map of world folklore), `figures/fig2_headline` (headline), `figures/fig3_validity` (validity), `figures/figS1_labels` (labels across edge constructions), `figures/figS2_headline_*` (headline with the second representation); PDF and PNG. Captions: `report/captions.md`. Table 1: `results/table1_robustness.csv` (data) and `report/table1.tex`; the community table as `report/community_table.tex`.
