"""Coding sheets for the machine coder (the coding agent), and validation of what it writes.

    uv run python scripts/coding.py show pass1 [--size 12]      next uncoded frame versions
    uv run python scripts/coding.py show pass2 [--size 12]      recode sample, anonymous handles, no titles
    uv run python scripts/coding.py show aesop [--size 15]      fables with the printed moral removed
    uv run python scripts/coding.py show morals                 the printed morals alone, shuffled
    uv run python scripts/coding.py ingest <sheet> <file>       validate a block of coded lines and append it
    uv run python scripts/coding.py status

A coded line is pipe-separated:

    id|outcome|behaviour|story_behaviour|mode|justification|lesson_place|confidence|lesson_text|quote

(`morals` lines are `id|behaviour`.) Values must be in data/annotations/codebook.yaml; a quote
must be at most 25 words and occur verbatim in the stored text. Nothing is appended unless the
whole block validates. The sheets never show the framing, collection or tradition of a version.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis.aesop import check_sample  # noqa: E402
from analysis.common import load_config  # noqa: E402

ANN = ROOT / "data/annotations"
MACHINE = ANN / "machine"
FIELDS = ["id", "outcome", "behaviour", "story_behaviour", "mode", "justification", "lesson_place", "confidence",
          "lesson_text", "quote"]
FILES = {"pass1": MACHINE / "lesson_codes_pass1.csv", "pass2": MACHINE / "lesson_codes_pass2.csv",
         "aesop": MACHINE / "aesop_story_codes.csv", "morals": MACHINE / "aesop_moral_codes.csv"}


def codebook() -> dict:
    return yaml.safe_load((ANN / "codebook.yaml").read_text(encoding="utf-8"))["fields"]


def norm(s: str) -> str:
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def texts() -> pd.DataFrame:
    nar = pd.read_parquet(ROOT / "data/processed/narratives.parquet").set_index("narrative_id")
    frame = pd.read_csv(ROOT / "data/processed/lesson_frame.csv")
    return frame.join(nar[["text"]], on="narrative_id")


def view(text: str, cfg: dict) -> str:
    """The part of a text the coder sees: all of it, or its opening and ending."""
    words = norm(text).split()
    v = cfg["coding_view"]
    if len(words) <= v["full_text_max_words"]:
        return " ".join(words)
    cut = len(words) - v["head_words"] - v["tail_words"]
    return " ".join(words[:v["head_words"]]) + f" [... {cut} words not shown ...] " + " ".join(words[-v["tail_words"]:])


def pass1_order(frame: pd.DataFrame, seed: int) -> list[str]:
    ids = sorted(frame["narrative_id"])
    random.Random(f"pass1:{seed}").shuffle(ids)          # same-type versions are not read side by side
    return ids


def pass2_handles(frame: pd.DataFrame, cfg: dict) -> dict[str, str]:
    """handle -> narrative_id for the recode sample (half religious, half other, tested types only)."""
    rc = cfg["recode_sample"]
    rng = random.Random(f"pass2:{rc['seed']}")
    tested = frame[frame["in_tests"]]
    picked = []
    for framing in ["religious", "other"]:
        ids = sorted(tested.loc[tested["framing"] == framing, "narrative_id"])
        picked += rng.sample(ids, rc["n"] // 2)
    rng.shuffle(picked)
    return {f"r{k:02d}": nid for k, nid in enumerate(picked, 1)}


def done(sheet: str) -> set[str]:
    p = FILES[sheet]
    return set(pd.read_csv(p, dtype=str)["id"]) if p.exists() else set()


def show(sheet: str, size: int) -> None:
    cfg = load_config()["lessons"]
    have = done(sheet)
    if sheet in ("pass1", "pass2"):
        frame = texts().set_index("narrative_id")
        if sheet == "pass1":
            todo = [(nid, nid) for nid in pass1_order(frame.reset_index(), cfg["seed"]) if nid not in have]
        else:
            todo = [(h, nid) for h, nid in pass2_handles(frame.reset_index(), cfg).items() if h not in have]
        print(f"# {sheet}: {len(todo)} left; showing {min(size, len(todo))}")
        for handle, nid in todo[:size]:
            r = frame.loc[nid]
            head = f"### {handle} | {int(r['n_words'])} words" + (f" | {r['title']}" if sheet == "pass1" else "")
            print(f"\n{head}\n{view(r['text'], cfg)}")
    elif sheet == "aesop":
        todo = [f for f in check_sample(cfg["aesop"]["n"], cfg["aesop"]["seed"]) if f["handle"] not in have]
        print(f"# aesop: {len(todo)} left; showing {min(size, len(todo))} (printed morals removed, titles shown)")
        for f in todo[:size]:
            print(f"\n### {f['handle']} | {f['n_words']} words | {f['title']}\n{f['body']}")
    elif sheet == "morals":
        sample = check_sample(cfg["aesop"]["n"], cfg["aesop"]["seed"])
        order = list(range(len(sample)))
        random.Random(f"morals:{cfg['aesop']['seed']}").shuffle(order)
        print("# printed morals alone, shuffled; code `behaviour` only: id|behaviour")
        for k, i in enumerate(order, 1):
            if f"m{k:02d}" not in have:
                print(f"m{k:02d} | {sample[i]['moral']}")


def moral_key() -> dict[str, str]:
    """m-handle -> a-handle (never printed by `show`)."""
    cfg = load_config()["lessons"]
    sample = check_sample(cfg["aesop"]["n"], cfg["aesop"]["seed"])
    order = list(range(len(sample)))
    random.Random(f"morals:{cfg['aesop']['seed']}").shuffle(order)
    return {f"m{k:02d}": sample[i]["handle"] for k, i in enumerate(order, 1)}


def ingest(sheet: str, path: Path) -> None:
    cb, cfg = codebook(), load_config()["lessons"]
    allowed = {f: set(map(str, (cb[f]["values"] if isinstance(cb[f]["values"], (dict, list)) else cb["behaviour"]["values"])))
               for f in ["outcome", "behaviour", "story_behaviour", "mode", "justification", "lesson_place", "confidence"]}
    have, rows, errors = done(sheet), [], []
    if sheet == "morals":
        valid_ids = set(moral_key())
        source = {}
    elif sheet == "aesop":
        sample = {f["handle"]: f["body"] for f in check_sample(cfg["aesop"]["n"], cfg["aesop"]["seed"])}
        valid_ids, source = set(sample), sample
    else:
        frame = texts().set_index("narrative_id")
        if sheet == "pass1":
            valid_ids, source = set(frame.index), frame["text"].to_dict()
        else:
            handles = pass2_handles(frame.reset_index(), cfg)
            valid_ids, source = set(handles), {h: frame.loc[n, "text"] for h, n in handles.items()}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if sheet == "morals":
            if len(parts) != 2 or parts[0] not in valid_ids or parts[1] not in allowed["behaviour"]:
                errors.append(f"line {n}: bad morals line: {line[:80]}")
            else:
                rows.append(dict(id=parts[0], behaviour=parts[1]))
            continue
        if len(parts) != len(FIELDS):
            errors.append(f"line {n}: {len(parts)} fields, expected {len(FIELDS)}: {line[:80]}")
            continue
        row = dict(zip(FIELDS, parts))
        if row["id"] not in valid_ids:
            errors.append(f"line {n}: unknown id {row['id']}")
            continue
        if row["id"] in have or any(r["id"] == row["id"] for r in rows):
            errors.append(f"line {n}: {row['id']} is already coded")
        for f, ok in allowed.items():
            if row[f] not in ok:
                errors.append(f"line {n} ({row['id']}): {f}={row[f]!r} is not in the codebook")
        if len(row["lesson_text"].split()) > 15:
            errors.append(f"line {n} ({row['id']}): lesson_text has more than 15 words")
        q = norm(row["quote"])
        if not q or len(q.split()) > 25:
            errors.append(f"line {n} ({row['id']}): quote is empty or longer than 25 words")
        elif q not in norm(source[row["id"]]):
            errors.append(f"line {n} ({row['id']}): quote is not verbatim in the text: {q[:60]!r}")
        row["quote"] = q
        rows.append(row)
    if errors:
        print("NOT INGESTED:\n  " + "\n  ".join(errors))
        sys.exit(1)
    out = pd.DataFrame(rows)
    p = FILES[sheet]
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        out = pd.concat([pd.read_csv(p, dtype=str), out.astype(str)], ignore_index=True)
    out.to_csv(p, index=False, lineterminator="\n")
    print(f"ingested {len(rows)} lines into {p.relative_to(ROOT)} ({len(out)} total)")


def status() -> None:
    cfg = load_config()["lessons"]
    frame = pd.read_csv(ROOT / "data/processed/lesson_frame.csv")
    total = {"pass1": len(frame), "pass2": cfg["recode_sample"]["n"], "aesop": cfg["aesop"]["n"], "morals": cfg["aesop"]["n"]}
    for sheet in FILES:
        print(f"{sheet:7} {len(done(sheet)):4d} / {total[sheet]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("sheet", choices=list(FILES)); s.add_argument("--size", type=int, default=12)
    i = sub.add_parser("ingest"); i.add_argument("sheet", choices=list(FILES)); i.add_argument("file", type=Path)
    sub.add_parser("status")
    a = ap.parse_args()
    if a.cmd == "show":
        show(a.sheet, a.size)
    elif a.cmd == "ingest":
        ingest(a.sheet, a.file)
    else:
        status()
