"""Unit tests for the analyses added after the TA's feedback (toy inputs; no data, network or model needed)."""
import numpy as np
import pytest

from ouaw.common import permute_within
from ouaw.corpus import check_calibration_exclusion, translator_of
from ouaw.headline import community_counts, headline_tests, profile, top_types, type_votes


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
