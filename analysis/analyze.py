"""Stage 5: graphs, communities and label agreement for every configuration in ANALYSIS_PLAN.md."""
from __future__ import annotations

import itertools
import platform
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

from . import SCHEMA_VERSION
from .common import INTERIM, OUTPUTS, PROCESSED, ROOT, content_hash, load_config, stable_hash, write_json, Timer
from .metrics import (codes, label_agreement, neighbour_label_rates, nmi, permutation_matrix, top_k_neighbours)
from .networks import louvain, modularity, select_edges, similarity_matrix, structure, to_graph

LABELS = ["atu", "place", "region", "source"]
LABEL_COL = {"atu": "atu_id", "place": "place_label", "region": "broad_region", "source": "source_key"}


def load_inputs():
    nar = pd.read_parquet(PROCESSED / "narratives.parquet").sort_values("narrative_id").reset_index(drop=True)
    order = pd.read_parquet(INTERIM / "lexical_order.parquet")["narrative_id"].tolist()
    assert order == nar["narrative_id"].tolist(), "lexical order must match narrative order"
    sem = np.load(INTERIM / "semantic_vectors.npz")
    assert sem["narrative_id"].tolist() == order
    reps = {
        "lexical": ("lexical", sp.load_npz(INTERIM / "lexical_tfidf.npz").tocsr()),
        "lexical_names": ("lexical", sp.load_npz(INTERIM / "lexical_tfidf_names_masked.npz").tocsr()),
        "semantic": ("semantic", sem["c200_mean"]),
        "semantic_tokw": ("semantic", sem["c200_tokw"]),
        "semantic_c128": ("semantic", sem["c128_mean"]),
    }
    return nar, reps


def cohort_indices(nar: pd.DataFrame, cfg: dict) -> dict[str, np.ndarray]:
    joint = nar["in_joint"].to_numpy()
    idx = {"text": np.arange(len(nar)), "joint": np.flatnonzero(joint)}
    # near-duplicate reduction inside the joint cohort: keep the lowest ID per component
    nd = pd.read_csv(OUTPUTS / "audit" / "near_duplicates.csv")
    pos = {k: i for i, k in enumerate(nar["narrative_id"])}
    parent = list(range(len(nar)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(nd["narrative_a"], nd["narrative_b"]):
        ia, ib = pos[a], pos[b]
        if joint[ia] and joint[ib]:
            ra, rb = find(ia), find(ib)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)  # the root is always the lowest index
    idx["joint_nodup"] = np.array([i for i in idx["joint"] if find(i) == i])
    idx["joint_nofrag"] = np.flatnonzero(joint & ~nar["suspected_fragment"].to_numpy())
    b = cfg["evaluation"]["balanced_subset"]
    rng = np.random.default_rng(b["seed"])
    keep = []
    reg = nar.loc[joint, "broad_region"]
    for region in sorted(reg.unique()):
        members = np.array(sorted(reg.index[reg == region]))
        keep.extend(members if len(members) <= b["cap"] else rng.choice(members, b["cap"], replace=False))
    idx["joint_balanced"] = np.array(sorted(keep))
    return idx


def configurations(cfg: dict) -> list[dict]:
    g = cfg["graphs"]
    seeds, dens, prim = g["seeds"], g["densities"], g["primary_density"]
    out = []
    for rep, d in itertools.product(["lexical", "semantic"], dens):
        out.append(dict(group="main", cohort="joint", rep=rep, density=d, seeds=seeds))
    for rep in ["semantic_tokw", "semantic_c128", "lexical_names"]:
        out.append(dict(group="representation", cohort="joint", rep=rep, density=prim, seeds=seeds))
    for cohort, rep in itertools.product(["joint_nodup", "joint_nofrag", "joint_balanced"], ["lexical", "semantic"]):
        out.append(dict(group="cohort", cohort=cohort, rep=rep, density=prim, seeds=seeds))
    for rep, d in itertools.product(["lexical", "semantic"], dens):
        out.append(dict(group="exploratory", cohort="text", rep=rep, density=d, seeds=seeds))
    for c in out:
        c["graph_id"] = f"{c['cohort']}-{c['rep']}-d{int(round(c['density'] * 100)):02d}"
    return out


def run() -> dict:
    t0 = time.time()
    cfg = load_config()
    nar, reps = load_inputs()
    idx = cohort_indices(nar, cfg)
    ecfg = cfg["evaluation"]
    (INTERIM / "graphs").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({c: pd.Series(nar.loc[v, "narrative_id"].tolist()) for c, v in idx.items()}).to_csv(
        OUTPUTS / "metrics" / "cohort_members.csv", index=False)

    # one permutation matrix per cohort, shared by all label systems and configurations
    perms = {c: permutation_matrix(len(v), ecfg["permutations"], ecfg["permutation_seed"]) for c, v in idx.items()
             if c != "text"}

    graphs_out, agreement_rows, nulls = [], [], {}
    sim_cache: dict = {}
    for c in configurations(cfg):
        ids = idx[c["cohort"]]
        kind, data = reps[c["rep"]]
        key = (c["cohort"], c["rep"])
        if key not in sim_cache:
            sim_cache.clear()
            sim_cache[key] = similarity_matrix(kind, ids, data if kind == "lexical" else None,
                                               data if kind == "semantic" else None)
        S = sim_cache[key]
        with Timer(c["graph_id"]):
            e = select_edges(S, c["density"])
            G = to_graph(len(ids), e["i"], e["j"], e["w"])
            st = structure(G)
            parts = {s: louvain(G, s, cfg["graphs"]["louvain_resolution"]) for s in c["seeds"]}
            np.savez_compressed(INTERIM / "graphs" / f"{c['graph_id']}.npz", i=e["i"], j=e["j"], w=e["w"],
                                nodes=np.array(nar.loc[ids, "narrative_id"].tolist()),
                                **{f"seed{s}": p for s, p in parts.items()})
            seed_nmi = {f"{a}-{b}": nmi(parts[a], parts[b]) for a, b in itertools.combinations(c["seeds"], 2)}
            g_rec = dict(**{k: c[k] for k in ("graph_id", "group", "cohort", "rep", "density")},
                         n=e["n"], m=e["m"], m_target=e["m_target"], density_achieved=e["density_achieved"],
                         similarity_threshold=e["threshold"], positive_pairs=e["positive_pairs"],
                         components=st["components"], largest_component=st["largest_component"],
                         isolates=[nar.loc[ids[k], "narrative_id"] for k in st["isolates"]],
                         mean_degree=2 * e["m"] / e["n"],
                         partitions={str(s): dict(communities=int(p.max() + 1), modularity=modularity(G, p),
                                                  sizes=np.bincount(p).tolist()) for s, p in parts.items()},
                         seed_agreement_nmi=seed_nmi)
            graphs_out.append(g_rec)
            if c["cohort"] == "text":
                continue
            sub = nar.loc[ids]
            # isolate-free sensitivity: same graph and partition restricted to tales with at least one edge
            deg = np.bincount(np.concatenate([e["i"], e["j"]]), minlength=len(ids))
            ni = np.flatnonzero(deg > 0)
            remap = -np.ones(len(ids), dtype=np.int64)
            remap[ni] = np.arange(len(ni))
            perms_ni = permutation_matrix(len(ni), ecfg["permutations"], ecfg["permutation_seed"]) if len(ni) < len(ids) else None
            for lab in LABELS:
                y, cats = codes(sub[LABEL_COL[lab]].tolist())
                for s, p in parts.items():
                    keep = (s == cfg["graphs"]["primary_seed"])
                    res = label_agreement(p, y, e["i"], e["j"], perms[c["cohort"]], keep_null=keep)
                    if keep:
                        nulls[f"{c['graph_id']}|{lab}"] = res.pop("null_values")
                    if perms_ni is not None:
                        y_ni, _ = codes([sub[LABEL_COL[lab]].tolist()[k] for k in ni])
                        p_ni, _ = codes(p[ni].tolist())
                        res_ni = label_agreement(p_ni, y_ni, remap[e["i"]], remap[e["j"]], perms_ni)
                        res["non_isolates"] = dict(n=int(len(ni)), isolates=int(len(ids) - len(ni)),
                                                   nmi=res_ni["nmi"], categories=res_ni["categories"])
                    agreement_rows.append(dict(graph_id=c["graph_id"], group=c["group"], cohort=c["cohort"],
                                               rep=c["rep"], density=c["density"], seed=s, label=lab,
                                               diagnostic=lab in ecfg["diagnostic_label_systems"], **res))

    # top-10 neighbour check in the original feature spaces (joint cohort + variants)
    neigh = {}
    k = ecfg["neighbours_k"]
    for cohort in ["joint", "joint_balanced", "joint_nodup", "joint_nofrag"]:
        ids = idx[cohort]
        sub = nar.loc[ids].reset_index(drop=True)
        src = sub["source_key"].to_numpy()
        known = src != "(no source)"
        eligible = ~((src[:, None] == src[None, :]) & known[:, None] & known[None, :])
        for rep in (["lexical", "semantic", "semantic_tokw", "semantic_c128", "lexical_names"] if cohort == "joint" else ["lexical", "semantic"]):
            kind, data = reps[rep]
            S = similarity_matrix(kind, ids, data if kind == "lexical" else None, data if kind == "semantic" else None)
            nb = top_k_neighbours(S, k)
            if cohort == "joint" and rep in ("lexical", "semantic"):
                np.savez_compressed(INTERIM / f"neighbours_joint_{rep}.npz", nb=nb,
                                    score=np.take_along_axis(S, nb, axis=1))
            nb_x = top_k_neighbours(S, k, eligible=eligible)
            entry = {}
            for lab in ["atu", "place", "region"]:
                y, cats = codes(sub[LABEL_COL[lab]].tolist())
                r = neighbour_label_rates(nb, y)
                rx = neighbour_label_rates(nb_x, y, eligible=eligible)
                per = pd.DataFrame({"cat": [cats[v] for v in y], "rate": r["rate"], "base": r["baseline"]})
                grp = per.groupby("cat").agg(n=("rate", "size"), rate=("rate", "mean"), base=("base", "mean"))
                entry[lab] = dict(
                    mean_rate=float(r["rate"].mean()), mean_baseline=float(r["baseline"].mean()),
                    lift=float(r["rate"].mean() / r["baseline"].mean()),
                    mean_rate_excl_same_source=float(rx["rate"].mean()),
                    mean_baseline_excl_same_source=float(rx["baseline"].mean()),
                    lift_excl_same_source=float(rx["rate"].mean() / rx["baseline"].mean()),
                    share_of_categories_above_baseline=float(((grp["rate"] > grp["base"]) & (grp["n"] >= 2)).sum() / (grp["n"] >= 2).sum()),
                    per_category=[dict(category=str(cat), n=int(g.n), rate=float(g.rate), baseline=float(g.base))
                                  for cat, g in grp.sort_values("n", ascending=False).iterrows()],
                )
            same_src = (src[nb] == src[:, None]) & known[:, None]
            entry["share_neighbours_same_source"] = float(same_src.mean())
            neigh[f"{cohort}|{rep}"] = entry

    run_inputs = {p.name: content_hash(p) for p in [PROCESSED / "narratives.parquet", INTERIM / "lexical_tfidf.npz",
                                                   INTERIM / "semantic_vectors.npz"]}
    run_id = f"ouaw-{time.strftime('%Y%m%d')}-{stable_hash({'cfg': cfg, 'inputs': run_inputs}, 8)}"
    import networkx, sklearn, sentence_transformers, torch
    run_meta = dict(run_id=run_id, schema_version=SCHEMA_VERSION, created=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    seconds=round(time.time() - t0, 1), config_hash=stable_hash(cfg), inputs_sha256=run_inputs,
                    versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                                  networkx=networkx.__version__, scikit_learn=sklearn.__version__,
                                  sentence_transformers=sentence_transformers.__version__, torch=torch.__version__),
                    cohort_sizes={c: int(len(v)) for c, v in idx.items()})
    write_json(OUTPUTS / "metrics" / "run.json", run_meta)
    write_json(OUTPUTS / "metrics" / "graphs.json", dict(run_id=run_id, graphs=graphs_out))
    write_json(OUTPUTS / "metrics" / "agreement.json", dict(run_id=run_id, rows=agreement_rows))
    write_json(OUTPUTS / "metrics" / "null_distributions.json", dict(run_id=run_id, values=nulls), compact=True)
    write_json(OUTPUTS / "metrics" / "neighbours.json", dict(run_id=run_id, k=k, results=neigh))
    print(f"  analysis run {run_id}: {len(graphs_out)} graphs, {len(agreement_rows)} agreement rows, "
          f"{time.time() - t0:.0f}s")
    return run_meta


if __name__ == "__main__":
    run()
