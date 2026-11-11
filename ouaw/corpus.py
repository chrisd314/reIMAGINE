"""Stage `data`: the folklore corpus split into the map (folktales) and the calibration set.

The cleaned narratives of the existing pipeline are reused as they are. The 36 versions from
religious collections listed in data/mappings/calibration_set.csv are taken out of the map and
kept as queries whose correct answer (a folktale of the same ATU type) is known.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .common import PARABLES_CSV, PROCESSED, ROOT, Ctx, n_tokens, write_json

EXPECTED_CALIBRATION = {"Jātaka": 18, "Gesta Romanorum": 11, "Rumi, Masnavi": 4,
                        "Jacques de Vitry, sermon exempla": 2, "Talmud": 1}


@dataclass
class Corpus:
    folk: pd.DataFrame      # the map: id, title, text, atu_id, atu_name, region, place, n_tokens
    calib: pd.DataFrame     # calibration queries: id, title, text, atu_id, tradition, collection, n_tokens

    def queries(self, ctx: Ctx) -> pd.DataFrame:
        """Parables, baseline passages and calibration versions in one table (kind tells them apart)."""
        cal = self.calib.assign(kind="calibration")[["id", "kind", "tradition", "title", "text", "n_tokens", "atu_id"]]
        path = PARABLES_CSV
        if ctx.sample and not path.exists():        # development run before the full collection exists
            path = ctx.results / "parables.csv"
        if not path.exists():
            return cal.reset_index(drop=True)
        par = pd.read_csv(path, dtype=str, keep_default_na=False)
        par["n_tokens"] = par["n_tokens"].astype(int)
        if ctx.sample:      # a few of every tradition and kind
            per = max(5, ctx.sample // 10)
            par = (par.sample(frac=1, random_state=ctx.seed).groupby(["tradition", "kind"], sort=False).head(per)
                      .sort_values("id"))
        par = par.assign(atu_id=None)[["id", "kind", "tradition", "title", "text", "n_tokens", "atu_id"]]
        return pd.concat([par, cal], ignore_index=True)


def load_corpus(ctx: Ctx) -> Corpus:
    path = PROCESSED / "narratives.parquet"
    if not path.exists():       # only on a fresh clone: run the existing data stages, nothing is re-cleaned otherwise
        from analysis.__main__ import main as website_pipeline
        website_pipeline(["fetch", "clean", "audit", "cohorts"])
    nar = pd.read_parquet(path).sort_values("narrative_id").reset_index(drop=True)
    cal = pd.read_csv(ROOT / ctx.paper["calibration_list"], dtype=str, keep_default_na=False)
    assert cal["narrative_id"].is_unique and set(cal["narrative_id"]) <= set(nar["narrative_id"])
    assert cal.groupby("collection").size().to_dict() == EXPECTED_CALIBRATION, "calibration list changed"

    tab = pd.DataFrame({
        "id": nar["narrative_id"], "title": nar["title"], "text": nar["text"],
        "atu_id": nar["atu_id"].where(nar["atu_status"] == "unique"), "atu_name": nar["atu_name"],
        "region": nar["broad_region"], "place": nar["place_label"], "n_tokens": nar["text"].map(n_tokens)})
    is_cal = tab["id"].isin(cal["narrative_id"])
    folk = tab[~is_cal].reset_index(drop=True)
    calib = tab[is_cal].merge(cal[["narrative_id", "tradition", "collection"]], left_on="id", right_on="narrative_id")
    calib = calib.drop(columns="narrative_id").sort_values("id").reset_index(drop=True)
    assert calib["atu_id"].notna().all(), "every calibration version needs one ATU type"
    assert calib["atu_id"].isin(folk["atu_id"]).all(), "every calibration type needs a folktale of the same type"
    if ctx.sample:
        folk = folk.sample(n=min(ctx.sample, len(folk)), random_state=ctx.seed).sort_values("id").reset_index(drop=True)
    return Corpus(folk=folk, calib=calib)


def run(ctx: Ctx) -> dict:
    c = load_corpus(ctx)
    f = c.folk
    summary = dict(
        folktales=int(len(f)), calibration=int(len(c.calib)),
        calibration_by_collection=c.calib.groupby("collection").size().to_dict(),
        folktales_with_one_atu_type=int(f["atu_id"].notna().sum()), atu_types=int(f["atu_id"].nunique()),
        folktales_with_region=int(f["region"].notna().sum()), regions=int(f["region"].nunique()),
        folktales_with_type_and_region=int((f["atu_id"].notna() & f["region"].notna()).sum()),
        folktale_tokens=dict(median=float(f["n_tokens"].median()), q25=float(f["n_tokens"].quantile(0.25)),
                             q75=float(f["n_tokens"].quantile(0.75))),
        region_counts=f["region"].value_counts().to_dict(),
        source="data/processed/narratives.parquet (existing cleaning; trilogy commit d57c2ce)")
    write_json(ctx.results / "corpus_summary.json", summary)
    print(f"  corpus: {summary['folktales']} folktales on the map, {summary['calibration']} calibration versions; "
          f"{summary['folktales_with_type_and_region']} folktales carry both a tale type and a region")
    return summary
