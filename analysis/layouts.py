"""Stage 8a: display-only backbones, layouts and projections (never used for statistics)."""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA

from .analyze import load_inputs
from .common import INTERIM, OUTPUTS, load_config, write_json, Timer
from .networks import disparity_backbone, layout, strongest_per_node


def load_graph(graph_id: str):
    z = np.load(INTERIM / "graphs" / f"{graph_id}.npz", allow_pickle=False)
    return {k: z[k] for k in z.files}


def backbone(g: dict, cfg: dict) -> np.ndarray:
    """Display-only backbone: each tale's k strongest edges in the analysis graph.

    The week-4 disparity filter was tried first but keeps almost nothing here (weights
    are nearly uniform per node), so the documented k-strongest rule is used instead.
    """
    n = len(g["nodes"])
    b = cfg["graphs"]["display_backbone"]
    if b["method"] == "disparity_filter":
        return disparity_backbone(n, g["i"], g["j"], g["w"], b["alpha"]) | strongest_per_node(n, g["i"], g["j"], g["w"], 1)
    return strongest_per_node(n, g["i"], g["j"], g["w"], b["k"])


def run() -> dict:
    cfg = load_config()
    nar, reps = load_inputs()
    pct = int(round(cfg["graphs"]["primary_density"] * 100))
    out = {}
    for cohort in ["joint", "text"]:
        res = {}
        masks = {}
        for rep in ["lexical", "semantic"]:
            g = load_graph(f"{cohort}-{rep}-d{pct:02d}")
            masks[rep] = (g, backbone(g, cfg))
        g_lex, k_lex = masks["lexical"]
        g_sem, k_sem = masks["semantic"]
        n = len(g_lex["nodes"])
        assert (g_lex["nodes"] == g_sem["nodes"]).all()
        # shared layout: union of both backbones, weight = mean of available weights
        edges = {}
        for g, k in ((g_lex, k_lex), (g_sem, k_sem)):
            for a, b, w in zip(g["i"][k], g["j"][k], g["w"][k]):
                edges.setdefault((int(a), int(b)), []).append(float(w))
        ei = np.array([a for a, _ in edges]); ej = np.array([b for _, b in edges])
        ew = np.array([np.mean(v) for v in edges.values()])
        with Timer(f"layout {cohort} shared ({len(ew)} edges)"):
            res["shared"] = layout(n, ei, ej, ew, seed=42)
        for rep, (g, k) in masks.items():
            with Timer(f"layout {cohort} {rep} ({int(k.sum())} edges)"):
                res[rep] = layout(n, g["i"][k], g["j"][k], g["w"][k], seed=42)
        idx = np.flatnonzero(nar["narrative_id"].isin(g_lex["nodes"]).to_numpy())
        assert nar.loc[idx, "narrative_id"].tolist() == g_lex["nodes"].tolist()
        V = reps["semantic"][1][idx]
        pca = PCA(n_components=2, random_state=42).fit(V)
        xy = pca.transform(V)
        xy = (xy - xy.min(axis=0)) / (xy.max(axis=0) - xy.min(axis=0)).max()
        res["pca"] = xy
        res["pca_explained_variance"] = pca.explained_variance_ratio_.tolist()
        res["backbone_edges"] = {rep: int(k.sum()) for rep, (g, k) in masks.items()}
        res["shared_edges"] = int(len(ew))
        res["nodes"] = g_lex["nodes"].tolist()
        np.savez_compressed(INTERIM / f"layout_{cohort}.npz", **{k: v for k, v in res.items()
                                                                  if isinstance(v, np.ndarray)})
        out[cohort] = {k: v for k, v in res.items() if not isinstance(v, np.ndarray)}
        print(f"  layout {cohort}: n={n}, backbone edges {res['backbone_edges']}, shared {res['shared_edges']}, "
              f"PCA variance {np.round(res['pca_explained_variance'], 3).tolist()}")
    write_json(OUTPUTS / "metrics" / "layouts.json", out)
    return out


if __name__ == "__main__":
    run()
