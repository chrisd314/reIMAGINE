# Results

Written by `python -m ouaw.run --stage figures` on 2026-11-11. Figures use the primary representation, **TF-IDF**; the other representation is reported next to it as the second method. Every sentence ends with the file that holds its numbers. All statements describe these English translations and this corpus.

## Data

- The map is built from 1,462 English folktale versions. The 36 versions from religious collections (18 Jātaka; 11 Gesta Romanorum; 4 Rumi, Masnavi; 2 Jacques de Vitry, sermon exempla; 1 Talmud) are held out as calibration queries (`results/corpus_summary.json`).
- 1,457 folktales carry one ATU tale type (182 types); 1,127 have a mapped region (13 regions); 1,123 have both. The type-versus-region test uses those 1,123 (`results/corpus_summary.json`).
- 281 parables from 5 traditions and 168 non-story baseline passages from the same translations (`results/parables_summary.csv`); full texts in `data/processed/parables.csv`:

| Tradition | Parables | Median tokens | Baseline passages | Baseline median tokens | Sources |
| --- | --- | --- | --- | --- | --- |
| Christian | 40 | 132 | 40 | 137 | World English Bible (eBible.org, engwebp) |
| Buddhist | 81 | 399 | 24 | 409 | Saddharma-Puṇḍarīka, or the Lotus of the True Law (Sacred Books of the East 21); The Jātaka, vol. 1 (ed. E. B. Cowell); The Jātaka, vol. 2 (ed. E. B. Cowell); The Jātaka, vol. 3 (ed. E. B. Cowell); The Jātaka, vol. 4 (ed. E. B. Cowell); The Jātaka, vol. 5 (ed. E. B. Cowell) |
| Jewish | 50 | 189 | 40 | 210 | Tales and Maxims from the Midrash |
| Sufi | 60 | 317 | 40 | 313 | Masnavi i Ma'navi, abridged |
| Taoist | 50 | 323 | 24 | 349 | The Writings of Kwang-dze (Sacred Books of the East 39-40) |

- Sources that could not be downloaded: 0. Stories left out and why: (`results/parables_skipped.csv`).

## Part A: the map of world folklore

### TF-IDF (primary)

- Network: 1,462 folktales, an edge for the top 10% of pairs by cosine (106,799 edges, cosine ≥ 0.096); 10 tales have no edge (`results/partA_graphs.csv`).
- Communities: Louvain (seed 42) finds 20 communities, 9 of them with at least 1% of the tales (1,450 tales; the other 12 tales sit in isolates and tiny groups) (`results/partA_summary.json`).
- Modularity is 0.138 against 0.044 ± 0.0008 in 100 degree-preserving shuffles (largest shuffle value 0.046; z = 112) (`results/partA_graphs.csv`).
- The three Louvain seeds agree with NMI 0.64 to 0.78 (`results/partA_graphs.csv`).
- Other densities: 5% density: 0.197 against 0.062 in 20 shuffles; 15% density: 0.114 against 0.036 in 20 shuffles (`results/partA_graphs.csv`).
- Type or region: on the 1,123 tales with both labels, NMI between communities and ATU type is 0.378 (1,000 label shuffles: mean 0.149, largest 0.167; excess 0.229). For region it is 0.087 (shuffles: mean 0.026, largest 0.037; excess 0.061) (`results/partA_type_vs_region.csv`).
- Attribute assortativity, which weighs every edge equally, is 0.024 for tale type and 0.054 for region (shuffles: -0.002 and -0.002; both above every shuffle) (`results/partA_type_vs_region.csv`).
- Share of edges joining two tales of the same type: 4.0% (shuffles 0.8%); of the same region: 22.8% (shuffles 18.3%) (`results/partA_type_vs_region.csv`).
- LDA with 9 topics: NMI between a tale's dominant topic and its community is 0.243 (label shuffles 0.012 ± 0.0020); topic words in (`results/partA_lda_topics.csv`).
- Drawing: the disparity filter at α = 0.05 keeps 73 of 106,799 edges. The figure draws each tale's 5 strongest edges (5,363 edges) (`results/partA_summary.json`).

Communities of the TF-IDF map (`results/partA_communities.csv`):

| Community | Tales | Top words (TF-IDF lift) | Most frequent tale types |
| --- | --- | --- | --- |
| C1 | 367 | king, prince, princess, daughter, queen, beautiful, palace, castle | 510B Peau d'asne (previously The Dress of Gold, of Silver, and of Stars [Cap o' Rushes]) (23); 545B Puss in Boots (17); 510A Cinderella (15) |
| C2 | 317 | fox, wolf, lion, tail, tortoise, hare, jackal, race | 275 The Race between Two Animals (previously The Race of the Fox and the Crayfish) (27); 155 The Ungrateful Snake Returned to Captivity (15); 20C The Animals Flee in Fear of the End of the World (12) |
| C3 | 265 | money, husband, woman, wife, man, good, just, home | 1540 The Student from Paradise (Paris) (15); 592 The Dance Among Thorns (12); 503 The Gifts of the Little People (11) |
| C4 | 155 | girl, door, house, children, spinning, flax, sister, woman | 480 The Kind and the Unkind Girls (previously The Spinning-Women by the Spring (13); 958E* Deep Sleep Brought on by a Robber (10); 327 The Children and the Ogre (10) |
| C5 | 121 | bridge, devil, shepherd, dream, dreamed, treasure, sheep, flute | 1645 The Treasure at Home (18); 1191 Sacrifice on the Bridge (previously The Dog on the Bridge) (13); 670 The Man who Understands Animal Languages (previously The Animal Languages) (10) |
| C6 | 116 | son, grandfather, father, man, death, child, old, merchant | 980 The Ungrateful Son (previously Ungrateful Son Reproved by Naive Actions of Own Son) (15); 332 Godfather Death (12); 779 Miscellaneous Divine Rewards and Punishments (10) |
| C7 | 59 | parrot, thou, thee, ship, thy, flying, eel, quoth | 777 The Wandering Jew (26); 737 Who Will Be her Future Husband On New Year's Eve (Christmas Eve) a young woman foresees her future husband [D1825 (6); 237 The Talking Parrot (previously Magpie Tells why Sow is Muddy) (5) |
| C8 | 27 | grasshopper, ant, ants, rat, wind, elephant, summer, sun | 280A The Ant and the Cricket (previously The Ant and the Lazy Cricket) (7); 2031C The Mightiest Being as Husband for the Daughter (previously The Man Seeks the Greatest Being as a Husband for his Daughter) (7); 1317 The Blind Men and the Elephant (5) |
| C9 | 23 | monkey, barber, monkeys, prize, razor, raja, birds, jackdaw | 782 Midas and the Donkey's Ears (3); 244 The Raven in Borrowed Feathers (3); 1586 The Man in Court for Killing a Fly (2) |
| small | 12 | statement, members, childhood, honest, ring, vote, damned, scene | 173 Human and Animal Life Spans Are Readjusted (previously Men and Animals Readjust Span of Life) (2); 920E The Three Rings (2); 1430 The Man and his Wife Build Air Castles (1) |

### Embeddings (second method)

- Network: 1,462 folktales, an edge for the top 10% of pairs by cosine (106,799 edges, cosine ≥ 0.643); 117 tales have no edge (`results/partA_graphs.csv`).
- Communities: Louvain (seed 42) finds 133 communities, 5 of them with at least 1% of the tales (1,294 tales; the other 168 tales sit in isolates and tiny groups) (`results/partA_summary.json`).
- Modularity is 0.186 against 0.039 ± 0.0010 in 100 degree-preserving shuffles (largest shuffle value 0.042; z = 150) (`results/partA_graphs.csv`).
- The three Louvain seeds agree with NMI 0.85 to 0.88 (`results/partA_graphs.csv`).
- Other densities: 5% density: 0.230 against 0.056 in 20 shuffles; 15% density: 0.162 against 0.033 in 20 shuffles (`results/partA_graphs.csv`).
- Type or region: on the 1,123 tales with both labels, NMI between communities and ATU type is 0.367 (1,000 label shuffles: mean 0.214, largest 0.226; excess 0.153). For region it is 0.134 (shuffles: mean 0.099, largest 0.114; excess 0.035) (`results/partA_type_vs_region.csv`).
- Attribute assortativity, which weighs every edge equally, is 0.017 for tale type and 0.032 for region (shuffles: -0.002 and -0.002; both above every shuffle) (`results/partA_type_vs_region.csv`).
- Share of edges joining two tales of the same type: 3.3% (shuffles 0.8%); of the same region: 22.7% (shuffles 18.3%) (`results/partA_type_vs_region.csv`).
- LDA with 5 topics: NMI between a tale's dominant topic and its community is 0.222 (label shuffles 0.004 ± 0.0015); topic words in (`results/partA_lda_topics.csv`).
- Drawing: the disparity filter at α = 0.05 keeps 0 of 106,799 edges. The figure draws each tale's 5 strongest edges (5,178 edges) (`results/partA_summary.json`).

Communities of the embeddings map (`results/partA_communities.csv`):

| Community | Tales | Top words (TF-IDF lift) | Most frequent tale types |
| --- | --- | --- | --- |
| C1 | 433 | fox, wolf, hare, tail, cat, lion, got, dog | 275 The Race between Two Animals (previously The Race of the Fox and the Crayfish) (17); 155 The Ungrateful Snake Returned to Captivity (16); 130 The Animals in Night Quarters (13) |
| C2 | 359 | king, prince, princess, daughter, beautiful, queen, castle, girl | 510B Peau d'asne (previously The Dress of Gold, of Silver, and of Stars [Cap o' Rushes]) (21); 510A Cinderella (18); 706 The Maiden without Hands (16) |
| C3 | 328 | man, devil, bridge, money, treasure, peasant, death, dream | 1645 The Treasure at Home (21); 980 The Ungrateful Son (previously Ungrateful Son Reproved by Naive Actions of Own Son) (14); 592 The Dance Among Thorns (13) |
| C4 | 126 | girl, woman, husband, wife, home, went, mother, witch | 366 The Man from the Gallows (9); 480 The Kind and the Unkind Girls (previously The Spinning-Women by the Spring (8); 327 The Children and the Ogre (7) |
| C5 | 48 | turtle, monkey, crab, fish, crane, pond, heron, shell | 231 The Heron and the Fish (previously The Heron [Crane] Transports the Fish) (10); 275 The Race between Two Animals (previously The Race of the Fox and the Crayfish) (9); 225 The Crane Teaches the Fox to Fly (5) |
| small | 168 | grasshopper, grave, ants, ant, elephant, summer, legend, traveller | 777 The Wandering Jew (20); 280A The Ant and the Cricket (previously The Ant and the Lazy Cricket) (8); 779 Miscellaneous Divine Rewards and Punishments (8) |

- The TF-IDF and the embedding map are different partitions of the same tales: NMI between them is 0.35 (`results/partA_summary.json`).
- Cross-check: the earlier network built only from the 1,133 tales with both labels (website pipeline) gives the same order of NMI excess. TF-IDF: type 0.191, region 0.088; embeddings: type 0.163, region 0.034 (`outputs/metrics/agreement.json`).
- Tales more central than their number of links predicts (TF-IDF; PageRank against the degree-preserving shuffles, among tales in the largest component with at least the median degree): “The Race (Parsons2)” (ATU 275, z = 39.0); “Keeping Pace” (ATU 275, z = 30.1); “The Wandering Jew (Scudder)” (ATU 777, z = 23.6); “Mr. Fox Goes a-Hunting, but Mr. Rabbit Bags the Game” (ATU 1, z = 23.0); “The Son Forgave His Father” (ATU 980, z = 20.7) (`results/partA_pagerank_top10.csv`).
- Tales more central than their number of links predicts (embeddings; PageRank against the degree-preserving shuffles, among tales in the largest component with at least the median degree): “The Dance for Water; or, Rabbit's Triumph” (ATU 175, z = 25.5); “The Awful Fate of Mr. Wolf” (ATU 124, z = 20.4); “Death's Messengers (Grimm)” (ATU 335, z = 19.9); “The Dream of the Zirl Bridge” (ATU 1645, z = 19.0); “Playing Dead Twice in the Road” (ATU 1, z = 18.5) (`results/partA_pagerank_top10.csv`).

## Part B: parables on the map

Folk-closeness of a text is the mean cosine to its 5 nearest folktales. Intervals are 95% bootstrap intervals over parables.

### TF-IDF (primary)

- Scale: a folktale's folk-closeness to the other folktales has median 0.186 (middle 50%: 0.152 to 0.227). Leaving out tales of its own type, the median is 0.155 (`results/partB_folktale_baseline.csv`).
- Ranking of traditions by median folk-closeness (`results/partB_traditions.csv`):

| Rank | Tradition | Parables | Median [95% CI] | Percentile among folktales | Same-translation baseline median | Parables minus baseline [95% CI] | Parables above baseline 95th pct | Minus folktales of same length |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Buddhist | 81 | 0.125 [0.116, 0.136] | 11 | 0.093 | +0.032 [+0.015, +0.046] | 48% | -0.053 |
| 2 | Christian | 40 | 0.110 [0.105, 0.122] | 4 | 0.102 | +0.008 [-0.008, +0.023] | 8% | -0.045 |
| 3 | Jewish | 50 | 0.109 [0.099, 0.113] | 4 | 0.097 | +0.011 [-0.002, +0.018] | 0% | -0.058 |
| 4 | Sufi | 60 | 0.108 [0.103, 0.112] | 4 | 0.103 | +0.005 [-0.009, +0.016] | 8% | -0.068 |
| 5 | Taoist | 50 | 0.101 [0.096, 0.106] | 3 | 0.086 | +0.015 [+0.008, +0.021] | 48% | -0.073 |

- Most folktale-like tradition: Buddhist (median 0.125); least: Taoist (0.101). The folktale median is 0.186, so the tradition medians sit at the 11th, 4th, 4th, 4th, 3rd percentile of folktales, in rank order (`results/partB_traditions.csv`).
- Above the style baseline (interval of parables minus same-translation non-story text excludes 0): Buddhist, Taoist. Not above: Christian, Jewish, Sufi (`results/partB_traditions.csv`).
- Placement: each parable is linked to its 10 nearest folktales. Entropy of a tradition's links over the communities, against 1,000 shuffles of the community labels (`results/partB_attachment_entropy.csv`): Christian 2.63 bits (shuffles 2.77 ± 0.07, p = 0.035); top community C1 with 28% of links; Buddhist 2.17 bits (shuffles 2.76 ± 0.08, p < 0.001); top community C1 with 57% of links; Jewish 2.48 bits (shuffles 2.77 ± 0.07, p < 0.001); top community C1 with 46% of links; Sufi 2.46 bits (shuffles 2.77 ± 0.07, p < 0.001); top community C1 with 44% of links; Taoist 2.23 bits (shuffles 2.76 ± 0.07, p < 0.001); top community C1 with 50% of links.
- Cells that differ from the shuffle expectation after Bonferroni correction over 50 cells (`results/partB_attachment.csv`): Buddhist: C1 +32 points (share 57%, expected 25%); Christian: C2 -11 points (share 10%, expected 22%); Jewish: C1 +21 points (share 46%, expected 25%), C2 -12 points (share 9%, expected 22%); Sufi: C1 +19 points (share 44%, expected 25%), C3 -10 points (share 8%, expected 18%); Taoist: C1 +25 points (share 50%, expected 25%).
- Do traditions land in the same communities? Mean Jensen-Shannon divergence between two traditions' link distributions is 0.051 bits; shuffling tradition labels over parables gives 0.013 ± 0.003 (p < 0.001). Closest pair: Jewish and Sufi (0.023); farthest: Christian and Buddhist (0.104) (`results/partB_tradition_overlap.csv`).
- Distinctive words of the closest against the farthest quarter of each tradition's parables (log-odds) (`results/partB_distinctive_words.csv`):
  - Christian: closest: came, did, father, vineyard, son, servant, sent, servants, gave, hour. Farthest: like, invited, parable, sit, wine, manager, fell, no, friends, world.
  - Buddhist: closest: king, day, asked, went, came, told, said, thou, wife, brahmin. Farthest: sleep, question, brahmadatta, poison, verses, bodhisatta, answer, parents, welfare, smell.
  - Jewish: closest: god, moses, jacob, joseph, did, life, thou, people, brothers, sons. Farthest: rabbi, woman, quite, taken, cause, child, voyage, sage, josé, went.
  - Sufi: closest: pharaoh, moses, ass, no, king, lion, away, fox, long, faith. Farthest: prophet, abu, evil, replied, cried, outward, free, discovered, answered, mosalman.
  - Taoist: closest: king, kwang, round, prince, dze, death, yüeh, majesty, wû, state. Farthest: shun, people, virtue, neither, lâo, tan, harmony, disciples, human, mean.

### Embeddings (second method)

- Scale: a folktale's folk-closeness to the other folktales has median 0.749 (middle 50%: 0.684 to 0.807). Leaving out tales of its own type, the median is 0.729 (`results/partB_folktale_baseline.csv`).
- Ranking of traditions by median folk-closeness (`results/partB_traditions.csv`):

| Rank | Tradition | Parables | Median [95% CI] | Percentile among folktales | Same-translation baseline median | Parables minus baseline [95% CI] | Parables above baseline 95th pct | Minus folktales of same length |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Buddhist | 81 | 0.664 [0.630, 0.683] | 19 | 0.563 | +0.101 [+0.062, +0.129] | 56% | -0.088 |
| 2 | Sufi | 60 | 0.635 [0.610, 0.659] | 12 | 0.597 | +0.038 [-0.008, +0.071] | 20% | -0.092 |
| 3 | Christian | 40 | 0.594 [0.569, 0.634] | 6 | 0.491 | +0.104 [+0.058, +0.148] | 40% | -0.063 |
| 4 | Jewish | 50 | 0.546 [0.518, 0.584] | 3 | 0.514 | +0.032 [-0.013, +0.086] | 26% | -0.137 |
| 5 | Taoist | 50 | 0.543 [0.518, 0.567] | 3 | 0.524 | +0.020 [-0.012, +0.047] | 30% | -0.180 |

- Most folktale-like tradition: Buddhist (median 0.664); least: Taoist (0.543). The folktale median is 0.749, so the tradition medians sit at the 19th, 12th, 6th, 3rd, 3rd percentile of folktales, in rank order (`results/partB_traditions.csv`).
- Above the style baseline (interval of parables minus same-translation non-story text excludes 0): Buddhist, Christian. Not above: Sufi, Jewish, Taoist (`results/partB_traditions.csv`).
- Placement: each parable is linked to its 10 nearest folktales. Entropy of a tradition's links over the communities, against 1,000 shuffles of the community labels (`results/partB_attachment_entropy.csv`): Christian 1.14 bits (shuffles 2.27 ± 0.09, p < 0.001); top community C3 with 76% of links; Buddhist 1.90 bits (shuffles 2.27 ± 0.09, p < 0.001); top community C2 with 42% of links; Jewish 1.62 bits (shuffles 2.30 ± 0.07, p < 0.001); top community C3 with 56% of links; Sufi 1.76 bits (shuffles 2.29 ± 0.08, p < 0.001); top community C3 with 49% of links; Taoist 1.87 bits (shuffles 2.29 ± 0.08, p < 0.001); top community C3 with 46% of links.
- Cells that differ from the shuffle expectation after Bonferroni correction over 30 cells (`results/partB_attachment.csv`): Sufi: C3 +27 points (share 49%, expected 23%), C1 -16 points (share 13%, expected 30%); Christian: C3 +54 points (share 76%, expected 23%), C1 -24 points (share 6%, expected 30%); Jewish: C3 +34 points (share 56%, expected 22%), C1 -20 points (share 9%, expected 30%); Taoist: C3 +23 points (share 46%, expected 22%), C1 -21 points (share 9%, expected 30%).
- Do traditions land in the same communities? Mean Jensen-Shannon divergence between two traditions' link distributions is 0.046 bits; shuffling tradition labels over parables gives 0.010 ± 0.004 (p < 0.001). Closest pair: Jewish and Sufi (0.006); farthest: Christian and Buddhist (0.144) (`results/partB_tradition_overlap.csv`).
- Distinctive words of the closest against the farthest quarter of each tradition's parables (log-odds) (`results/partB_distinctive_words.csv`):
  - Christian: closest: said, lord, did, came, servant, servants, father, talents, went, son. Farthest: light, wine, friend, like, no, say, children, sit, heaven, bread.
  - Buddhist: closest: king, said, day, asked, brahmin, shall, death, come, lion, place. Farthest: sleep, born, sea, spirit, good, crow, brahmadatta, heart, water, verses.
  - Jewish: closest: man, wife, king, brought, old, tongue, woman, majesty, power, husband. Farthest: went, asked, men, place, rabbi, called, means, persian, food, away.
  - Sufi: closest: ass, fox, said, solomon, faith, ayaz, woman, king, told, wife. Farthest: outward, voice, prophet, darvesh, abu, moses, object, house, hand, ground.
  - Taoist: closest: king, kwang, kâu, death, prince, round, wû, majesty, officers, did. Farthest: tâo, dze, kung, know, yâo, shun, neither, carry, no, wish.

- Reading the placement test: the label shuffle treats the 10 links of a parable as separate draws, but the nearest folktales of one parable resemble each other, so the shuffle spread is too narrow and the z-scores in `partB_attachment.csv` are generous. The tradition-label shuffle above uses the parable as the unit.

## Checks

### Calibration (the 14 November gate): **passed**

- Rule: recall@10 of the 36 calibration versions is clearly above chance for at least one representation: the bootstrap 95% interval lies above the analytic chance rate and the chance of that many hits is below 0.001 (`results/gate.json`).
- tfidf: recall@10 = 0.69 (95% CI 0.53 to 0.83; 25 of 36 queries) against a chance rate of 0.055 (2.0 hits expected; p < 0.001). Recall@1 = 0.50, recall@5 = 0.61; the first same-type folktale is at median rank 1.5 of 1,462 (`results/calibration.csv`).
- tfidf_masked: recall@10 = 0.69 (95% CI 0.53 to 0.83; 25 of 36 queries) against a chance rate of 0.055 (2.0 hits expected; p < 0.001). Recall@1 = 0.50, recall@5 = 0.61; the first same-type folktale is at median rank 1.5 of 1,462 (`results/calibration.csv`).
- embedding: recall@10 = 0.61 (95% CI 0.44 to 0.78; 22 of 36 queries) against a chance rate of 0.055 (2.0 hits expected; p < 0.001). Recall@1 = 0.44, recall@5 = 0.50; the first same-type folktale is at median rank 5.5 of 1,462 (`results/calibration.csv`).
- embedding_masked: recall@10 = 0.61 (95% CI 0.44 to 0.78; 22 of 36 queries) against a chance rate of 0.055 (2.0 hits expected; p < 0.001). Recall@1 = 0.44, recall@5 = 0.56; the first same-type folktale is at median rank 4 of 1,462 (`results/calibration.csv`).
- Per query: (`results/calibration_queries.csv`).

### Second method

- TF-IDF against embeddings over 281 parables: Spearman correlation of folk-closeness 0.58; mean Jaccard overlap of the two top-10 neighbour lists 0.08; 31% of parables share no neighbour; 5% have the same nearest folktale (`results/checks_second_method.csv`).
- By tradition (Spearman; Jaccard): Christian 0.52; 0.05; Buddhist 0.74; 0.12; Jewish 0.19; 0.06; Sufi 0.52; 0.12; Taoist 0.30; 0.04 (`results/checks_second_method.csv`).

### Length

- TF-IDF: Spearman correlation of folk-closeness with length in tokens: parables ρ = 0.36; baseline passages ρ = 0.20; folktales (leave-one-out) ρ = 0.43 (`results/checks_length.csv`).
- embeddings: Spearman correlation of folk-closeness with length in tokens: parables ρ = 0.61; baseline passages ρ = 0.67; folktales (leave-one-out) ρ = 0.71 (`results/checks_length.csv`).

### Hubness

- TF-IDF: 42% of folktales are in no parable's top 10; the 10 most frequent neighbours take 12% of all links (uniform: 0.7%); skewness of the occurrence counts 6.44. Most frequent: “The Wild Man” (5009 tokens), a neighbour of 21% of parables (`results/checks_hubness.csv`), (`results/checks_hubs.csv`).
- embeddings: 63% of folktales are in no parable's top 10; the 10 most frequent neighbours take 20% of all links (uniform: 0.7%); skewness of the occurrence counts 6.54. Most frequent: “Ali Baba and the Forty Thieves” (11088 tokens), a neighbour of 25% of parables (`results/checks_hubness.csv`), (`results/checks_hubs.csv`).

### Does the tradition ranking survive?

Order of the traditions by median, most folktale-like first, under each variant (`results/checks_ranking_variants.csv`):

| Representation | Variant | Order (median) |
| --- | --- | --- |
| TF-IDF | as reported | Buddhist (0.125) > Christian (0.110) > Jewish (0.109) > Sufi (0.108) > Taoist (0.101) |
| TF-IDF | names and formulae masked | Buddhist (0.130) > Christian (0.112) > Sufi (0.109) > Taoist (0.104) > Jewish (0.103) |
| TF-IDF | without the 10 most frequent neighbours | Buddhist (0.122) > Christian (0.110) > Jewish (0.106) > Sufi (0.105) > Taoist (0.101) |
| TF-IDF | parables of at least 100 tokens | Buddhist (0.125) > Christian (0.121) > Jewish (0.109) > Sufi (0.108) > Taoist (0.101) |
| TF-IDF | minus folktales of the same length | Christian (-0.045) > Buddhist (-0.053) > Jewish (-0.058) > Sufi (-0.068) > Taoist (-0.073) |
| TF-IDF | nearest folktale only (k = 1) | Buddhist (0.149) > Christian (0.129) > Jewish (0.127) > Sufi (0.125) > Taoist (0.113) |
| TF-IDF | 10 nearest folktales (k = 10) | Buddhist (0.116) > Christian (0.102) > Jewish (0.098) > Sufi (0.098) > Taoist (0.093) |
| embeddings | as reported | Buddhist (0.664) > Sufi (0.635) > Christian (0.594) > Jewish (0.546) > Taoist (0.543) |
| embeddings | names and formulae masked | Buddhist (0.713) > Sufi (0.670) > Christian (0.621) > Taoist (0.620) > Jewish (0.617) |
| embeddings | without the 10 most frequent neighbours | Buddhist (0.647) > Sufi (0.629) > Christian (0.585) > Jewish (0.541) > Taoist (0.537) |
| embeddings | parables of at least 100 tokens | Buddhist (0.664) > Christian (0.639) > Sufi (0.635) > Jewish (0.552) > Taoist (0.545) |
| embeddings | minus folktales of the same length | Christian (-0.063) > Buddhist (-0.088) > Sufi (-0.092) > Jewish (-0.137) > Taoist (-0.180) |
| embeddings | nearest folktale only (k = 1) | Buddhist (0.689) > Sufi (0.665) > Christian (0.628) > Jewish (0.578) > Taoist (0.560) |
| embeddings | 10 nearest folktales (k = 10) | Buddhist (0.641) > Sufi (0.621) > Christian (0.581) > Taoist (0.534) > Jewish (0.530) |

- Masking replaces 4,024 name-like words and 12 formulae; on average 3.5% of a parable's tokens. Spearman correlation between masked and unmasked folk-closeness: TF-IDF 0.95; embeddings 0.88 (`results/checks_masking.json`), (`results/checks_length.csv`).

### Hand labels

- **Pending.** `labeling/hand_labels_template.csv` holds the top-1 pair of 100 parables (20 per tradition, seed 0). Copy it to `labeling/hand_labels.csv`, fill `coder1` and `coder2`, then run `python -m ouaw.agreement` and `python -m ouaw.run --stage figures`. No label was filled in by code.

## The five closest parable-folktale pairs

TF-IDF (`results/top_pairs.csv`):

- cosine 0.343: Sufi, “The Elephant in a Dark Room (Masnavi, Book III, Story V)” and the folktale “All Faiths Lead to God: Four Blind Men and an Elephant” (ATU 1317, tale-0112).
  - Parable: “Some Hindoos were exhibiting an elephant in a dark room, and many people collected to see it. But as the place was too dark to permit them to see the …”
  - Folktale: “Four blind men went to see an elephant. One who touched its leg said, 'The elephant is like a pillar.' The second who touched the trunk said, 'The elephant is …”
- cosine 0.336: Jewish, “The matron whom we find so often arguing… (Exod. Rabba 3)” and the folktale “God and Moses” (ATU 845, tale-1358).
  - Parable: “The matron whom we find so often arguing with Rabbi José observed one day to that sage, 'My god is surely greater than yours. When your God appeared to Moses …”
  - Folktale: “Said a fellow named Moses, an' he was prayin' to God to take him out de world. An' while he was prayin' to God to take him out de worl', …”
- cosine 0.317: Sufi, “The Lion who Hunted with the Wolf and the Fox (Masnavi, Book I, Story XI)” and the folktale “Keeping Pace” (ATU 275, tale-1183).
  - Parable: “A lion took a wolf and a fox with him on a hunting excursion, and succeeded in catching a wild ox, an ibex, and a hare. He then directed the …”
  - Folktale: “Once upon a time there was a fox and a lion. They were going to have a race. The lion said that he could beat all the fox racin'. The …”
- cosine 0.280: Sufi, “The Lion and the Beasts (Masnavi, Book I, Story V)” and the folktale “The Lion Whose Name Was Pingala” (ATU 92, tale-0727).
  - Parable: “In the book of Kalila and Damna a story is told of a lion who held all the beasts of the neighborhood in subjection, and was in the habit of …”
  - Folktale: “At last a hare's turn came to satisfy the lion's hunger and he declined to carry out the agreement. The other animals remonstrated with him and said: 'You must go, …”
- cosine 0.273: Buddhist, “Vānarinda-Jātaka (Jātaka 57)” and the folktale “The Monkey and the Crocodile” (ATU 91, tale-0775).
  - Parable: “Once on a time when Brahmadatta was reigning in Benares, the Bodhisatta came to life again as a monkey. When full-grown, he was as big as a mare's foal and …”
  - Folktale: “In a forest called Pushpâkara, lived a small monkey whose name was Vanapriya. One day he was walking close to the river bank, when he saw a crocodile basking in …”

Embeddings (`results/top_pairs.csv`):

- cosine 0.870: Buddhist, “Mudu-Pāṇi-Jātaka (Jātaka 262)” and the folktale “The Girl without Hands (Jones)” (ATU 706, tale-0588).
  - Parable: “Once upon a time, while king Brahmadatta reigned in Benares, the Bodhisatta was horn as the son of his Queen Consort. Growing up, he was educated at Takkasilā, and on …”
  - Folktale: “The people of the house had supper prepared for the messenger, and during the meal the woman questioned him whether he thought her or her daughter to be the prettier, …”
- cosine 0.850: Buddhist, “The Lost Son (Lotus Sutra, ch. 4)” and the folktale “The Divided Horse-Blanket” (ATU 980, tale-0867).
  - Parable: “It is a case, O Lord, as if a certain man went away from his father and betook himself to some other place. He lives there in foreign parts for …”
  - Folktale: “In goodly words and speech, it behooves every man, as best he may, to show and relate and tell clearly in the common tongue the adventures that befall in this …”
- cosine 0.844: Buddhist, “Sattubhasta-Jātaka (Jātaka 402)” and the folktale “The Grateful Animals and the Ungrateful Man (Panchatantra)” (ATU 160, tale-0601).
  - Parable: “Once upon a time a king called Janaka was reigning in Benares. At that time the Bodhisatta was born in a brahmin family, and they called his name young Senaka. …”
  - Folktale: “In a certain place there lived a Brahmin whose name was Jadschnjadatta [Given to Sacrifice]. His wife, overcome by poverty, every day would say: 'Oh, you cowardly, heard-hearted Brahmin. Do …”
- cosine 0.844: Buddhist, “Asilakkhaṇa-Jātaka (Jātaka 126)” and the folktale “The Sleeping Beauty in the Wood” (ATU 410, tale-1076).
  - Parable: “Once on a time when Brahmadatta was reigning in Benares, he had in his service a brahmin who professed to tell whether swords were lucky or not, and all came …”
  - Folktale: “There were formerly a king and a queen, who were so sorry that they had no children; so sorry that it cannot be expressed. They went to all the waters …”
- cosine 0.831: Buddhist, “Jambuka-Jātaka (Jātaka 335)” and the folktale “The Blue Jackal” (ATU 244, tale-0948).
  - Parable: “Once upon a time when Brahmadatta was reigning in Benares, the Bodhisatta was born as a young lion, and dwelt in a cave of the Himālayas, and one day after …”
  - Folktale: “In times long past there was a very greedy jackal, which used to roam in the forest, and even in places uninhabited by men. At length he made his way …”

## Figures

- `figures/fig1_map` (map and type-versus-region check), `figures/fig2_closeness` (folk-closeness by tradition with both baselines), `figures/fig3_placement` (tradition by community), `figures/fig4_calibration` (recall@10 and hand-label precision). Each as PDF and PNG.
