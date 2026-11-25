# reIMAGINE

## Research questions

1. Do religious parables resemble folktales more closely than non-story text from their own traditions does?
2. Which parts of the folktale corpus and which tale types do they come closest to?

The project started from a broader question: are parables just folktales with a moral attached? Text similarity cannot measure a moral, so we test the part it can measure.

**Website:** <https://chrisd314.github.io/reIMAGINE/>

## How the questions are answered

1. **A network of folktales.** 1,462 English folktales from *Annotated Folktales*, each with its ATU tale type, the region it was recorded in and the book it came from, are linked by how alike their texts are (TF-IDF cosine, the strongest 10% of pairs). Sentence embeddings are the second method. Louvain finds the communities, three seeds test their stability and degree-preserving shuffles test their modularity. Label shuffles, also within each source book, test whether the communities follow tale type, region or source book. The network is rebuilt twelve ways to show that the result does not depend on how the links are drawn.
2. **A test of the method.** 36 religious retellings of known tale type are kept out of the network. For each one we ask whether a folktale of the same type is among its 10 most similar folktales.
3. **The parables.** 281 parables from five traditions (Buddhist, Taoist, Jewish, Christian and Sufi) are compared with 168 non-story passages from the same traditions, matched in length and taken from the same translation wherever possible. A text's folk-closeness is its mean similarity to its 5 nearest folktales. The parable and passage labels are shuffled 1,000 times within each tradition. The nearest folktales also show where the parables land among the communities and which tale types they resemble.
4. **Checks.** The comparison is repeated with embeddings, at equal length, with nouns masked, with names and fixed phrases masked, without the hub folktales and on the other networks. Source books are tested as a confound.

### The nine communities of the main network

| | Name | Most distinctive words | Tales |
| --- | --- | --- | --- |
| C1 | Royal wonder tales | king, prince, princess | 367 |
| C2 | Animal fables | fox, wolf, lion | 317 |
| C3 | Domestic & trickster | money, husband, woman | 265 |
| C4 | Household & youth | girl, door, house | 155 |
| C5 | Devil & supernatural | bridge, devil, shepherd | 121 |
| C6 | Family & moral fate | son, grandfather, father | 116 |
| C7 | Archaic-register tales | parrot, thou, thee | 59 |
| C8 | Insect & nature fables | grasshopper, ant, ants | 27 |
| C9 | Satirical & monkey fables | monkey, barber, monkeys | 23 |

The names are our reading of each community's dominant tale types and words. They are set in `analysis.yaml` and checked against the network every time it is built.

## What we found

- The network is organized by kind of story. Its communities follow tale type (NMI 0.40, against 0.25 when types are shuffled within source books), while region hardly differs from its within-book null (0.091 against 0.086).
- Buddhist (+0.032, p < 0.001) and Taoist (+0.015, p < 0.001) parables are closer to folktales than their baselines are. Jewish parables are weakly closer (+0.011, p = 0.020). Christian and Sufi parables are not (p ≥ 0.07).
- An apparent pull toward royal wonder tales (C1) is shared by the non-story text. The clearest shift moves Christian parables toward domestic and trickster tales (C3, +17 percentage points).
- Every tradition stays below folktale excerpts of equal length (by 0.038 to 0.060), so parables sit at the edge of folklore.
- Only the Buddhist result holds under every check.

The website shows every number next to the check behind it.

## The website

Five pages, all interactive:

- **Overview:** the questions, the three steps, the main result, every check at once, and what can and cannot be answered.
- **Folktales:** the corpus and its tale types, text similarity, the network against random graphs, the communities and what they follow, edges as a modelling choice, and the most central tales.
- **Parables:** the parables and their baseline, the test of the method, closeness to folktales, where the parables land, what the resemblance rests on, and the checks.
- **Explore:** the whole network, zoomable and searchable, coloured by community, tale type, region or book, with any tradition's parables placed on it.
- **Methods:** every method with the course week that teaches it, and the data sources.

Every map zooms and pans. Every tale opens with its ten nearest folktales and the words behind each match, and every text links to its full version at the source. A switch in every section turns the whole site from TF-IDF to embeddings. The label shuffles and the permutation test can be rerun in the browser on the same data as the pipeline.

## Run it

Requirements: [uv](https://docs.astral.sh/uv/) with Python 3.11 (about 2 GB of disk for PyTorch and the sentence encoder), and Node.js 20.19 or newer for the website.

```bash
uv sync --group spacy                                     # the pinned environment from uv.lock, with spaCy for the noun masking
uv run python -m reimagine.run --stage all                # the whole analysis, then the website's data and build
uv run python -m reimagine.run --stage partB checks       # single stages, always run in pipeline order
uv run python -m reimagine.run --stage all --sample 100   # fast development run into results/_sample
uv run pytest                                             # unit tests and checks on the outputs

cd web && npm ci && npm run dev                           # the website at http://localhost:5173/
uv run python tests/browser/site_check.py                 # with npm run preview running: every page and control, desktop and phone
```

If Node is not installed system-wide, a portable Node can sit in `.tools/` (git-ignored), where the `site` stage finds it.

| Stage | Module | What it does |
| --- | --- | --- |
| `data` | `reimagine/corpus.py`, `reimagine/core/` | Checks the pinned corpus, cleans it and builds the folktale table. Splits the 1,462 folktales from the 36 held-out retellings, makes sure no retelling or near-copy is in the network, and adds source collection and translator |
| `parables` | `reimagine/parables/` | Cuts the parables out of their books, and the length-matched baseline passages, into `data/processed/parables.csv` |
| `partA` | `reimagine/part_a.py` | Networks at 5%, 10% and 15% density, Louvain, modularity against degree-preserving shuffles, community words, LDA topics, PageRank and the layout |
| `partB` | `reimagine/part_b.py` | Folk-closeness and the nearest folktales of every parable, passage and retelling |
| `vocab` | `reimagine/vocab.py` | Part-of-speech tags (spaCy), nouns masked, and the words behind every closest match |
| `headline` | `reimagine/headline.py` | Parables against their baseline: permutation within tradition, community profile and voted tale types |
| `length` | `reimagine/length.py` | Length-matched folktale excerpts, the length regression and the length matching of the baseline |
| `network` | `reimagine/network.py` | The twelve edge constructions, shuffles within source books, the masked network, backbones, structure against random graphs, and the community table with the names |
| `checks` | `reimagine/checks.py` | The test of the method on the held-out retellings, the second method and hubness |
| `robustness` | `reimagine/robustness.py` | The main result under every check, with a fixed yes, partly or no rule |
| `site` | `reimagine/site.py`, `reimagine/folktexts.py` | The website's data (`data/site/story.json`, `network.json`, `near.json`), then `npm run build` |

Embeddings, part-of-speech tags and shuffle nulls are cached by content, so a rerun only recomputes what changed. All seeds are fixed in `analysis.yaml` and `config.yaml`. No number on the website is typed by hand.

## What is in the repository

```text
README.md, LICENSE, LICENSE_NOTES.md   this file, the licence, and why we chose it
config.yaml       sources, cleaning, TF-IDF, embedding and network settings (fixed on 29 October 2026)
analysis.yaml     settings of each analysis stage (seeds, shuffles, masking, community names)
reimagine/        the analysis pipeline: run.py, one module per stage, and parables/ (one module per tradition)
  core/           data preparation (fetch, clean, audit) and core functions (TF-IDF, embeddings, networks, metrics)
data/             raw inputs (pinned), reviewed mappings, processed tables, and the website's data in site/
results/          the analysis tables behind the website, and the audit of the data preparation
web/              the website (Vite, React and TypeScript)
tests/            unit tests, checks on the data and the website's data files, and the browser check
ai-assist/        the decision log, and the log of how an AI coding assistant was used
.github/          the workflow that builds and publishes the website
```

**Deployment.** `.github/workflows/deploy-pages.yml` builds the site from the committed `data/site/` files and publishes `web/dist` on every push to `master` that touches `data/site/` or `web/`. It refuses to publish if any opening is longer than the excerpt limit.

## Data sources

| Data | Edition | Where from | Retrieved | Status |
| --- | --- | --- | --- | --- |
| Folktales (1,498 versions, of which 1,462 are in the network and 36 are held out) | Hagedorn & Darányi (2022), *Bearing a Bag-of-Tales: An Open Corpus of Annotated Folktales for Reproducible Research*, Journal of Open Humanities Data 8: 16, [doi:10.5334/johd.78](https://doi.org/10.5334/johd.78), built on D. L. Ashliman's *Folktexts* (University of Pittsburgh) | github.com/j-hagedorn/trilogy at commit `d57c2ce`: `aft.csv` (the corpus) and `atu_df.csv` (tale-type names). The repository's `README.md` and `LICENSE.md` and the Zenodo record are kept as licence records, and Ashliman's two index pages as attribution records and to link every tale to its page | 2026-11-11 | CC BY-NC-SA 4.0, the more restrictive of two statements in the repository ([LICENSE_NOTES.md](LICENSE_NOTES.md)) |
| Christian parables and baseline | World English Bible | ebible.org, `engwebp_vpl.zip` | 2026-11-11 | Public domain, as stated in the archive |
| Buddhist parables | *The Jātaka*, ed. E. B. Cowell, 6 vols (1895–1907), and *Saddharma-Puṇḍarīka*, tr. H. Kern, SBE 21 (1884) | sacred-texts.com | 2026-11-11 | Published before 1908 (see the note below) |
| Buddhist baseline | *The Dhammapada*, tr. F. Max Müller, SBE 10 (1881) | sacred-texts.com | 2026-11-11 | As above |
| Jewish parables and baseline | S. Rapaport, *Tales and Maxims from the Midrash* (1907), and C. Taylor, *Sayings of the Jewish Fathers* (1897) | sacred-texts.com | 2026-11-11 | As above |
| Sufi parables and baseline | *Masnavi i Ma'navi*, tr. and abridged by E. H. Whinfield (1898) | sacred-texts.com | 2026-11-11 | As above |
| Taoist parables and baseline | *The Texts of Taoism*, tr. J. Legge, SBE 39–40 (1891): the Zhuangzi and the Tao Te Ching | sacred-texts.com | 2026-11-11 | As above |

Tale types follow Uther (2004), *The Types of International Folktales* (FF Communications 284–286). Regions are UN M49 sub-regions. The mapping from recorded places to regions (`data/mappings/provenance_map.csv`) was drafted once with Natural Earth country points (public domain) and then reviewed row by row. The Natural Earth files are not needed to run anything. The sentence encoder is `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (Apache-2.0).

Every downloaded file is listed with its URL, version, retrieval time and SHA-256 in `data/raw/source_manifest.json` (folktale corpus) and `data/raw/parables/fetch_log.csv` (parables). The raw parable pages are cached in `data/raw/parables/` and are not committed.

**Note on sacred-texts.com.** The books were published between 1881 and 1907 and are in the public domain in the United States. We did not check whether each translator died more than 70 years ago. The site's terms of use ask users "not to … scrape … the service outside its documented interfaces", while its `robots.txt` allows all paths. The pages were collected on 11 November 2026 at one request per second, before the terms were read. For that reason:

- downloading is **off by default**. The `parables` stage works from the cache, and if the cache is missing it keeps the committed `parables.csv` and says so.
- `--fetch` switches downloading on. Decide first whether to keep this source, ask the site, or use another copy of the same editions.
- nothing from the site's own markup, design or commentary is stored in `parables.csv`.

## Course and authors

reIMAGINE is a project for the course 02805 Social Graphs and Interactions at DTU (Technical University of Denmark), autumn 2026, taught by Sune Lehmann: <https://sunelehmann.com/socialgraphs2026-web/index.html>. Its authors are Christos Diamantis, Dávid Weiner and Evangelos Panagiotopoulos. The website's Methods page maps every method to the course week that teaches it.

Software: Python 3.11 with pandas, NumPy, SciPy, scikit-learn, NetworkX, sentence-transformers, PyTorch, spaCy, ftfy, PyYAML and Playwright. The website uses Node.js 24 with React 19, Vite 8 and TypeScript 5.9. Exact versions are in `uv.lock` and `web/package-lock.json`.

## Licence

Copyright © 2026 Christos Diamantis, Dávid Weiner and Evangelos Panagiotopoulos.

Everything in this repository is released under CC BY-NC-SA 4.0 ([`LICENSE`](LICENSE)). It is the most restrictive of the licences the folktale corpus states, and its ShareAlike term carries over to everything built from the corpus, so we apply it to the code, the result tables and the website alike. [`LICENSE_NOTES.md`](LICENSE_NOTES.md) explains the reasons and lists the terms of the third-party material.
