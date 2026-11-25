# Licence notes

Copyright © 2026 Christos Diamantis, Dávid Weiner and Evangelos Panagiotopoulos.

Everything in this repository is released under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** licence (CC BY-NC-SA 4.0). The full text is in [`LICENSE`](LICENSE). That covers the code, the website, the result tables and the data files the website publishes.

These notes explain the choice. They are not legal advice, and nobody was contacted on the project's behalf.

## Why the most restrictive licence

The folktales come from the open corpus *Annotated Folktales* (repository `j-hagedorn/trilogy`, pinned commit `d57c2ce`). The corpus does not state its licence consistently:

| Where | What it says |
| --- | --- |
| `README.md` at the pinned commit | "This repository is licensed under a CC-BY-SA 4.0 open license. Its contents are either in the public domain, or permissions have been granted by the copyright holder for inclusion." |
| `LICENSE.md` at the pinned commit | The full text of CC BY-NC-SA 4.0 |
| Zenodo record 6575263 (release v1.1, 2022-05-24) | Licence id `other-open` |

When two statements disagree, the safe reading is the stricter one, so we follow CC BY-NC-SA 4.0. Its three conditions then shape the whole repository.

1. **NonCommercial.** The corpus may not be used commercially, so nothing built from it may be either.
2. **ShareAlike.** Whatever we adapt from the corpus has to be shared under the same licence. That includes the cleaned data in `data/processed/`, the tables in `results/`, the website's data files in `data/site/` and the site itself, which shows the tales' titles, labels and openings.
3. **Attribution.** The corpus and its sources are credited (see "Data sources" in the README), and the corpus's own `README.md` and `LICENSE.md` are kept unchanged in `data/raw/trilogy/`.

We release the code under the same licence instead of a separate software licence. The code writes the website's data files and ships them with the site, so code and data are hard to separate. One licence for everything means that anyone who reuses any part of the repository follows one set of rules, and those rules are never looser than the corpus allows.

## Third-party material

- **Folktale texts.** They come from D. L. Ashliman's *Folktexts* (University of Pittsburgh), whose index page reads "edited and/or translated by D. L. Ashliman … © 1996-2026". Many are public-domain translations and some are Ashliman's own translations. The corpus README says permissions were granted for inclusion, but it does not document how far any permission extends to third parties.
- **Schools' Collection tales.** Some tales from the National Folklore Collection's Schools' Collection (dúchas.ie) carry their own notice in the `notes` field: CC BY-NC 4.0. Material under CC BY-NC 4.0 may be adapted and shared under CC BY-NC-SA 4.0.
- **Other individual sources** may have their own restrictions. The bibliographic `source` field of every record is kept and shown.
- **Parables and baseline passages.** They come from public-domain translations: the World English Bible (eBible.org, public domain as stated in the archive) and books published between 1881 and 1907, read at sacred-texts.com. Those books are in the public domain in the United States. We did not check whether each translator died more than 70 years ago.
- **Sentence encoder.** `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0. It is downloaded when the pipeline runs. Neither the model nor vectors made with it are included.
- **Fonts.** The website uses Source Serif 4, Inter and IM Fell English under the SIL Open Font License, installed from the `@fontsource` packages.

## What the website shows

- **Excerpts only.** The site reads three files in `data/site/` with titles, ATU labels, regions, source names, the words that carry each match and openings of at most 40 words. No full text, TF-IDF weight vector or embedding vector is published. The deploy workflow and `tests/test_site.py` refuse an opening over the limit.
- **Full texts are read at the source.** Every folktale links to the page of D. L. Ashliman's *Folktexts* it was taken from, and every parable and passage to its page at sacred-texts.com or eBible.org. The links are built from the collection's two index pages with the rules of the corpus's own scraper (`reimagine/folktexts.py`). Each index page was saved once, in `data/raw/metadata/`, and the site was not crawled.
- **The repository contains the full corpus** (`data/raw/trilogy/aft.csv`), as the pipeline needs it. Making the repository public redistributes the corpus under the same CC BY-NC-SA 4.0 terms, with its notices kept.
