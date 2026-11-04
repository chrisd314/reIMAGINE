"""Checks on the actual pipeline outputs (brief §16): data, representations, graphs, evaluation, export.

Run after `python -m analysis all`. Tests are skipped if an output is missing.
"""
import base64
import json
import re
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
from sklearn.metrics import normalized_mutual_info_score

ROOT = Path(__file__).resolve().parent.parent
RAW, INTERIM, PROCESSED, OUT = ROOT / "data/raw", ROOT / "data/interim", ROOT / "data/processed", ROOT / "outputs"
WEB = ROOT / "web/public/data"
LEAK = re.compile(r"Aarne|\bATU\b|[Tt]ale[- ]type|\btypes? \d{1,4}[A-Z]?\b|Ashliman|folktexts|Return to|\bSource:")


def need(*paths):
    for p in paths:
        if not Path(p).exists():
            pytest.skip(f"missing output {p}")


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- data
def test_raw_file_is_pinned_and_hashed():
    need(RAW / "source_manifest.json")
    from analysis.common import sha256_file
    man = load_json(RAW / "source_manifest.json")
    entry = next(e for e in man["files"] if e["filename"] == "trilogy/aft.csv")
    assert man["trilogy_commit"] in entry["url"] and entry["version"] == man["trilogy_commit"]
    assert sha256_file(RAW / "trilogy/aft.csv") == entry["sha256"]
    for e in man["files"]:
        assert {"url", "version", "retrieved_at", "sha256", "bytes", "format", "citation", "stated_licence", "role"} <= set(e)


def test_audit_reproduces_brief_diagnostics():
    need(OUT / "audit/raw_audit.json")
    checks = load_json(OUT / "audit/raw_audit.json")["brief_diagnostics"]
    assert all(c["match"] for c in checks.values()), checks


def test_review_and_mapping_files_are_well_formed():
    review = pd.read_csv(ROOT / "data/mappings/text_review.csv", dtype=str, keep_default_na=False)
    assert list(review.columns) == ["record_id", "action", "pattern", "reason", "reviewer", "reviewed_on"]
    assert set(review["action"]) <= {"exclude", "trim_before", "trim_from", "strip_suffix", "flag_fragment", "keep", "no_auto_tail"}
    assert (review["reason"].str.len() > 10).all(), "every decision needs a reason"
    pm = pd.read_csv(ROOT / "data/mappings/provenance_map.csv", dtype=str, keep_default_na=False)
    required = ["raw_provenance", "normalised_label", "entity_kind", "country_code_if_applicable", "broad_region",
                "latitude", "longitude", "coordinate_meaning", "confidence", "evidence_url_or_source", "rationale",
                "review_status"]
    assert set(required) <= set(pm.columns)


def test_ids_traceable_and_ledger_complete():
    need(INTERIM / "records.parquet", PROCESSED / "narratives.parquet", OUT / "audit/inclusion_ledger.csv")
    rec = pd.read_parquet(INTERIM / "records.parquet")
    raw = pd.read_csv(RAW / "trilogy/aft.csv", dtype=str, keep_default_na=False, na_values=[])
    assert len(rec) == len(raw) and rec["record_id"].is_unique
    assert (rec["source_row"] == np.arange(1, len(raw) + 1)).all()
    assert (rec["text_raw"].to_numpy() == raw["text"].to_numpy()).all(), "raw strings must be preserved"
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    members = [r for ids in nar["record_ids"] for r in ids]
    assert len(members) == len(set(members)) == (rec["excluded_reason"] == "").sum()
    for nid, ids in zip(nar["narrative_id"], nar["record_ids"]):
        assert nid == f"tale-{min(int(i.rsplit('-', 1)[1]) for i in ids):04d}"
    led = pd.read_csv(OUT / "audit/inclusion_ledger.csv")
    assert len(led) == len(raw) and set(led["record_id"]) == set(rec["record_id"])


def test_duplicate_and_conflict_policy():
    need(PROCESSED / "narratives.parquet")
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    assert nar["text"].is_unique, "identical narrative texts are represented once"
    conflict = nar["atu_status"] == "conflict"
    assert conflict.sum() > 0 and not nar.loc[conflict, "in_atu"].any()
    assert nar.loc[conflict, "in_text"].all(), "label conflicts stay in the text cohort"
    assert (nar.loc[nar["in_atu"], "atu_ids"].map(len) == 1).all()


def test_model_input_is_narrative_text_only():
    need(PROCESSED / "narratives.parquet", INTERIM / "lexical_vocab.parquet")
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    leaked = nar[nar["text"].str.contains(LEAK)]
    assert leaked.empty, f"classification or site text left in: {leaked['narrative_id'].tolist()[:5]}"
    vocab = set(pd.read_parquet(INTERIM / "lexical_vocab.parquet")["term"])
    assert not {"aarne", "ashliman", "folktexts", "atu"} & vocab
    assert {"not", "no", "never"} <= vocab, "negation must be preserved"


def test_tfidf_rows_rebuild_from_text_only():
    need(INTERIM / "lexical_tfidf.npz")
    from analysis.common import load_config
    from analysis.lexical import fit
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    X = sp.load_npz(INTERIM / "lexical_tfidf.npz").tocsr()
    _, X2, _ = fit(nar["text"].tolist(), load_config()["lexical"])
    assert abs(X - X2).max() < 1e-12


def test_chunks_fit_encoder_and_vectors_valid():
    need(INTERIM / "semantic_chunks.parquet", INTERIM / "semantic_vectors.npz")
    ch = pd.read_parquet(INTERIM / "semantic_chunks.parquet")
    assert (ch["n_tokens"] <= 256).all()
    assert (ch.loc[ch["setting"] == "c200", "n_tokens"] <= 200).all()
    assert (ch.loc[ch["setting"] == "c128", "n_tokens"] <= 128).all()
    z = np.load(INTERIM / "semantic_vectors.npz")
    for k in ("c200_mean", "c200_tokw", "c128_mean"):
        v = z[k]
        assert v.shape[1] == 384 and np.isfinite(v).all()
        assert np.allclose(np.linalg.norm(v, axis=1), 1, atol=1e-6)
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    assert set(ch["narrative_id"]) == set(nar["narrative_id"]), "every tale is encoded"


def test_similarity_matrices_symmetric_with_unit_diagonal():
    need(INTERIM / "lexical_tfidf.npz", INTERIM / "semantic_vectors.npz")
    from analysis.analyze import load_inputs
    from analysis.networks import similarity_matrix
    nar, reps = load_inputs()
    idx = np.flatnonzero(nar["in_joint"].to_numpy())[:300]
    for name in ("lexical", "semantic"):
        kind, data = reps[name]
        S = similarity_matrix(kind, idx, data if kind == "lexical" else None, data if kind == "semantic" else None)
        assert np.allclose(S, S.T, atol=1e-12) and np.allclose(np.diag(S), 1)
        assert S.max() <= 1 + 1e-9
        if name == "lexical":
            assert S.min() >= -1e-12


def test_unknown_geography_stays_unknown_and_coordinates_valid():
    need(PROCESSED / "narratives.parquet")
    pm = pd.read_csv(ROOT / "data/mappings/provenance_map.csv", dtype=str, keep_default_na=False)
    nogeo = pm["entity_kind"].isin(["author", "collection", "unknown"])
    assert (pm.loc[nogeo, ["place_label", "broad_region", "latitude"]] == "").all().all()
    aesop = pm[pm["raw_provenance"] == "Aesop"].iloc[0]
    grimm = pm[pm["raw_provenance"] == "Jacob and Wilhelm Grimm"].iloc[0]
    assert aesop["place_label"] == "" and grimm["place_label"] == "", "authors are not story-origin places"
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    outside = nar[nar["in_atu"] & ~nar["in_joint"]]
    assert len(outside) > 0 and (outside["geo_status"] != "unique").all(), "tales left out for geography must lack a unique place"
    assert outside["latitude"].isna().all(), "no coordinates for tales without defensible geography"
    lat, lon = nar["latitude"].dropna(), nar["longitude"].dropna()
    assert lat.between(-90, 90).all() and lon.between(-180, 180).all()
    assert nar.loc[nar["in_distance"], "latitude"].notna().all()


def test_known_great_circle_distance():
    from analysis.distance import haversine_km
    R = 6371.0088
    assert haversine_km(0.0, 0.0, 0.0, 1.0, R) == pytest.approx(2 * np.pi * R / 360, rel=1e-9)
    assert haversine_km(0.0, 0.0, 0.0, 180.0, R) == pytest.approx(np.pi * R, rel=1e-9)
    assert haversine_km(51.5074, -0.1278, 48.8566, 2.3522, R) == pytest.approx(343.5, abs=2)  # London-Paris


# ---------------------------------------------------------------- graphs and evaluation
@pytest.fixture(scope="module")
def graphs_meta():
    need(OUT / "metrics/graphs.json")
    return {g["graph_id"]: g for g in load_json(OUT / "metrics/graphs.json")["graphs"]}


def test_saved_graphs_obey_construction_rules(graphs_meta):
    for gid, meta in graphs_meta.items():
        z = np.load(INTERIM / "graphs" / f"{gid}.npz")
        i, j = z["i"], z["j"]
        n = len(z["nodes"])
        assert (i < j).all(), f"{gid}: self-loop or unordered pair"
        assert len(set(zip(i.tolist(), j.tolist()))) == len(i), f"{gid}: repeated edge"
        assert meta["m"] == len(i) and meta["n"] == n
        assert meta["density_achieved"] == pytest.approx(len(i) / (n * (n - 1) / 2))
        assert abs(meta["density_achieved"] - meta["density"]) < 1e-5
        for s, part in meta["partitions"].items():
            p = z[f"seed{s}"]
            assert len(p) == n and part["communities"] == p.max() + 1 and sum(part["sizes"]) == n


def test_edges_are_the_strongest_pairs_with_declared_scores(graphs_meta):
    from analysis.analyze import load_inputs, cohort_indices
    from analysis.common import load_config
    from analysis.networks import similarity_matrix
    nar, reps = load_inputs()
    idx = cohort_indices(nar, load_config())["joint"]
    for rep in ("lexical", "semantic"):
        z = np.load(INTERIM / "graphs" / f"joint-{rep}-d10.npz")
        assert z["nodes"].tolist() == nar.loc[idx, "narrative_id"].tolist()
        kind, data = reps[rep]
        S = similarity_matrix(kind, idx, data if kind == "lexical" else None, data if kind == "semantic" else None)
        assert np.allclose(S[z["i"], z["j"]], z["w"], atol=1e-12)
        mask = np.zeros_like(S, dtype=bool)
        mask[z["i"], z["j"]] = True
        iu, ju = np.triu_indices(len(idx), 1)
        outside = ~mask[iu, ju]
        assert S[iu, ju][outside].max() <= z["w"].min() + 1e-12


def test_label_comparisons_share_one_cohort_and_match_recomputation(graphs_meta):
    need(OUT / "metrics/agreement.json")
    rows = load_json(OUT / "metrics/agreement.json")["rows"]
    nar = pd.read_parquet(PROCESSED / "narratives.parquet").set_index("narrative_id")
    for gid in ("joint-lexical-d10", "joint-semantic-d10"):
        z = np.load(INTERIM / "graphs" / f"{gid}.npz")
        sub = nar.loc[z["nodes"]]
        assert sub["in_joint"].all() and len(sub) == graphs_meta[gid]["n"]
        G = nx.Graph()
        G.add_nodes_from(range(len(sub)))
        G.add_weighted_edges_from(zip(z["i"].tolist(), z["j"].tolist(), z["w"].tolist()))
        p = z["seed42"]
        comms = [set(np.flatnonzero(p == k).tolist()) for k in range(p.max() + 1)]
        q = nx.community.modularity(G, comms, weight="weight")
        assert q == pytest.approx(graphs_meta[gid]["partitions"]["42"]["modularity"], abs=1e-9)
        for lab, col in (("atu", "atu_id"), ("place", "place_label"), ("region", "broad_region")):
            row = next(r for r in rows if r["graph_id"] == gid and r["seed"] == 42 and r["label"] == lab)
            nmi = normalized_mutual_info_score(sub[col].to_numpy(), p)
            assert nmi == pytest.approx(row["nmi"]["observed"], abs=1e-9)
            nx.set_node_attributes(G, dict(enumerate(sub[col].tolist())), "lab")
            r = nx.attribute_assortativity_coefficient(G, "lab")
            assert r == pytest.approx(row["assortativity"]["observed"], abs=1e-9)
            # (1 + #shuffles >= observed) / (1 + N): exactly 1/1001 when no shuffle reaches the observed value
            if row["nmi"]["exceeds_all"]:
                assert row["nmi"]["p_upper"] == pytest.approx(1 / 1001)


def test_validation_pending_without_annotations():
    need(OUT / "validation/validation_summary.json")
    summary = load_json(OUT / "validation/validation_summary.json")
    files = list((OUT / "validation/annotations").glob("*.csv"))
    assert (summary["annotations"]["status"] == "pending") == (len(files) == 0)
    sample = pd.read_csv(OUT / "validation/validation_sample.csv")
    assert len(sample) == summary["items"] and sample["item_id"].is_unique
    counts = pd.concat([sample["narrative_a"], sample["narrative_b"]]).value_counts()
    assert counts.max() <= 2


# ---------------------------------------------------------------- export
def test_web_payloads_share_one_run_and_match_pipeline():
    need(WEB / "manifest.json", OUT / "metrics/run.json")
    run_id = load_json(OUT / "metrics/run.json")["run_id"]
    for p in [WEB / "manifest.json", WEB / "summary.json", WEB / "agreement.json", WEB / "catalogue.json",
              *sorted((WEB / "graphs").glob("*.json"))[:4], *sorted((WEB / "tales").glob("*.json"))[:5]]:
        assert load_json(p)["run_id"] == run_id, p
    summary = load_json(WEB / "summary.json")
    assert summary["counts"] == load_json(OUT / "audit/cohort_counts.json")
    # fields the website reads from every graph entry (a stale export once lacked them)
    need_fields = {"graph_id", "group", "cohort", "rep", "density", "n", "m", "isolates", "communities", "modularity",
                   "seed_agreement_nmi", "modularity_null"}
    for g in summary["graphs"]:
        assert need_fields <= set(g), f"summary graph entry {g.get('graph_id')} lacks {need_fields - set(g)}"
    main = [g for g in summary["graphs"] if g["group"] == "main"]
    assert main and all(g["modularity_null"] is not None for g in main), "modularity null missing for a main graph"
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    assert summary["counts"]["joint_cohort"] == int(nar["in_joint"].sum())


def test_exported_vectors_reproduce_pipeline_scores():
    need(WEB / "tales/tale-0086.json")
    a, b = load_json(WEB / "tales/tale-0086.json"), load_json(WEB / "tales/tale-0087.json")
    dec = lambda s: np.frombuffer(base64.b64decode(s), dtype="<f4").astype(np.float64)
    from analysis.analyze import load_inputs
    from analysis.networks import similarity_matrix
    nar, reps = load_inputs()
    ia, ib = [int(np.flatnonzero(nar["narrative_id"] == t)[0]) for t in ("tale-0086", "tale-0087")]
    S_sem = similarity_matrix("semantic", np.array([ia, ib]), None, reps["semantic"][1])
    S_lex = similarity_matrix("lexical", np.array([ia, ib]), reps["lexical"][1], None)
    assert dec(a["vector"]) @ dec(b["vector"]) == pytest.approx(S_sem[0, 1], abs=1e-5)
    wa = dict(a["tfidf"])
    lex = sum(w * wa[t] for t, w in b["tfidf"] if t in wa)
    assert lex == pytest.approx(S_lex[0, 1], abs=1e-4)
    nb = dict((x[0], x[1]) for x in a["neighbours"]["joint"]["semantic"])
    if "tale-0087" in nb:
        assert nb["tale-0087"] == pytest.approx(S_sem[0, 1], abs=1e-6)
