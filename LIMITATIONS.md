# Limitations

Every limitation below is visible on the website (Story, chapter 10; Data & Methods) or in the outputs it names.

## Sample and sources

- **Not world folklore.** The 1,498 narratives are English texts selected by one editor (D. L. Ashliman), mostly nineteenth- and early twentieth-century publications by European and American collectors and translators. 71% of the joint cohort is European, so no global geographical claim is made.
- **Translation and source dependence.** A few translators and collections supply many tales (the Grimms, J. Jacobs, T. F. Crane, A. Lang, J. C. Harris, …). Shared translation style can make tales textually similar and also share a recorded place. Excluding neighbours from the same bibliographic source reduces the geography lift only modestly (see `outputs/metrics/neighbours.json`), but the source key is coarse: 180 tales have no source, and author strings vary.
- **Truncated texts.** The original scrape lost the opening paragraphs, or a closing verse, of some tales. 48 narratives start with a mid-story connective and are flagged; a sensitivity check without them is reported. The full texts were deliberately not re-fetched, to keep the pinned dataset as the single source.
- **Cleaning is rule-based plus reviewed.** Navigation, citations, classification notes and editorial notes were removed with logged rules and 40 reviewed decisions (`data/mappings/text_review.csv`). These were reviewed by the coding agent and **still need a human check**.

## Labels

- **ATU labels are page-level.** The dataset assigns a tale the type of the Ashliman page it appears on, so loosely related tales inherit the page's type. Several near-identical texts carry different types on different pages; five identical texts with conflicting labels are excluded from the ATU cohort.
- **Motifs are not annotated per tale.** The ATU and Thompson motif tables describe canonical types, not individual texts, and are not used as tale annotations.
- **Provenance is a collector's attribution, not an origin.** Author-only and collection-only strings (Aesop, the Grimms, the 1001 Nights, …) are left without a place: 360 usable ATU-labelled tales have no defensible geography. The mapping (`data/mappings/provenance_map.csv`) was drafted and reviewed by the coding agent; **human review is pending** for every row.
- **Coordinates are coarse.** Country label points (Natural Earth) stand for recorded country associations, so tales recorded in the same country are 0 km apart. Communities without a recorded country, and multi-country regions, have no coordinates and are excluded from the distance analysis (49 joint-cohort tales).
- **Category sizes differ.** ATU has 164 categories, place 89 and region 13. NMI excess, assortativity and neighbour lift are each compared with label-shuffle references, but scores for different label systems are not interchangeable effect sizes.

## Methods

- **Global threshold.** One threshold for all tales leaves isolates, especially under embeddings (114 at 10%). An isolate-free check is reported. Mean pooling of chunk embeddings discards narrative order and can blur multiple topics.
- **Label shuffles assume exchangeability.** They describe association beyond label frequencies on a fixed graph. They do not remove dependence from shared sources, translators or ancestry, and support no population-wide claim.
- **Distance analysis.** Pairs share tales and sources, so no independence-based p-values are given. A weak negative Spearman correlation is not evidence of transmission, migration or direction of influence.
- **Communities are one partition per seed.** Lexical partitions are only moderately stable across seeds: seed-pair NMI is 0.48–0.62 at 10% density and 0.44–0.82 across the three densities. Semantic partitions are more stable (0.78–0.94).
- **Validation is pending.** No human annotations exist yet. The site reports no validation accuracy or agreement, and no machine labels are counted as human labels.

## Dates

`date_obtained` is the scrape date (2021–2022), not a collection, publication or origin date. No chronology or diffusion animation is shown.
