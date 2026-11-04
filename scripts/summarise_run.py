"""Print the headline numbers of the current pipeline run (all read from outputs/).

Usage: uv run python scripts/summarise_run.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "outputs" / "metrics"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    run = load(M / "run.json")
    counts = load(ROOT / "outputs/audit/cohort_counts.json")
    graphs = {g["graph_id"]: g for g in load(M / "graphs.json")["graphs"]}
    rows = load(M / "agreement.json")["rows"]
    neigh = load(M / "neighbours.json")["results"]
    mnull = load(M / "modularity_null.json")["results"] if (M / "modularity_null.json").exists() else {}
    dist = load(M / "distance.json")
    val = load(ROOT / "outputs/validation/validation_summary.json")
    out = [f"Run {run['run_id']} (created {run['created']})", ""]
    out.append("Cohorts: raw {raw_records} -> usable narratives {text_cohort} -> ATU {atu_cohort} -> joint {joint_cohort} "
               "-> distance {distance_cohort}; joint covers {joint_distinct_atu} ATU types, {joint_distinct_place} places, "
               "{joint_distinct_region} regions".format(**counts))
    out.append("")
    for rep in ("lexical", "semantic"):
        gid = f"joint-{rep}-d10"
        g = graphs[gid]
        p = g["partitions"]["42"]
        mn = mnull.get(gid)
        out.append(f"{rep} 10% (seed 42): {p['communities']} communities, Q {p['modularity']:.3f}"
                   + (f" vs degree-preserving null {mn['null_mean']:.3f}±{mn['null_sd']:.3f}" if mn else "")
                   + f"; isolates {len(g['isolates'])}; seed NMI {', '.join(f'{v:.2f}' for v in g['seed_agreement_nmi'].values())}")
        for lab in ("atu", "place", "region", "source"):
            r = next(x for x in rows if x["graph_id"] == gid and x["seed"] == 42 and x["label"] == lab)
            nb = neigh[f"joint|{rep}"].get(lab)
            out.append(f"   {lab:7s} NMI {r['nmi']['observed']:.3f} (shuffle mean {r['nmi']['null_mean']:.3f}, excess {r['nmi']['excess']:.3f}; "
                       f"beats all 1000: {r['nmi']['exceeds_all']}) | assortativity {r['assortativity']['observed']:.3f} "
                       f"(shuffle mean {r['assortativity']['null_mean']:.4f})"
                       + (f" | top-10 lift {nb['lift']:.1f}x (excl. same source {nb['lift_excl_same_source']:.1f}x)" if nb else ""))
    # robustness tally with the pre-declared rule
    by = {}
    for r in rows:
        by.setdefault((r["graph_id"], r["seed"]), {})[r["label"]] = r
    tally = dict(settings=0, all_beat=0, type_top_nmi=0, type_top_lift=0, cons_place=0, cons_region=0)
    for (gid, s), d in by.items():
        a, pl, rg = d["atu"], d["place"], d["region"]
        nb = neigh.get(f"{a['cohort']}|{a['rep']}")
        lift = lambda lab: nb[lab]["lift"]
        v = lambda x, lab: (x["nmi"]["excess"], x["assortativity"]["observed"], lift(lab))
        va, vp, vr = v(a, "atu"), v(pl, "place"), v(rg, "region")
        tally["settings"] += 1
        tally["all_beat"] += all(x["nmi"]["exceeds_all"] and x["assortativity"]["exceeds_all"] for x in (a, pl, rg))
        tally["type_top_nmi"] += va[0] > max(vp[0], vr[0])
        tally["type_top_lift"] += va[2] > max(vp[2], vr[2])
        sp = [va[i] > vp[i] for i in range(3)]
        sr = [va[i] > vr[i] for i in range(3)]
        tally["cons_place"] += all(sp) or not any(sp)
        tally["cons_region"] += all(sr) or not any(sr)
    out.append("")
    out.append("Robustness over {settings} joint-cohort settings (density x seed, representation and cohort variants): "
               "all three labels beat every shuffle in {all_beat}; ATU has the largest NMI excess in {type_top_nmi} and the "
               "largest neighbour lift in {type_top_lift}; pre-declared verdict consistent for type vs place in {cons_place}, "
               "for type vs region in {cons_region} (otherwise mixed).".format(**tally))
    out.append("")
    for rep in ("lexical", "semantic"):
        d = dist["results"][rep]
        n = d["spearman_null"]
        out.append(f"Distance ({rep}): Spearman rho {d['spearman_rho']:.3f} vs whole-location shuffles {n['min']:.3f}..{n['max']:.3f} "
                   f"(mean {n['mean']:.3f}); same-ATU pairs mean similarity by bin "
                   + ", ".join(f"{c['mean']:.2f}" for c in d["same_atu"]["curve"])
                   + "; different-ATU " + ", ".join(f"{c['mean']:.2f}" for c in d["different_atu"]["curve"]))
    out.append("")
    out.append(f"Validation: {val['items']} items ({val['development_items']} development, {val['final_items']} final); status {val['annotations']['status']}")
    text = "\n".join(out)
    print(text)
    return text


if __name__ == "__main__":
    main()
