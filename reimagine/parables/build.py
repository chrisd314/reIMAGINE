"""Stage `parables`: build data/processed/parables.csv from the five traditions.

For each tradition: collect the parables, drop any that repeats one of the 36 calibration versions
(same story number where the corpus prints one, same title, or TF-IDF cosine above 0.9), draw the
target number where more qualify, and cut length-matched baseline passages from non-story teaching
text of the same translation. A source that cannot be downloaded is reported and skipped; the other
traditions still run.
"""
from __future__ import annotations

import random
import re
import unicodedata

import numpy as np
import pandas as pd

from ..common import PARABLES_CSV, TRADITIONS, Ctx, n_tokens, write_csv, write_json
from ..corpus import load_corpus
from ..reps import TfidfSpace
from . import buddhist, christian, jewish, sufi, taoist
from .http import CacheMiss, Fetcher, SourceBlocked

COLUMNS = ["id", "tradition", "kind", "source", "translator", "year", "title", "text", "n_tokens", "url", "retrieved_at",
           "segment_note"]
PREFIX = {"Christian": "chr", "Buddhist": "bud", "Jewish": "jew", "Sufi": "suf", "Taoist": "tao"}


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", re.sub(r"\([^)]*\)", " ", title))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


class Duplicates:
    """Is a new story one of the 36 calibration versions? Same title (after removing case, accents,
    punctuation and brackets), or TF-IDF cosine above the threshold. Story numbers printed in the corpus
    (Jātaka number; Masnavi book and story) are matched by the tradition modules."""

    def __init__(self, ctx: Ctx):
        corpus = load_corpus(ctx)
        self.space = TfidfSpace(corpus.folk["text"].tolist(), ctx.cfg)
        self.cal = corpus.calib
        self.C = self.space.transform(self.cal["text"].tolist())
        self.titles = [norm_title(t) for t in self.cal["title"]]
        self.threshold = ctx.paper["parables"]["duplicate_cosine"]
        cal_list = pd.read_csv(ctx.paper["calibration_list"], dtype=str, keep_default_na=False)
        known = [k.split(":") for k in cal_list["known_story"] if k]
        self.jataka_numbers = {int(k[1]) for k in known if k[0] == "jataka"}
        self.masnavi_stories = {(int(k[1]), int(k[2])) for k in known if k[0] == "masnavi"}

    def cosine(self, texts: list[str]) -> np.ndarray:
        return np.asarray((self.space.transform(texts) @ self.C.T).todense())

    def __call__(self, title: str, text: str, alt_text: str | None = None) -> str | None:
        t = norm_title(title)
        for k, c in enumerate(self.titles):
            if t and t == c:
                return f"same title as calibration version {self.cal.at[k, 'id']}"
        S = self.cosine([text] + ([alt_text] if alt_text else []))
        if S.max() > self.threshold:
            k = int(S.max(axis=0).argmax())
            return f"TF-IDF cosine {S.max():.2f} to calibration version {self.cal.at[k, 'id']}"
        return None


def draw(items: list[dict], target, seed: int) -> tuple[list[dict], int]:
    """A seeded random draw of `target` items (all of them when target is 'all' or not smaller than the pool)."""
    if target == "all" or len(items) <= int(target):
        return items, 0
    keep = sorted(random.Random(seed).sample(range(len(items)), int(target)))
    return [items[k] for k in keep], len(items) - len(keep)


def make_baseline(units: list[dict], lengths: list[int], n: int, seed: int) -> list[dict]:
    """`n` non-overlapping passages of consecutive units, with lengths matched to the parables.

    Target lengths are evenly spaced quantiles of the parable lengths, in a seeded random order.
    The source is divided among the passages in proportion to their targets, so they are spread
    over the whole text. When the source is too short for `n` passages of these lengths, fewer
    are cut rather than shorter ones. A passage never crosses from one `group` into another.
    """
    if not units or not lengths:
        return []
    tok = np.array([n_tokens(u["text"]) for u in units])
    total = int(tok.sum())
    targets = np.quantile(lengths, (np.arange(n) + 0.5) / n)
    while n > 1 and targets.sum() > 0.95 * total:
        n -= 1
        targets = np.quantile(lengths, (np.arange(n) + 0.5) / n)
    targets = np.random.default_rng(seed).permutation(targets)
    bounds = np.concatenate([[0], np.cumsum(targets) / targets.sum() * total])
    starts_tok = np.concatenate([[0], np.cumsum(tok)[:-1]])
    out = []
    for k, target in enumerate(targets):
        i = int(np.searchsorted(starts_tok, bounds[k], side="left"))
        if out and i <= out[-1]["_last"]:
            i = out[-1]["_last"] + 1
        if i >= len(units):
            break
        j, size = i, 0
        while j < len(units) and starts_tok[j] < bounds[k + 1] and units[j]["group"] == units[i]["group"]:
            size += tok[j]
            j += 1
            if size >= target:
                break
        first, last = units[i], units[j - 1]
        label = first["label"] if first["label"] == last["label"] else f"{first['label']} to {last['label']}"
        out.append(dict(tradition=first["tradition"], source=first["source"], translator=first["translator"], year=first["year"],
                        title=f"Non-story passage: {label}", text=" ".join(u["text"] for u in units[i:j]), url=first["url"],
                        retrieved_at=first["retrieved_at"], _last=j - 1,
                        segment_note=f"{j - i} consecutive units; target {int(round(target))} tokens"))
    return out


def collect_all(ctx: Ctx):
    pc = ctx.paper["parables"]
    fetcher = Fetcher(pc["user_agent"], pc["seconds_between_requests"], allow_fetch=ctx.fetch)
    dup = Duplicates(ctx)
    jobs = {
        "Christian": lambda: christian.collect(ctx, fetcher) + ([],),
        "Buddhist": lambda: buddhist.collect(ctx, fetcher, dup, dup.jataka_numbers),
        "Jewish": lambda: jewish.collect(ctx, fetcher, dup),
        "Sufi": lambda: sufi.collect(ctx, fetcher, dup, dup.masnavi_stories),
        "Taoist": lambda: taoist.collect(ctx, fetcher, dup),
    }
    targets = {"Christian": "all", "Buddhist": "all", "Jewish": pc["targets"]["jewish"], "Sufi": pc["targets"]["sufi"],
               "Taoist": "all"}       # Jātaka and Zhuangzi are drawn inside their modules
    rows, skipped, blocked = [], [], []
    for tradition in TRADITIONS:
        try:
            parables, units, skip = jobs[tradition]()
        except SourceBlocked as e:
            blocked.append(dict(tradition=tradition, error=str(e)))
            print(f"  {tradition}: BLOCKED ({e}); continuing with the other traditions")
            continue
        parables = sorted(parables, key=lambda r: r["key"])
        parables, dropped = draw(parables, targets[tradition] if not ctx.sample else 8, ctx.seed)
        if dropped:
            skip.append(dict(tradition=tradition, item=f"{dropped} qualifying stories", reason="not drawn (seeded random draw to the target size)"))
        base = make_baseline(units, [n_tokens(p["text"]) for p in parables],
                             pc["baseline_per_tradition"] if not ctx.sample else 5, ctx.seed)
        for kind, items in (("parable", parables), ("baseline", base)):
            for k, r in enumerate(items, start=1):
                rows.append(dict(id=f"{PREFIX[tradition]}-{'b' if kind == 'baseline' else 'p'}{k:03d}", kind=kind,
                                 n_tokens=n_tokens(r["text"]), **{c: r[c] for c in COLUMNS if c in r}))
        skipped += skip
        print(f"  {tradition}: {len(parables)} parables (median {int(np.median([n_tokens(p['text']) for p in parables]))} tokens), "
              f"{len(base)} baseline passages (median {int(np.median([n_tokens(b['text']) for b in base])) if base else 0} tokens)")
    table = pd.DataFrame(rows)[COLUMNS]
    assert table["id"].is_unique and (table["text"].str.len() > 0).all()
    return table, pd.DataFrame(skipped, columns=["tradition", "item", "reason"]), blocked, dup


def run(ctx: Ctx) -> dict:
    try:
        table, skipped, blocked, dup = collect_all(ctx)
    except CacheMiss as e:
        existing = PARABLES_CSV if PARABLES_CSV.exists() else None
        if existing is None:
            raise SystemExit(f"parables stage: {e}\nNo data/processed/parables.csv exists either. Read 'Data sources' in README.md, "
                             "then rerun with --fetch if you decide to download the pages.") from e
        n = sum(1 for _ in open(existing, encoding="utf-8")) - 1
        print(f"  parables: source pages are not cached ({e}).\n  Keeping the existing data/processed/parables.csv ({n} rows). "
              "Rerun with --fetch to download and rebuild; read 'Data sources' in README.md first.")
        return dict(kept_existing=True)
    out_csv = PARABLES_CSV if not ctx.sample else ctx.results / "parables.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_csv, index=False, lineterminator="\n", encoding="utf-8")

    g = table.groupby(["tradition", "kind"], sort=False)
    summary = g.agg(n=("id", "size"), tokens_median=("n_tokens", "median"), tokens_q25=("n_tokens", lambda x: x.quantile(0.25)),
                    tokens_q75=("n_tokens", lambda x: x.quantile(0.75)), tokens_min=("n_tokens", "min"), tokens_max=("n_tokens", "max"),
                    whole_text_kept=("segment_note", lambda x: int(x.str.startswith("whole text").sum())),
                    sources=("source", lambda x: "; ".join(sorted(set(x)))),
                    retrieved=("retrieved_at", lambda x: f"{min(x)[:10]}")).reset_index()
    write_csv(summary, ctx.results / "parables_summary.csv")
    write_csv(skipped, ctx.results / "parables_skipped.csv")
    par = table[table["kind"] == "parable"].reset_index(drop=True)
    S = dup.cosine(par["text"].tolist())                 # how close the kept parables still are to a calibration version
    top = np.dstack(np.unravel_index(np.argsort(-S, axis=None)[:15], S.shape))[0]
    write_csv(pd.DataFrame([dict(parable_id=par.at[i, "id"], parable_title=par.at[i, "title"], calibration_id=dup.cal.at[j, "id"],
                                 calibration_title=dup.cal.at[j, "title"], tfidf_cosine=S[i, j]) for i, j in top]),
              ctx.results / "parables_calibration_overlap.csv")
    write_json(ctx.results / "blocked_sources.json", dict(blocked=blocked))
    n_par, n_base = int((table.kind == "parable").sum()), int((table.kind == "baseline").sum())
    print(f"  parables.csv: {n_par} parables and {n_base} baseline passages from {table.tradition.nunique()} traditions; "
          f"{len(blocked)} blocked source(s); highest remaining cosine to a calibration version {S.max():.2f}")
    return dict(parables=n_par, baseline=n_base, blocked=blocked)
