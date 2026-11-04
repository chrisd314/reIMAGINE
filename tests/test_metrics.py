"""The vectorised measures must equal the reference implementations they replace."""
import networkx as nx
import numpy as np
import pytest
from sklearn.metrics import normalized_mutual_info_score

from analysis.metrics import (assortativity_and_share, codes, label_agreement, nmi, permutation_matrix,
                              top_k_neighbours)
from analysis.networks import align_communities, disparity_backbone, select_edges


@pytest.fixture(scope="module")
def random_graph():
    rng = np.random.default_rng(0)
    n = 120
    X = rng.normal(size=(n, 16))
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    S = X @ X.T
    e = select_edges(S, 0.1)
    labels = rng.integers(0, 7, size=n)
    return S, e, labels


def test_nmi_matches_sklearn():
    rng = np.random.default_rng(1)
    for _ in range(20):
        a = rng.integers(0, rng.integers(2, 30), size=300)
        b = rng.integers(0, rng.integers(2, 30), size=300)
        a, _ = codes(a.tolist())
        b, _ = codes(b.tolist())
        assert nmi(a, b) == pytest.approx(normalized_mutual_info_score(a, b), abs=1e-10)


def test_assortativity_matches_networkx(random_graph):
    S, e, labels = random_graph
    G = nx.Graph()
    G.add_nodes_from(range(S.shape[0]))
    G.add_edges_from(zip(e["i"].tolist(), e["j"].tolist()))
    nx.set_node_attributes(G, {k: int(v) for k, v in enumerate(labels)}, "lab")
    deg = np.bincount(np.concatenate([e["i"], e["j"]]), minlength=S.shape[0]).astype(float)
    r, share = assortativity_and_share(labels, e["i"], e["j"], deg)
    assert r == pytest.approx(nx.attribute_assortativity_coefficient(G, "lab"), abs=1e-10)
    assert share == pytest.approx(np.mean(labels[e["i"]] == labels[e["j"]]))


def test_edge_selection_rules(random_graph):
    S, e, _ = random_graph
    n = S.shape[0]
    assert e["m"] == round(0.1 * n * (n - 1) / 2)
    assert e["density_achieved"] == pytest.approx(e["m"] / (n * (n - 1) / 2))
    assert (e["i"] < e["j"]).all(), "no self-loops, each undirected pair once"
    assert len(set(zip(e["i"], e["j"]))) == e["m"], "no repeated edges"
    assert np.allclose(e["w"], S[e["i"], e["j"]]), "edge weights equal declared scores"
    iu, ju = np.triu_indices(n, 1)
    outside = np.ones(len(iu), bool)
    sel = set(zip(e["i"].tolist(), e["j"].tolist()))
    outside = np.array([(a, b) not in sel for a, b in zip(iu, ju)])
    assert S[iu, ju][outside].max() <= e["w"].min() + 1e-12, "selected edges are the strongest pairs"


def test_tie_rule_is_deterministic():
    S = np.full((5, 5), 0.5)
    np.fill_diagonal(S, 1)
    e = select_edges(S, 0.3)  # 3 of 10 tied pairs
    assert list(zip(e["i"].tolist(), e["j"].tolist())) == [(0, 1), (0, 2), (0, 3)]


def test_permutations_preserve_counts_and_leave_graph_fixed(random_graph):
    S, e, labels = random_graph
    perms = permutation_matrix(len(labels), 50, 3)
    for p in perms:
        assert sorted(labels[p].tolist()) == sorted(labels.tolist())
    i0, j0 = e["i"].copy(), e["j"].copy()
    part = np.arange(len(labels)) % 4
    label_agreement(part, labels, e["i"], e["j"], perms)
    assert (e["i"] == i0).all() and (e["j"] == j0).all()


def test_neighbours_exclude_self_and_respect_eligibility(random_graph):
    S, _, _ = random_graph
    nb = top_k_neighbours(S, 10)
    assert not (nb == np.arange(len(S))[:, None]).any()
    elig = np.ones_like(S, dtype=bool)
    elig[:, :5] = False
    nb2 = top_k_neighbours(S, 10, eligible=elig)
    assert (nb2 >= 5).all()


def test_double_edge_swaps_preserve_degrees_without_loops_or_repeats(random_graph):
    from analysis.networks import double_edge_swaps
    S, e, _ = random_graph
    n = S.shape[0]
    edges = np.stack([e["i"], e["j"]], 1).astype(np.int64)
    out = double_edge_swaps(edges, n, nswap=10 * len(edges), rng=np.random.default_rng(5), max_tries=10 ** 7)
    assert (np.bincount(out.ravel(), minlength=n) == np.bincount(edges.ravel(), minlength=n)).all()
    assert (out[:, 0] != out[:, 1]).all()
    canon = {(min(a, b), max(a, b)) for a, b in out.tolist()}
    assert len(canon) == len(out), "no repeated edges"
    before = {(min(a, b), max(a, b)) for a, b in edges.tolist()}
    assert len(canon & before) < 0.5 * len(before), "the shuffle should actually rewire most edges"


def test_backbone_and_alignment_shapes(random_graph):
    S, e, _ = random_graph
    keep = disparity_backbone(S.shape[0], e["i"], e["j"], e["w"], 0.2)
    assert keep.dtype == bool and len(keep) == e["m"]
    ref = np.array([0, 0, 1, 1, 2, 2])
    other = np.array([1, 1, 0, 0, 2, 3])
    m = align_communities(ref, other)
    assert m[1] == 0 and m[0] == 1 and m[2] == 2 and m[3] == 3
