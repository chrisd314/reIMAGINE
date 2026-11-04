"""Stage 5b: degree-preserving null for modularity (week 4), for the main joint-cohort graphs.

Each shuffle keeps n, m and every node's degree (double edge swaps), assigns the
original edge weights to the shuffled edges at random, and reruns weighted
Louvain. This tests whether the observed modularity exceeds what the degree
sequence and weight distribution alone produce. Label shuffles do not test this.
"""
from __future__ import annotations

import numpy as np

from .common import INTERIM, OUTPUTS, load_config, read_json, write_json, Timer
from .networks import degree_preserving_null, to_graph


def run(graph_ids: list[str] | None = None) -> dict:
    cfg = load_config()
    mcfg = cfg["graphs"]["modularity_null"]
    prim = cfg["graphs"]["primary_seed"]
    graphs = {g["graph_id"]: g for g in read_json(OUTPUTS / "metrics" / "graphs.json")["graphs"]}
    graph_ids = graph_ids or [g for g, m in graphs.items() if m["group"] == "main"]
    path = OUTPUTS / "metrics" / "modularity_null.json"
    results = read_json(path)["results"] if path.exists() else {}
    for gid in graph_ids:
        meta = graphs[gid]
        obs_q = meta["partitions"][str(prim)]["modularity"]
        signature = f"swap-v2|{mcfg['seed']}|{mcfg['swaps_per_edge']}|{meta['n']}|{meta['m']}|{meta['similarity_threshold']:.12f}|{obs_q:.12f}"
        old = results.get(gid)
        # reuse only results computed with this method on exactly this graph (same size, threshold, observed Q)
        if old and old["shuffles"] == mcfg["shuffles"] and old.get("signature") == signature:
            print(f"  {gid}: cached")
            continue
        z = np.load(INTERIM / "graphs" / f"{gid}.npz")
        G = to_graph(len(z["nodes"]), z["i"], z["j"], z["w"])
        with Timer(f"modularity null {gid}"):
            q = degree_preserving_null(G, mcfg["shuffles"], mcfg["swaps_per_edge"], mcfg["seed"], prim)
        obs = graphs[gid]["partitions"][str(prim)]["modularity"]
        results[gid] = dict(signature=signature, observed=obs, shuffles=int(len(q)), null_mean=float(q.mean()), null_sd=float(q.std(ddof=1)),
                            null_min=float(q.min()), null_max=float(q.max()), difference=float(obs - q.mean()),
                            z=float((obs - q.mean()) / q.std(ddof=1)) if q.std(ddof=1) > 0 else None,
                            values=q.round(5).tolist(),
                            preserved="n, m, degree sequence, multiset of edge weights",
                            randomised="which tales are joined, and which weight each edge carries")
        write_json(path, dict(results=results))
        print(f"  {gid}: Q={obs:.3f} vs null {q.mean():.3f}±{q.std(ddof=1):.3f}")
    results = {k: v for k, v in results.items() if k in graph_ids}  # drop entries for graphs no longer computed
    write_json(path, dict(results=results))
    return results


if __name__ == "__main__":
    run()
