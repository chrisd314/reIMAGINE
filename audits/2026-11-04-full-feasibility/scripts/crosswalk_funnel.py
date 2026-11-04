"""Pilot A: rule-based screening of every candidate link, agreement with the hand review, coverage funnel and
the region/religion overlap diagnostic. Descriptive only: no association between religion and motifs is computed.
"""
import itertools
import math
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pairs = pd.read_csv("crosswalk/crosswalk_candidate_pairs.csv", low_memory=False)
rev = pd.read_csv("crosswalk/crosswalk_reviewed.csv")
POOLED = re.compile(r",|\band\b|\b(district|islands?|land|papuans|region|coast)\b", re.I)
PERIOD = re.compile(r"\bancient\b|\bAD\b|\bBC\b|\d{3,4}\s*-\s*\d{3,4}", re.I)


def year(v):
    try:
        return float(str(v).split("..")[0])
    except ValueError:
        return float("nan")


def screen(r):
    routes = set(str(r.routes).split("+"))
    name = str(r.berezkin_name)
    shared_name = "name" in routes
    if "name" not in routes and "ea" not in routes:
        ident = "rejected"  # proximity alone never establishes identity
    elif pd.notna(r.distance_km) and r.distance_km > 1000:
        ident = "rejected"
    elif POOLED.search(name):
        ident = "unresolved"
    elif not shared_name:
        ident = "unresolved"  # published EA assignment without a shared name: identity not shown
    else:
        ident = "validated"
    fy, fp = year(r.t_focal_year), r.year_firstpub
    if PERIOD.search(name) and fy >= 1800 or (fy < 1500 and not PERIOD.search(name)):
        t = "incompatible"
    elif pd.isna(fp) or math.isnan(fy):
        t = "unclear"
    else:
        t = "compatible" if fy >= fp - 50 else "incompatible"
    final = "validated" if ident == "validated" and t == "compatible" else ("rejected" if ident == "rejected" or t == "incompatible" else "unresolved")
    return pd.Series(dict(rule_identity=ident, rule_time=t, rule_final=final))


pairs = pd.concat([pairs, pairs.apply(screen, axis=1)], axis=1)
pairs.to_csv("crosswalk/crosswalk_candidate_pairs_screened.csv", index=False)
out = []

# --- rule vs hand review on the 30 sampled links
m = rev.merge(pairs[["target", "berezkin_name", "target_id", "rule_final"]].astype({"target_id": str}),
              left_on=["target", "berezkin_name", rev.target_id.astype(str)], right_on=["target", "berezkin_name", "target_id"], how="left")
ct = pd.crosstab(m.final_status, m.rule_final)
out.append("Hand review (rows) vs rule screen (columns) on the 30 reviewed links:\n" + ct.to_string())

# --- family mapping for SCCS2002
FAM = {"0": "Indigenous", "1": "Islam", "3": "Islam", "2": "Christianity", "4": "Christianity", "5": "Buddhism", "6": "Buddhism", "7": "Buddhism", "8": "Hinduism"}
DEPTH = {"1": "deep", "2": "deep", "3": "superficial", "4": "superficial"}
sc = pairs[pairs.target == "SCCS"].copy()
sc["code"] = sc.religion_code.astype(str).str.extract(r"^(\d)")[0]
sc["family"] = sc.code.map(FAM)
sc["branch"] = sc.code.map({"5": "Mahayana", "6": "Hinayana/Theravada", "7": "Vajrayana"})
sc["depth"] = sc.code.map(DEPTH)

# --- funnel on the coordinate snapshot (macleginn, 926 traditions)
bz = pd.read_csv("downloads/gh_mythq/berezkin_new.csv", sep="\t", low_memory=False)
meta = ["idn", "groups", "latit", "longit", "sum", "cosm_mot", "areas1", "AREA2", "areas3", "lang1", "lang2", "lang3"]
mot = [c for c in bz.columns if c not in meta]
nm = (bz[mot] > 0).sum(axis=1)
names = set(bz.groups)
ok10 = set(bz.groups[nm >= 10])
named = lambda df: df[df.routes.str.split("+").map(lambda r: bool({"name", "ea"} & set(r)))]
anycand = set(named(pairs[pairs.berezkin_name.isin(names)]).berezkin_name)
v = sc[(sc.rule_identity == "validated") & sc.berezkin_name.isin(names)]
v_coded = v[v.family.notna()]
v_world = v_coded[v_coded.family != "Indigenous"]
v_deep = v_world[(v_world.depth != "superficial")]
v_branch = v_world[v_world.branch.notna()]
v_time = v_world[v_world.rule_time == "compatible"]
final = v_time[v_time.berezkin_name.isin(ok10)]
final_ind = v_coded[(v_coded.family == "Indigenous") & (v_coded.rule_time == "compatible") & v_coded.berezkin_name.isin(ok10)]
pu = pairs[(pairs.target == "Pulotu") & pairs.berezkin_name.isin(names)]
dr = pairs[(pairs.target == "DRH(eHRAF)") & pairs.berezkin_name.isin(names)]
f = [
    ("Berezkin traditions in the coordinate snapshot (macleginn, 926 x 2,138)", len(names)),
    ("... with a motif profile of at least 10 motifs", len(ok10)),
    ("... with an interpretable location (area centroid, mostly whole/half degree)", int(bz.latit.notna().sum())),
    ("... with any candidate link to a religion-coded record by name or published EA assignment (SCCS, Pulotu, DRH)", len(anycand)),
    ("... with a rule-validated identity link to an SCCS society", v.berezkin_name.nunique()),
    ("... whose SCCS society has a SCCS2002 code (any, incl. indigenous)", v_coded.berezkin_name.nunique()),
    ("... coded with a world religion (deep or superficial; Buddhist; Hindu)", v_world.berezkin_name.nunique()),
    ("... world religion excluding 'superficial' Christianization/Islamization", v_deep.berezkin_name.nunique()),
    ("... with a branch-level label (Buddhist branches only)", v_branch.berezkin_name.nunique()),
    ("... world-religion links that also pass the time check", v_time.berezkin_name.nunique()),
    ("... and have >= 10 motifs (final world-religion sample)", final.berezkin_name.nunique()),
    ("comparison group: rule-validated, time-compatible, indigenous-coded, >= 10 motifs", final_ind.berezkin_name.nunique()),
    ("Pulotu name candidates (traditions); identity still to be checked", pu.berezkin_name.nunique()),
    ("DRH eHRAF-entry name candidates (traditions); no world-religion affiliation field", dr.berezkin_name.nunique()),
]
out.append("\nCoverage funnel (rule screen; hand review suggests about half of world-religion candidates survive):")
out += [f"  {n:5d}  {lab}" for lab, n in f]
fin = pd.concat([final.assign(group="world religion"), final_ind.assign(group="indigenous")])
fin.to_csv("crosswalk/final_sample_rule_screen.csv", index=False)
out.append("\nFinal rule-screened sample by SCCS region and religion family:")
out.append(pd.crosstab(fin.t_region, fin.family, margins=True).to_string())
out.append("\nWorld-religion part by depth/branch: " + str(final.assign(k=final.family + ":" + final.depth.fillna(final.branch.fillna(""))).k.value_counts().to_dict()))


def hav(a, b):
    p1, p2 = math.radians(a.t_lat), math.radians(b.t_lat)
    dp, dl = p2 - p1, math.radians(b.t_lon - a.t_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


one = fin.drop_duplicates("berezkin_name")
rows = []
for (_, a), (_, b) in itertools.combinations(one.iterrows(), 2):
    d = hav(a, b)
    band = "<500 km" if d < 500 else "500-1500 km" if d < 1500 else "1500-3000 km" if d < 3000 else ">3000 km"
    rows.append(dict(band=band, same_family=a.family == b.family, both_world=(a.family != "Indigenous") and (b.family != "Indigenous"),
                     world_pair=f"{min(a.family, b.family)}-{max(a.family, b.family)}"))
pp = pd.DataFrame(rows)
order = ["<500 km", "500-1500 km", "1500-3000 km", ">3000 km"]
out.append(f"\nPairs among the {len(one)} final traditions by distance band (SCCS coordinates):")
out.append(pd.crosstab(pp.band, pp.same_family.map({True: "same family", False: "different family"})).reindex(order).to_string())
ww = pp[pp.both_world]
out.append("\nPairs where both traditions carry a world religion:")
out.append(pd.crosstab(ww.band, ww.same_family.map({True: "same family", False: "different family"})).reindex(order).fillna(0).astype(int).to_string())
out.append("\nDifferent-family world-religion pairs closer than 1500 km: " + str(ww[(~ww.same_family) & ww.band.isin(order[:2])].world_pair.value_counts().to_dict()))
txt = "\n".join(out)
print(txt)
open("pilots/a_join/pilot_a_summary.txt", "w", encoding="utf-8").write(txt + "\n")
