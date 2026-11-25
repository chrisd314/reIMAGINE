"""Similarity graphs, Louvain communities, modularity null, backbones and layouts."""
from __future__ import annotations

import numpy as np
import networkx as nx
import scipy.sparse as sp


def similarity_matrix(kind: str, idx: np.ndarray, lexical: sp.csr_matrix | None, vectors: np.ndarray | None) -> np.ndarray:
    """Cosine similarity in the original feature space (rows are L2-normalised)."""
    if kind == "lexical":
        X = lexical[idx]
        S = (X @ X.T).toarray()
    else:
        V = vectors[idx]
        S = V @ V.T
    S = (S + S.T) / 2.0  # exact symmetry
    np.fill_diagonal(S, 1.0)
    return S


def select_edges(S: np.ndarray, density: float):
    """Strongest positive pairs up to the target density, with a deterministic tie rule.

    Pairs are ordered by similarity rounded to 12 decimals (descending), then by
    row index and column index (ascending), where indices follow the sorted
    narrative IDs of the cohort.
    """
    n = S.shape[0]
    iu, ju = np.triu_indices(n, k=1)
    w = S[iu, ju]
    n_pairs = len(w)
    m_target = int(round(density * n_pairs))
    order = np.lexsort((ju, iu, -np.round(w, 12)))
    order = order[w[order] > 0]
    sel = np.sort(order[:m_target])
    return dict(i=iu[sel].astype(np.int32), j=ju[sel].astype(np.int32), w=w[sel],
                m_target=m_target, m=len(sel), n=n, n_pairs=n_pairs,
                density_target=density, density_achieved=len(sel) / n_pairs,
                threshold=float(w[sel].min()) if len(sel) else None,
                positive_pairs=int((w > 0).sum()))


def to_graph(n: int, i: np.ndarray, j: np.ndarray, w: np.ndarray) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_weighted_edges_from(zip(i.tolist(), j.tolist(), w.tolist()))
    return G


def louvain(G: nx.Graph, seed: int, resolution: float = 1.0) -> np.ndarray:
    comms = nx.community.louvain_communities(G, weight="weight", resolution=resolution, seed=seed)
    comms = sorted(comms, key=lambda c: (-len(c), min(c)))  # IDs by size, then lowest node
    labels = np.empty(G.number_of_nodes(), dtype=np.int32)
    for k, c in enumerate(comms):
        labels[list(c)] = k
    return labels


def partition_sets(labels: np.ndarray) -> list[set]:
    return [set(np.flatnonzero(labels == k).tolist()) for k in range(labels.max() + 1)]


def modularity(G: nx.Graph, labels: np.ndarray, weight: str | None = "weight") -> float:
    return float(nx.community.modularity(G, partition_sets(labels), weight=weight))


def structure(G: nx.Graph) -> dict:
    comps = list(nx.connected_components(G))
    return dict(components=len(comps), largest_component=max(len(c) for c in comps),
                isolates=sorted(nx.isolates(G)))


def double_edge_swaps(edges: np.ndarray, n: int, nswap: int, rng: np.random.Generator, max_tries: int) -> np.ndarray:
    """Degree-preserving rewiring (week 2, 'Edge swapping'): pick links A-B and C-D, rewire to A-D and C-B.

    The same rule as networkx.double_edge_swap (a swap is rejected if it would create a
    self-loop or a repeated edge), implemented on an edge list plus a hash set so each
    attempt costs O(1) instead of O(degree) on the hub-heavy similarity graphs.
    """
    e = edges.astype(np.int64).copy()
    key = lambda a, b: a * n + b if a < b else b * n + a
    present = {key(int(a), int(b)) for a, b in e}
    m = len(e)
    done = tries = 0
    batch = 65536
    while done < nswap:
        idx = rng.integers(0, m, size=(batch, 2))
        flip = rng.random(batch) < 0.5
        for (k1, k2), f in zip(idx.tolist(), flip.tolist()):
            tries += 1
            if tries > max_tries:
                raise RuntimeError(f"edge swap: {done} of {nswap} swaps after {max_tries} attempts")
            if k1 == k2:
                continue
            a, b = int(e[k1, 0]), int(e[k1, 1])
            c, d = (int(e[k2, 1]), int(e[k2, 0])) if f else (int(e[k2, 0]), int(e[k2, 1]))
            if a == d or c == b or a == c or b == d:
                continue
            k_ad, k_cb = key(a, d), key(c, b)
            if k_ad in present or k_cb in present:
                continue
            present.discard(key(a, b)); present.discard(key(c, d))
            present.add(k_ad); present.add(k_cb)
            e[k1] = (a, d)
            e[k2] = (c, b)
            done += 1
            if done >= nswap:
                break
    return e


def disparity_backbone(n: int, i: np.ndarray, j: np.ndarray, w: np.ndarray, alpha: float) -> np.ndarray:
    """Serrano-Boguna-Vespignani disparity filter (week 4): keep an edge if significant at either end."""
    deg = np.bincount(np.concatenate([i, j]), minlength=n).astype(float)
    strength = np.bincount(np.concatenate([i, j]), weights=np.concatenate([w, w]), minlength=n)
    keep = np.zeros(len(w), dtype=bool)
    for end in (i, j):
        k = deg[end]
        p = w / strength[end]
        with np.errstate(divide="ignore", invalid="ignore"):
            pval = np.where(k > 1, (1 - p) ** (k - 1), 1.0)
        keep |= pval < alpha
    return keep


def strongest_per_node(n: int, i: np.ndarray, j: np.ndarray, w: np.ndarray, k: int) -> np.ndarray:
    """Mask of edges that are among the k strongest of at least one endpoint."""
    keep = np.zeros(len(w), dtype=bool)
    ends = np.concatenate([i, j])
    eidx = np.concatenate([np.arange(len(w)), np.arange(len(w))])
    ww = np.concatenate([w, w])
    order = np.lexsort((eidx, -ww, ends))
    ends_sorted = ends[order]
    starts = np.searchsorted(ends_sorted, np.arange(n))
    rank = np.arange(len(order)) - starts[ends_sorted]
    keep[eidx[order][rank < k]] = True
    return keep


def layout(n: int, i: np.ndarray, j: np.ndarray, w: np.ndarray, seed: int) -> np.ndarray:
    """ForceAtlas2 layout of a backbone, rescaled to the unit square. Display only."""
    G = to_graph(n, i, j, w)
    pos = nx.forceatlas2_layout(G, max_iter=600, scaling_ratio=2.0, gravity=1.0, linlog=True,
                                weight="weight", seed=seed, strong_gravity=False)
    xy = np.array([pos[k] for k in range(n)], dtype=float)
    xy -= xy.min(axis=0)
    span = xy.max(axis=0)
    span[span == 0] = 1
    return xy / span.max()


def align_communities(ref: np.ndarray, other: np.ndarray) -> dict[int, int]:
    """Display-only colour mapping: greedily match communities of `other` to `ref` by overlap size.

    Unmatched communities receive new indices after the reference ones. This is a
    declared overlap-based mapping. Community IDs have no meaning of their own.
    """
    cont = {}
    for a, b in zip(other.tolist(), ref.tolist()):
        cont[(a, b)] = cont.get((a, b), 0) + 1
    pairs = sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))
    mapping, used = {}, set()
    for (a, b), _ in pairs:
        if a not in mapping and b not in used:
            mapping[a] = b
            used.add(b)
    nxt = int(ref.max()) + 1
    for a in sorted(set(other.tolist())):
        if a not in mapping:
            mapping[a] = nxt
            nxt += 1
    return mapping
