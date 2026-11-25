"""Paths, settings and the run context of the analysis pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .core.common import INTERIM, PROCESSED, ROOT, load_config, read_json, write_json  # noqa: F401  (re-exported)

PARABLES_CSV = PROCESSED / "parables.csv"
RAW_PARABLES = ROOT / "data" / "raw" / "parables"
REFS = ROOT / "data" / "mappings" / "parables"          # reviewable reference files (verse ranges, anchors)
TRADITIONS = ["Christian", "Buddhist", "Jewish", "Sufi", "Taoist"]


def load_analysis() -> dict:
    with open(ROOT / "analysis.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class Ctx:
    """One pipeline run. `sample` switches to a small development run with its own output folders."""
    sample: int | None = None
    fetch: bool = False         # download source pages that are not in the cache (off by default, see README.md)
    cfg: dict = field(default_factory=load_config)
    analysis: dict = field(default_factory=load_analysis)

    def _dir(self, base: Path) -> Path:
        p = base / "_sample" if self.sample else base
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def results(self) -> Path:
        return self._dir(ROOT / "results")

    @property
    def work(self) -> Path:
        """Intermediate arrays (graphs, layouts, neighbour lists), git-ignored."""
        return self._dir(INTERIM / "reimagine")

    @property
    def seed(self) -> int:
        return int(self.analysis["seed"])

    def shuffles(self, n: int, cap: int = 100) -> int:
        """Shuffle and bootstrap counts are capped in a development run."""
        return min(int(n), cap) if self.sample else int(n)

    @property
    def reps(self) -> list[str]:
        return list(self.analysis["representations"])

    @property
    def primary(self) -> str:
        return self.analysis["primary_representation"]


def n_tokens(text: str) -> int:
    """Whitespace-delimited words: the same definition as `n_words` of the folktales."""
    return len(text.split())


def write_csv(df: pd.DataFrame, path: Path, digits: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n", encoding="utf-8", float_format=f"%.{digits}g")


def top_k(S: np.ndarray, k: int) -> np.ndarray:
    """Column indices of the k largest entries of each row. Ties go to the lower column index."""
    k = min(k, S.shape[1])
    return np.argsort(-np.round(S, 12), axis=1, kind="stable")[:, :k]


def permute_within(groups, rng: np.random.Generator) -> np.ndarray:
    """Index permutation that moves items only within their own group (stratified shuffle).

    `labels[permute_within(groups, rng)]` shuffles labels within each group: within a tradition for the
    headline test (parable vs baseline), within a source collection for the conditional label null.
    """
    groups = np.asarray(groups)
    perm = np.arange(len(groups))
    for g in pd.unique(groups):
        pos = np.flatnonzero(groups == g)
        perm[pos] = pos[rng.permutation(len(pos))]
    return perm


def summarise_null(obs: float, null: np.ndarray) -> dict:
    """Observed value against a null sample: mean, sd, z and one-sided upper p (1 + #null >= obs) / (1 + N)."""
    null = np.asarray(null, dtype=float)
    sd = float(null.std(ddof=1)) if len(null) > 1 else 0.0
    return dict(observed=float(obs), null_mean=float(null.mean()), null_sd=sd,
                z=float((obs - null.mean()) / sd) if sd > 0 else float("nan"),
                p_upper=float((1 + (null >= obs).sum()) / (1 + len(null))), n_null=int(len(null)))
