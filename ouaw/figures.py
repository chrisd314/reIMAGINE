"""Stage `figures`: the four figures of the paper (PDF + PNG), then results/RESULTS.md.

Figures are drawn for the primary representation (paper.yaml), at PNAS column widths, with a
colour-blind-safe palette. Categories are labelled directly; text is never set in a series colour.
  fig1  the folklore map (backbone, coloured by community) with the type-vs-region check
  fig2  folk_closeness of every parable by tradition, with the two baselines
  fig3  tradition x community: share of links minus the shuffle expectation
  fig4  calibration recall@10 against chance, and hand-label precision (pending until coded)
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

from .common import TRADITIONS, Ctx, read_json  # noqa: E402

BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, RULE, BAND = "#1f2933", "#6b7785", "#d9dee4", "#e8ebef"
# the three base hues first, then further colour-blind-safe hues (Okabe-Ito) for maps with more communities
COMMUNITY = [BLUE, ORANGE, GREEN, "#CC79A7", "#E6B800", "#56B4E9", "#4d4d4d", "#8c564b", "#6a3d9a"]
SMALL = "#b8c0c8"
DIVERGING = LinearSegmentedColormap.from_list("ouaw_div", ["#b8491f", ORANGE, "#f6c9b5", "#ffffff", "#cde2fb", "#6da7ec", "#184f95"])
REP_NAME = {"tfidf": "TF-IDF", "embedding": "Embeddings"}


def style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 7,
        "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
        "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5,
        "ytick.major.size": 2.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
        "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "figure.dpi": 150})


def save(fig, ctx: Ctx, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(ctx.figures / f"{name}.{ext}", dpi=ctx.paper["figures"]["dpi"], bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def halo(artist, width: float = 1.8) -> None:
    artist.set_path_effects([patheffects.withStroke(linewidth=width, foreground="white")])


def panel_letter(ax, letter: str, dx: float = -16, dy: float = 5) -> None:
    """Bold panel letter outside the top-left corner of the axes (offsets in points)."""
    ax.annotate(letter, xy=(0, 1), xycoords="axes fraction", xytext=(dx, dy), textcoords="offset points",
                fontsize=9, fontweight="bold", va="bottom", ha="right", annotation_clip=False)


def tradition_order(ctx: Ctx, rep: str) -> list[str]:
    t = pd.read_csv(ctx.results / "partB_traditions.csv")
    return t[t["rep"] == rep].sort_values("median", ascending=False)["tradition"].tolist()


# ----------------------------------------------------------------- figure 1
def spread(points: np.ndarray, min_dx: float, min_dy: float, rounds: int = 200) -> np.ndarray:
    """Push label anchors apart until no two are closer than (min_dx, min_dy). Display only."""
    p = points.astype(float).copy()
    for _ in range(rounds):
        moved = False
        for a in range(len(p)):
            for b in range(a + 1, len(p)):
                dx, dy = p[b] - p[a]
                if abs(dx) < min_dx and abs(dy) < min_dy:
                    push = (min_dy - abs(dy)) / 2 + 1e-4
                    sign = 1.0 if dy >= 0 else -1.0
                    p[a, 1] -= sign * push
                    p[b, 1] += sign * push
                    moved = True
        if not moved:
            break
    return p


def fig1(ctx: Ctx, rep: str) -> None:
    z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
    xy, group, bb = z["xy"], z["group"], z["backbone"]
    ei, ej = z["i"][bb], z["j"][bb]
    comm = pd.read_csv(ctx.results / "partA_communities.csv")
    comm = comm[comm["rep"] == rep].set_index("community")
    agree = pd.read_csv(ctx.results / "partA_type_vs_region.csv")
    agree = agree[(agree["rep"] == rep) & (agree["node_set"] == "type_and_region") & (agree["measure"] == "nmi")].set_index("label")
    nulls = read_json(ctx.work / f"map_{rep}_nulls.json")
    deg = np.bincount(np.concatenate([z["i"], z["j"]]), minlength=len(xy))
    shown = deg > 0                                               # a tale without any link has no place on the map
    majors = sorted(set(group[group >= 0].tolist()))
    colour = {g: COMMUNITY[k % len(COMMUNITY)] for k, g in enumerate(majors)}

    w = ctx.paper["figures"]["double_column_in"]
    fig = plt.figure(figsize=(w, w * 0.56))

    # ---- a: the map
    ax = fig.add_axes([0.0, 0.045, 0.56, 0.93])
    ax.add_collection(LineCollection(np.stack([xy[ei], xy[ej]], axis=1), colors=MUTED, linewidths=0.1, alpha=0.16, zorder=1))
    order = np.argsort(-(group < 0).astype(int), kind="stable")   # small communities underneath
    order = order[shown[order]]
    ax.scatter(xy[order, 0], xy[order, 1], s=3.4, c=[colour.get(g, SMALL) for g in group[order]], linewidths=0, zorder=2)
    lo, hi = np.quantile(xy[shown], 0.003, axis=0), np.quantile(xy[shown], 0.997, axis=0)
    pad = 0.04 * (hi - lo)
    ax.set_xlim(lo[0] - pad[0], hi[0] + pad[0])
    ax.set_ylim(lo[1] - pad[1], hi[1] + pad[1])
    centres = np.array([[np.median(xy[(group == g) & shown, 0]), np.median(xy[(group == g) & shown, 1])] for g in majors])
    tags = spread(centres, 0.075 * (hi[0] - lo[0]), 0.06 * (hi[1] - lo[1]))
    for g, (cx, cy) in zip(majors, tags):
        ax.text(cx, cy, f"C{g + 1}", fontsize=7, fontweight="bold", ha="center", va="center", zorder=5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=colour[g], lw=1.0))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.0, 0.985, "a", fontsize=9, fontweight="bold", va="top", ha="left")
    note = (f"{int(shown.sum()):,} of {len(xy):,} folktales, placed by the whole network; each tale's "
            f"{ctx.paper['map']['backbone']['fallback_k']} strongest links drawn.")
    fig.text(0.0, 0.012, note, fontsize=6, color=MUTED, va="bottom", ha="left")

    # ---- legend: what the communities are
    lx = fig.add_axes([0.585, 0.44, 0.41, 0.54])
    lx.axis("off")
    rows = [(f"C{g + 1}", colour[g]) for g in majors] + ([("small", SMALL)] if (group < 0).any() else [])
    lx.set_xlim(0, 1)
    lx.set_ylim(len(rows) + 0.2, -1.2)
    lx.text(0.0, -0.75, "Communities and their most distinctive words", fontsize=7.5, va="center")
    for r, (name, col) in enumerate(rows):
        lx.scatter([0.025], [r], s=20, c=col, linewidths=0)
        lx.text(0.07, r, name if name != "small" else "", fontsize=6.8, fontweight="bold", va="center")
        if name == "small":
            n_small, n_iso = int((group < 0).sum()), int((~shown).sum())
            words = f"{n_small} tales in groups under 1% of the map" + (f" ({n_iso} unlinked, not drawn)" if n_iso else "")
            lx.text(0.07, r, words, fontsize=6.5, va="center", color=MUTED)
        else:
            lx.text(0.17, r, ", ".join(str(comm.at[name, "top_words"]).split()[:3]), fontsize=6.8, va="center")
            lx.text(1.0, r, f"{int(comm.at[name, 'size'])}", fontsize=6.5, va="center", ha="right", color=MUTED)
    lx.text(1.0, -0.75, "tales", fontsize=6.5, va="center", ha="right", color=MUTED)

    # ---- b: type against region, observed NMI and the range of the label shuffles
    bx = fig.add_axes([0.70, 0.125, 0.29, 0.165])
    labels = [("atu_type", "Tale type"), ("region", "Region")]
    for y, (key, label) in enumerate(labels):
        null = np.array(nulls[f"type_and_region|{key}"]["nmi"])
        obs = agree.at[key, "observed"]
        bx.plot([null.min(), null.max()], [y, y], color=MUTED, lw=4.5, solid_capstyle="butt", zorder=2)
        bx.plot([null.max(), obs], [y, y], color=RULE, lw=0.7, zorder=1)
        bx.scatter([obs], [y], s=20, c=BLUE, zorder=3, linewidths=0)
        bx.annotate(f"{obs:.2f}", (obs, y), xytext=(5, 0), textcoords="offset points", fontsize=6.5, va="center")
    bx.set_yticks(range(len(labels)), [r[1] for r in labels])
    bx.set_ylim(len(labels) - 0.45, -0.55)
    bx.set_xlim(0, float(agree["observed"].max()) * 1.25)
    bx.set_xlabel("NMI with the communities", labelpad=2)
    bx.tick_params(axis="y", length=0)
    bx.spines["left"].set_visible(False)
    fig.text(0.585, 0.375, "b", fontsize=9, fontweight="bold", va="top", ha="left")
    fig.text(0.615, 0.372, f"Communities follow tale type more than region\n(n = {int(agree['n'].iloc[0]):,} tales with both labels)",
             fontsize=7.5, va="top", ha="left", linespacing=1.2)
    fig.text(0.585, 0.012, "Dot: observed. Grey bar: range of 1,000 label shuffles.", fontsize=6, color=MUTED, va="bottom", ha="left")
    save(fig, ctx, "fig1_map")


# ----------------------------------------------------------------- figure 2
def fig2(ctx: Ctx, reps: list[str]) -> None:
    ranking = pd.read_csv(ctx.results / "partB_ranking.csv")
    trad = pd.read_csv(ctx.results / "partB_traditions.csv")
    base = pd.read_csv(ctx.results / "partB_folktale_baseline.csv")
    order = tradition_order(ctx, reps[0])
    w = ctx.paper["figures"]["double_column_in"]
    fig, axes = plt.subplots(1, len(reps), figsize=(w, w * 0.42), squeeze=False)
    rng = np.random.default_rng(ctx.seed)
    for k, (ax, rep) in enumerate(zip(axes[0], reps)):
        r = ranking[ranking["rep"] == rep]
        t = trad[trad["rep"] == rep].set_index("tradition")
        f = base[(base["rep"] == rep) & (base["candidates"] == "all other folktales")].iloc[0]
        ax.axhspan(f["q25"], f["q75"], color=BAND, zorder=0, lw=0)
        ax.axhline(f["q50"], color=MUTED, lw=0.6, zorder=1)
        for x, name in enumerate(order):
            if name not in t.index:
                continue
            v = r[(r["kind"] == "parable") & (r["tradition"] == name)]["folk_closeness"].to_numpy()
            b = r[(r["kind"] == "baseline") & (r["tradition"] == name)]["folk_closeness"].to_numpy()
            ax.scatter(x - 0.12 + rng.uniform(-0.17, 0.17, len(v)), v, s=5, c=BLUE, alpha=0.55, linewidths=0, zorder=3)
            ax.plot([x - 0.33, x + 0.09], [np.median(v)] * 2, color=INK, lw=1.3, zorder=5, solid_capstyle="butt")
            ax.plot([x - 0.12] * 2, [t.at[name, "ci_low"], t.at[name, "ci_high"]], color=INK, lw=0.7, zorder=5)
            if len(b):
                ax.plot([x + 0.3] * 2, np.quantile(b, [0.25, 0.75]), color=ORANGE, lw=3.2, alpha=0.55, zorder=2, solid_capstyle="butt")
                ax.plot([x + 0.22, x + 0.38], [np.median(b)] * 2, color=ORANGE, lw=1.3, zorder=4, solid_capstyle="butt")
        ax.set_xticks(range(len(order)), [f"{n}\nn = {int(t.at[n, 'n_parables'])}" if n in t.index else n for n in order])
        ax.tick_params(axis="x", length=0)
        ax.set_xlim(-0.6, len(order) - 0.4)
        ax.set_ylabel("Folk-closeness (mean cosine to the 5 nearest folktales)" if k == 0 else "")
        ax.set_title(f"{REP_NAME[rep]}" + ("" if k == 0 else " (second method)"), loc="left")
        ax.yaxis.grid(True, color=RULE, lw=0.4)
        ax.set_axisbelow(True)
        panel_letter(ax, "ab"[k])
        if k == 0:
            ax.text(len(order) - 0.45, f["q50"], "folktales to\neach other", fontsize=6, color=MUTED, ha="right", va="bottom",
                    linespacing=1.0)
    handles = [plt.Line2D([], [], marker="o", ls="", ms=3, color=BLUE, alpha=0.7, label="parable"),
               plt.Line2D([], [], color=INK, lw=1.3, label="tradition median, 95% bootstrap interval"),
               plt.Line2D([], [], color=ORANGE, lw=3, alpha=0.6, label="non-story text of the same translation (middle 50%, median)"),
               plt.Rectangle((0, 0), 1, 1, color=BAND, label="folktales against the other folktales (middle 50%, median)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.11), columnspacing=1.6,
               handlelength=1.6)
    fig.tight_layout(w_pad=1.6)
    save(fig, ctx, "fig2_closeness")


# ----------------------------------------------------------------- figure 3
def fig3(ctx: Ctx, rep: str) -> None:
    cells = pd.read_csv(ctx.results / "partB_attachment.csv")
    cells = cells[cells["rep"] == rep]
    comm = pd.read_csv(ctx.results / "partA_communities.csv")
    comm = comm[comm["rep"] == rep].set_index("community")
    order = [t for t in tradition_order(ctx, rep) if t in set(cells["tradition"])]
    cols = [c for c in comm.index if c in set(cells["community"])]
    val = cells.pivot(index="tradition", columns="community", values="share_minus_expected").loc[order, cols] * 100
    sig = cells.pivot(index="tradition", columns="community", values="significant_bonferroni").loc[order, cols]
    exp = cells.groupby("community")["community_share_of_folktales"].first().loc[cols] * 100
    wide = len(cols) > 6
    w = ctx.paper["figures"]["double_column_in" if wide else "single_column_in"]
    fig, ax = plt.subplots(figsize=(w, 0.36 * len(order) + 1.25))
    lim = max(5.0, float(np.abs(val.to_numpy()).max()))
    im = ax.imshow(val.to_numpy(), cmap=DIVERGING, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    for i in range(len(order)):
        for j in range(len(cols)):
            v = val.iat[i, j]
            ax.text(j, i, ("0" if abs(v) < 0.5 else f"{v:+.0f}") + ("*" if bool(sig.iat[i, j]) else ""), ha="center", va="center", fontsize=6.5,
                    color="white" if abs(v) > 0.62 * lim else INK)
    labels = [f"{c}\n" + "\n".join(str(comm.at[c, "top_words"]).split()[:3]) if c != "small" else "small\ncommu-\nnities\n"
              for c in cols]
    ax.set_xticks(range(len(cols)), labels, linespacing=1.05)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(order)), order)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(cols)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(order)), minor=True)
    ax.grid(which="minor", color="white", lw=1.2)
    ax.tick_params(which="minor", length=0)
    for j, c in enumerate(cols):
        ax.text(j, len(order) - 0.42, f"{exp[c]:.0f}%", ha="center", va="top", fontsize=6, color=MUTED)
    ax.text(-0.55, len(order) - 0.42, "expected", ha="right", va="top", fontsize=6, color=MUTED)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.06, pad=0.16, aspect=30)
    cb.set_label("Share of a tradition's links to the community minus the shuffle expectation (percentage points)", fontsize=6.3)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2, labelsize=6)
    if bool(sig.to_numpy().any()):
        cb.ax.text(0.0, -3.4, "* outside the label shuffles at p < 0.05 after Bonferroni correction", transform=cb.ax.transAxes,
                   fontsize=6, color=MUTED, va="top")
    save(fig, ctx, "fig3_placement")


# ----------------------------------------------------------------- figure 4
def fig4(ctx: Ctx, reps: list[str]) -> None:
    cal = pd.read_csv(ctx.results / "calibration.csv").set_index("representation")
    hand = read_json(ctx.results / "hand_label_agreement.json") if (ctx.results / "hand_label_agreement.json").exists() else {"status": "pending"}
    w = ctx.paper["figures"]["single_column_in"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(w, w * 0.62), gridspec_kw=dict(width_ratios=[1.6, 1], wspace=0.6))
    xs = [1.5 * k for k in range(len(reps))]
    for x, rep in zip(xs, reps):
        r = cal.loc[rep]
        ax.bar(x, r["recall_at_k"], width=0.7, color=BLUE, zorder=2)
        ax.plot([x, x], [r["ci_low"], r["ci_high"]], color=INK, lw=0.8, zorder=3)
        ax.text(x, r["ci_high"] + 0.02, f"{r['recall_at_k']:.2f}", ha="center", va="bottom", fontsize=6.8)
    chance = float(cal.loc[reps[0], "chance_at_k"])
    ax.axhline(chance, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=4)
    ax.text(xs[-1] + 0.5, chance + 0.02, f"chance\n{chance:.2f}", fontsize=6.3, color=MUTED, ha="left", va="bottom", linespacing=1.0)
    ax.set_xticks(xs, [REP_NAME[r] for r in reps])
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.65, xs[-1] + 1.35)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Recall@10")
    ax.set_title(f"Known parallels found\n({int(cal.loc[reps[0], 'queries'])} religious retellings)", loc="left")
    panel_letter(ax, "a")

    bx.set_ylim(0, 1)
    bx.set_title("Top-1 pairs judged\nparallel by hand", loc="left")
    panel_letter(bx, "b")
    if hand.get("status") in ("complete", "partial") and "precision" in hand:
        vals = [hand["precision"][k].get("both_coders_agree_it_is_a_parallel", np.nan) for k in ("strict", "lenient")]
        for x, v in enumerate(vals):
            bx.bar(x, v, width=0.56, color=BLUE, zorder=2)
            bx.text(x, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=6.8)
        bx.set_xticks([0, 1], ["same plot", "plot or\nmotif"])
        bx.tick_params(axis="x", length=0)
        bx.set_xlim(-0.55, 1.45)
        bx.set_ylabel("Precision (both coders)")
        if "cohen_kappa" in hand:
            bx.text(0.98, 0.97, f"κ = {hand['cohen_kappa']:.2f}\nn = {hand['coded_by_both']}", transform=bx.transAxes, fontsize=6.3,
                    ha="right", va="top", color=MUTED)
    else:
        bx.set_xticks([])
        bx.set_yticks([0, 0.5, 1])
        bx.set_ylabel("Precision")
        bx.text(0.5, 0.5, "pending:\n100 pairs,\ntwo coders", transform=bx.transAxes, ha="center", va="center", fontsize=6.8,
                color=MUTED, linespacing=1.25)
    save(fig, ctx, "fig4_calibration")


def run(ctx: Ctx) -> dict:
    style()
    primary = ctx.primary
    reps = [primary] + [r for r in ctx.reps if r != primary]
    fig1(ctx, primary)
    fig2(ctx, reps)
    fig3(ctx, primary)
    fig4(ctx, ["tfidf", "embedding"] if set(ctx.reps) >= {"tfidf", "embedding"} else reps)
    from .report import write
    write(ctx)
    print(f"  figures in {ctx.figures.relative_to(ctx.figures.parents[1 if ctx.sample else 0]).as_posix()}/ ; RESULTS.md written")
    return dict(primary=primary)
