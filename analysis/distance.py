"""Stage 6: geographic distance versus textual similarity (distance cohort).

Great-circle distance with the haversine formula between documented
representative points (Natural Earth label points). Statistics use every
eligible pair; the permutation reference moves each tale's whole location as
one unit. Pairs share tales, so no independence-based p-values are reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .analyze import load_inputs
from .common import OUTPUTS, load_config, write_json, Timer
from .networks import similarity_matrix


def haversine_km(lat1, lon1, lat2, lon2, radius: float) -> np.ndarray:
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def spearman_from_ranks(rx: np.ndarray, ry: np.ndarray) -> float:
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    return float((rx * ry).sum() / np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))


def run() -> dict:
    cfg = load_config()
    dcfg = cfg["distance"]
    nar, reps = load_inputs()
    ids = np.flatnonzero(nar["in_distance"].to_numpy())
    sub = nar.loc[ids].reset_index(drop=True)
    lat, lon = sub["latitude"].to_numpy(float), sub["longitude"].to_numpy(float)
    locs, loc_idx = np.unique(np.stack([lat, lon], 1), axis=0, return_inverse=True)
    loc_idx = loc_idx.ravel()
    R = dcfg["earth_radius_km"]
    Dloc = haversine_km(locs[:, None, 0], locs[:, None, 1], locs[None, :, 0], locs[None, :, 1], R)
    n = len(ids)
    iu, ju = np.triu_indices(n, 1)
    dist = Dloc[loc_idx[iu], loc_idx[ju]]
    same_atu = (sub["atu_id"].to_numpy()[iu] == sub["atu_id"].to_numpy()[ju])
    bins = np.array(dcfg["bins_km"], dtype=float)
    labels = [f"{int(a)}–{int(b)} km" if a > 0 else "same point (0 km)" for a, b in zip(bins[:-1], bins[1:])]
    which = np.clip(np.searchsorted(bins, dist, side="right") - 1, 0, len(labels) - 1)

    out = dict(cohort_size=int(n), pairs=int(len(dist)), distinct_points=int(len(locs)),
               earth_radius_km=R, formula="haversine great-circle distance",
               coordinate_meaning="Natural Earth label point of the recorded country/territory; tales recorded in the same country share one point (distance 0).",
               bins=labels, results={})
    rng = np.random.default_rng(dcfg["permutation_seed"])
    perms = [rng.permutation(n) for _ in range(dcfg["permutations"])]
    for rep in ["lexical", "semantic"]:
        kind, data = reps[rep]
        S = similarity_matrix(kind, ids, data if kind == "lexical" else None, data if kind == "semantic" else None)
        sim = S[iu, ju]
        res = {}
        for subset, mask in (("all", np.ones_like(same_atu)), ("same_atu", same_atu), ("different_atu", ~same_atu)):
            rows = []
            for b in range(len(labels)):
                v = sim[mask & (which == b)]
                rows.append(dict(bin=labels[b], pairs=int(len(v)),
                                 mean=float(v.mean()) if len(v) else None,
                                 q25=float(np.quantile(v, .25)) if len(v) else None,
                                 median=float(np.median(v)) if len(v) else None,
                                 q75=float(np.quantile(v, .75)) if len(v) else None))
            res[subset] = dict(curve=rows, pairs=int(mask.sum()))
        with Timer(f"distance permutations {rep}"):
            rs = rankdata(sim)
            rho = spearman_from_ranks(rankdata(dist), rs)
            null = np.array([spearman_from_ranks(rankdata(Dloc[loc_idx[p][iu], loc_idx[p][ju]]), rs) for p in perms])
        res["spearman_rho"] = rho
        res["spearman_null"] = dict(mean=float(null.mean()), sd=float(null.std(ddof=1)),
                                    p2_5=float(np.quantile(null, .025)), p97_5=float(np.quantile(null, .975)),
                                    min=float(null.min()), max=float(null.max()),
                                    share_at_least_as_negative=float((1 + (null <= rho).sum()) / (1 + len(null))),
                                    values=null.round(5).tolist())
        same_point = which == 0
        res["mean_similarity_same_point"] = float(sim[same_point].mean())
        res["mean_similarity_different_point"] = float(sim[~same_point].mean())
        out["results"][rep] = res

    # deterministic display sample: all same-ATU pairs plus a random sample of the rest
    rng = np.random.default_rng(dcfg["display_sample_seed"])
    same_idx = np.flatnonzero(same_atu)
    other = np.flatnonzero(~same_atu)
    take = np.sort(np.concatenate([same_idx, rng.choice(other, dcfg["display_sample_pairs"], replace=False)]))
    S_lex = similarity_matrix("lexical", ids, reps["lexical"][1], None)
    S_sem = similarity_matrix("semantic", ids, None, reps["semantic"][1])
    sample = pd.DataFrame(dict(a=sub["narrative_id"].to_numpy()[iu[take]], b=sub["narrative_id"].to_numpy()[ju[take]],
                               km=dist[take].round(1), lexical=S_lex[iu[take], ju[take]].round(4),
                               semantic=S_sem[iu[take], ju[take]].round(4), same_atu=same_atu[take]))
    sample.to_csv(OUTPUTS / "metrics" / "distance_display_sample.csv", index=False)
    out["display_sample"] = dict(pairs=int(len(take)), same_atu_pairs_all_included=int(len(same_idx)),
                                 random_other_pairs=int(dcfg["display_sample_pairs"]), seed=dcfg["display_sample_seed"])
    write_json(OUTPUTS / "metrics" / "distance.json", out)
    for rep in ("lexical", "semantic"):
        r = out["results"][rep]
        print(f"  distance {rep}: rho={r['spearman_rho']:.3f} (location-shuffle mean {r['spearman_null']['mean']:.3f}, "
              f"range {r['spearman_null']['min']:.3f}..{r['spearman_null']['max']:.3f})")
    return out


if __name__ == "__main__":
    run()
