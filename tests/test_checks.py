"""Unit tests of the headline, length, vocabulary and network checks (toy inputs; no data, network or model needed)."""
import numpy as np
import pytest

from reimagine.common import permute_within
from reimagine.corpus import check_calibration_exclusion, translator_of
from reimagine.headline import community_counts, headline_tests, profile, top_types, type_votes


# ----------------------------------------------------------------- step 1: calibration is not circular
def test_calibration_exclusion_passes_on_a_clean_pool():
    S = np.array([[0.2, 0.5, 0.1], [0.3, 0.0, 0.89]])
    out = check_calibration_exclusion(["f1", "f2", "f3"], ["c1", "c2"], {"c1": ["x9"]}, S, 0.9)
    assert out["calibration_ids_in_pool"] == 0 and out["pairs_above_threshold"] == 0
    assert out["max_cosine"] == pytest.approx(0.89)
    assert out["closest"][0] == dict(calibration_id="c2", folktale_id="f3", cosine=0.89)


def test_calibration_exclusion_refuses_a_retelling_in_the_pool():
    with pytest.raises(AssertionError, match="calibration versions in the folktale pool"):
        check_calibration_exclusion(["f1", "c2"], ["c1", "c2"])


def test_calibration_exclusion_refuses_a_shingle_near_duplicate():
    with pytest.raises(AssertionError, match="near-duplicates"):
        check_calibration_exclusion(["f1", "f2"], ["c1"], {"c1": ["f2"]})


def test_calibration_exclusion_refuses_a_near_copy_by_cosine():
    S = np.array([[0.2, 0.95]])
    with pytest.raises(AssertionError, match="c1~f2"):
        check_calibration_exclusion(["f1", "f2"], ["c1"], None, S, 0.9)


def test_translator_is_read_from_the_source_reference():
    src = "Peter Christen Asbjørnsen, Fairy Tales from the Far North, translated from the Norwegian by H. L. Brækstad (London: David Nutt, 1897)."
    assert translator_of(src, None) == "H. L. Brækstad"
    assert translator_of("Jacob and Wilhelm Grimm, Kinder- und Hausmärchen (Berlin, 1857).", "Translated by D. L. Ashliman.") == "D. L. Ashliman"
    assert translator_of("Joseph Jacobs, English Fairy Tales (London, 1890).", None) is None


# ----------------------------------------------------------------- step 2: the headline test
def test_permute_within_moves_items_only_inside_their_group():
    groups = np.array(["a", "b", "a", "c", "b", "a", "c", "c"])
    rng = np.random.default_rng(1)
    seen_moves = set()
    for _ in range(50):
        perm = permute_within(groups, rng)
        assert sorted(perm.tolist()) == list(range(len(groups)))           # a permutation
        assert (groups[perm] == groups).all()                              # nothing leaves its group
        seen_moves |= {(i, int(j)) for i, j in enumerate(perm) if i != j}
    assert seen_moves                                                       # it does shuffle
    labels = np.array([1, 0, 0, 1, 1, 1, 0, 0])
    for _ in range(20):
        lab = labels[permute_within(groups, rng)]
        for g in "abc":                                                     # label counts per group are kept
            assert lab[groups == g].sum() == labels[groups == g].sum()


def test_headline_null_shuffles_labels_within_each_tradition_only():
    rng = np.random.default_rng(0)
    # tradition A: parables clearly closer than baseline; tradition B: no difference
    x = np.concatenate([rng.normal(0.3, 0.01, 20), rng.normal(0.1, 0.01, 20), rng.normal(0.2, 0.01, 40)])
    is_par = np.array([True] * 20 + [False] * 20 + [True, False] * 20)
    trad = np.array(["A"] * 40 + ["B"] * 40)
    C = np.zeros((80, 2), dtype=int)
    C[:20, 0] = 10                       # A's parables link to community 0, everything else to community 1
    C[20:, 1] = 10
    out = headline_tests(x, C, is_par, trad, n_perm=200, n_boot=200, seed=3)
    a, b = out["A"], out["B"]
    assert a["diff"] == pytest.approx(0.2, abs=0.02) and a["diff_p_upper"] < 0.01 and a["diff_ci_low"] > 0.15
    assert b["diff_p_upper"] > 0.05
    assert a["excess"][0] == pytest.approx(1.0) and a["excess_p"][0] < 0.01 and a["jsd"] == pytest.approx(1.0)
    assert b["excess"] == pytest.approx([0.0, 0.0]) and b["jsd_p_upper"] == pytest.approx(1.0)
    assert a["inside"] == 1.0 and a["inside_p_upper"] < 0.01
    # the null is within tradition: tradition B's statistics never see tradition A's texts
    assert b["parable_median"] == pytest.approx(np.median(x[40:][is_par[40:]]))


def test_community_counts_and_profile():
    group = np.array([0, 0, 1, -1, 2])
    idx = np.array([[0, 1, 2], [3, 4, 4]])
    C, names = community_counts(idx, group)
    assert names == ["C1", "C2", "C3", "small"]
    assert C.tolist() == [[2, 1, 0, 0], [0, 0, 2, 1]]
    assert profile(C).tolist() == pytest.approx([2 / 6, 1 / 6, 2 / 6, 1 / 6])


def test_type_vote_sums_cosines_and_breaks_ties_by_the_nearer_tale():
    atu = np.array(["510A", "327", None, "327", "510A"], dtype=object)
    idx = np.array([[0, 1, 2, 3], [1, 0, 2, 4], [2, 2, 2, 2]])
    val = np.array([[0.5, 0.3, 0.9, 0.3], [0.4, 0.4, 0.3, 0.0], [0.5, 0.4, 0.3, 0.2]])
    votes = type_votes(idx, val, atu)
    assert votes[0] == "327"            # 0.3 + 0.3 beats 0.5; the untyped tale does not vote
    assert votes[1] == "327"            # tie 0.4 / 0.4: the nearer tale's type wins
    assert votes[2] is None
    tt = top_types(votes, {"327": "The Children and the Ogre"})
    assert tt[0] == dict(rank=1, atu_id="327", atu_name="The Children and the Ogre", texts=2, share=2 / 3)


# ----------------------------------------------------------------- step 3: length-matched excerpts
def test_excerpts_are_contiguous_length_matched_and_from_long_enough_tales():
    from reimagine.length import sample_excerpts
    rng = np.random.default_rng(0)
    folk = [[f"t{i}w{j}" + ("." if j % 7 == 6 else "") for j in range(n)] for i, n in enumerate(rng.integers(20, 400, 60))]
    targets = [30, 100, 250, 395]
    ex = sample_excerpts(targets, folk, n_per=5, tol=0.10, seed=1)
    assert ex == sample_excerpts(targets, folk, n_per=5, tol=0.10, seed=1)            # seeded
    for t, n in enumerate(targets):
        mine = [e for e in ex if e["target"] == t]
        eligible = [i for i, w in enumerate(folk) if len(w) >= np.ceil(0.9 * n)]
        assert len(mine) == min(5, len(eligible))
        assert len({e["source"] for e in mine}) == len(mine)                          # distinct source tales
        for e in mine:
            assert e["source"] in eligible
            assert 0.9 * n <= e["n_tokens"] <= n                                      # within 10% of the target
            words = folk[e["source"]]
            assert e["text"].split() == words[e["start"]:e["start"] + e["n_tokens"]]   # one contiguous stretch
            if e["start"] > 0 and e["n_tokens"] < len(words) - 7:
                assert words[e["start"] - 1].endswith(".")                            # opens at a sentence start


def test_group_model_recovers_slope_and_group_levels():
    from reimagine.length import contrast, group_model
    rng = np.random.default_rng(2)
    lt = rng.uniform(3, 7, 400)
    g = np.array(["a", "b"] * 200)
    y = 0.05 * (lt - 5) + np.where(g == "a", 0.30, 0.20) + rng.normal(0, 0.005, 400)
    names, beta, cov = group_model(y, lt, g, at=5.0)
    assert names == ["log_words", "a", "b"]
    assert beta == pytest.approx([0.05, 0.30, 0.20], abs=0.003)
    est, se, p = contrast(names, beta, cov, "a", "b")
    assert est == pytest.approx(0.10, abs=0.003) and se < 0.002 and p < 1e-6


# ----------------------------------------------------------------- step 4: vocabulary against narrative
TAGGED = [("Once", "ADV", " "), ("a", "DET", " "), ("fox", "NOUN", " "), ("met", "VERB", " "), ("King", "PROPN", " "),
          ("Janaka", "PROPN", " "), ("near", "ADP", " "), ("the", "DET", " "), ("old", "ADJ", " "), ("river", "NOUN", ""),
          (".", "PUNCT", " "), ("The", "DET", " "), ("fox", "NOUN", " "), ("ran", "VERB", " "), ("quickly", "ADV", ""),
          (".", "PUNCT", "")]


def test_noun_masking_replaces_nouns_and_proper_nouns_only():
    from reimagine.vocab import mask_nouns
    out = mask_nouns(TAGGED, "[N]")
    assert out == "Once a [N] met [N] [N] near the old [N]. The [N] ran quickly."
    for kept in ("met", "near", "old", "ran", "quickly", "Once"):          # verbs, adjectives, adverbs, function words
        assert kept in out
    for gone in ("fox", "King", "Janaka", "river"):
        assert gone not in out


def test_masked_placeholder_is_invisible_to_tfidf():
    from reimagine.core.lexical import preprocess
    import re
    cfg = dict(unicode_normalisation="NFKC", lowercase=True, expand_negated_contractions=True)
    tokens = re.findall(r"(?u)\b[^\W\d_]{2,}\b", preprocess("a [N] met [N] near the old [N]", cfg))
    assert "n" not in tokens and tokens == ["met", "near", "the", "old"]


def test_noun_lexicon_and_match_drivers():
    import scipy.sparse as sp
    from reimagine.vocab import drivers, noun_counts, noun_lexicon, noun_share_of_cosine
    lex = noun_lexicon([noun_counts(TAGGED), noun_counts([("fox", "VERB", " ")])])
    assert lex == {"fox", "king", "janaka", "river"}                       # fox: noun 2 of 3 uses
    vocab = np.array(["fox", "king", "ran", "river"])
    q = sp.csr_matrix(np.array([[0.6, 0.0, 0.8, 0.0]]))
    f = sp.csr_matrix(np.array([[0.8, 0.3, 0.5, 0.1]]))
    d = drivers(q, f, vocab, k=5)
    assert [w for w, _ in d] == ["fox", "ran"] and d[0][1] == pytest.approx(0.48)
    assert noun_share_of_cosine(q, f, np.array([w in lex for w in vocab])) == pytest.approx(0.48 / 0.88)


def test_vote_chance_is_low_for_a_large_pool():
    from reimagine.checks import vote_chance
    atu = np.array([f"T{i % 50}" for i in range(500)], dtype=object)
    val = np.tile(np.linspace(0.5, 0.3, 10), (4, 1))
    m, lo, hi = vote_chance(np.array(["T1", "T2", "T3", "T4"]), atu, val, n_draws=200, seed=0)
    assert 0.0 <= lo <= m <= hi <= 1.0 and m < 0.1


# ----------------------------------------------------------------- steps 5 and 6: network robustness and collection
def test_knn_graph_is_symmetrised_and_positive():
    from reimagine.network import knn_edges
    S = np.array([[1.0, 0.9, 0.1, 0.0], [0.9, 1.0, 0.2, 0.0], [0.1, 0.2, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
    e = knn_edges(S, 1)
    pairs = set(zip(e["i"].tolist(), e["j"].tolist()))
    assert pairs == {(0, 1), (1, 2)}                    # 2's nearest is 1 (kept by 2's choice); 3 has only zeros
    assert all(a < b for a, b in pairs) and np.allclose(e["w"], [0.9, 0.2])


def test_clustering_matches_networkx():
    import networkx as nx
    from reimagine.network import clustering
    rng = np.random.default_rng(4)
    G = nx.gnm_random_graph(40, 160, seed=4)
    i, j = map(np.array, zip(*G.edges()))
    w = rng.uniform(0.1, 1.0, len(i))
    for (a, b), x in zip(G.edges(), w):
        G[a][b]["weight"] = x
    ref_u = nx.clustering(G)
    ref_w = nx.clustering(G, weight="weight")
    assert clustering(40, i, j) == pytest.approx([ref_u[k] for k in range(40)])
    assert clustering(40, i, j, w) == pytest.approx([ref_w[k] for k in range(40)])


def test_within_collection_shuffle_keeps_each_collection_fixed():
    from reimagine.network import stratified_perms
    coll = np.array(["grimm"] * 5 + ["lang"] * 4 + ["jacobs"])
    perms = stratified_perms(coll, 30, seed=0)
    assert perms.shape == (30, 10)
    for p in perms:
        assert (coll[p] == coll).all()
    assert (perms[:, 9] == 9).all()                     # a one-tale collection never moves


def test_type_signal_that_is_only_collection_style_disappears_under_the_within_collection_null():
    import pandas as pd
    from reimagine.network import label_tests
    # 4 collections of 10 tales; communities = collections; tale type follows collection perfectly
    coll = np.repeat([f"c{k}" for k in range(4)], 10)
    folk = pd.DataFrame(dict(atu_id=np.repeat(["A", "B", "C", "D"], 10), region=np.tile(["x", "y"], 20), source_collection=coll))
    part = np.repeat(np.arange(4), 10)
    i, j = np.triu_indices(40, 1)
    keep = part[i] == part[j]
    e = dict(i=i[keep], j=j[keep], w=np.ones(keep.sum()))
    rows = {(r["label"], r["null"], r["measure"]): r for r in label_tests(part, e, folk, np.arange(40), 200, 1)}
    plain = rows[("atu_type", "label shuffle", "nmi")]
    within = rows[("atu_type", "within-collection shuffle", "nmi")]
    assert plain["observed"] == pytest.approx(1.0) and plain["p_upper"] < 0.01      # looks like a strong type signal ...
    assert within["null_mean"] == pytest.approx(1.0) and within["p_upper"] == 1.0    # ... but collection explains all of it
    assert ("source_collection", "within-collection shuffle", "nmi") not in rows


def test_gini_of_equal_and_concentrated_degrees():
    from reimagine.network import gini
    assert gini(np.ones(10)) == pytest.approx(0.0)
    assert gini(np.array([0, 0, 0, 10])) == pytest.approx(0.75)
