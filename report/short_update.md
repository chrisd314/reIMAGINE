# Short update: headline and robustness (2026-11-18)

**Headline figure:** `figures/fig2_headline.pdf` (PNG next to it; caption in `report/captions.md`).

**Question.** Do parables from different religious traditions sit inside folktale communities more than non-story text from the same translations does, and which communities and tale types do they land in? ("Just folktales with a moral?" stays as motivation; the moral is not measured.)

**What the figure shows.**
1. Against non-story text cut from the same translations (same lengths; 1,000 shuffles of the parable/baseline label within each tradition), parables are closer to folktales for Buddhist, Taoist and Jewish, but not for Christian and Sufi (TF-IDF).
2. Where a tradition's community profile differs from its baseline's, the parables lean toward: Taoist, C4 (girl, door, house, +5 points); Christian, C3 (money, husband, woman, +17 points); Sufi, C2 (fox, wolf, lion, +11 points). The parables of Buddhist, Jewish, Sufi and Taoist link to C1 (king, prince, princess) far beyond its share of the map (+24 points on average), but so does their own baseline (+31 points): this lean belongs to the translations, not to the parables.
3. Every tradition's parables stay less folktale-like than folktale excerpts of the same length (−0.060 to −0.038): parables sit at the edge of folklore, not inside it.

**Two main robustness results.**
- *Length.* Baselines are length-matched; at equal length (regression on log words) the verdicts agree with the headline in 3 of 5 traditions (partly).
- *Noun masking.* With nouns and proper nouns masked (spaCy), the known parallels are still found well above chance (recall@10 0.47 against 0.69); parables stay closer than their baseline for Buddhist and Taoist (for these the resemblance is more than a shared cast); become closer for Christian; are no longer closer for Jewish (there the resemblance rests on shared nouns) (Table 1: no, 4 of 10 verdicts kept).

Full numbers: `report/RESULTS.md`; robustness table: `results/table1_robustness.csv`.
