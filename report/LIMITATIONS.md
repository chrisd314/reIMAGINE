# Limitations

The main limitations are stated on the website (the answer on the Overview, and Methods & sources); this file lists all of them with the outputs they refer to, for the paper's discussion.

## What the question can and cannot reach

- **No morals.** Text similarity measures shared wording (TF–IDF) or shared sentence meaning (embeddings). It cannot see a moral, so "are parables folktales with a moral attached?" is the motivation, not a tested claim.
- **No descent.** Nothing in the data has dates or routes of transmission. A parable close to a folktale is not evidence that one borrowed from the other.
- **Translations, not originals.** Every parable, baseline passage and folktale is read in English translation, most of them made between 1881 and 1907 (the Bible text is the modern World English Bible). The same-translation baseline removes the translators' shared voice from the comparison, not the act of translation; archaic pronouns (thou, thee, thy) still appear among the words that carry matches (`results/match_drivers_by_tradition.csv`).
- **Fragile traditions.** Only the Buddhist result holds under every check; Taoist fails with embeddings; Christian, Jewish and Sufi depend on how the text is represented (`results/robustness_headline.csv`, Table 1).
- **No hand validation of single matches.** The method is validated on average by the 36 held-out retellings of known tale type (recall@10 0.69 against chance 0.055), not by people judging parable–folktale pairs; by the authors' decision of 18 November there are no hand labels. A single close pair can share a cast (animals, kings) rather than a plot.

## Sample and sources

- **Not world folklore.** The 1,462 folktales are English texts selected by one editor (D. L. Ashliman), mostly from nineteenth- and early twentieth-century European and American collectors; 72% of the tales with a recorded region are European.
- **Source collection and translator.** A few collections supply many tales (the Grimms, J. Jacobs, T. F. Crane, A. Lang, …). The source collection is known for 1,284 tales, the translator for only 168. Region's agreement with the communities almost disappears when labels are shuffled within collections, so the map's apparent geography is mostly the book a tale was printed in (`results/collection_confound.csv`).
- **Truncated texts and editor's notes.** The original scrape lost the opening paragraphs or a closing verse of some tales (48 start mid-story and are flagged). Some cleaned texts still end with the editor's notes (ai-assist/DECISIONS.md N4).
- **Cleaning is rule-based plus reviewed.** Navigation, citations, classification notes and editorial notes were removed with logged rules and 40 reviewed decisions (`data/mappings/text_review.csv`), reviewed by the coding agent and still to be spot-checked by a person.
- **Parable segmentation.** Where a parable starts and ends was set by rules per source (`reimagine/parables/`), tested on examples but not checked by hand on a sample.
- **sacred-texts.com terms.** Four traditions were collected from a site whose terms ask users not to scrape it (README, ai-assist/DECISIONS.md N1).

## Labels

- **ATU labels are page-level.** The dataset gives a tale the type of the Ashliman page it appears on, so loosely related tales inherit the page's type.
- **Provenance is a collector's attribution, not an origin.** Author-only and collection-only strings (Aesop, the Grimms, the 1001 Nights, …) are left without a place.
- **Category sizes differ.** Tale type has far more categories than region (13), so every agreement score is compared with its own shuffled-label reference; scores of different labels are not interchangeable effect sizes.

## Methods

- **One graph is a modelling choice.** The 10% density threshold is one of several; communities change with it (NMI 0.33–0.62 between constructions), although tale type beats region in every one (`results/network_robustness.csv`).
- **Communities are one partition per seed.** Three Louvain seeds agree at NMI 0.64–0.78 on the TF–IDF map.
- **Shuffles assume exchangeability.** Label and parable/baseline shuffles describe association beyond label frequencies on a fixed graph. They do not remove dependence from shared sources, translators or ancestry, and they support no population-wide claim.
- **Mean pooling** of chunk embeddings discards narrative order and can blur several topics.

## Dates

`date_obtained` in the corpus is the scrape date (2021–2022), not a collection, publication or origin date. No chronology is shown.
