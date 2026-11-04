# Feasibility audit: folklore, religion, geography, moral lessons and transmission

**Project:** Once Upon a World (DTU 02805 Social Graphs and Interactions) · **Audit date:** 2026-11-04 · **Prepared by:** the coding agent (Claude) for the project group.

This audit evaluates the expanded proposal against the actual repository, data and sources. Every judgement here is the agent's, made from the evidence cited. No person has yet checked the crosswalk decisions, the provisional story readings or the case-study assessments. Supporting files are listed in [README.md](README.md).

---

## 1. Decision

**Recommendation: integrate a narrowed version of the proposal.** The new primary question should compare outcomes and lessons *within tale types* that occur both in religious teaching collections and in other collections. The finished plot-versus-place analysis becomes its supporting backbone. Religion of communities stays exploratory description. Branch-level religion and historical snapshots are dropped. Historical influence appears only as one or two evidence-graded case studies.

> **Recommended primary question.** When the same tale type appears in a religious teaching collection (Buddhist Jātaka, Christian exempla such as the Gesta Romanorum, Sufi or Talmudic retellings) and in other collections in our corpus, do the versions keep the plot but change the outcome, the behaviour they endorse, or the justification they give?

The strongest evidence behind this decision:

1. **The religion-of-community comparison has no usable sample.** After identity checks, time checks and a minimum of 10 motifs, about **21 Berezkin traditions** carry a world-religion code (9 Christian, 9 Muslim, 3 Buddhist, 0 Hindu). Another 37 are coded indigenous. Only **4 pairs** of traditions with different world religions lie within 1,500 km of each other, so religion and geography cannot be separated (§5).
2. **No source distinguishes Christian or Islamic branches** for folklore traditions or story versions. SCCS separates only Buddhist branches, which covers at most 4 matched traditions (§6).
3. **Nothing in the available data dates a narrative.** The corpus has edition years (median earliest cited year 1888) and 2021–2022 scrape dates. The Berezkin matrices are undated aggregates. Historical snapshots would show publishing activity, not change (§8).
4. **Each direction of historical influence has one candidate case, verified in the texts.** The first is the Mesopotamian flood narrative → Genesis 6–9. The second is an apologue in *Barlaam and Ioasaph* → three later Western versions of ATU 1678 in our corpus. Text similarity cannot detect either link: same-translation or same-genre controls score as high as the related pairs. Any transmission claim therefore has to rest on cited scholarship (§8).
5. **The moral-lesson comparison is workable.** The texts exist and can be segmented, and the corpus already contains a matched design: **29 tale types with 36 religious-collection versions and 257 other versions**. In a 30-story pilot, TF-IDF ranked all 6 pre-declared plot parallels first or second, yet the stated lessons of those same-plot pairs diverged. Examples, from the agent's provisional readings: the talkative turtle teaches vanity in one version and restrained speech in the other; the crane teaches distrust of enemies in one and retribution for cheats in the other. No outcome or lesson labels exist yet; they must be hand-coded (§9).

---

## 2. Component verdicts

Verdicts use four levels: *feasible now*, *feasible with specified work*, *exploratory only*, *unsupported with the available evidence*. The same table is in [feasibility_matrix.csv](feasibility_matrix.csv).

| Component | Current evidence | Usable sample | Main gap | Verdict | Smallest viable scope |
| --- | --- | ---: | --- | --- | --- |
| Motif/narrative communities | Story versions: complete pipeline (TF-IDF and MiniLM graphs, Louvain over 3 seeds, 1,000 label shuffles, degree-preserving null). Traditions: Berezkin matrices 926 × 2,138 (~2016) and 958 × 2,564 (2019, CC0) inspected | 1,133 versions (164 types); 866 traditions with ≥ 10 motifs | Tradition matrices lag the catalogue (3,328 motifs / 1,031 traditions in Dec 2025); motif counts per tradition range 1–426 (documentation intensity) | Feasible now (versions, done); feasible with specified work (traditions) | Keep existing story-version communities; tradition level optional |
| Geographical comparison | Distance analysis on 1,084 versions (ρ −0.063 TF-IDF, −0.110 embeddings, beyond location shuffles); centroids for 926 traditions | 1,084 versions; 926 traditions | Location = collector attribution or group-area centroid, never origin; collection intensity, language family and a 71% European share compete as explanations | Feasible now (descriptive) | Existing analysis, with location meaning stated |
| Broad religious-family association | SCCS2002 (all 186 coded), Pulotu (137), DRH (1,687 entries); 190 traditions with any candidate link; 68 rule-validated SCCS identity links | ~21 world-religion + 37 indigenous traditions | Tiny sample; religion almost perfectly regional; undated motifs vs focal-year codes; codes come from a mourning-practice study | Exploratory only | Descriptive table or map of matched traditions with coverage shown |
| Major religious-branch association | SCCS: Buddhist branches only; DRH branch tags rare on culture entries (Catholic 3, Orthodox 6, Protestant 0, Sunni 6, Shi'a 2); Pulotu none | 3–4 traditions | No source links Christian or Islamic branches to folklore units | Unsupported | Drop |
| Earlier folklore/mythology → religious text | Sumerian Flood story (ETCSL, fragmentary) and Genesis 6–9 (WEB); DRH dates Gilgamesh −1900..−130 and Atra-Hasis −1700..−600; Yale lecture on adaptation | 1 case | Genesis dating and contact not verified; the earlier narrative is itself religious; similarity not diagnostic | Exploratory only | One evidence-graded case with primary scholarship |
| Religious narrative → later local folklore | Barlaam apologue found in Gutenberg #749; 3 later ATU 1678 versions in corpus (1350–55, 15th c., c. 1510); DRH: legend disseminated 750–1700 | 1 case | No scholarly source for the specific link inspected; no dated folk versions before/after conversion (Pulotu) | Exploratory only | One candidate case, clearly labelled |
| Moral lessons and parables | Aesop for Children: 144 fables with printed morals; Jātaka: 547 stories, 533 with editor keywords; Gospel parables (WEB); corpus: 29 matched tale types; 30-story pilot | 117-version annotation frame | No outcome/lesson labels; most lessons unstated (16 of the 293 frame versions state one); framing needs hand-coding | Feasible with specified work | Codebook + human coding; within-type comparison with a shuffle baseline |
| Historical snapshots | Edition years (85% of versions), scrape dates; undated Berezkin aggregates; DRH dated entries for religious groups, places and texts, not story versions | 0 suitable dated observations | No composition or attestation dates for versions | Unsupported | Drop (at most a labelled "documentation timeline") |

---

## 3. What the project implements now

**Question as implemented.** "Do communities in TF-IDF and semantic text-similarity networks align more with recorded geography or with ATU tale types?" ([README.md](../../README.md), [ANALYSIS_PLAN.md](../../ANALYSIS_PLAN.md)). The pipeline runs as `python -m analysis all` ([analysis/\_\_main\_\_.py](../../analysis/__main__.py), 12 stages from fetch to export).

| Element | Where | What exists | Status |
| --- | --- | --- | --- |
| Source data | [data/raw/trilogy/aft.csv](../../data/raw/trilogy/aft.csv), `data/raw/source_manifest.json`, [analysis/fetch.py](../../analysis/fetch.py) | 1,518 rows from D. L. Ashliman's *Folktexts* via the trilogy repository, commit d57c2ce. Columns: atu_id, tale_title, provenance, notes, source, text, data_source, date_obtained | Real; licence question open ([LICENSE_NOTES.md](../../LICENSE_NOTES.md)) |
| Unit of observation | [analysis/clean.py](../../analysis/clean.py) `clean_text`; [analysis/cohorts.py](../../analysis/cohorts.py) | **Story version**: one tale text per Ashliman page entry. 11 exact duplicates merged → 1,498 narratives in `data/processed/narratives.parquet` | Real |
| Labels | `analysis/cohorts.py` `atu_chapter`, `load_provenance_map`, `source_key` | ATU type (page-level); place and UN M49 region via [provenance_map.csv](../../data/mappings/provenance_map.csv) (406 strings, agent-drafted); bibliographic source key | Real; human review of the map pending |
| Geography | `analysis/distance.py` `haversine_km` | Natural Earth country label points standing for the collector's recorded attribution | Real |
| Time | — | Only `date_obtained` (2021–2022 scrape) and years inside citations | No chronology |
| Religion | — | No religion field. Religious framing can be recovered only from source metadata | Missing |
| Text representations | [analysis/lexical.py](../../analysis/lexical.py) `fit`; [analysis/semantic.py](../../analysis/semantic.py) `Chunker`, `pool` | TF-IDF (negations kept, min_df 2) and pinned all-MiniLM-L6-v2 with ≤ 200-token chunks, mean-pooled | Real |
| Networks | [analysis/networks.py](../../analysis/networks.py) `select_edges`, `louvain`, `degree_preserving_null`, `strongest_per_node` | 21 graphs at 5/10/15% density. Joint cohort at 10%: 1,133 nodes, 64,128 edges. Text cohort at 10%: 1,498 nodes, 112,125 edges | Real (`outputs/metrics/graphs.json`) |
| Agreement measures | [analysis/metrics.py](../../analysis/metrics.py) `nmi`, `assortativity_and_share`, `permutation_matrix`, `top_k_neighbours` | NMI, attribute assortativity and top-10 lift, each against 1,000 label shuffles | Real (180 rows in `outputs/metrics/agreement.json`) |
| Validation | [analysis/validation.py](../../analysis/validation.py) (aspects include `shared_plot` and `different_outcome`); `web/src/pages/Validation.tsx` | Blind 84-pair sample and annotation tool | Tool real; **no annotations exist** |
| Website | `web/src/pages` (Story, Explore, DataMethods, Validation, Sources); components `NetworkCanvas`, `PairReader`, `TalePanel` | Shows computed payloads stamped with run `ouaw-20261030-ed9feb8a`. Re-checked today: production build served, desktop journey test passed 14/14 steps with no console errors | Real |

**Current results** (run `ouaw-20261030-ed9feb8a`):

- ATU type has the largest NMI excess and neighbour lift in all 45 robustness settings.
- Broad region has the highest assortativity in all 45, so the pre-declared verdict for type vs region is "mixed".
- Similarity falls weakly with distance: ρ −0.063 (TF-IDF) and −0.110 (embeddings).

**Unsupported claims.** None found. Every site mention of origin or transmission is a disclaimer (e.g. `web/src/pages/Explore.tsx:215`, `web/src/pages/story/DistanceChapter.tsx:138`). No placeholders.

**Assumptions that conflict with the proposal:**

- **Place.** Place is the collector's attribution, not the narrator's community or an origin, so it cannot carry "the religion of the area".
- **Morals inside texts.** Morals and "Applications" are stored inside 34 narrative texts, so they are part of what the current TF-IDF and embeddings read. A lesson analysis must split them off.
- **Religious framing.** Framing is recoverable only from source strings, and a regex screen is unreliable. Two of the three "scripture" hits were folk texts that merely mention a Bible: "The Bible and Key Trial" and "The Fable of the Flying Dutchman".
- **Places of religious-collection versions.** These versions mostly lack a place: only 10 of 36 are in the joint cohort. A lesson analysis has to use the text-cohort graphs.

**What can be reused:**

- the whole pipeline;
- the label-shuffle machinery, for any new label;
- the validation tool, which already asks about shared plot and different outcome;
- the pair reader and the network and map canvases;
- URL state.

---

## 4. Data audit

Full provenance (URLs, retrieval times, sizes, SHA-256) is in [source_manifest.csv](source_manifest.csv) and [source_manifest_files.csv](source_manifest_files.csv). "Inspected" means records or content were read and counted. "Partial" means access, terms or structure only. "Lead" means not inspected.

### 4.1 Verified usable material

| Source | What one record is | Verified usable after filtering | Rights | Status |
| --- | --- | --- | --- | --- |
| Existing corpus (aft.csv, cleaned) | story version (translation) | 1,498 texts; 29 tale types with 36 religious-collection + 257 other versions; 34 texts state a lesson | open question (LICENSE_NOTES.md) | inspected |
| Berezkin via macleginn/mythology-queries | tradition × motif presence | 926 traditions × 2,138 motifs; 866 with ≥ 10 motifs; coordinates for all | repository: no licence; catalogue CC BY-NC-SA 4.0 | inspected |
| Berezkin via Michalopoulos & Xue (2021) replication package | tradition × motif; EA group × motif | 958 × 2,564 (README: catalogue as of Oct 2019). Per-tradition documentation metadata: sources, authors, languages, first and mean publication year. 1,265 EA→Berezkin assignments; 1,019 Berezkin→Atlas Narodov Mira matches with notes; MTurk shares for whether antisocial trickster behaviour succeeds, for 281 motifs | CC0 | inspected (8 files read from the 209 MB zip by HTTP range requests, CRC-checked) |
| D-PLACE SCCS | society at a focal year | 186 societies; SCCS2002 "World Religions (1807)" coded for all 186 | CC BY-NC 4.0 | inspected |
| Pulotu | Austronesian culture at a "traditional time focus" | 137 cultures with Christian, Islamic and Hindu/Buddhist influence codes and conversion variables | CC BY 4.0 | inspected |
| DRH / SCCSR v2 (backup 2025-02-25) | religious group, place or text with a year range and region | 1,687 entries; 209 culture entries from eHRAF; hierarchical tradition tags | CC BY 4.0 | inspected |
| *The Aesop for Children* (Gutenberg #19994) | fable + printed epimythium | 144 fables with a separable moral (3 headings without one are front matter) | public domain (US) | inspected |
| Jātaka, ancient-buddhist-texts.net (revision of the Cowell translation) | birth story: frame, story of the past, verses, word commentary, identification | 547 stories; 528 synopses (median 52 words); 533 keyword sets with 372 distinct non-category keywords (223 used once); 8 of 8 pilot pages segmented | **no licence statement found** on index, table, story pages or EPUB metadata | inspected |
| World English Bible (engwebp) | verse | Genesis 6–9; 7 Gospel narrative parables by verse range | public domain | inspected |
| ETCSL t.1.7.4 "The Flood story" | translated composition | 1 text, fragmentary | © ETCSL 2003–2006 | inspected |
| *Barlaam and Ioasaph*, tr. Woodward & Mattingly (Gutenberg #749) | legend with embedded apologues | 1 text (86,014 words) | public domain (US) | inspected |
| Open Yale Courses RLST 145, lecture 4 | lecture transcript | secondary support for case C1 | CC BY-NC-SA 3.0 | inspected |

### 4.2 Missing information, by source

- **Berezkin catalogue site.** The site's version table runs from 3 Jan 2015 (1,952 motifs, 914 traditions) to 22 Dec 2025 (3,328, 1,031). The macleginn matrix is close to the late-2016 release. The Michalopoulos–Xue matrix matches the 10 Apr 2019 release (2,576, 958), though their README says October 2019. The two snapshots disagree on 178 tradition names (73 + 105). They should not be merged to raise coverage. No machine-readable current matrix was found. The catalogue's per-tradition material consists of Russian-language summaries of about 80–85 thousand texts, not the texts themselves.
- **Michalopoulos & Xue.** Their README does not say how EA groups were assigned to Berezkin traditions, so the assignment is a proxy, not a documented identity crosswalk. 168 of the 1,265 EA names did not match D-PLACE names in this audit.
- **SCCS2002.** The codes come from a grief-and-mourning coding project (Rosenblatt, Walsh & Jackson 2011). They describe the *depth* of Islamization or Christianization at a focal year, not a population majority.
- **Pulotu.** The codebook asks coders to note the period of conversion, but the coder's notes are empty for the sampled cultures in the CLDF export. "Dominant world religion" refers to about 2014.
- **Jātaka.** Reuse terms for the revised translation are unstated. The underlying Cowell (1895–1907) translation is public domain; its online host was not verified. Gutenberg holds Rhys Davids' *Buddhist Birth Stories* vol. 1 and children's retellings.
- **Existing corpus.** No narrative dates. Lessons are stated in only 34 texts.

### 4.3 Leads not inspected, or only partly

Seshat (polity-level data via API; Polaris-2026 snapshot announced): not inspected. Sefaria: the API works and licences vary by version (JPS 1917 public domain, Sefaria Community Translation CC0, many CC BY-NC); not needed for the recommended scope. The St Andrews Barlaam project page gives context only; its manuscript platform was not available. Cowell's six-volume Jātaka text: host not verified.

### 4.4 Distinctions the proposal asked for

- **Catalogue entry vs text.** Berezkin rows and the Jātaka table are catalogue entries and synopses. The corpus, Aesop, Jātaka story pages, the WEB and Barlaam are texts (translations).
- **Motif definition vs narrative.** Berezkin's English definitions (median 30 words) are definitions.
- **Complete story vs retelling.** Several texts are retellings, not complete source stories:
  - *The Aesop for Children* is a children's adaptation;
  - the corpus Boccaccio is "retold and shortened" by the editor;
  - Jacobs' "Androcles and the Lion" is, by the editor's note, "a reconstruction from various historical sources".
- **Source date vs origin.** Corpus years are edition or publication years; DRH dates are expert-coded ranges for texts and groups.
- **Religious presence vs majority.** SCCS codes depth of influence. Pulotu codes influence (0/1/2) and adoption at > 5%, > 25% or ≥ 75% at any post-contact time. None of these is a majority at the time folklore was recorded.
- **Annotated vs to create.**
  - *Already annotated:* ATU type, place, Berezkin motifs, SCCS/Pulotu/DRH codes, Jātaka editor keywords, crowd-coded trickster outcomes.
  - *To create:* outcome, lesson and justification labels; framing codes; crosswalk verification.

---

## 5. Can the datasets be joined? (Pilot A)

**Method.** Candidate links between Berezkin traditions and religion-coded records were generated by three separate routes, so each link's evidence stays visible:

- **name:** a normalised name part equals a society's name or a listed alternative;
- **published EA assignment:** Michalopoulos and Xue assigned an EA group to the tradition, and D-PLACE's cross-dataset id links that EA society to an SCCS society;
- **nearest SCCS society within 250 km:** listed for review only.

A stratified sample of 30 links (seed 2805) was then reviewed by hand. All candidates were screened with the same rules, written down before review.

- *Identity:* same people or a named subgroup, with compatible location and language family.
- *Time:* the focal year lies no more than 50 years before the tradition's first source publication, and the tradition is not tied to another period.

Files: [crosswalk/](crosswalk/) and [pilots/a_join/pilot_a_summary.txt](pilots/a_join/pilot_a_summary.txt).

*Correction made during the audit.* The first SCCS table dropped the codes of 10 societies with no language-family entry, such as Burusho and Hadza. After the fix, all 186 societies are coded and the screen and funnel were rerun. The 30 reviewed links had already been drawn (seed 2805); none of them involves those 10 societies. Their keys are frozen in [review_sample_keys.csv](crosswalk/review_sample_keys.csv), so the hand decisions stay attached to the same links.

**Hand review of 30 links** ([crosswalk_reviewed.csv](crosswalk/crosswalk_reviewed.csv)): 14 validated, 8 unresolved, 8 rejected.

- In the decisive stratum (SCCS societies with a world-religion code), 7 of 14 sampled links survived.
- The rule screen agreed with the hand review on 24 of 30. Every link the rule validated (11) was also validated by hand, and the hand review validated 3 more, so the rule is conservative.

Typical failures:

- **Pooled units.** "Oromo, Konso, Sidamo" → Konso; "Murut, Dusun, Tombonuvo, Bajau" → Dusun, where the Bajau are largely Muslim and the others are not.
- **Proxy assignments.** "Arabs: Palestine, Syria, Lebanon" → the Rwala Bedouin; Palaung → Lamet.
- **Wrong period.** "Japan AD 700–1700" → an Okayama village in 1950. Pulotu's Roti code describes 1843, but the first folklore source is 1932.

**Join losses** (coordinate snapshot, rule screen):

| Step | Traditions |
| --- | ---: |
| Berezkin traditions (macleginn, 926 × 2,138) | 926 |
| … with ≥ 10 motifs | 866 |
| … with an interpretable location (area centroid) | 926 |
| … with any candidate link by name or published EA assignment (SCCS, Pulotu, DRH) | 190 |
| … with a rule-validated identity link to an SCCS society | 68 |
| … whose society has an SCCS2002 code | 68 |
| … coded with a world religion | 23 |
| … excluding "superficial" Christianization/Islamization | 14 |
| … with a branch-level label (Buddhist branches only) | 4 |
| … world-religion links passing the time check | 22 |
| **… and ≥ 10 motifs: final world-religion sample** | **21** |
| Comparison group: indigenous-coded, time-compatible, ≥ 10 motifs | 37 |

The rule screen is stricter than the hand review, so a full hand review would probably land somewhere around **21–30** world-religion traditions. That is an estimate from 30 reviewed links, not a measurement.

**Coverage by region and religion** (final 58 rule-screened traditions):

- **Christian (9):** Mexico 2, Northeast Tropical Africa 2, and one each in the Caucasus, Eastern Europe, the Russian Far East, Subarctic America and Western Canada. Six of the nine are "superficial Christianization", typically missionised indigenous peoples.
- **Muslim (9):** West Tropical Africa 2, Western Asia 2, and one each in Northern Africa, Northeast Tropical Africa, Middle Asia, Southeastern Europe and the Indian Subcontinent.
- **Buddhist (3):** China 2, Indo-China 1.
- **Indigenous (37):** mostly the Americas.

**Overlap diagnostic.** Among those 58 traditions, only 10 pairs lie within 500 km. Among pairs where both carry a world religion, only **4 different-religion pairs lie within 1,500 km**, all of them Christian–Muslim. A "geographically comparable traditions of different affiliation" design therefore has almost no units.

**Selection bias in the survivors.** SCCS was built to sample culturally independent, ethnographically described societies (focal years mostly 1850–1965). Survivors are well-documented traditions whose names match ethnographic names. Literate European and Middle Eastern traditions are scarce, and "Christian" mostly means missionised peoples of the Americas and the Pacific.

**Limits on extrapolating from this pilot:**

- 30 reviewed links is a small sample.
- Name matching misses spelling variants such as Khalkha/Khalka, and over-matches generic names such as "Chinese" and "Japan".
- Pulotu (35 candidate traditions) and DRH (75) were screened but not resolved. DRH culture entries carry indigenous-religion tags far more often than world-religion tags.

---

## 6. What "the major religion of that area" can mean here

| Source | Population and unit | Period | Categories | Denominator | What it measures |
| --- | --- | --- | --- | --- | --- |
| SCCS2002 | the society's described community | focal year (−1750 to 1965, median 1915) | indigenous; deep or superficial Islamization; deep or superficial Christianization; Mahayana, Hinayana, Vajrayana Buddhism; Hinduism | none | depth of influence (from a mourning-practice study), not a majority |
| SCCS1997 | same | same | degree of Christian influence (~1–100) | none | coded for 76 societies |
| Pulotu | Austronesian culture | traditional time focus (pre-Christian state; e.g. 1837–1950) and current focus (~2014) | influence 0/1/2 per religion; adoption > 5% / > 25% / ≥ 75% at any time after contact; dominant religion now | coarse share thresholds | "predominant" at some time, not at the time folklore was recorded |
| DRH | expert-defined religious group, place or text | entry year ranges | hierarchical tradition tags, including branches | none | describes religious groups, not populations' majorities |

**Verdicts.**

- **Broad families: exploratory only.** About 21–30 traditions, inseparable from region.
- **Finer branches: unsupported.** No source codes Catholic, Orthodox or Protestant, or Sunni or Shi'a, for folklore units. SCCS's Buddhist branches cover at most 4 matched traditions.
- **Shared scriptures give no branch-specific corpora.** The Gospels belong to every Christian branch, and the World English Bible is a single translation, so identical passages cannot reveal denominational differences.

**What survives.** Only descriptive statements about which matched traditions share motifs. For story versions, the usable variable is the **religious framing of the collection** a version comes from (Buddhist Jātaka, Christian exemplum, Sufi or Talmudic retelling). That is a property of the text's source, not of a population. Code 0 ("indigenous") also lumps 116 societies' unrelated religions together and must not be read as one religion.

---

## 7. Geography

| Dataset | What a location means |
| --- | --- |
| Existing corpus | Natural Earth point of the country in the collector's recorded attribution (provenance map). Not the narrator's community, the setting or an origin. Tales attributed to the same country are 0 km apart |
| Berezkin | Area centroid of a tradition, mostly at whole or half degrees (99%). Some traditions are regional bundles ("Arabs: Palestine, Syria, Lebanon") |
| SCCS / Pulotu | Point for the described community at its focal year or time focus |
| DRH | Region polygon per entry (e.g. "Area of dissemination of Barlaam and Ioasaph") |

None of these is a collection place, story setting, manuscript findspot or proposed origin in any consistent sense. Broad traditions should be treated as regions, and distances reported in bands (< 500, 500–1,500, 1,500–3,000, > 3,000 km), not as exact kilometres.

**Distance computation.** Great-circle distance between points, as already implemented in `analysis/distance.py::haversine_km`. Pairs share members and are not independent, so only shuffle-based descriptive comparisons are appropriate (as in the existing analysis), not per-pair tests.

**Competing explanations:**

- language family (Berezkin `lang1` and the D-PLACE family);
- documentation intensity (Michalopoulos–Xue `nmbr_title`, `motifs_total`);
- shared sources and translators (existing `source_key`; excluding same-source neighbours barely changes the lifts);
- regional imbalance (71% European in the joint cohort).

In the matched religion sample, religion is almost perfectly separated by region (§5), so that sample cannot distinguish religion from geography.

---

## 8. Historical influence in both directions (Pilot C)

**Evidence levels used:**

1. similarity of motifs, plot or language;
2. chronological compatibility and plausible contact;
3. historically documented transmission, translation or adaptation.

Only level 3 supports a directed edge. Details are in [pilots/c_history/case_evidence.csv](pilots/c_history/case_evidence.csv).

**C1. Earlier mythology → religious text: Mesopotamian flood → Genesis 6–9.**

- **Texts.** The ETCSL English translation of the Sumerian Flood story was read. It is fragmentary, with gaps of 30–40 lines between segments A–E. Genesis 6:5–9:17 was read in the WEB. Atra-Hasis and Gilgamesh XI were not retrieved (DRH metadata only).
- **Plot.** Plot similarity is verified in the texts: a divine decision to destroy humankind; a pious king, Zi-ud-sura, forewarned; "the huge boat"; a storm "for seven days and seven nights"; and a sacrifice afterwards.
- **Dates.** DRH gives the Epic of Gilgamesh −1900..−130 and Atra-Hasis −1700..−600. No DRH entry exists for Genesis, and its composition date was not verified here.
- **Scholarly support.** Support for level 3 comes from an introductory lecture (Yale RLST 145, lecture 4): "the Bible is making use of older traditions and motifs and adapting them to their own purposes". The lecture also describes a **changed justification**: Gilgamesh gives no motive, Atra-Hasis gives human noise, and Genesis gives violence and injustice (*ḥamas*), with Noah saved for righteousness. The Sumerian text's reason is lost in a gap.
- **Caveat.** The earlier narrative is itself religious mythology, so this is not a case of secular folklore entering religion.
- **Text similarity is not diagnostic.** Sumerian flood vs Genesis scores TF-IDF 0.114 and embedding 0.511. Genesis vs an unrelated parable in the same translation scores 0.062 and 0.498.
- **Verdict.** Exploratory: one case study, needing primary scholarship.

**C2. Religious narrative → later local folklore: Barlaam and Ioasaph apologue → ATU 1678.**

- **Texts.** Gutenberg #749 (Woodward and Mattingly) contains the apologue of a king's son who had never seen anything. When he asks what women are called, the king's spearman answers "Devils that deceive men". Our corpus holds three later versions:
  - Boccaccio, *Decameron* IV introduction (written 1350–1355; retold and shortened by the editor);
  - Poggio, *Facetiae* no. 150 (Poggio lived 1380–1459; the editor says it combines ATU 1678 and 1686);
  - Geiler von Kaysersberg, c. 1510.

  In both Boccaccio and Geiler the women are called "geese".
- **Dates and contact.** DRH gives the legend's dissemination as 750–1700 and calls it popular "in the literatures of Islam, Judaism, and Christianity … dozens of versions". The St Andrews project describes translations "between the sixth and seventeenth centuries".
- **Documented transmission.** **Not verified.** The corpus notes do not mention Barlaam, and no inspected scholarly source documents this specific link.
- **Text similarity is not diagnostic.** An unrelated moralised Gesta exemplum is *closer* to the Barlaam apologue by embedding (0.578) than any of the three related versions (0.40–0.52).
- **Moral framing (provisional reading).** In Barlaam the tale is told by a character planning to tempt the ascetic prince ("there is nothing like the sight of women to allure"). In the Boccaccio retelling, the father's precautions are "no match for the boy's natural inclinations". Same punchline, opposite valuation.
- **Verdict.** Exploratory: a candidate case only.

**Time snapshots.** None are recommended. The corpus's cited years run from the 1400s (2 versions) through the 1800s (848) and 1900s (370), which measures when editors' sources were published. Berezkin aggregates have per-tradition first and mean publication years, not per-motif dates. Pulotu's conversion records cannot be paired with dated folk versions. Animating change from these data would manufacture history.

---

## 9. Moral lessons and parables (Pilot B)

### 9.1 What "matching moral lessons" should mean

Each version gets four separate codes:

- **Plot:** events. For matched comparisons, use the ATU type, which is an independent editor's grouping and not derived from our text similarity.
- **Outcome:** who benefits, suffers, succeeds or fails, and through whose action.
- **Endorsed or discouraged behaviour:** up to two codes from a fixed codebook, each with a valence (+ or −). "None identifiable" and "unclear" are allowed.
- **Justification:** consequence to self, reciprocity, social order or law, compassion or neighbour-love, divine judgement or salvation, karma/merit/rebirth, prudence or wisdom, or none stated.

Each lesson code also records **where the lesson comes from**:

- stated by the narrator inside the story;
- stated by a character;
- stated in a frame or application;
- an editor's or translator's note;
- not stated (annotator's inference).

From these codes, four kinds of pair:

- **Matching lessons:** same behaviour code with the same valence.
- **Opposing lessons:** same behaviour code with opposite valence.
- **Same topic:** a shared topic with different behaviour codes.
- **Different plots with similar lessons:** a matching lesson with a different tale type.

Shared words are not a matching lesson. In the pilot, the Gospel Rich Fool is the *nearest TF-IDF neighbour* of Aesop's Ants and Grasshopper (shared "store", "grain"), but the two evaluate storing the harvest in opposite ways.

### 9.2 Pilot design (30 real stories)

Selection was fixed before any similarity was computed:

| Collection | Purposive items | Random items (`random.Random(2805)`) |
| --- | --- | --- |
| *Aesop for Children* | 5, chosen for known parallels | 3 (Dog, Cock and Fox; Oak and Reeds; Town Mouse and Country Mouse) |
| Jātaka | 5 (Ja 38, 136, 189, 215, 316) | 3 of the other 542 (Ja 144, 381, 468) |
| Gospel narrative parables | 7, each with a plot and an outcome | — |
| Existing corpus | 4 | 3 of the 34 lesson-stating narratives |

Six known-parallel pairs, six same-topic pairs and eight random cross-collection pairs were declared in advance. Narrative bodies exclude printed morals, applications, frames, verse commentary and editor keywords. Files are in [pilots/b_text_morals/](pilots/b_text_morals/). Full texts stay in the git-ignored `downloads/derived/` because rights differ by source.

**Extraction:**

- *Aesop for Children:* 144 of 147 headings split cleanly (the other three are front matter).
- *Jātaka:* all 8 pages split into frame, story of the past, verses, word commentary and identification. Frames run 66–1,269 words against stories of 143–1,233 words.
- *Gospel parables:* the verse ranges had to be chosen by hand.
- *Existing corpus:* 2 of 7 items needed manual handling. tale-0293 stores a second telling after "Moral:". In tale-1196, Croxall's "Application" is a prose essay longer than the fable.

**Similarity (project settings: TF-IDF fitted with the 1,498 corpus texts; MiniLM, chunked):**

- **Collection style dominates.** Mean cosine within collections exceeds the mean between them: TF-IDF 0.057 vs 0.028; embeddings 0.504 vs 0.401. Of each story's top-3 neighbours, 52% (TF-IDF) and 62% (embeddings) come from the same collection, against about 23% expected by chance.
- **TF-IDF retrieves the declared parallels.** It ranked all 6 known parallels 1st or 2nd. With embeddings, the partner was the top *cross-collection* match for only 2 of 6. For example, three other Jātakas are closer to Ja 189 than its Aesop twin, pulled together by the frame formula ("Brahmadatta … Benares … Bodhisatta").
- **Embedding scores need baselines.** Random cross-collection pairs score 0.29–0.51 (mean 0.39), so unrelated religious narratives (Ja 136 vs the Sower, 0.509) score as high as true parallels.
- **Lessons do not follow plots in these examples.** For the five known parallels where both versions state a lesson (the Bierce satire states none), the lessons have embedding cosines of only 0.20–0.28. That lies inside the 0.03–0.35 range of random pairs.

**Provisional readings (agent's, not validated)**, from [provisional_readings.csv](pilots/b_text_morals/provisional_readings.csv):

| Pair | Similarity | Provisional reading |
| --- | --- | --- |
| Tortoise and Ducks ~ Ja 215 | TF-IDF rank 2 | Same plot; lesson differs: vanity and curiosity vs restrained speech (frame: slander) |
| Ass in the Lion's Skin ~ Ja 189 | TF-IDF rank 1 | Same plot, similar lesson; harsher outcome in the Jātaka (the ass is beaten to death) |
| Goose and Golden Egg ~ Ja 136 | rank 2 | Same plot family, similar lesson (greed); the Jātaka adds monastic discipline and a rebirth identity |
| Crane and Fish (Telugu) ~ Ja 38 | rank 1 | Same plot, different lesson: distrust your natural enemies vs the cheat gets a like return |
| Ants and Grasshopper ~ Bierce | TF-IDF rank 2, embedding rank 14 | Same skeleton, satirical inversion; lesson unclear without context |
| Androcles (Jacobs) ~ Gesta "Remembrance of Benefits" | rank 1–2 | Same plot; "Gratitude is the sign of noble souls" vs an allegory of sin and baptism |
| Ants and Grasshopper ~ Rich Fool | TF-IDF nearest neighbour | Same topic, opposing evaluation of storing grain (prudence vs divine judgement) |
| Ants and Grasshopper ~ Prodigal Son | top cross-collection embedding match | Different plots, opposing treatment of the idler (desert vs grace, the latter inferred from the frame) |
| Unforgiving Servant ~ Androcles | highest lesson-embedding similarity (0.394) | Different plots, related lesson (a benefit received obliges), different justification |
| Ja 316 (the hare's gift) ~ Good Samaritan | embedding 0.485 | Different plots, similar endorsed behaviour (giving); merit vs neighbour-love |

**Misleading sources of similarity seen in the pilot:**

- translation style (the Genesis controls in §8);
- editorial wording (ATU 280A: three translators append three different applications);
- length and frames (Jātaka frames are up to 1,269 words);
- collection imbalance (58 Aesop versions vs 11 Gesta versions in the corpus);
- repeated stories (ATU 275 has 31 versions);
- religious names and formulae (the Jātaka frame formula).

Name and formula masking should be a sensitivity check, not automatic removal.

### 9.3 A small independent review the group should run

- **Sample.** Twenty versions for a codebook pilot: 6 religious-collection versions, 6 Aesop fables with the printed moral hidden, and 8 folk versions. Then the full annotation frame of 117 versions: all 36 religious-collection versions plus up to 3 other versions for each of the 29 types. Fifty of these are coded twice.
- **Procedure.** First pass on the narrative body only, with collection, frame and printed moral hidden. Second pass with the frame visible, to code frame-level justification separately. Code per version as in §9.1, plus confidence (1–3) and a supporting quote of at most 25 words. For about 80 same-type pairs, also judge: same plot, same outcome, same behaviour, opposite valence, same justification, unclear.
- **Report.** Raw agreement and a confusion table for each field. Discuss and adjudicate disagreements, and report them. No machine label is ever counted as a human label.
- **It must establish:**
  1. whether outcomes and lessons can be coded reliably from narrative bodies;
  2. how often annotators recover a printed moral they have not seen;
  3. whether religious versions differ mainly in justification rather than in the behaviour they endorse.

No ratings, agreement figures or accuracies exist yet.

---

## 10. Networks and NLP methods

| Graph | Nodes | Edge rule | Direction and weights | Size (actual or estimate) | Missing data | What it can answer |
| --- | --- | --- | --- | --- | --- | --- |
| G1 text network (exists) | story versions, text cohort | cosine ≥ global threshold for 10% density (5% and 15% as sensitivity); display backbone keeps 5 strongest per node | undirected; cosine weights | 1,498 nodes; 112,125 edges at 10% (56,063 at 5%) | isolates reported (11 at 10%, TF-IDF) | similarity of wording or meaning; not relatedness |
| G2 lesson overlay (new) | the ~117 annotated versions inside G1 | G1's edges among annotated versions | as G1 | ~117 nodes; a few hundred to ~1,500 induced edges (**estimate**) | unannotated nodes excluded from statistics and shown grey | do text neighbours share lessons beyond tale type (within-type label shuffle)? |
| G3 lesson co-assignment (optional) | annotated versions | shared primary behaviour code with the same valence | undirected; weight = shared codes | ~117 nodes; ~450 edges with ~15 categories (**estimate**) | "unclear" versions isolated | lesson communities exist **by construction**; only the share of edges crossing framings and tale types, and its difference from G1's communities, is informative |
| G4 documented adaptations | texts or traditions in the case studies | directed edge only with cited documentary scholarship | directed; evidence-level attribute | ≤ 6 nodes; 0 validated edges now (2 candidates) | — | historical claims, kept apart from similarity |
| G5 tradition–motif network (optional) | Berezkin traditions (958; 2019, CC0) | Jaccard of motif sets; 5% density or k = 10 | undirected; weighted | 958 nodes; ~22,900 edges at 5% (**estimate**) | traditions with < 10 motifs flagged; documentation intensity as a covariate | motif sharing; confounded by documentation |

**Avoiding circularity:**

- Religious or framing labels never build edges.
- Lesson labels build only G3, and G3's communities are not presented as a discovery.
- Plot sameness comes from ATU types, not from the text similarity being tested.
- Motif descriptions aggregated and compared with the same motif matrix is not independent confirmation.

**Text caveats.** Cosine is not a probability of shared meaning or borrowing. Embeddings serve as a retrieval aid whose behaviour is checked against baselines. Pairwise similarities share nodes, so any inference uses label shuffles (within tale type when testing framing), never per-pair significance tests.

---

## 11. Course compatibility

The full mapping is in [evidence/course_method_map.csv](evidence/course_method_map.csv), checked against the 2026 course pages retrieved today.

- **Every analytical method in the recommended design is taught:**
  - TF-IDF and cosine (week 6, §6.1–6.2);
  - sentence embeddings with a stated chunking rule (week 7, §7.1–7.2);
  - Louvain, modularity, the degree-preserving shuffle and seed NMI (week 4, §4.3–4.6);
  - label shuffles (week 2, §7 and exercise 2.8);
  - attribute assortativity (week 3, §7 and exercise 3.9);
  - comparing groupings (week 7, §7.3–7.4);
  - distinctive vocabulary between two collections (week 6, §6.3);
  - hand-labelled samples with reported agreement (week 7, §7.5–7.8; week 8, §2 "Analysis and checks").
- **Flagged as not introduced:**
  - Cohen's kappa (report raw agreement and confusion tables; explain kappa if used);
  - LLM or zero-shot lesson labelling (at most provisional drafts, scored against hand labels);
  - bipartite projections (only optional G5);
  - Spearman correlation and great-circle distance (supporting calculations, as in the existing METHOD_MAP.md).
- **Ordinary software, not methods:** React, Vite, D3, Canvas, Playwright, pandas.
- **Deliverables and timeline.** The course grades a PNAS-format paper (≤ 6 pages), three slides and a half-page reflection. The website is the group's own brief, not a course deliverable. Week 8 sets today, 4 November, for "dataset locked, question drafted", with hand-in on Friday 27 November and presentations on Wednesday 2 December.

---

## 12. The website as an analytical presentation

**Reusable as is:**

- `NetworkCanvas` (network with zoom, colour-by-label, density stops);
- the "Shuffle labels" control with its saved shuffle histogram;
- `PairReader` (shared TF-IDF terms with their contributions; best-matching passages);
- the map;
- the distance chart;
- the Validation tool (already asks about shared plot and different outcome);
- URL state with run stamps.

**Three explorables that would show real results:**

1. **"Same plot, different lesson"** (tale-type viewer).
   - *Question:* within a tale type, do religious and other versions share the plot but differ in outcome, lesson or justification?
   - *Data:* annotations, texts, framing codes, pair-reader evidence.
   - *Interaction:* pick a type; versions are laid out by framing; open two in the pair reader. Chips show outcome, behaviour and justification, each tagged *stated*, *frame* or *inferred*, with an agreement badge.
   - *Uncertainty:* disagreements, "unclear" and the number of versions per type are visible.
   - *Misleading if* inferred lessons look like quotations, framing is read as the storytellers' religion, or one type is generalised.
2. **"Do text neighbours share lessons?"**
   - *Question:* does text similarity carry lesson information beyond tale type?
   - *Data:* G1 with the annotation overlay (G2).
   - *Interaction:* colour annotated nodes by behaviour code; "shuffle lessons within tale type" drops one draw onto the saved shuffle histogram.
   - *Uncertainty:* unannotated nodes grey; counts shown.
   - *Misleading if* colours imply that every node is annotated, or communities are read as "moral schools".
3. **"Evidence ladder"** for the two case studies.
   - *Question:* what links an earlier narrative to a later religious text, and the reverse?
   - *Data:* the [case_evidence.csv](pilots/c_history/case_evidence.csv) table, short public-domain passages side by side, citations.
   - *Interaction:* step from similarity to chronology and contact to documented adaptation. Steps not reached are greyed and labelled "not established".
   - *Misleading if* arrows or maps imply routes, or edition dates are shown as story ages.

**Not to build:**

- migration routes;
- animated "spread";
- historical snapshots;
- maps coloured by present-day majority religion.

**Reference site.** "A Polarized America" is organised as an Overview (background, idea) plus separate Network Analysis, Text Analysis, Notebook and Dataset pages. Only its overview page was readable without a browser. Our site already has a narrative page plus Explore and Data & Methods. The useful lesson is to organise the site around the single question and put each check next to its claim, as week 8 asks for figures.

---

## 13. Recommendation and plan

### 13.1 Primary question, hypotheses and the quantities that answer them

**Question.** As in §1. The unit is the story version. The frame is the corpus's 29 tale types that have at least one religious-collection version (36 versions: 18 Jātaka, 11 Gesta Romanorum, 2 Jacques de Vitry, 4 Rumi/*Masnavi*, 1 Talmud via Clouston) and other versions (257).

**Hypotheses, written down before any annotation is analysed:**

- **H1 (plot persists across framings).** Same-type pairs that cross the framing boundary are more similar in TF-IDF than different-type pairs, relative to shuffled type labels. This is expected, given the existing type lift of 31×.
- **H2 (lessons diverge with framing).** Among same-type pairs, the share whose primary endorsed behaviour (with valence) differs is higher across framings than within framings.
- **H3 (justification shifts).** Religious-collection versions more often carry a doctrinal or supernatural justification (divine judgement, salvation allegory, karma or merit) than other versions of the same types.
- **H4 (text ≠ lesson).** A version's top-10 text neighbours share its lesson only slightly more often than a type-matched baseline.

**Exact quantities:**

- **Q1.** Lesson agreement rate for same-type pairs, across framings vs within framings. The difference Δ is compared with 1,000 shuffles of framing labels *within tale type*, giving p = (1 + k)/(1 + N).
- **Q2.** Share of versions per framing with a doctrinal or supernatural justification, compared with within-type shuffles.
- **Q3.** Outcome agreement rate within type, across vs within framings.
- **Q4.** Lesson-code assortativity on the annotated subgraph of G1 vs lesson shuffles within type.
- **Q5.** Annotator agreement for outcome, behaviour, valence and justification (raw agreement and confusion tables).
- **Q6.** The existing type-vs-place NMI excess, assortativity and lift, already computed.

Types, not pairs, are the units that vary independently, and all claims are descriptive for this corpus.

### 13.2 The smallest scientifically coherent scope

Keep the existing corpus, pipeline and site. Add:

1. hand-checked framing codes for the 36 religious-collection versions;
2. the 117-version annotation frame with stated lessons, applications and frames separated from narrative bodies;
3. the codebook and its 20-version pilot;
4. human coding (50 versions coded twice);
5. the within-type comparisons Q1–Q5 on the text-cohort network;
6. one evidence-graded case study (C2 is already in the corpus; C1 needs Genesis and Atra-Hasis citations).

No new external text is needed for this scope. The external collections are extensions (§13.4).

### 13.3 Supporting analyses

1. **Plot baseline:** the existing text-network result, type over place.
2. **Lesson overlay:** G2, with within-type shuffles.
3. **Case study:** one per direction if citations are found; otherwise only C2, labelled as a candidate.

### 13.4 Optional extensions, ranked by value and effort

| Rank | Extension | Value | Effort |
| --- | --- | --- | --- |
| 1 | Hidden-moral check: annotators infer the lesson of 30 *Aesop for Children* fables without the printed moral, then compare with it | High: a direct test of whether lessons can be inferred | Low (data parsed) |
| 2 | Add Gospel narrative parables (from a defined list) and the 18 corpus Jātakas' full frames, to study "different plots, similar lessons" across religious and secular collections | Medium–high | Medium (verse ranges by hand; rights checks) |
| 3 | Jātaka editor keywords (533 stories) as a seed vocabulary and an external comparison for the codebook | Medium | Low–medium |
| 4 | Tradition-level motif communities from the 2019 CC0 Berezkin matrix, compared with story-version results | Medium | Medium–high |
| 5 | Descriptive religion-family table and map for the 21–30 matched traditions | Low under current evidence | Medium (full crosswalk review) |

### 13.5 Defer or drop

- **Drop branch-level religion.** No data (§6).
- **Drop historical snapshots and animated diffusion.** No dated observations (§8).
- **Drop network-scale transmission inference.** Similarity cannot detect documented links (§8).
- **Never assign modern country majority religions to tales.**
- **Defer a religion-family association test.** Too few units, no overlap with geography (§5).

### 13.6 What the study could and could not conclude

**Could conclude**, for this corpus's tale types, collections, translations and editions:

- how often same-plot versions differ in outcome, endorsed behaviour and justification;
- whether that divergence is larger across religious/secular framing than within it, relative to within-type shuffles;
- which lesson codes recur across Buddhist, Christian, Sufi and secular collections;
- whether text similarity carries lesson information beyond tale type;
- that communities follow tale type more than recorded place (existing result);
- for each case study, which evidence level was reached and how the moral framing changed.

**Could not establish:**

- that a community's religion causes or predicts motif sharing;
- any branch-level difference;
- when, or by which route, a story travelled;
- origin locations;
- that textually similar versions are historically related;
- the moral outlook of whole religions;
- any population-level significance (pairs are dependent, and the corpus is one editor's selection).

### 13.7 Manual work still needed

- Hand-check the framing codes.
- Write and pilot the codebook.
- Annotate and adjudicate.
- Find scholarly citations for the case studies.
- Check passages quoted in the paper.
- Existing open items: human review of [provenance_map.csv](../../data/mappings/provenance_map.csv) and [text_review.csv](../../data/mappings/text_review.csv); human annotation of the existing 84-pair validation sample; the licence decision for displaying aft.csv texts.

### 13.8 Effort estimate

**Assumptions:** 3 group members; agent coding by Claude, with the group reviewing diffs; about 6 minutes to read and code a median-length version.

| Task | Agent coding | Human work |
| --- | --- | --- |
| Framing table, annotation frame, segmentation of lessons and frames | ~1 day | 1–2 h checking framing and segmentation |
| Codebook and 20-version pilot | prepare forms (0.5 day) | ~6 h (2 people + discussion) |
| Annotation tool (extend the Validation page and CSV schema) | ~1 day | — |
| Annotation of 117 versions (50 coded twice), adjudication | — | ~20 h |
| Analysis Q1–Q5, shuffles, figures | ~1.5 days | 2–3 h review |
| Case study citations and reading | — | 4–6 h |
| Existing open reviews (provenance spot-check, text review, 84-pair validation) | — | ~12 h |
| Optional site views (§12) | 1–2 days | 1–2 h review |
| **Total** | **~4–6 agent days** | **~45–55 person-hours (~15–18 h each)** |

### 13.9 Criteria for proceeding

1. **Frame holds.** After the hand check, at least 25 tale types keep ≥ 1 religious-collection version and ≥ 2 other versions with readable narrative text. The regex screen currently gives 27.
2. **Codebook reliability.** On the 20-version pilot, raw agreement reaches ≥ 0.70 for outcome and ≥ 0.60 for primary behaviour with valence. If not, merge categories once and re-pilot. If it still fails, make outcome the primary measure and report lessons qualitatively. If even outcome fails, keep type-vs-place as the primary question and present lessons as a qualitative section.
3. **Case study support.** Each case has at least one primary or scholarly source beyond the introductory lecture. Otherwise it is shown only as candidate similarity.
4. **Rights.**
   - Display texts only from public-domain or permissive sources (WEB, Gutenberg, the Cowell original) or as short quotations.
   - Do not redistribute the Jātaka revision without permission.
   - Resolve the aft.csv licence before any public deployment.
5. **Pre-registration.** Thresholds, hypotheses and shuffle designs are written into ANALYSIS_PLAN.md before annotations are analysed.

Suggested gates: criteria 1 and 2 by Monday 9 November; criterion 3 by the session on Wednesday 11 November; annotations finished by 18 November; draft by 25 November.

### 13.10 Implementation outline (for a later instruction)

1. **Data:** framing codes; annotation frame; lesson/frame segmentation; rights decisions.
2. **Measurement:** codebook; pilot; annotation tool; double coding; agreement report.
3. **Analysis:** Q1–Q5 with within-type shuffles; overlay on the text-cohort network; robustness (masking names and formulae; TF-IDF vs embeddings).
4. **Case studies:** citations; evidence ladders.
5. **Presentation:** paper figures; optional site views (§12).
6. **Extensions:** in the order of §13.4.

---

## 14. Limits of this audit

**Checks not completed:**

- Atra-Hasis and Gilgamesh XI texts were not retrieved, and Genesis' composition date was not verified.
- No scholarly source for the Barlaam → ATU 1678 link was found.
- Seshat was not inspected.
- The Jātaka revision's licence was not found; Cowell's original text host was not verified.
- The DRH answerset (174 MB) was not analysed.
- Jātaka endnotes mention Aesop, Babrius, Phaedrus, Panchatantra, Gesta, Arabian Nights, Grimm or Jacobs 46 times, but a simple parser could not attach them to stories reliably.
- Pulotu and DRH candidate links were screened but not resolved.
- Only the overview page of the reference site was readable.

**Agent judgements without human review:** all crosswalk decisions, provisional readings and case assessments.

**Pilot size.** The pilots are diagnostic samples (30 links, 30 stories, 2 cases), not grounds for general conclusions.

**Repository state.** The project was left unchanged: 3,413 project files had identical SHA-256 hashes before and after the audit. Git status differs only by the new untracked `audits/` folder (see [README.md](README.md)).
