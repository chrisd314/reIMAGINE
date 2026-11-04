"""Tabulate SCCS religion variables per society from the D-PLACE GeoJSON exports (data only)."""
import json
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
D = "downloads/"
rows = []
for v, path in [("SCCS2002", "dplace_sccs2002/SCCS2002_all.geojson"), ("SCCS2001", "dplace_sccs_rel/SCCS2001_all.geojson"),
                ("SCCS1997", "dplace_sccs_rel/SCCS1997_all.geojson"), ("SCCS1837", "dplace_sccs_rel/SCCS1837_all.geojson"),
                ("SCCS238", "dplace_sccs_rel/SCCS238_all.geojson")]:
    for f in json.load(open(D + path, encoding="utf-8"))["features"]:
        p, l = f["properties"], f["properties"]["language"]
        rows.append(dict(var=v, xd_id=l.get("xid"), name_in_source=l.get("name_in_source"), region=l.get("region"), glottocode=l.get("glottocode"),
                         family=l.get("language_family"), focal_year=l.get("year"), value=p.get("label"),
                         lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1]))
df = pd.DataFrame(rows)
df.to_csv("evidence/sccs_religion_values.csv", index=False)
vals = df.pivot_table(index="xd_id", columns="var", values="value", aggfunc="first").reset_index()
# attributes from the SCCS2002 export (focal years and names can differ between variables' exports)
attr = df[df["var"] == "SCCS2002"][["xd_id", "name_in_source", "region", "focal_year", "family"]].drop_duplicates("xd_id")
w = attr.merge(vals, on="xd_id", how="outer")
assert w.xd_id.is_unique and len(w) == df.xd_id.nunique(), "one row per society expected"
diff_years = df.groupby("xd_id").focal_year.nunique()
print("societies whose focal year differs between variable exports:", int((diff_years > 1).sum()))
w.to_csv("evidence/sccs_religion_wide.csv", index=False)
print("SCCS2002:", w.SCCS2002.value_counts(dropna=False).to_dict())
