"""Pilot A: generate candidate links between Berezkin folklore traditions and religion-coded societies.

Inputs (downloads/, read as data only):
  * macleginn/mythology-queries berezkin_new.csv: 926 traditions x 2,138 motifs, with coordinates
  * Michalopoulos & Xue (2021) Motifs_Berezkin_groups.dta: 958 traditions (Oct 2019 catalogue) with
    documentation metadata, and Motifs_EA_groups.dta: their assignment of EA groups to Berezkin traditions
  * D-PLACE SCCS (186 societies; SCCS2002 'World Religions', Rosenblatt et al. 2011) and EA societies (xd_id)
  * Pulotu (137 Austronesian cultures) and DRH/SCCSR entries derived from eHRAF
Candidate routes, kept separate so each link's evidence is visible:
  name   - a normalised Berezkin name part equals a normalised society name or listed alternative name
  ea     - Michalopoulos & Xue assign an EA group to the tradition, and that EA group is the same D-PLACE
           cross-dataset society (xd_id) as an SCCS society
  near   - (SCCS only) nearest SCCS society within 250 km, listed for review, never accepted automatically
Nothing here decides identity: the output is reviewed by hand (crosswalk_reviewed.csv).
"""
import json
import math
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
A = Path(sys.argv[1])
D = A / "downloads"
OUT = A / "crosswalk"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parts(name):
    """Name variants: the whole string, comma/slash/semicolon parts, and parenthesised aliases."""
    name = str(name)
    out = {norm(name)}
    for p in re.split(r"[,;/]| and |\(|\)", name):
        if norm(p):
            out.add(norm(p))
    return {p for p in out if len(p) >= 3}


def hav(lat1, lon1, lat2, lon2):
    if any(pd.isna(x) for x in (lat1, lon1, lat2, lon2)):
        return float("nan")
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


# ---- Berezkin traditions: macleginn snapshot (coordinates) + M&X Oct-2019 snapshot (documentation metadata)
bz = pd.read_csv(D / "gh_mythq/berezkin_new.csv", sep="\t", low_memory=False)
meta = ["idn", "groups", "latit", "longit", "sum", "cosm_mot", "areas1", "AREA2", "areas3", "lang1", "lang2", "lang3"]
mot = [c for c in bz.columns if c not in meta]
bz["n_motifs"] = (bz[mot] > 0).sum(axis=1)
bz = bz[["idn", "groups", "latit", "longit", "n_motifs", "areas1", "AREA2", "lang1", "lang2"]].rename(
    columns={"groups": "berezkin_name", "latit": "b_lat", "longit": "b_lon", "lang1": "b_family", "lang2": "b_branch"})
mx = pd.read_stata(D / "dataverse_mx/extracted/Motifs_Berezkin_groups.dta",
                   columns=["oid", "group_Berezkin", "motifs_total", "nmbr_title", "year_firstpub", "year_avgpub"])
mx["key"] = mx.group_Berezkin.map(norm)
bz["key"] = bz.berezkin_name.map(norm)
both = bz.merge(mx, on="key", how="outer", indicator=True)
snap = both["_merge"].value_counts().to_dict()
bz = bz.merge(mx.drop(columns=["group_Berezkin"]), on="key", how="left")

# ---- SCCS societies with world-religion codes
sccs = pd.read_csv(D / "gh_sccs/societies.csv")
rel = pd.read_csv(A / "evidence/sccs_religion_wide.csv")
sccs = sccs.merge(rel[["xd_id", "SCCS2002", "SCCS2001", "SCCS1997", "family"]], on="xd_id", how="left")
sccs["names"] = sccs.apply(lambda r: parts(r.Name) | set().union(*[parts(x) for x in re.split(r"[;,]", str(r.alt_names_by_society)) if x and x != "nan"] or [set()]), axis=1)

# ---- EA societies (for the Michalopoulos & Xue route)
ea = pd.read_csv(D / "gh_ea/societies.csv")
# EA names: preferred name, the name used in the source (without its code) and listed alternatives
ea_keys = []
for _, r in ea.iterrows():
    ks = {norm(r.Name), norm(re.sub(r"\(.*?\)", "", str(r.Name_and_ID_in_source)))}
    ks |= {norm(x) for x in re.split(r"[;,]", str(r.alt_names_by_society)) if x and x != "nan"}
    ea_keys += [dict(key=k, ea_id=r.ID, ea_name=r.Name, xd_id=r.xd_id) for k in ks if k]
ea_keys = pd.DataFrame(ea_keys).drop_duplicates(["key", "ea_id"])
ambiguous = ea_keys.groupby("key").ea_id.nunique()
ea_keys = ea_keys[ea_keys.key.isin(ambiguous[ambiguous == 1].index)]  # a name that points to two EA societies is not used
mxea = pd.read_stata(D / "dataverse_mx/extracted/Motifs_EA_groups.dta", columns=["atlas", "oid", "group_Berezkin"])
mxea["key"] = mxea.atlas.map(norm)
mxea = mxea.merge(ea_keys, on="key", how="left")
ea_unmatched = int(mxea.ea_id.isna().sum())

rows = []
# name route
for _, b in bz.iterrows():
    bn = parts(b.berezkin_name)
    for _, s in sccs.iterrows():
        hit = bn & s.names
        if hit:
            rows.append(dict(route="name", evidence="name part(s) equal: " + "; ".join(sorted(hit)), **b.to_dict(),
                             target="SCCS", target_id=s.ID, target_name=s.Name, target_alt=str(s.alt_names_by_society)[:120],
                             t_lat=s.Latitude, t_lon=s.Longitude, t_family=s.family, t_region=s.region, t_focal_year=s.main_focal_year,
                             religion_code=s.SCCS2002, deep_code=s.SCCS2001, christian_influence=s.SCCS1997, xd_id=s.xd_id))
# EA route
sccs_by_xd = sccs.set_index("xd_id")
for _, e in mxea.dropna(subset=["xd_id"]).iterrows():
    if e.xd_id in sccs_by_xd.index:
        s = sccs_by_xd.loc[e.xd_id]
        b = bz[bz.oid == e.oid]
        bd = b.iloc[0].to_dict() if len(b) else dict(oid=e.oid, berezkin_name=e.group_Berezkin)
        rows.append(dict(route="ea", evidence=f"M&X assign EA '{e.atlas}' to this tradition; EA {e.ea_id} shares xd_id {e.xd_id} with SCCS", **bd,
                         target="SCCS", target_id=s.ID, target_name=s.Name, target_alt=str(s.alt_names_by_society)[:120],
                         t_lat=s.Latitude, t_lon=s.Longitude, t_family=s.family, t_region=s.region, t_focal_year=s.main_focal_year,
                         religion_code=s.SCCS2002, deep_code=s.SCCS2001, christian_influence=s.SCCS1997, xd_id=e.xd_id))
# nearest-SCCS route (review only)
for _, b in bz.iterrows():
    d = sccs.apply(lambda s: hav(b.b_lat, b.b_lon, s.Latitude, s.Longitude), axis=1)
    k = d.idxmin()
    if d[k] <= 250:
        s = sccs.loc[k]
        rows.append(dict(route="near", evidence=f"nearest SCCS society, {d[k]:.0f} km", **b.to_dict(), target="SCCS", target_id=s.ID,
                         target_name=s.Name, target_alt=str(s.alt_names_by_society)[:120], t_lat=s.Latitude, t_lon=s.Longitude,
                         t_family=s.family, t_region=s.region, t_focal_year=s.main_focal_year, religion_code=s.SCCS2002,
                         deep_code=s.SCCS2001, christian_influence=s.SCCS1997, xd_id=s.xd_id))

# ---- Pulotu (Austronesian) name route
pu = pd.read_csv(D / "gh_pulotu/societies.csv")
pdat = pd.read_csv(D / "gh_pulotu/data.csv", low_memory=False)
pv = pdat.pivot_table(index="Language_ID", columns="Parameter_ID", values="Value", aggfunc="first")
pu["names"] = pu.apply(lambda r: parts(r.Name) | set().union(*[parts(x) for x in re.split(r"[;,]", str(r.Ethonyms)) if x and x != "nan"] or [set()]), axis=1)
for _, b in bz.iterrows():
    bn = parts(b.berezkin_name)
    for _, p in pu.iterrows():
        hit = bn & p.names
        if hit:
            v = pv.loc[p.ID] if p.ID in pv.index else {}
            rows.append(dict(route="name", evidence="name part(s) equal: " + "; ".join(sorted(hit)), **b.to_dict(), target="Pulotu",
                             target_id=p.ID, target_name=p.Name, target_alt=str(p.Ethonyms)[:120], t_lat=p.Latitude, t_lon=p.Longitude,
                             t_family="Austronesian", t_region="Pulotu", t_focal_year=v.get(1, None) if len(v) else None,
                             religion_code=f"christian_infl={v.get(24)}; hindu_buddhist_infl={v.get(25)}; islamic_infl={v.get(27)}; adopted_world_religion={v.get(68)}; dominant_2014={v.get(85)}" if len(v) else None))

# ---- DRH entries derived from eHRAF (religious-group records with year ranges)
z = zipfile.ZipFile(D / "gh_sccsr/drh_tables.zip")
ent = pd.read_csv(z.open([n for n in z.namelist() if n.endswith("entry_data.csv")][0]), low_memory=False)
eh = ent[ent.data_source.astype(str).str.contains("eHRAF", na=False)].copy()
eh["names"] = eh.entry_name.map(parts)
for _, b in bz.iterrows():
    bn = parts(b.berezkin_name)
    for _, e in eh.iterrows():
        hit = bn & e.names
        if hit:
            rows.append(dict(route="name", evidence="name part(s) equal: " + "; ".join(sorted(hit)), **b.to_dict(), target="DRH(eHRAF)",
                             target_id=e.entry_id, target_name=e.entry_name, target_alt=e.poll_name, t_focal_year=f"{e.year_from}..{e.year_to}",
                             religion_code="expert-coded religious group entry (no affiliation label)"))

cw = pd.DataFrame(rows)
cw["distance_km"] = cw.apply(lambda r: round(hav(r.b_lat, r.b_lon, r.get("t_lat"), r.get("t_lon")), 0), axis=1)
cw["multi_group_berezkin"] = cw.berezkin_name.astype(str).str.contains(",")
cw = cw.drop(columns=["key"], errors="ignore").sort_values(["target", "berezkin_name", "route"])
cw.to_csv(OUT / "crosswalk_candidates.csv", index=False)

s = []
s.append(f"Berezkin snapshots: macleginn 926 vs Michalopoulos-Xue 958 joined on normalised names: {snap}")
s.append(f"M&X EA groups: {len(mxea)}; EA names not found in D-PLACE EA by normalised name: {ea_unmatched}")
for t in ["SCCS", "Pulotu", "DRH(eHRAF)"]:
    c = cw[cw.target == t]
    for route in ["name", "ea", "near"]:
        cr = c[c.route == route]
        if len(cr):
            s.append(f"{t:11s} route={route:4s}: {len(cr):4d} candidate links, {cr.berezkin_name.nunique():4d} traditions, {cr.target_id.nunique():4d} target records")
sc = cw[cw.target == "SCCS"]
pairs = sc.groupby(["berezkin_name", "target_id"]).route.apply(lambda x: "+".join(sorted(set(x)))).reset_index()
s.append("SCCS candidate pairs by supporting routes: " + str(pairs.route.value_counts().to_dict()))
nn = pairs[pairs.route.str.split("+").map(lambda r: bool({"name", "ea"} & set(r)))]
s.append(f"SCCS pairs supported by name or EA route: {len(nn)} pairs, {nn.berezkin_name.nunique()} traditions, {nn.target_id.nunique()} SCCS societies")
print("\n".join(s))
(OUT / "crosswalk_candidates_summary.txt").write_text("\n".join(s) + "\n", encoding="utf-8")
