"""Stage 9: export compact, lazily loaded JSON payloads for the static website.

Every payload carries the same run_id and schema_version. Numbers are exported
at full useful precision; rounding happens only in the presentation layer.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil

import numpy as np
import pandas as pd
import scipy.sparse as sp

from . import SCHEMA_VERSION
from .analyze import load_inputs
from .common import (DATA, INTERIM, MAPPINGS, OUTPUTS, PROCESSED, RAW, WEB_DATA, load_config, read_json, sha256_file,
                     utc_now, write_json)
from .layouts import backbone as display_backbone, load_graph
from .networks import align_communities


def b64(arr: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(arr, dtype="<f4").tobytes()).decode("ascii")


def clean_list(v):
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v if isinstance(v, list) else ([] if v is None else [v])


def none_if_nan(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


EXCERPT_WORDS = 120


def public_build() -> bool:
    """True when OUAW_PUBLIC_BUILD is set: the export is meant for a public deployment.

    A public build never contains full texts, whatever `export.include_full_texts` says
    (see LICENSE_NOTES.md). The deployment workflow sets this variable.
    """
    return os.environ.get("OUAW_PUBLIC_BUILD", "").strip().lower() in {"1", "true", "yes"}


def excerpt_of(text: str, words: int = EXCERPT_WORDS) -> str:
    """Verbatim opening of a text (its first `words` words).

    The cut is a prefix of the original string, so passage offsets into the full text
    stay valid for the part that is kept. Texts no longer than the limit are returned whole.
    """
    ends = [m.end() for m in re.finditer(r"\S+", text)]
    return text if len(ends) <= words else text[:ends[words - 1]]


def run() -> dict:
    cfg = load_config()
    run_meta = read_json(OUTPUTS / "metrics" / "run.json")
    run_id = run_meta["run_id"]
    stamp = dict(run_id=run_id, schema_version=SCHEMA_VERSION)
    full_text = bool(cfg.get("export", {}).get("include_full_texts", True)) and not public_build()
    # Passages quoted by the story's opening scene. An excerpt-only build ships these two
    # passages in addition to each tale's opening, so the scene still works.
    quoted: dict[str, set[int]] = {}
    op = cfg.get("export", {}).get("opening_pair")
    if op:
        quoted.setdefault(op["a"], set()).add(int(op["a_chunk"]))
        quoted.setdefault(op["b"], set()).add(int(op["b_chunk"]))
    nar, reps = load_inputs()
    nar = nar.reset_index(drop=True)
    pos = {k: i for i, k in enumerate(nar["narrative_id"])}
    if WEB_DATA.exists():
        shutil.rmtree(WEB_DATA)
    for d in ["tales", "graphs", "layouts"]:
        (WEB_DATA / d).mkdir(parents=True, exist_ok=True)

    graphs_meta = {g["graph_id"]: g for g in read_json(OUTPUTS / "metrics" / "graphs.json")["graphs"]}
    agreement = read_json(OUTPUTS / "metrics" / "agreement.json")["rows"]
    pct = int(round(cfg["graphs"]["primary_density"] * 100))
    seeds = cfg["graphs"]["seeds"]
    prim_seed = cfg["graphs"]["primary_seed"]
    modnull = read_json(OUTPUTS / "metrics" / "modularity_null.json")["results"] \
        if (OUTPUTS / "metrics" / "modularity_null.json").exists() else {}

    # ---- graphs: partitions with aligned colours, backbone, strongest edges per node ----
    exported_graphs = []
    for gid, meta in graphs_meta.items():
        g = load_graph(gid)
        n = len(g["nodes"])
        ref_id = f"{meta['cohort']}-{meta['rep']}-d{pct:02d}"
        ref = load_graph(ref_id)[f"seed{prim_seed}"] if gid != ref_id else g[f"seed{prim_seed}"]
        parts, colours = {}, {}
        for s in seeds:
            p = g[f"seed{s}"]
            parts[str(s)] = p.tolist()
            m = align_communities(ref, p) if (gid != ref_id or s != prim_seed) else {k: k for k in range(p.max() + 1)}
            colours[str(s)] = [int(m[k]) for k in range(p.max() + 1)]
        keep = display_backbone(g, cfg)
        kmax = cfg["graphs"]["display_backbone"]["max_edges_per_node_listed"]
        adj = [[] for _ in range(n)]
        order = np.argsort(-g["w"], kind="stable")
        for e in order:
            a, b, w = int(g["i"][e]), int(g["j"][e]), float(g["w"][e])
            if len(adj[a]) < kmax:
                adj[a].append([b, round(w, 6)])
            if len(adj[b]) < kmax:
                adj[b].append([a, round(w, 6)])
        deg = np.bincount(np.concatenate([g["i"], g["j"]]), minlength=n)
        strength = np.bincount(np.concatenate([g["i"], g["j"]]), weights=np.concatenate([g["w"], g["w"]]), minlength=n)
        payload = dict(**stamp, graph_id=gid, **{k: meta[k] for k in ("group", "cohort", "rep", "density", "n", "m",
                                                                       "m_target", "density_achieved",
                                                                       "similarity_threshold", "components",
                                                                       "largest_component", "isolates", "mean_degree",
                                                                       "seed_agreement_nmi")},
                       nodes=g["nodes"].tolist(), partitions=parts, colour_index=colours,
                       partition_stats=meta["partitions"], colour_reference=ref_id,
                       backbone=[[int(a), int(b), round(float(w), 5)] for a, b, w in
                                 zip(g["i"][keep], g["j"][keep], g["w"][keep])],
                       backbone_rule=f"each tale's {cfg['graphs']['display_backbone']['k']} strongest edges (display only)",
                       top_edges=adj, top_edges_rule=f"up to {kmax} strongest edges per tale in this graph",
                       degree=deg.tolist(), strength=np.round(strength, 4).tolist(),
                       modularity_null=modnull.get(gid))
        write_json(WEB_DATA / "graphs" / f"{gid}.json", payload, compact=True)
        mn = modnull.get(gid)
        exported_graphs.append(dict(graph_id=gid, group=meta["group"], cohort=meta["cohort"], rep=meta["rep"],
                                    density=meta["density"], n=meta["n"], m=meta["m"], isolates=len(meta["isolates"]),
                                    communities=meta["partitions"][str(prim_seed)]["communities"],
                                    modularity=meta["partitions"][str(prim_seed)]["modularity"],
                                    seed_agreement_nmi=meta["seed_agreement_nmi"],
                                    modularity_null=None if mn is None else {k: mn[k] for k in ("null_mean", "null_sd", "shuffles", "z")}))

    # ---- layouts ----
    lay_meta = read_json(OUTPUTS / "metrics" / "layouts.json")
    for cohort in ["joint", "text"]:
        z = np.load(INTERIM / f"layout_{cohort}.npz")
        write_json(WEB_DATA / "layouts" / f"{cohort}.json", dict(
            **stamp, cohort=cohort, nodes=lay_meta[cohort]["nodes"],
            shared=np.round(z["shared"], 5).tolist(), lexical=np.round(z["lexical"], 5).tolist(),
            semantic=np.round(z["semantic"], 5).tolist(), pca=np.round(z["pca"], 5).tolist(),
            pca_explained_variance=lay_meta[cohort]["pca_explained_variance"],
            notes=dict(shared="ForceAtlas2 layout of the union of the lexical and semantic display backbones at the primary density. Positions are a drawing aid; distances on screen are not measurements.",
                       lexical="ForceAtlas2 layout of the lexical display backbone only (optional relayout).",
                       semantic="ForceAtlas2 layout of the semantic display backbone only (optional relayout).",
                       pca="First two principal components of the semantic tale vectors (PC1/PC2); explained variance shown. Neighbours are always computed in the original space.")),
            compact=True)

    # ---- neighbours per tale (joint and text cohorts, both representations) ----
    from .metrics import top_k_neighbours
    from .networks import similarity_matrix
    k = cfg["evaluation"]["neighbours_k"]
    neighbours: dict[str, dict] = {nid: {} for nid in nar["narrative_id"]}
    for cohort, mask in (("joint", nar["in_joint"].to_numpy()), ("text", np.ones(len(nar), bool))):
        idx = np.flatnonzero(mask)
        for rep in ["lexical", "semantic"]:
            kind, data = reps[rep]
            S = similarity_matrix(kind, idx, data if kind == "lexical" else None, data if kind == "semantic" else None)
            nb = top_k_neighbours(S, k)
            for r, row in enumerate(nb):
                neighbours[nar.loc[idx[r], "narrative_id"]].setdefault(cohort, {})[rep] = [
                    [nar.loc[idx[c], "narrative_id"], round(float(S[r, c]), 6)] for c in row]

    # ---- per-tale payloads ----
    chunks = pd.read_parquet(INTERIM / "semantic_chunks.parquet")
    chunks = chunks[chunks["setting"] == "c200"].reset_index(drop=True)
    chunk_vecs = np.load(INTERIM / "semantic_chunk_vectors_c200.npy")
    assert len(chunk_vecs) == len(chunks)
    X = sp.load_npz(INTERIM / "lexical_tfidf.npz").tocsr()
    vocab = pd.read_parquet(INTERIM / "lexical_vocab.parquet")["term"].to_numpy()
    from .lexical import preprocess
    tok = re.compile(cfg["lexical"]["token_pattern"])
    sem = reps["semantic"][1]
    for i, r in nar.iterrows():
        nid = r["narrative_id"]
        ch = chunks[chunks["narrative_id"] == nid]
        row = X.getrow(i)
        terms = sorted(((vocab[j], float(v)) for j, v in zip(row.indices, row.data)), key=lambda t: -t[1])
        toks = tok.findall(preprocess(r["text"], cfg["lexical"]))
        freq = pd.Series(toks).value_counts()
        shown = r["text"] if full_text else excerpt_of(r["text"])
        is_excerpt = len(shown) < len(r["text"])
        spans = list(zip(ch["char_start"], ch["char_end"]))
        payload = dict(
            **stamp, id=nid, title=r["title"], titles=clean_list(r["titles"]), record_ids=clean_list(r["record_ids"]),
            text=shown, text_is_excerpt=is_excerpt,
            passages={str(c): r["text"][int(spans[c][0]):int(spans[c][1])] for c in sorted(quoted.get(nid, ()))
                      if c < len(spans)} if is_excerpt else {},
            n_words=int(r["n_words"]),
            atu=dict(id=r["atu_id"], ids=clean_list(r["atu_ids"]), name=r["atu_name"], chapter=r["atu_chapter"],
                     status=r["atu_status"]),
            provenance=dict(raw=clean_list(r["provenance_raw"]), label=clean_list(r["provenance_label"]),
                            kinds=clean_list(r["entity_kind"]), status=r["geo_status"], place=r["place_label"],
                            place_kind=r["place_kind"], detail=none_if_nan(r["place_detail"]), region=r["broad_region"],
                            confidence=r["geo_confidence"], lat=none_if_nan(r["latitude"]), lon=none_if_nan(r["longitude"]),
                            coordinate_meaning=r["coordinate_meaning"]),
            source=none_if_nan(r["source"]), sources=clean_list(r["sources"]), source_key=r["source_key"],
            notes=none_if_nan(r["notes"]), flags=clean_list(r["flags"]),
            cohorts=dict(text=True, atu=bool(r["in_atu"]), joint=bool(r["in_joint"]), distance=bool(r["in_distance"])),
            exclusion_reasons=r["exclusion_reasons"], near_duplicates=clean_list(r["near_duplicates"]),
            chunks=[[int(a), int(b), int(t)] for a, b, t in zip(ch["char_start"], ch["char_end"], ch["n_tokens"])],
            chunk_vectors=b64(chunk_vecs[ch.index.to_numpy()]), vector=b64(sem[i]),
            tfidf=[[t, round(w, 6)] for t, w in terms],
            frequencies=[[t, round(c / max(len(toks), 1), 6)] for t, c in freq.head(25).items()],
            n_tokens_lexical=len(toks),
            neighbours=neighbours[nid])
        write_json(WEB_DATA / "tales" / f"{nid}.json", payload, compact=True)

    # ---- catalogue (all usable narratives) + excluded records ----
    fields = ["id", "title", "atu", "atu_name", "atu_chapter", "place", "region", "provenance", "entity_kind",
              "source_key", "n_words", "in_atu", "in_joint", "in_distance", "lat", "lon", "n_records", "flags",
              "fragment", "geo_status"]
    rows = []
    for _, r in nar.iterrows():
        rows.append([r["narrative_id"], r["title"], r["atu_id"], r["atu_name"], r["atu_chapter"], r["place_label"],
                     r["broad_region"], " | ".join(clean_list(r["provenance_label"])), " | ".join(clean_list(r["entity_kind"])),
                     r["source_key"], int(r["n_words"]), bool(r["in_atu"]), bool(r["in_joint"]), bool(r["in_distance"]),
                     none_if_nan(r["latitude"]), none_if_nan(r["longitude"]), int(r["n_records"]),
                     clean_list(r["flags"]), bool(r["suspected_fragment"]), r["geo_status"]])
    rec = pd.read_parquet(INTERIM / "records.parquet")
    excluded = rec[rec["excluded_reason"] != ""][["record_id", "title", "atu_id", "provenance", "excluded_reason"]]
    write_json(WEB_DATA / "catalogue.json", dict(**stamp, fields=fields, rows=rows,
                                                 excluded_records=excluded.to_dict("records")), compact=True)

    # ---- analysis summaries ----
    shutil.copy(OUTPUTS / "audit" / "inclusion_ledger.csv", WEB_DATA / "inclusion_ledger.csv")
    shutil.copy(MAPPINGS / "provenance_map.csv", WEB_DATA / "provenance_map.csv")
    nulls = read_json(OUTPUTS / "metrics" / "null_distributions.json")["values"]
    write_json(WEB_DATA / "agreement.json", dict(**stamp, rows=agreement), compact=True)
    write_json(WEB_DATA / "nulls.json", dict(**stamp, nmi={k: v["nmi"] for k, v in nulls.items()}), compact=True)
    write_json(WEB_DATA / "neighbour_stats.json", {**read_json(OUTPUTS / "metrics" / "neighbours.json"), **stamp}, compact=True)
    if (OUTPUTS / "metrics" / "distance.json").exists():
        dist = read_json(OUTPUTS / "metrics" / "distance.json")
        sample = pd.read_csv(OUTPUTS / "metrics" / "distance_display_sample.csv")
        dist["pairs_sample"] = sample.values.tolist()
        dist["pairs_sample_fields"] = list(sample.columns)
        write_json(WEB_DATA / "distance.json", {**dist, **stamp}, compact=True)
    pm = pd.read_csv(MAPPINGS / "provenance_map.csv", dtype=str, keep_default_na=False)
    write_json(WEB_DATA / "mapping.json", dict(**stamp, fields=list(pm.columns), rows=pm.values.tolist()), compact=True)
    vs = pd.read_csv(OUTPUTS / "validation" / "validation_sample.csv")
    vsum = read_json(OUTPUTS / "validation" / "validation_summary.json")
    write_json(WEB_DATA / "validation.json", dict(
        **stamp, status=vsum["annotations"]["status"], annotations=vsum["annotations"], rubric=vsum["rubric"],
        aspects=vsum["aspects"], values=vsum["values"],
        items=[dict(item_id=r.item_id, split=r.split, a=r.narrative_a, b=r.narrative_b) for r in vs.itertuples()]))
    manifest = read_json(RAW / "source_manifest.json")
    write_json(WEB_DATA / "sources.json", dict(**stamp, manifest=manifest, model=dict(
        name=cfg["semantic"]["model"], revision=cfg["semantic"]["revision"], licence="Apache-2.0",
        url=f"https://huggingface.co/{cfg['semantic']['model']}/tree/{cfg['semantic']['revision']}")))
    summary = dict(**stamp, generated=utc_now(), run=run_meta, counts=read_json(OUTPUTS / "audit" / "cohort_counts.json"),
                   audit=read_json(OUTPUTS / "audit" / "raw_audit.json")["brief_diagnostics"],
                   cleaning=read_json(OUTPUTS / "audit" / "raw_audit.json")["cleaning"],
                   lexical=read_json(OUTPUTS / "metrics" / "lexical_vocabulary.json"),
                   semantic=read_json(OUTPUTS / "metrics" / "semantic_representation.json"),
                   graphs=exported_graphs, primary=dict(density=cfg["graphs"]["primary_density"], seed=prim_seed),
                   config=dict(densities=cfg["graphs"]["densities"], seeds=seeds,
                               permutations=cfg["evaluation"]["permutations"],
                               balanced_cap=cfg["evaluation"]["balanced_subset"]["cap"]),
                   layouts=lay_meta, validation_status=vsum["annotations"]["status"],
                   full_texts_included=full_text, excerpt_words=EXCERPT_WORDS, public_build=public_build(),
                   opening=cfg.get("export", {}).get("opening_pair"),
                   story_pairs=cfg.get("export", {}).get("story_pairs", {}))
    write_json(WEB_DATA / "summary.json", summary)
    # Overview and Parables pages: results of the paper pipeline (`python -m ouaw.run --stage site` writes these committed
    # files, and web-sized copies of the paper's figures). Titles, labels and openings of at most 40 words; never full texts.
    for name in ("parables.json", "paper.json"):
        site_file = DATA / "site" / name
        if site_file.exists():
            write_json(WEB_DATA / name, {**read_json(site_file), **stamp}, compact=True)
    site_figures = DATA / "site" / "figures"
    if site_figures.exists():
        (WEB_DATA / "figures").mkdir(parents=True, exist_ok=True)
        for png in sorted(site_figures.glob("*.png")):
            (WEB_DATA / "figures" / png.name).write_bytes(png.read_bytes())
    files = {p.relative_to(WEB_DATA).as_posix(): dict(bytes=p.stat().st_size)
             for p in sorted(WEB_DATA.rglob("*")) if p.is_file() and "tales/" not in p.relative_to(WEB_DATA).as_posix()}
    write_json(WEB_DATA / "manifest.json", dict(**stamp, generated=utc_now(), tales=len(nar),
                                                full_texts_included=full_text, public_build=public_build(), files=files))
    total = sum(p.stat().st_size for p in WEB_DATA.rglob("*") if p.is_file())
    print(f"  exported run {run_id}: {len(nar)} tale files, {len(exported_graphs)} graphs, {total / 1e6:.1f} MB total "
          f"({'full texts' if full_text else f'excerpts only, first {EXCERPT_WORDS} words'})")
    return summary


if __name__ == "__main__":
    run()
