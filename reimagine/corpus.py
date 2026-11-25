"""Stage `data`: the folklore corpus split into the map (folktales) and the calibration set.

The cleaned narratives of the existing pipeline are reused as they are. The 36 versions from
religious collections listed in data/mappings/calibration_set.csv are taken out of the map and
kept as queries whose correct answer (a folktale of the same ATU type) is known.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .common import PARABLES_CSV, PROCESSED, ROOT, Ctx, n_tokens, write_json

EXPECTED_CALIBRATION = {"Jātaka": 18, "Gesta Romanorum": 11, "Rumi, Masnavi": 4,
                        "Jacques de Vitry, sermon exempla": 2, "Talmud": 1}


_TRANSLATED = re.compile(r"[Tt]ranslated(?: from the [A-Z]\w+)?(?: into [A-Z]\w+)?(?: and edited)?(?: with notes)? by "
                         r"((?:[A-Z][\w'.-]*\.?\s?){1,6}?(?:and (?:[A-Z][\w'.-]*\.?\s?){1,5})?)(?=[,(;]|\s*$|\s[a-z(])")


def translator_of(source, notes) -> str | None:
    """The translator named in a tale's source reference (or, failing that, its notes): 'translated ... by X'.

    None when no translator is stated. Ashliman's own translations usually state none.
    """
    for s in (source, notes):
        if isinstance(s, str):
            m = _TRANSLATED.search(s)
            if m:
                return re.sub(r"\s+", " ", m.group(1)).strip(" .")
    return None


def check_calibration_exclusion(folk_ids, calib_ids, near_dups: dict | None = None, S: np.ndarray | None = None,
                                threshold: float = 0.9) -> dict:
    """The calibration test is circular if a retelling (or a copy of it) is also a folktale it can be matched to.

    Asserts that no calibration ID is in the folktale pool, that no pool folktale is a near-duplicate of a
    calibration version by the corpus audit (`near_dups`: id -> partner ids, 5-word shingles), and, given
    `S` (calibration x pool cosines), that no pool folktale has cosine above `threshold` with a calibration
    version. Every network, ranking, vote and null of the pipeline uses this pool.
    """
    folk_ids, calib_ids = [str(x) for x in folk_ids], [str(x) for x in calib_ids]
    inside = sorted(set(folk_ids) & set(calib_ids))
    assert not inside, f"calibration versions in the folktale pool: {inside}"
    pool = set(folk_ids)
    dup = sorted({(c, p) for c in calib_ids for p in (near_dups or {}).get(c, []) if p in pool})
    assert not dup, f"near-duplicates of calibration versions in the folktale pool: {dup}"
    out = dict(calibration_ids=len(calib_ids), pool=len(folk_ids), calibration_ids_in_pool=0,
               shingle_near_duplicates_in_pool=0, cosine_threshold=threshold)
    if S is not None:
        S = np.asarray(S)
        assert S.shape == (len(calib_ids), len(folk_ids)), S.shape
        over = np.argwhere(S > threshold)
        assert not len(over), "folktales above the near-duplicate cosine: " + ", ".join(
            f"{calib_ids[a]}~{folk_ids[b]} ({S[a, b]:.3f})" for a, b in over)
        j = S.argmax(axis=1)
        out.update(pairs_above_threshold=0, max_cosine=float(S.max()),
                   closest=[dict(calibration_id=calib_ids[a], folktale_id=folk_ids[j[a]], cosine=round(float(S[a, j[a]]), 4))
                            for a in np.argsort(-S.max(axis=1))[:5]])
    return out


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
    if not path.exists():       # only on a fresh clone: run the data preparation, nothing is re-cleaned otherwise
        from .core import prepare
        prepare()
    nar = pd.read_parquet(path).sort_values("narrative_id").reset_index(drop=True)
    cal = pd.read_csv(ROOT / ctx.analysis["calibration_list"], dtype=str, keep_default_na=False)
    assert cal["narrative_id"].is_unique and set(cal["narrative_id"]) <= set(nar["narrative_id"])
    assert cal.groupby("collection").size().to_dict() == EXPECTED_CALIBRATION, "calibration list changed"

    tab = pd.DataFrame({
        "id": nar["narrative_id"], "title": nar["title"], "text": nar["text"],
        "atu_id": nar["atu_id"].where(nar["atu_status"] == "unique"), "atu_name": nar["atu_name"],
        "region": nar["broad_region"], "place": nar["place_label"], "n_tokens": nar["text"].map(n_tokens),
        "source_collection": nar["source_key"].where(~nar["source_key"].isin(["(no source)", "(unparsed)"])),
        "translator": [translator_of(s, t) for s, t in zip(nar["source"], nar["notes"])]})
    is_cal = tab["id"].isin(cal["narrative_id"])
    folk = tab[~is_cal].reset_index(drop=True)
    calib = tab[is_cal].merge(cal[["narrative_id", "tradition", "collection"]], left_on="id", right_on="narrative_id")
    calib = calib.drop(columns="narrative_id").sort_values("id").reset_index(drop=True)
    assert calib["atu_id"].notna().all(), "every calibration version needs one ATU type"
    assert calib["atu_id"].isin(folk["atu_id"]).all(), "every calibration type needs a folktale of the same type"
    near = {k: list(v) for k, v in zip(nar["narrative_id"], nar["near_duplicates"]) if len(v)}
    check_calibration_exclusion(folk["id"], calib["id"], near)       # cosines are checked in the data and checks stages
    if ctx.sample:
        folk = folk.sample(n=min(ctx.sample, len(folk)), random_state=ctx.seed).sort_values("id").reset_index(drop=True)
    return Corpus(folk=folk, calib=calib)


def calibration_exclusion(ctx: Ctx, c: Corpus, spaces: dict | None = None) -> dict:
    """The calibration test is not circular: the 36 retellings and their near-copies are outside the folktale pool.

    Checked with both representations (cosine of every calibration version to every pool folktale).
    `spaces` reuses already-built representation spaces (rep -> space fitted on `c.folk`).
    """
    from .reps import build_space
    thr = float(ctx.analysis["calibration_exclusion"]["max_cosine"])
    out = {}
    for rep in ctx.reps:
        sp = (spaces or {}).get(rep) or build_space(rep, c.folk["text"].tolist(), ctx.cfg)
        S = sp.sim(sp.transform(c.calib["text"].tolist()))
        out[rep] = check_calibration_exclusion(c.folk["id"], c.calib["id"], None, S, thr)
    print("  calibration exclusion: no retelling or near-copy in the pool; highest cosine "
          + ", ".join(f"{rep} {v['max_cosine']:.3f}" for rep, v in out.items()) + f" (limit {thr})")
    return dict(rule="no calibration ID, no 5-word-shingle near-duplicate (corpus audit) and no folktale with cosine above "
                     f"{thr} to a calibration version in the pool used for networks, rankings, votes and nulls",
                passed=True, per_representation=out)


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
    write_json(ctx.results / "calibration_exclusion.json", calibration_exclusion(ctx, c))
    print(f"  corpus: {summary['folktales']} folktales on the map, {summary['calibration']} calibration versions; "
          f"{summary['folktales_with_type_and_region']} folktales carry both a tale type and a region")
    return summary
