"""Write the audit's authored tables: course method map, feasibility matrix, Pilot B readings, Pilot C evidence ladder.

These are the coding agent's judgements, written down with their evidence; none is a human rating.
"""
import sys
from pathlib import Path

import pandas as pd

A = Path(sys.argv[1])
W = "weeks/week{}.html"

course = [
    ("TF-IDF document vectors and cosine similarity", "Text similarity between story versions; candidate parallels", f"{W.format(6)} 6.1 'TF-IDF and cosine, by hand', 6.2 'Document similarity on Marvel'; {W.format(5)} 5.6-5.7 bag of words", "Taught", "Already implemented: analysis/lexical.py::fit, analysis/networks.py::similarity_matrix"),
    ("Sentence-embedding similarity with an explicit chunking rule", "Second text representation", f"{W.format(7)} 7.1 'Static and contextual representations', 7.2 'Build a corpus atlas' (record model, max length, chunking rule)", "Taught", "Already implemented: analysis/semantic.py::Chunker, pool"),
    ("Similarity graph by global threshold; weighted edges; display backbone", "Story-version network", f"{W.format(4)} section 7 'Weights', section 8 'Backbones', 4.10-4.11", "Taught", "analysis/networks.py::select_edges, strongest_per_node"),
    ("Louvain communities and modularity", "Narrative communities", f"{W.format(4)} section 3 'modularity', section 4 'Louvain', 4.3, 4.5", "Taught", "analysis/networks.py::louvain, modularity"),
    ("Degree-preserving shuffle; seed stability by NMI", "Is community structure beyond degrees; is it stable", f"{W.format(4)} 4.6 'Compared to what, and how stable'", "Taught", "analysis/networks.py::double_edge_swaps, degree_preserving_null"),
    ("Label shuffle (permutation) reference", "Baseline for every association: type, place, framing, lesson", f"{W.format(2)} section 7 'Shuffling: the model becomes a test', 2.8 'Compared to what - properly'; {W.format(3)} 3.8-3.9", "Taught", "Shuffle lesson or framing labels WITHIN tale type when testing framing effects"),
    ("Attribute assortativity", "Do linked versions share lesson/framing labels", f"{W.format(3)} section 7 'Mixing patterns', 3.9 'Mixing, compared to what'", "Taught", "analysis/metrics.py::assortativity_and_share"),
    ("NMI between communities and labels", "Do communities carry tale type / place / lesson", f"{W.format(4)} section 4 and 4.6", "Taught", "analysis/metrics.py::nmi, label_agreement"),
    ("Comparing groupings of the same documents", "Narrative communities vs lesson categories vs collections", f"{W.format(7)} 7.3-7.4 'Same documents, different groupings'", "Taught", "Contingency table / colour toggle"),
    ("Distinctive vocabulary of two labelled collections", "How religious vs other versions phrase lessons", f"{W.format(6)} 6.3 'Compare two corpora with Scattertext'", "Taught", "Optional, on stated-lesson text only"),
    ("Sparse vs dense retrieval", "Finding candidate parallels for annotators", f"{W.format(7)} 7.9-7.10", "Taught", "Retrieval only; a retrieved pair is not a parallel until read"),
    ("Hand-labelled sample, error table, reported agreement", "Outcome/lesson/justification codes; validation of every model output", f"{W.format(7)} 7.5-7.6 (held-out labels, error table), 7.8 (hand-label before running a model); {W.format(8)} section 2 'Analysis and checks', 'Validate your choices'", "Taught", "Core of the recommended design"),
    ("Cohen's kappa (chance-corrected agreement)", "Annotator agreement", "not found in the inspected pages", "Not introduced: extension", "Report raw agreement and confusion tables; kappa only with an explanation"),
    ("TF-IDF + logistic regression classifier", "Predicting lesson categories", f"{W.format(7)} 7.5-7.6 (sentiment classifier)", "Taught but not recommended", "Too few labels (~117 versions, ~15 categories)"),
    ("LLM or zero-shot lesson labelling", "Drafting lesson codes", f"'Go nuts with your LLM' boxes are free-form; {W.format(8)} section 2: model output must be checked against hand labels", "Not a taught method: extension", "If used, provisional and scored against human labels; never counted as human labels"),
    ("Bipartite tradition-motif projection; Jaccard similarity of motif profiles", "Optional tradition-level motif network (Berezkin)", f"{W.format(4)} section 6 uses a Jaccard-style overlap for link communities; projections not introduced", "Partial: extension", "Optional only"),
    ("Great-circle distance and Spearman correlation", "Distance vs similarity (existing analysis)", "not introduced; permutation logic from week 2", "Supporting calculation", "As documented in METHOD_MAP.md rows 20-21"),
    ("Explorables (interactive views)", "Presentation", "weekly 'Ship an explorable' (stretch, optional)", "Presentation, not an analytical method", "Course deliverables are the paper, three slides and a reflection (overview page; week 8 section 2)"),
]
pd.DataFrame(course, columns=["method", "used_for", "course_section", "status", "notes"]).to_csv(A / "evidence/course_method_map.csv", index=False)

matrix = [
    ("Motif/narrative communities", "Story versions: complete pipeline (1,498 texts; TF-IDF and MiniLM graphs; Louvain x3 seeds; 1,000 label shuffles; degree-preserving null). Traditions: Berezkin matrices 926 x 2,138 (~2016) and 958 x 2,564 (Apr-Oct 2019, CC0 package) inspected", "1,133 joint-cohort versions (164 types); 866 traditions with >= 10 motifs", "Tradition matrices are 6-9 years behind the catalogue (3,328 motifs / 1,031 traditions in Dec 2025) and dominated by documentation intensity (1-426 motifs per tradition)", "Feasible now (story versions, done); feasible with specified work (tradition level)", "Keep the existing story-version communities; tradition-level communities optional"),
    ("Geographical comparison", "Existing distance analysis on 1,084 versions (rho -0.063 TF-IDF, -0.110 embeddings, beyond whole-location shuffles); Berezkin centroids for 926 traditions", "1,084 versions; 926 traditions", "Location means collector attribution (versions) or area centroid (traditions), never origin; collection intensity, language family and 71% European skew compete as explanations", "Feasible now (descriptive)", "Existing analysis with explicit location meaning; no origin or route claims"),
    ("Broad religious-family association", "SCCS2002 (all 186 coded), Pulotu (137 Austronesian cultures), DRH (1,687 entries). 190 traditions with any candidate link; 68 rule-validated SCCS identity links; hand review validated 7 of 14 world-religion-coded links", "~21 world-religion-coded traditions (9 Christian, 9 Islam, 3 Buddhist, 0 Hindu) + 37 indigenous after the rule screen; about half expected to survive hand review", "Tiny sample; religion almost perfectly regional (4 different-religion pairs within 1,500 km); undated motif aggregates vs focal-year codes; codes measure depth of Islamization/Christianization from a mourning-practice study; two incompatible catalogue snapshots", "Exploratory only", "Descriptive table/map of matched traditions with coverage shown; no association test"),
    ("Major religious-branch association", "SCCS distinguishes only Buddhist branches; DRH has Catholic/Orthodox/Protestant/Sunni/Shi'a tags on religious-group entries, rarely on culture entries (eHRAF-derived: 3/6/0/6/2); Pulotu none", "3-4 traditions (Buddhist branches only)", "No source links Christian or Islamic branches to folklore traditions or story versions; shared scriptures give no branch-specific text corpus", "Unsupported with the available evidence", "Drop"),
    ("Earlier folklore/mythology to religious text", "Flood case: ETCSL Sumerian Flood story (fragmentary, (c) ETCSL) and Genesis 6-9 (WEB, public domain); DRH dates Gilgamesh -1900..-130 and Atra-Hasis -1700..-600; Yale lecture: Genesis adapts older Mesopotamian traditions and adds a moral rationale", "1 case (2 texts read; 2 not retrieved)", "Genesis dating and specific contact not verified here; the earlier narrative is itself religious; text similarity no higher than a same-translation control (embedding 0.511 vs 0.498)", "Exploratory only", "One evidence-graded case study with primary scholarship cited"),
    ("Religious narrative to later local folklore", "Barlaam and Ioasaph apologue (king's son told women are 'Devils that deceive men') found in Gutenberg #749; three later ATU 1678 versions in the corpus (Boccaccio 1350-55, Poggio 15th c., Geiler c. 1510); DRH dates the legend's dissemination 750-1700", "1 case (4 texts)", "No inspected scholarly source documents this specific link; Pulotu conversion data have no dated folklore to compare; similarity cannot detect the link (control exemplum scores higher by embedding)", "Exploratory only", "One evidence-graded candidate case, clearly labelled"),
    ("Moral lessons and parables", "Aesop for Children: 144 fables with separable printed morals (PD); Jataka: 547 stories, 533 with editor keywords (ABT revision, no licence found; Cowell original PD); 7 Gospel parables segmented (WEB, PD); corpus: 34 versions state a lesson; 29 tale types with 36 religious-collection and 257 other versions. Pilot: 30 stories segmented; TF-IDF ranked all 6 pre-declared plot parallels 1st or 2nd", "117-version annotation frame (all 36 religious-collection versions + up to 3 others per type) in 29 types", "No outcome/lesson labels exist; lessons are mostly unstated (16 of the 293 frame versions state one); printed morals are edition-specific; framing must be hand-coded (2 of 3 regex 'scripture' hits were false)", "Feasible with specified work", "Codebook + double coding of ~50 and single coding of the rest; within-type comparison across framings with a shuffle baseline"),
    ("Historical snapshots", "Corpus has edition/publication years (85% of versions; median earliest 1888) and scrape dates; Berezkin is an undated aggregate (M&X give first/mean publication year per tradition); Pulotu time foci; DRH dated religious entries", "0 dated narrative observations suitable", "No composition or attestation dates for versions; snapshots would show documentation activity, not change", "Unsupported with the available evidence", "Drop (at most a labelled 'documentation timeline')"),
]
pd.DataFrame(matrix, columns=["component", "current_evidence", "usable_sample", "main_gap", "verdict", "smallest_viable_scope"]).to_csv(A / "feasibility_matrix.csv", index=False)

P = "provisional (coding agent's reading; not validated)"
readings = [
    ("B1", "KNOWN", "aesop:The Tortoise And The Ducks ~ ja:215", "Gutenberg #19994; ABT Ja 215",
     "tfidf 0.113 (rank 2); embedding 0.670 (rank 2); lesson-embedding 0.282",
     "A: 'Take hold of this stick with your teeth ... But keep quiet' | B: 'we will take you, if only you can keep your mouth shut'",
     "Same plot: carried on a stick, opens mouth, falls.", "Same: the turtle dies.",
     "A printed moral: 'Foolish curiosity and vanity often lead to misfortune.' B verse: 'speak a word that is wholesome and concise ... by talking much too much, the turtle came to disaster'; frame: a monk who slandered.",
     "A: consequence for the vain; B: consequence of excessive speech, applied by the Buddha to slander.",
     "same plot, related but different lesson (vanity vs. speech)", P),
    ("B2", "KNOWN", "aesop:The Ass In The Lion's Skin ~ ja:189", "Gutenberg #19994; ABT Ja 189 (headnote: 'This is Aesop's Ass in the Lion's Skin')",
     "tfidf 0.194 (rank 1); embedding 0.593 (rank 4; three Jatakas closer)", "both: the ass in the lion skin betrays itself by braying",
     "Same core plot.", "Different severity: A mocked by the fox; B beaten to death by villagers.",
     "A: 'A fool may deceive by his dress ... but his words will soon show what he really is.' B verses: '...he spoiled it all by braying'; frame: a monk who could not recite.",
     "Both: pretension exposed by speech.", "same plot, similar lesson, harsher outcome in the religious version", P),
    ("B3", "KNOWN", "aesop:The Goose And The Golden Egg ~ ja:136", "Gutenberg #19994; ABT Ja 136",
     "tfidf 0.058 (rank 2); embedding 0.502 (top cross-collection match)", "A: kills the goose to get all the eggs | B: 'Let us ... pluck him clean'",
     "Same plot family (destroying the source of gold), different agents (a reborn husband in B).", "Same: the gold is lost.",
     "A: 'Those who have plenty want more and so lose all they have.' B verse: 'You should be content with what is received'; frame: a nun's greed leads to a monastic rule.",
     "A: prudential consequence; B: contentment, plus monastic discipline and rebirth identity.",
     "same plot, similar lesson, different justification", P),
    ("B4", "KNOWN", "aft:tale-0293 (Telugu, Pantulu) ~ ja:38", "existing corpus tale-0293 (ATU 231); ABT Ja 38",
     "tfidf 0.185 (rank 1); embedding 0.776 (rank 1)", "A: crane offers to carry the fish to a lake that never dries | B: 'Believing the crane, the fish presented to him a great big fish'",
     "Same plot (crane deceives and eats the fish).", "Different: A ends with the fish eaten; B the crab kills the crane.",
     "A: 'We should never, therefore, believe the words of our natural enemies.' B verse: 'the clever cheat gets a like return'.",
     "A: prudence of the victims; B: retribution for the deceiver.",
     "same plot, different lesson (perspective shifts from victim to cheat)", P + "; note: tale-0293 stores a second telling after the moral"),
    ("B5", "KNOWN", "aesop:The Ants And The Grasshopper ~ aft:tale-0057 (Bierce)", "Gutenberg #19994; existing corpus tale-0057 (ATU 280A)",
     "tfidf 0.038 (rank 2); embedding 0.372 (rank 14)", "A: the ants refuse the starving grasshopper | B: legislators refuse the honest miner",
     "Same skeleton, characters inverted into satire.", "Same refusal.",
     "A: 'There's a time for work and a time for play.' B: no stated lesson; the refusers' words echo the fable's moral ironically.",
     "A: desert/industry; B: implied critique of the rich (unstated).", "same plot, ironic or opposing lesson; unclear without reading the satire in context", P),
    ("B6", "KNOWN", "aft:tale-0027 (Jacobs' Aesop) ~ aft:tale-0029 (Gesta Romanorum)", "existing corpus (ATU 156)",
     "tfidf 0.164 (rank 2); embedding 0.746 (rank 1)", "A: Androcles removes the thorn | B: a knight draws the thorn from a lame lion",
     "Same plot.", "Same: the lion later spares/rescues its helper.",
     "A: 'Gratitude is the sign of noble souls.' B Application: 'the lame lion is the human race; the thorn, original sin, drawn out by baptism...'",
     "A: virtue of gratitude; B: Christian allegory of salvation.", "same plot, reinterpreted lesson and justification", P),
    ("B7", "TOPIC", "aesop:The Ants And The Grasshopper ~ web:Rich Fool (Luke 12:13-21)", "Gutenberg #19994; WEB LUK12",
     "tfidf 0.064 (the Rich Fool is the fable's nearest TF-IDF neighbour; shared 'store', 'grain'); embedding 0.329 (rank 22)",
     "A: grain 'stored up during the summer' | B: 'I don't have room to store my crops'",
     "Different plots, shared topic (storing the harvest).", "Opposite: the storers prosper (A) vs the storer dies that night (B).",
     "A: printed moral praises foresight; B 12:21: 'So is he who lays up treasure for himself, and is not rich toward God.'",
     "A: prudence; B: divine judgement and mortality.", "same topic, opposing evaluation of the same behaviour", P),
    ("B8", "TOPIC", "aesop:The Ants And The Grasshopper ~ web:Prodigal Son (Luke 15)", "Gutenberg #19994; WEB LUK15",
     "embedding 0.481 (the parable is the fable's top cross-collection embedding match); tfidf 0.030", "both: an idler in want asks for help",
     "Different plots, shared situation.", "Opposite: refused (A) vs welcomed with a feast (B).",
     "A: printed moral (industry). B: no application stated inside 15:11-32; frame 15:1-3 (grumbling about sinners).",
     "A: desert; B: grace (inferred from the frame).", "different plots, opposing values; B's lesson is inferred, not stated", P),
    ("B9", "TOPIC", "web:Unforgiving Servant (Matthew 18:21-35) ~ aft:tale-0027 Androcles", "WEB MAT18; existing corpus",
     "lesson-embedding 0.394 (highest of the examined pairs); embedding 0.450", "A: the servant forgiven a debt refuses to forgive | B: a helped lion repays the help",
     "Different plots.", "Different: the ungrateful servant is punished; the helper is saved.",
     "A 18:35: 'So my heavenly Father will also do to you, if you don't each forgive your brother'; B: 'Gratitude is the sign of noble souls.'",
     "A: divine judgement; B: virtue/reciprocity.", "different plots, related lesson (a benefit received obliges), different justification", P),
    ("B10", "TOPIC", "ja:316 (the hare's gift) ~ web:Good Samaritan (Luke 10:25-37)", "ABT Ja 316; WEB LUK10",
     "embedding 0.485; tfidf 0.046", "A: the hare offers its own body to a hungry brahmin | B: a Samaritan cares for a robbed stranger",
     "Different plots, shared act (giving to someone in need).", "A: the hare is honoured by Sakka; B: no reward narrated.",
     "A keywords (editor): Generosity, Self-sacrifice; B 10:37: 'Go and do likewise.'", "A: perfection of giving (merit); B: neighbour-love in answer to a question about eternal life.",
     "different plots, similar endorsed behaviour, different justification", P),
    ("B11", "RANDOM", "ja:136 ~ web:Sower (Mark 4)", "ABT Ja 136; WEB MRK04", "embedding 0.509 (higher than the known Golden Egg parallel, 0.502)",
     "-", "No shared plot.", "-", "-", "-", "embedding baseline problem: unrelated religious narratives score as high as true parallels", P),
]
pd.DataFrame(readings, columns=["id", "pre_declared_set", "pair", "sources", "similarity", "passages", "plot", "outcome", "lessons_as_stated", "justification", "provisional_classification", "status"]).to_csv(A / "pilots/b_text_morals/provisional_readings.csv", index=False)

ladder = [
    ("C1", "Mesopotamian flood narrative -> Genesis 6-9", "texts", "Partly", "ETCSL t.1.7.4 Sumerian Flood story (English translation; segments A-E with ~30-40-line gaps; (c) ETCSL); Genesis 6:5-9:17 (WEB, public domain). Atra-Hasis and Gilgamesh XI not retrieved (DRH metadata only)."),
    ("C1", "", "dates", "Partly", "DRH entry 1375 Epic of Gilgamesh -1900..-130; DRH 1855 Atra-Hasis -1700..-600 (best-preserved edition dated to Ammi-saduqa's reign per DRH). No DRH entry for Genesis; its composition date was not verified in this audit."),
    ("C1", "", "plot similarity", "Yes (read)", "Divine decision to destroy humankind; a pious king (Zi-ud-sura) warned; huge boat; storm 'for seven days and seven nights'; sacrifice afterwards (ETCSL segment D) - parallel elements in Genesis 6-8."),
    ("C1", "", "text similarity", "Not diagnostic", "TF-IDF 0.114 vs 0.062 for Genesis vs an unrelated parable in the same translation; embedding 0.511 vs 0.498."),
    ("C1", "", "contact", "Not established here", "The lecture asserts adaptation of older traditions; a specific contact route or channel was not verified."),
    ("C1", "", "documented adaptation", "Asserted by an introductory lecture", "Yale RLST 145 lecture 4: 'the Bible is making use of older traditions and motifs and adapting them to their own purposes'. Primary scholarship still to be cited. Tradition-level, not text-to-text."),
    ("C1", "", "moral framing", "Yes (per lecture)", "Gilgamesh: no motive; Atra-Hasis: the gods disturbed by human noise; Genesis: violence/injustice ('hamas') and Noah's righteousness. The Sumerian text's reason is lost in a gap."),
    ("C1", "", "verdict", "Exploratory case study", "Earlier narrative is itself religious mythology; supports a directed edge only at the tradition level and only with cited scholarship."),
    ("C2", "Barlaam and Ioasaph apologue -> later Western versions of ATU 1678", "texts", "Yes", "Gutenberg #749 (Woodward & Mattingly translation): a king's son who never saw anything is told women are 'Devils that deceive men'. Corpus: tale-0137 Boccaccio (Decameron IV intro, retold and shortened by Ashliman), tale-0136 Poggio Facetiae no. 150 (combines ATU 1678 and 1686), tale-0135 Geiler von Kaysersberg c. 1510 (freely translated)."),
    ("C2", "", "dates", "Partly", "DRH entry 1406: legend disseminated 750-1700; corpus notes: Decameron written 1350-1355; Poggio lived 1380-1459; Geiler c. 1510. Date of the Greek text and its Latin channel not verified here."),
    ("C2", "", "plot similarity", "Yes (read)", "Isolated boy, first sight of women, told they are devils (Barlaam) or geese (Boccaccio and Geiler), and he wants one."),
    ("C2", "", "text similarity", "Not diagnostic", "TF-IDF 0.050-0.075 vs 0.022 control; embedding 0.40-0.52 vs 0.578 for an unrelated Gesta exemplum."),
    ("C2", "", "contact", "General only", "DRH: popular in Islamic, Jewish and Christian literatures, 'dozens of versions'; St Andrews: translated into many languages between the sixth and seventeenth centuries. No specific channel to Boccaccio verified."),
    ("C2", "", "documented adaptation", "Not verified", "Corpus notes do not mention Barlaam. A folklore reference (e.g. the ATU 1678 literature) or a study of Boccaccio's sources must be found before an edge is drawn."),
    ("C2", "", "moral framing", "Provisional", "In Barlaam the tale is told by a character planning to tempt the ascetic prince ('there is nothing like the sight of women to allure'); in the corpus retelling of Boccaccio the father's precautions are 'no match for the boy's natural inclinations'. Same punchline, opposite valuation (agent's reading)."),
    ("C2", "", "verdict", "Exploratory candidate", "Direction religious legend -> later jest/novella is plausible but undocumented here; the legend's own ancestry (often traced to the life of the Buddha) was not verified in the inspected sources."),
]
pd.DataFrame(ladder, columns=["case", "relationship", "evidence_dimension", "status", "evidence"]).to_csv(A / "pilots/c_history/case_evidence.csv", index=False)
print("tables written")
