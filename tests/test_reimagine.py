"""Fast unit tests of the paper pipeline's core functions (toy inputs; no data, network or model needed)."""
import math

import networkx as nx
import numpy as np
import pytest

from reimagine.checks import calibration, chance_recall, first_hit_rank, poisson_binomial_sf
from reimagine.common import top_k
from reimagine.parables import buddhist, christian, html, jewish, sufi, taoist
from reimagine.parables.build import make_baseline, norm_title
from reimagine.parables.html import Block
from reimagine.parables.narrative import is_saying, is_story
from reimagine.part_a import community_words, degree_null, major_communities, tfidf_lift_words
from reimagine.part_b import (entropy_bits, folk_closeness, jsd_bits, leave_one_out, length_curve, log_odds, nearest,
                         placement_null)
from reimagine.reps import Masker


# ----------------------------------------------------------------- segmentation
def p(text, tag="p"):
    return Block(tag, text, False)


def test_jataka_keeps_only_the_story_of_the_past():
    rule = "_" * 29
    blocks = [p("No. 9. Test-Jātaka", "h1"), p("This story was told by the Master while at Jetavana."), p(rule),
              p("[12] Once on a time when Brahmadatta was reigning in Benares, the Bodhisatta was a hare."),
              p("He lived in a wood."), p(rule), p("His lesson ended, the Master identified the Birth."),
              p("[Note. Compare the Pañcatantra.]")]
    text, note = buddhist.segment_jataka(blocks)
    assert text == "Once on a time when Brahmadatta was reigning in Benares, the Bodhisatta was a hare. He lived in a wood."
    assert note == ""


def test_jataka_rule_in_the_same_block_and_end_by_closing_formula():
    blocks = [p("This story the Master told at Jetavana."),
              p("_" * 29 + " Once upon a time the Bodhisatta was a merchant."), p("He travelled far."),
              p("When the Master had ended this discourse, he identified the Birth: I was the merchant.")]
    text, note = buddhist.segment_jataka(blocks)
    assert text == "Once upon a time the Bodhisatta was a merchant. He travelled far." and note == ""


def test_jataka_without_an_opening_is_kept_whole_with_a_note():
    text, note = buddhist.segment_jataka([p("This story was told about a monk."), p("(Only a summary is given here.)")])
    assert text.startswith("This story was told") and note.startswith("whole text kept")


def test_lotus_parable_stops_at_the_application():
    blocks = [p("Thus spoke the Lord."), p("Let us suppose the following case. A man had a house. It caught fire."),
              p("He called his children out. In the same manner, the Tathâgata saves beings."), p("Later text.")]
    assert buddhist.lotus_parable(blocks, "Let us suppose") == (
        "Let us suppose the following case. A man had a house. It caught fire. He called his children out.")


def test_midrash_items_end_at_the_source_reference():
    items = jewish.midrash_items(["A king had a son,", "whom he loved.--Gen. Rabba 22.", "Charity saves.--Mid. Psalms 3."])
    assert items == [("A king had a son, whom he loved.", "Gen. Rabba 22"), ("Charity saves.", "Mid. Psalms 3")]


def test_masnavi_story_splits_prose_verse_and_notes():
    prose = " ".join(["word"] * 30)
    block = p(f"STORY II.\nThe Oilman and his Parrot.\n{prose}\nA short line of verse,\nAnother short line.\nNOTES:\n1. A note.")
    out = sufi.stories([p("PROLOGUE.\nHearken to the reed."), block, p("Verse that continues the story.")])
    assert len(out) == 1 and out[0]["number"] == "II" and out[0]["title"] == "The Oilman and his Parrot"
    assert out[0]["prose"] == [prose]
    assert out[0]["verse"] == ["A short line of verse,", "Another short line.", "Verse that continues the story."]


def test_zhuangzi_sections_follow_the_numbering():
    blocks = [p("BOOK I.", "h2"), p("1. First section."), p("It continues."), p("2. Second section.")]
    assert taoist.sections(blocks) == [(1, "First section. It continues."), (2, "Second section.")]
    assert taoist.sections([p("An undivided book."), p("Second paragraph.")]) == [(1, "An undivided book. Second paragraph.")]


def test_christian_reference_and_longest_version():
    verses = {("LUK", 15, 8): "Or what woman,", ("LUK", 15, 9): "when she has found it,", ("LUK", 15, 10): "even so."}
    assert christian.passage(verses, "LUK 15:8-10") == "Or what woman, when she has found it, even so."
    assert christian.passage(verses, "LUK 15:9") == "when she has found it,"
    assert christian.pretty("MAT 13:3-9") == "Matthew 13:3-9"


def test_reader_page_blocks_drop_notes_and_join_across_a_page_number():
    page = ('<article class="x" data-slot="reader-content"><h1>Title</h1><p>A fox <a></a><a href="#fn-1" '
            'data-footnote-ref="1:1">1</a> met a crow and</p><p><a>p. 12</a></p><p>asked for cheese.</p>'
            '<div data-ad-vro="0" class="not-prose"><div class="r"></div></div><div>Verse one,<br> verse two.</div>'
            '<section data-slot="reader-footnotes"><li>1:1 a note</li></section></article>')
    blocks = html.blocks(page)
    assert [(b.tag, b.text) for b in blocks] == [("h1", "Title"), ("p", "A fox met a crow and asked for cheese."),
                                                 ("div", "Verse one, verse two.")]
    assert html.blocks(page, lines=True)[2].text == "Verse one,\nverse two."
    assert html.chapter_slugs('<a href="/book/b/one">1</a><a href="/book/b/two#x">2</a><a href="/book/b/one">again</a>', "b") == ["one", "two"]


def test_story_rule():
    story = ("A certain man went to the market and met a merchant. He asked him the price of a lamb, and the merchant "
             "replied that it was dear. The man said he would return, and went home. When he came back the lamb was sold, "
             "and the merchant told him to come earlier. So he went away and found another, which he bought and took home.")
    saying = "Charity is greater than sacrifice, and loving-kindness is greater than charity."
    assert is_story(story, 40) and not is_story(saying, 5)
    assert is_saying(saying) and not is_saying(story)


def test_title_normalisation():
    assert norm_title("The Three Fishes (Masnavi, Book IV)") == norm_title("the three fishes.") == "the three fishes"
    assert norm_title("Vedabbha-Jātaka") == "vedabbha jataka"


# ----------------------------------------------------------------- baseline passages
def test_baseline_passages_do_not_overlap_and_match_lengths():
    units = [dict(tradition="T", source="s", translator="t", year="1", url="u", retrieved_at="r", group="a" if k < 150 else "b",
                  label=f"u{k}", text=" ".join([f"w{k}"] * 10)) for k in range(300)]
    lengths = [40, 60, 80, 100, 120]
    out = make_baseline(units, lengths, 10, seed=0)
    assert len(out) == 10
    used = [w for b in out for w in set(b["text"].split())]
    assert len(used) == len(set(used)), "passages overlap"
    sizes = sorted(len(b["text"].split()) for b in out)
    assert abs(np.median(sizes) - np.median(lengths)) <= 20
    for b in out:           # a passage never mixes the two groups (units 0-149 and 150-299)
        ks = {int(w[1:]) < 150 for w in set(b["text"].split())}
        assert len(ks) == 1
    short = make_baseline(units[:20], [150, 180], 10, seed=0)       # 200 tokens of source: one passage, not ten short ones
    assert len(short) == 1


# ----------------------------------------------------------------- Part B quantities
def test_folk_closeness_on_a_toy_matrix():
    S = np.array([[0.9, 0.1, 0.5, 0.3], [0.2, 0.2, 0.2, 0.8]])
    assert folk_closeness(S, 2) == pytest.approx([0.7, 0.5])
    idx, val = nearest(S, 3)
    assert idx.tolist() == [[0, 2, 3], [3, 0, 1]]           # ties go to the lower index
    assert val[0].tolist() == [0.9, 0.5, 0.3]
    assert top_k(np.array([[0.5, 0.5, 0.5]]), 2).tolist() == [[0, 1]]


def test_leave_one_out_ignores_self_and_excluded():
    S = np.array([[1.0, 0.8, 0.2], [0.8, 1.0, 0.4], [0.2, 0.4, 1.0]])
    assert leave_one_out(S, 1) == pytest.approx([0.8, 0.8, 0.4])
    exclude = np.zeros((3, 3), dtype=bool)
    exclude[0, 1] = exclude[1, 0] = True
    assert leave_one_out(S, 1, exclude) == pytest.approx([0.2, 0.4, 0.4])
    assert S[0, 0] == 1.0, "the input matrix must not be changed"


def test_placement_null_shape_and_conservation():
    groups = np.array([0] * 6 + [1] * 3 + [2] * 1)
    attach = np.arange(10, dtype=float)
    null = placement_null(attach, groups, 3, 200, seed=1)
    assert null.shape == (200, 3)
    assert np.allclose(null.sum(axis=1), attach.sum())                       # every shuffle keeps all links
    assert null.mean(axis=0) / attach.sum() == pytest.approx([0.6, 0.3, 0.1], abs=0.03)   # expectation = group share
    assert (placement_null(attach, groups, 3, 5, seed=1) == placement_null(attach, groups, 3, 5, seed=1)).all()


def test_entropy_divergence_and_log_odds():
    assert entropy_bits(np.array([5, 5, 0]))[0] == pytest.approx(1.0)
    assert entropy_bits(np.array([[4, 0], [1, 1]])).tolist() == pytest.approx([0.0, 1.0])
    assert jsd_bits(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(1.0)
    assert jsd_bits(np.array([2.0, 2.0]), np.array([5.0, 5.0])) == pytest.approx(0.0)
    z = log_odds(np.array([50.0, 5.0, 20.0]), np.array([5.0, 50.0, 20.0]), prior=0.01)
    assert z[0] > 2 and z[1] < -2 and abs(z[2]) < 1e-9


def test_length_curve_recovers_a_trend():
    tokens = np.arange(50, 2050, 10)
    f = length_curve(tokens, np.log(tokens), bins=10)
    assert f(np.array([400.0]))[0] == pytest.approx(np.log(400), abs=0.15)


# ----------------------------------------------------------------- calibration
def test_chance_recall_formula():
    N, k = 1462, 10
    for n in (0, 1, 6, 24):
        expected = 1 - math.comb(N - n, k) / math.comb(N, k)
        assert chance_recall(np.array([n]), N, k)[0] == pytest.approx(expected, abs=1e-12)
    assert chance_recall(np.array([1]), 100, 10)[0] == pytest.approx(0.1)
    assert chance_recall(np.array([95]), 100, 10)[0] == pytest.approx(1.0)      # more right answers than misses


def test_first_hit_rank_and_recall():
    S = np.array([[0.9, 0.8, 0.1, 0.0], [0.1, 0.2, 0.3, 0.4], [0.5, 0.4, 0.3, 0.2]])
    right = np.array([[False, True, False, False], [True, False, False, False], [False, False, False, False]])
    assert first_hit_rank(S, right).tolist() == [2, 4, 5]                    # no right answer -> beyond the last rank
    cal_atu, folk_atu = np.array(["a", "b", "zzz"]), np.array(["x", "a", "y", "b"])
    summary, ranks, chance = calibration(S, cal_atu, folk_atu, k=2, n_boot=200, seed=0)
    assert ranks.tolist() == [2, 1, 5] and summary["recall_at_k"] == pytest.approx(2 / 3)
    assert chance.tolist() == pytest.approx([0.5, 0.5, 0.0])


def test_poisson_binomial_tail():
    assert poisson_binomial_sf(np.array([0.5, 0.5]), 1) == pytest.approx(0.75)
    assert poisson_binomial_sf(np.full(10, 0.1), 0) == pytest.approx(1.0)
    assert poisson_binomial_sf(np.full(10, 0.1), 10) == pytest.approx(1e-10)


# ----------------------------------------------------------------- Part A helpers
def test_degree_null_keeps_degrees_and_is_reproducible():
    G = nx.gnm_random_graph(40, 160, seed=3)
    nx.set_edge_attributes(G, 1.0, "weight")
    q1, pr1 = degree_null(G, shuffles=3, swaps_per_edge=5, seed=7, louvain_seed=1, resolution=1.0, want_pagerank=True, workers=1)
    q2, _ = degree_null(G, shuffles=3, swaps_per_edge=5, seed=7, louvain_seed=1, resolution=1.0, want_pagerank=True, workers=1)
    assert q1.shape == (3,) and pr1.shape == (3, 40) and (q1 == q2).all()
    assert pr1.sum(axis=1) == pytest.approx([1.0, 1.0, 1.0])


def test_community_word_lists():
    import scipy.sparse as sp
    vocab = np.array(["fox", "king", "said"])
    X = sp.csr_matrix(np.array([[5, 0, 3], [4, 0, 2], [0, 6, 3], [0, 5, 2]]))
    labels = np.array([0, 0, 1, 1])
    words = community_words(X, vocab, labels, top=2)
    assert words == {0: ["fox"], 1: ["king"]}               # "said" occurs in both groups: IDF 0
    lift = tfidf_lift_words(X.astype(float), vocab, labels, top=1, exclude={"king"})
    assert lift[0] == ["fox"] and lift[1] == []
    assert major_communities(np.array([0] * 150 + [1] * 49 + [2])).tolist() == [0, 1]


def test_masker_replaces_names_and_formulae():
    texts = ["Once upon a time Jack went to Benares. Jack saw the king.", "The king said to Jack: I am glad."]
    m = Masker(texts, dict(placeholder="X", name_threshold=0.5, formulae=["Once upon a time"]))
    assert "jack" in m.names and "king" not in m.names
    out = m.mask(texts[0])
    assert "Jack" not in out and "Once upon a time" not in out and "Benares" not in out
    assert m.mask("I am glad.") == "I am glad."              # one-letter words are kept


# ----------------------------------------------------------------- downloads are opt-in
def test_fetcher_reads_the_cache_and_never_downloads_unless_switched_on(tmp_path, monkeypatch):
    import gzip

    from reimagine.parables import http

    monkeypatch.setattr(http, "RAW_PARABLES", tmp_path)
    monkeypatch.setattr(http, "LOG", tmp_path / "fetch_log.csv")

    def no_network(*a, **k):
        raise AssertionError("a request was made although downloading is off")
    monkeypatch.setattr(http.requests, "get", no_network)

    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "page.gz").write_bytes(gzip.compress(b"<p>cached</p>"))
    (tmp_path / "fetch_log.csv").write_text(
        "tradition,name,url,final_url,retrieved_at,http_status,bytes,sha256,local_file\n"
        "t,page,https://example.org/a,https://example.org/b,2026-11-11T00:00:00Z,200,13,x,t/page.gz\n", encoding="utf-8")
    f = http.Fetcher("test-agent", delay=0.0)
    assert f.get("t", "page", "https://example.org/a") == "<p>cached</p>"
    assert f.info("t", "page")["final_url"] == "https://example.org/b"
    with pytest.raises(http.CacheMiss):
        f.get("t", "missing", "https://example.org/missing")


def test_masker_with_empty_placeholder_removes_words():
    texts = ["Once upon a time Jack went to Benares. Jack saw the king.", "The king said to Jack: I am glad."]
    m = Masker(texts, dict(placeholder="", name_threshold=0.5, formulae=["Once upon a time"]))
    assert m.mask(texts[0]) == "went to. saw the king."
    assert m.masked_share("Jack saw the king") == pytest.approx(0.25)
