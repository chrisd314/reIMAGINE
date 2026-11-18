"""One command for the paper pipeline.

    python -m ouaw.run --stage all                 everything, on the full data
    python -m ouaw.run --stage partA partB         single stages, in pipeline order
    python -m ouaw.run --stage all --sample 100    fast development run (100 folktales, a few texts per
                                                   tradition, at most 100 shuffles; writes to results/_sample)

Stages: data -> parables -> partA -> partB -> vocab -> headline -> length -> network -> checks -> robustness
-> figures -> site. `figures` also writes the report material into report/ (git-ignored): RESULTS.md, captions.md,
short_update.md, numbers.tex, table1.tex; `site` writes the website's data and builds the site (web/dist) when Node is available.
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time

from .common import Ctx

ORDER = ["data", "parables", "partA", "partB", "vocab", "headline", "length", "network", "checks", "robustness", "figures", "site"]
MODULE = {"data": ".corpus", "parables": ".parables.build", "partA": ".part_a", "partB": ".part_b", "vocab": ".vocab",
          "headline": ".headline", "length": ".length", "network": ".network", "checks": ".checks",
          "robustness": ".robustness", "figures": ".figures", "site": ".site"}


def _stage(name: str):
    return importlib.import_module(MODULE[name], __package__).run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ouaw.run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", nargs="+", default=["all"], help=f"'all' or any of: {', '.join(ORDER)}")
    ap.add_argument("--sample", type=int, default=None, metavar="N", help="development run on N folktales")
    ap.add_argument("--fetch", action="store_true",
                    help="parables stage: download source pages missing from data/raw/parables/ (one request per second). "
                         "Off by default: the terms of sacred-texts.com ask users not to scrape the site; read README.md first")
    args = ap.parse_args(argv)
    stages = ORDER if "all" in args.stage else args.stage
    unknown = set(stages) - set(ORDER)
    if unknown:
        ap.error(f"unknown stage(s): {', '.join(sorted(unknown))}")
    ctx = Ctx(sample=args.sample, fetch=args.fetch)
    for name in [s for s in ORDER if s in stages]:
        print(f"== {name}" + (f" (sample {args.sample})" if args.sample else ""), flush=True)
        t0 = time.time()
        _stage(name)(ctx)
        print(f"== {name} done in {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
