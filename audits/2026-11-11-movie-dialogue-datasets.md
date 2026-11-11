# Datasets for women’s spoken dialogue in film

**Research date:** 2026-11-11  
**Question:** Which primary-source datasets can support testing whether women have
less spoken dialogue time in movies, and whether that changes across 1926–2026?

## Bottom line

No single public option observed here supports a clean 1926–2026 estimate of
*actual seconds spoken by women*. The best directly usable historical measure is
the **Polygraph Film Dialogue Dataset**: it has 2,000 films, explicit
character-to-gender coding, and word totals, but covers 1929–2015 and treats
time only as a speaking-rate estimate. **Cornell Movie-Dialogs** is a useful
larger conversational corpus with gender labels for only part of its characters,
covering 1927–2010; its utterance “timestamp” is supplied as a field but the
documentation does not establish that it is audiovisual elapsed time. **MovieNet**
has the strongest multimodal route to real timing (815 subtitle files and 479
scripts among 1,100 movies), but does not publish speaker-gender labels and its
official paper/site do not state an exact year range in the text. It therefore
requires substantial linking and annotation.

For a defensible 1926–2026 study, use Polygraph/Cornell for a reproducible
script-dialogue trend, report **words (or utterances), not seconds**, and add a
new subtitle/audio annotation sample for actual elapsed speaking time. Treat
2026 as a target endpoint, not as covered data: none of these releases reaches
2026.

## Comparison

| Option | Verified temporal and film coverage | Dialogue / transcript | Gender | Measure of “time” | Access and licensing |
|---|---|---|---|---|---|
| **Polygraph’s Film Dialogue Dataset** | 2,000 films; the repository’s `meta_data7.csv` has release years **1929–2015** (computed from the official CSV; the repository README identifies 2,000 records). Thus it starts three years after 1926 and ends eleven years before 2026. | Screenplay-derived character dialogue totals; the project says each screenplay has at least 90% of lines categorized by gender, with some inference from pronouns. | Explicit male/female mapping for characters with at least 100 words, matched to an IMDb actor/actress page; residual characters can be inferred from pronouns. This is not a non-binary or self-identification scheme. | **Words** are the primary released measure. `lines_data` is a sequence of line counts, and the README converts it to approximate minutes using 140 words/minute and about 10 words/line; it is not measured audio time. | CSVs and code are publicly downloadable in the first-party GitHub repository, but the README does not grant a dataset licence. Underlying screenplays and IMDb-derived metadata have separate rights; the project explicitly says it shared what it could “without getting sued.” |
| **Cornell Movie-Dialogs Corpus / ConvoKit movie corpus** | Official page: 617 movies, 9,035 characters, 304,713 utterances. Parsing the release-year field in the official ConvoKit archive gives **1927–2010** (so it overlaps the requested period but covers neither endpoint). | 304,713 utterances in fictional conversations extracted from raw movie scripts; utterance text and speaker IDs are available. The archive documentation also exposes conversation and movie metadata. | Character-level `gender` is supplied, with “?” for unknown cases. The official corpus page reports gender for **3,774 characters** (of 9,035), so most speakers are not directly labelled; the remainder would need manual/metadata derivation. | Utterance text and a `timestamp` field are documented, but no source here says it is audio start/end time or supplies speaking duration. Word/utterance counts are therefore safer than seconds. | Cornell/ConvoKit provides a direct download and documentation. The cited first-party pages do not state an open-data licence; screenplay-derived text should be treated as access for research rather than automatically redistributable. |
| **MovieNet** | The official paper/site define a corpus of **1,100 movies** and show a release-date/year distribution. The paper/site text does **not** give a numeric min/max year, so an exact coverage range cannot be verified without inspecting the released metadata. It is not evidence of 1926–2026 coverage. | The official project page lists **815 subtitle files** and **479 scripts** for Movie1K, alongside 1,100-movie metadata. Subtitles can contain timing; scripts provide dialogue text but not performed timing. Speaker attribution in subtitles is not advertised as a corpus field. | No speaker-gender label is listed in the project’s data inventory. Gender could potentially be derived by linking named characters/cast identities, but that is an additional annotation and is not equivalent to a supplied label. | Subtitle timestamps can support elapsed subtitle-display time, not necessarily vocal speaking time (overlap, pauses, music, and reading-time conventions remain problems). Audio/video would be needed for actual speech segmentation; the public release is primarily metadata/annotations/subtitles/scripts, not unrestricted movie files. | Official site says annotation/meta/subtitles/scripts are downloadable through OpenDataLab, requiring registration and a User Service Agreement; movies are subject to strict copyright conditions and are not generally released. The paper is the primary dataset description. |

## Evidence and interpretation

### 1. Polygraph / Pudding film-dialogue data

The project’s first-party article says it compiled dialogue by gender for
“roughly 2,000 films,” matched characters to IMDb people, and used words spoken
by male and female characters ([project article](https://pudding.cool/2017/03/film-dialogue/)).
Its methodological caveat is important: the data are screenplays rather than
perfect film transcriptions, and films can cut, add, or change lines and
characters. The article also says minor characters below 100 words may be
omitted from gender classification.

The companion repository is more precise about the released variables:
`character_list5.csv` contains character word totals, `meta_data7.csv` contains
2,000 film IDs/titles/years, and `lines_data` is a line-based encoding
([repository README](https://raw.githubusercontent.com/matthewfdaniels/scripts/graphs/README.md);
[metadata CSV](https://raw.githubusercontent.com/matthewfdaniels/scripts/graphs/meta_data7.csv)).
The README explicitly distinguishes word totals from “lines” and explains that
its minute-by-minute series is an estimate based on 14 lines per minute. This
makes it the strongest option for a large historical *dialogue-share* analysis,
but not for the claim “women spoke fewer seconds.”

### 2. Cornell / ConvoKit

Cornell’s dataset page reports 220,579 conversational exchanges between 10,292
character pairs in 617 movies, 9,035 characters, and 304,713 utterances, with
movie release years and character gender metadata
([Cornell dataset page](https://www.cs.cornell.edu/~cristian/Cornell_Movie-Dialogs_Corpus.html)).
The maintained ConvoKit documentation specifies the speaker fields, including
`gender` with “?” for unlabeled cases, and utterance fields including speaker,
text, and `timestamp`; it also documents the direct download
([ConvoKit documentation](https://convokit.cornell.edu/documentation/movie.html);
[archive endpoint](https://zissou.infosci.cornell.edu/convokit/datasets/movie-corpus/movie-corpus.zip)).

The 1927–2010 range above was checked by parsing the `release_year` values in
that official archive, not inferred from a secondary article. The archive is
script-derived fictional dialogue, so its coverage is useful for comparisons
but does not solve audiovisual timing or missing-gender bias.

### 3. MovieNet

MovieNet’s primary paper describes 1,100 movies and multimodal annotations
([ECCV paper](https://arxiv.org/abs/2007.10937)); the first-party project page
lists the actual downloadable components and counts, including 815 subtitles
and 479 scripts, and explains that movie files are restricted
([MovieNet project page](https://movienet.github.io/)). This is the most
promising option for constructing a timing-aware subset, but the public
inventory does not claim speaker-gender labels or speaker-attributed subtitle
dialogue. Subtitle display intervals are only a proxy for speech duration.

## Recommendation for a 1926–2026 design

1. **Primary trend series:** use the Polygraph 2,000-film file for 1929–2015,
   with film-level female word share as the outcome; publish inclusion rules for
   unknown and under-100-word characters.
2. **Robustness series:** use Cornell for 1927–2010, restricting to speakers
   with supplied gender and reporting the labelled-speaker denominator.
3. **Timing validation:** sample MovieNet subtitle/script pairs where access is
   permitted, link speakers to cast/characters, and annotate speech start/end
   from legally accessible audiovisual material. Report subtitle-display time
   separately from actual speech time.
4. **Endpoint discipline:** do not interpolate 1926 or 2016–2026 from these
   releases. Add a newly licensed contemporary sample if the study must claim
   change through 2026.

These are different estimands: Polygraph measures words, Cornell measures
utterances/text, and MovieNet can at best provide subtitle intervals unless
additional audio annotation is done. A conclusion about “spoken dialogue time”
must therefore either use the timing validation subset or be explicitly
renamed “share of dialogue words/utterances.”
