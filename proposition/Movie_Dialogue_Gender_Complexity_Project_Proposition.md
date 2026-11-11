# Women's representation and dialogue complexity in film

## Project proposition for audit

**Draft date:** 2026-11-11

## 1. Project summary

This project will study how women's representation in movie dialogue changed
over time and whether the linguistic complexity of women's dialogue changed
alongside it. The analysis will compare women's and men's scripted dialogue
across films released from approximately 1929 to 2015, using decade-level
trends.

The project will use **dialogue words**, not actual speaking seconds, as its
primary measure of representation. The available historical datasets contain
screenplay-derived dialogue and do not provide verified audio durations for
the full period. This distinction is essential: the project will not claim to
measure the exact number of seconds women speak.

The primary dataset will be the Polygraph Film Dialogue Dataset, which contains
approximately 2,000 films with film metadata, character-level word totals, and
male/female character classifications. The Cornell Movie-Dialogs/ConvoKit
corpus will provide utterance-level text for the complexity analysis and a
robustness comparison where its gender labels are available.

## 2. Research questions

### Main research question

> **How did women's share of movie dialogue words and the linguistic
> complexity of their dialogue change from the late 1920s to the 2010s,
> compared with men's dialogue?**

### Subquestions

1. **Representation:** Did women's share of movie dialogue words increase or
   decrease over time?
2. **Complexity over time:** Did measurable features of women's dialogue
   complexity change across the period?
3. **Gender comparison:** How did women's dialogue complexity compare with men's
   dialogue in the same films and decades?
4. **Representation-complexity relationship:** Are films in which women have a
   larger share of dialogue also films in which women's dialogue is more
   linguistically complex?

### Exploratory geographic extension

If sufficient country metadata and sample sizes are available, the project may
also examine:

> **Do countries that are geographically close to one another show similar
> levels of women's movie dialogue representation?**

The geographic extension will not initially test whether nearby countries are
more progressive. That claim would require a separately defined,
country-level gender-equality measure and creates a substantially different
comparative research design. It will be included only if country identifiers,
film counts, and comparable language handling pass an explicit feasibility
check.

## 3. Motivation

Film is a widely consumed cultural form through which gender roles and social
relationships are represented. Dialogue provides an observable way to study
this representation. A long-term comparison can show whether women's
visibility in scripted conversations changed and whether changes in quantity
were accompanied by changes in the language assigned to female characters.

The project deliberately separates **how much women speak** from **how they
speak**. A larger share of dialogue does not necessarily mean more complex
characters, and greater linguistic complexity does not necessarily indicate
greater social or narrative importance.

## 4. Data

### Primary dataset: Polygraph Film Dialogue Dataset

The Polygraph dataset is the primary source for the representation analysis.
The documented release contains approximately 2,000 films with metadata for
release year, character-level word totals, and character gender mappings.
Its verified release-year range is approximately **1929-2015**.

The primary outcome will be calculated at film level:

```text
female dialogue share =
female-character dialogue words / all classified-character dialogue words
```

Films with substantial unclassified dialogue will be retained only under a
predefined missingness rule and reported in sensitivity analyses.

### Secondary dataset: Cornell Movie-Dialogs/ConvoKit

The Cornell corpus contains approximately 617 films and 304,713 utterances,
with utterance text, speaker identifiers, film metadata, and character gender
fields. Its documented release-year values span approximately **1927-2010**.
Many characters have unknown gender, so analyses using this source will report
the labelled-speaker denominator and will not silently infer missing labels.

Cornell is especially useful for measuring linguistic features at utterance
level. It will also serve as a robustness comparison for the historical
dialogue-share trend where the data permit.

### Coverage boundary

The current releases do not cover the complete requested period 1926-2026.
The project will therefore describe its observed period accurately as
approximately **1929-2015** for the primary series. The years 1926-1928 and
2016-2026 will not be interpolated or presented as observed evidence. A
contemporary extension would require a newly licensed dataset or a new sample.

The full dataset comparison, access notes, and source links are recorded in
[`audits/2026-11-11-movie-dialogue-datasets.md`](../audits/2026-11-11-movie-dialogue-datasets.md).

## 5. Operational definitions and measures

### 5.1 Dialogue representation

The primary representation measure is the percentage of classified dialogue
words spoken by female characters in each film. The corresponding male share
will be reported alongside it. The analysis will also report:

- total dialogue words;
- number and percentage of classified versus unclassified words;
- number of female and male characters;
- female-to-male word ratio;
- distribution of film-level shares, not only the average.

Because film lengths and dialogue amounts differ, the main analysis will use
film-level shares rather than simply pooling all words across decades.

### 5.2 Linguistic complexity

The project will pre-register a small, interpretable set of text-based
measures. Candidate primary measures are:

- **lexical diversity**, using a length-aware measure such as moving-average
  type-token ratio or a comparable standardized metric;
- **mean utterance length**, measured in words;
- **syntactic complexity**, such as clauses per sentence or dependency-based
  complexity;
- **readability**, reported cautiously because readability formulas are
  sensitive to historical language and genre.

Secondary exploratory measures may include:

- question and negation rates;
- emotional or semantic-category diversity;
- conversational turn length and response patterns;
- abstract versus concrete vocabulary.

Complexity will be calculated separately for women's and men's dialogue. Where
possible, women's and men's values will be compared within the same film to
reduce confounding by film genre and writing style.

The project will not interpret a higher score as proof that a character is
more intelligent, more important, or more socially progressive. It will use
the narrower term **linguistic complexity**.

### 5.3 Geographic similarity (exploratory)

If included, geographic analysis will require a country of production or
origin for each film, a documented distance measure between countries, and
enough films per country and period. The initial outcome will be similarity in
female dialogue share, not a causal claim about geographic influence.

Films with ambiguous, multinational, or missing production countries will be
handled using explicit inclusion categories rather than silent assignment.

## 6. Proposed methodology

### Phase 1: Data audit and inclusion rules

1. Obtain the permitted Polygraph and Cornell files.
2. Record source versions, download dates, hashes, and access conditions.
3. Inspect year coverage, duplicate films, missing metadata, and gender-label
   distributions.
4. Define inclusion rules before calculating the final results.
5. Identify whether the text needed for complexity analysis is available
   directly or must be reconstructed from permitted source files.

### Phase 2: Representation analysis

1. Join film metadata to character-level gender and word totals.
2. Calculate female dialogue share for every eligible film.
3. Group films by decade.
4. Report medians, means, uncertainty intervals, sample sizes, and the share
   of unclassified dialogue for each decade.
5. Estimate the time trend using a regression or generalized additive model,
   with film-level observations and decade/year as the main predictor.
6. Conduct sensitivity analyses for unknown characters, minimum film dialogue
   totals, and genre composition.

### Phase 3: Complexity analysis

1. Tokenize and sentence-segment the utterances using one fixed pipeline.
2. Preserve contractions and document treatment of punctuation, names,
   stage directions, and non-dialogue text.
3. Calculate the pre-registered complexity measures separately by gender.
4. Compare women and men within films where both have sufficient dialogue.
5. Estimate trends over release year while accounting for film-level
   clustering and, where available, genre.
6. Report standardized effect sizes and uncertainty rather than relying only
   on statistical significance.

### Phase 4: Robustness and validation

The project will compare:

- Polygraph and Cornell where their estimands overlap;
- pooled-word versus film-level analyses;
- decade categories versus continuous release year;
- all eligible films versus films with high gender-classification coverage;
- raw complexity scores versus scores standardized within decade or genre;
- analyses including and excluding films with uncertain gender labels.

At least a small manually checked sample will be used to verify gender
assignments and text preprocessing decisions. Agreement and unresolved cases
will be documented.

### Phase 5: Optional geographic extension

The geographic extension will proceed only if the Phase 1 audit confirms
adequate country coverage. It will:

1. map production countries to stable geographic identifiers;
2. calculate country-pair distances using a documented convention;
3. aggregate female dialogue share by country and period;
4. compare geographic distance with similarity in the outcome;
5. report sample-size and language limitations;
6. avoid causal or cultural-progress claims unsupported by the data.

## 7. Hypotheses

The project will treat these as testable expectations, not guaranteed findings:

- **H1:** Women's mean share of movie dialogue words differs across release
  decades.
- **H2:** Women's dialogue share shows an upward trend over the observed
  period.
- **H3:** The linguistic complexity of women's dialogue differs from men's
  dialogue, after accounting for film and period where possible.
- **H4:** Women's dialogue complexity changes across release decades.
- **H5:** The relationship between dialogue share and complexity is not
  necessarily positive; representation and complexity may change independently.

No directional hypothesis will be made for the geographic extension until the
country coverage and external measures have been audited.

## 8. Feasibility assessment

The main project is feasible as a descriptive, comparative study because:

- Polygraph supplies a large film-level historical sample for word-share
  analysis;
- Cornell supplies utterance-level text suitable for linguistic measures;
- release years allow decade-level comparisons;
- the main outcomes can be calculated without claiming unavailable audio
  timing.

The project is not feasible in its current form as a complete 1926-2026 study
of actual speaking seconds. It would also be difficult to make a global
country comparison without additional metadata and language-specific
processing.

### Feasibility gates

The project should proceed to full analysis only if:

1. at least 80% of eligible films have usable release years and dialogue
   totals;
2. the proportion of classified dialogue words is reported and acceptable for
   the chosen inclusion rule;
3. enough films remain in each decade for stable descriptive comparisons;
4. the required utterance text is legally and technically available for the
   complexity analysis;
5. preprocessing checks pass on a manually reviewed sample;
6. gender-label uncertainty is measured rather than hidden.

If the complexity text cannot be used from Polygraph under its access
conditions, the complexity analysis will use Cornell as a separate sample and
will not imply that the two datasets are identical populations.

## 9. Limitations and claim boundaries

- **Words are not seconds.** Script word counts and line-based estimates do not
  measure actual vocal duration, pauses, overlaps, or cuts in the finished
  film.
- **Incomplete time coverage.** The current data do not observe 1926 or
  2016-2026.
- **Screenplays are not films.** Final performances can add, remove, or alter
  dialogue relative to the source scripts.
- **Binary gender coding.** The main sources primarily classify characters as
  male or female, with unknown cases. This does not represent the full range
  of gender identities.
- **Missing labels are not random.** Minor characters and ambiguous names may
  be more likely to lack gender labels.
- **Genre and selection effects.** Changes in genres, countries, studios,
  censorship, and dataset composition may create apparent historical trends.
- **Language and translation.** Complexity measures are not automatically
  comparable across languages or translated scripts.
- **Complexity is construct-dependent.** Readability, vocabulary diversity,
  syntax, and emotional range measure different properties.
- **No causal claim.** The design can describe associations over time; it
  cannot show that social progress caused changes in movie dialogue.
- **Geographic extension limits.** Country similarity requires additional
  metadata, comparable samples, and potentially external gender-equality
  indicators.

## 10. Expected outputs

The completed project will produce:

1. a reproducible data and preprocessing manifest;
2. a film-level dataset of dialogue shares and inclusion decisions;
3. decade-level tables and visualizations;
4. complexity measures with gender- and period-specific comparisons;
5. robustness and missing-data analyses;
6. a limitations and licensing record;
7. an auditable report distinguishing observed results from interpretation.

## 11. Requested audit feedback

The audit should evaluate:

1. whether the main research question is sufficiently focused;
2. whether dialogue-word share is an appropriate and defensible primary
   outcome;
3. whether the selected complexity measures are implementable and
   interpretable;
4. whether the Polygraph/Cornell combination creates unacceptable
   comparability problems;
5. whether the proposed inclusion and missing-label rules are adequate;
6. whether the geographic extension should be removed, postponed, or
   developed as a separate project;
7. whether the proposed claims are appropriately limited by the data;
8. what minimum sample sizes or feasibility thresholds should be required
   before modeling trends.

