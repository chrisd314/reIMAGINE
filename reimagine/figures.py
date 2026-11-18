"""Stage `figures`: the paper's figures around one headline, then the report material
in report/ (RESULTS.md, captions.md, short_update.md, numbers.tex, table1.tex; see reimagine/report.py).

Figures are drawn at PNAS column widths with a colour-blind-safe palette: three categorical hues at most
(blue, orange, green), greys for everything else, text never set in a series colour, every panel lettered.
  fig1_map            background: the map of world folklore (disparity backbone, coloured by community), and
                      what the communities follow: tale type, region, source collection against two nulls
  fig2_headline       headline: where each tradition's parables land compared with non-story text of the same
                      translation (community excess, voted tale types), and how much closer they are to
                      folktales than that baseline and than length-matched folktale excerpts
  fig3_validity       calibration recall@10 and type-vote accuracy (TF-IDF, embeddings, nouns masked, chance)
  figS1_labels        supplementary: tale type, region and source collection across all edge constructions
  figS2_headline_embeddings  supplementary: Figure 2 with the second representation
No figure or table title claims anything about morals or lessons: text similarity does not measure them.
"""
from __future__ import annotations

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402

from .common import Ctx  # noqa: E402

BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, RULE, BAND = "#1f2933", "#6b7785", "#d9dee4", "#e8ebef"
OTHER, SMALL = "#9aa5b1", "#cfd5db"            # communities beyond the three largest; groups under 1% of the map
HUES = [BLUE, ORANGE, GREEN]
REP_NAME = {"tfidf": "TF-IDF", "embedding": "Embeddings", "tfidf_nouns_masked": "TF-IDF, nouns masked"}


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
        fig.savefig(ctx.figures / f"{name}.{ext}", dpi=ctx.paper["figures"]["dpi"], bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def letter(fig, x: float, y: float, s: str) -> None:
    fig.text(x, y, s, fontsize=9, fontweight="bold", va="top", ha="left")


def community_colour(names: list[str]) -> dict[str, str]:
    """The three largest communities get the three hues; the others grey (direct labels tell them apart)."""
    majors = [c for c in names if c != "small"]
    return {c: (HUES[k] if k < 3 else OTHER) for k, c in enumerate(majors)} | {"small": SMALL}


def short_type(atu: str, name: str, width: int = 26) -> str:
    name = str(name).split(" (previously")[0].split(" [")[0]
    name = name[4:] if name.startswith("The ") else name
    return textwrap.shorten(f"{atu} {name}", width=width, placeholder="…")


def spread(points: np.ndarray, min_dx: float, min_dy: float, rounds: int = 300) -> np.ndarray:
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


def headline_order(ctx: Ctx, variant: str) -> list[str]:
    hb = pd.read_csv(ctx.results / "headline_by_tradition.csv")
    return hb[hb["variant"] == variant].sort_values("diff", ascending=False)["tradition"].tolist()


# ----------------------------------------------------------------- figure 1: the map of world folklore
def null_rows(ctx: Ctx, rep: str) -> pd.DataFrame:
    cc = pd.read_csv(ctx.results / "collection_confound.csv")
    return cc[(cc["rep"] == rep) & cc["map"].str.startswith("canonical")]


def label_panel(ax, rows: pd.DataFrame, measure: str, xlabel: str) -> None:
    """Observed value (dot) against the middle 95% of the plain label shuffles (dark bar) and of the shuffles within
    source collection (light bar), for tale type, region and source collection."""
    labels = [("atu_type", "Tale type"), ("region", "Region"), ("source_collection", "Source collection")]
    r = rows[rows["measure"] == measure].set_index(["label", "null"])
    hi = 0.0
    for y, (key, name) in enumerate(labels):
        for dy, null, colour, lw in ((-0.13, "label shuffle", MUTED, 3.6), (0.17, "within-collection shuffle", SMALL, 3.6)):
            if (key, null) not in r.index:
                continue
            x = r.loc[(key, null)]
            ax.plot([x["null_q025"], x["null_q975"]], [y + dy] * 2, color=colour, lw=lw, solid_capstyle="butt", zorder=2)
            hi = max(hi, x["null_q975"])
        obs = r.loc[(key, "label shuffle"), "observed"]
        ax.scatter([obs], [y - 0.13], s=16, c=INK, zorder=4, linewidths=0)
        ax.annotate(f"{obs:.2f}" if measure == "nmi" else f"{obs:.3f}", (obs, y - 0.13), xytext=(4, 0), textcoords="offset points",
                    fontsize=6.3, va="center")
        hi = max(hi, obs)
    ax.set_yticks(range(len(labels)), [n for _, n in labels])
    ax.set_ylim(len(labels) - 0.5, -0.6)
    lo = min(0.0, float(rows[rows["measure"] == measure]["null_q025"].min()) * 1.2)
    ax.set_xlim(lo, hi + 0.3 * (hi - lo))
    ax.xaxis.set_major_locator(plt.MaxNLocator(4))
    ax.set_xlabel(xlabel, labelpad=2)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.axvline(0, color=RULE, lw=0.6, zorder=1)


def fig1(ctx: Ctx, rep: str) -> None:
    z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
    xy, group = z["xy"], z["group"]
    from .network import backbone_path
    nc = ctx.paper["network"]
    bbp = backbone_path(ctx, rep, nc["backbone_drawn_from"], nc["backbone_drawn_alpha"])
    bb = np.load(bbp, allow_pickle=False) if bbp.exists() else None
    comm = pd.read_csv(ctx.results / "community_table.csv")
    comm = comm[comm["rep"] == rep].set_index("community")
    names = list(comm.index)
    colour = community_colour(names)
    deg = np.bincount(np.concatenate([z["i"], z["j"]]), minlength=len(xy))
    shown = deg > 0
    gname = np.array([f"C{g + 1}" if g >= 0 else "small" for g in group])

    w = ctx.paper["figures"]["double_column_in"]
    fig = plt.figure(figsize=(w, w * 0.62))
    ax = fig.add_axes([0.0, 0.085, 0.57, 0.9])
    if bb is not None and len(bb["i"]):
        ax.add_collection(LineCollection(np.stack([xy[bb["i"]], xy[bb["j"]]], axis=1), colors=INK, linewidths=0.3, alpha=0.22, zorder=1))
    order = np.argsort([0 if c == "small" else (1 if colour[c] == OTHER else 2) for c in gname], kind="stable")
    order = order[shown[order]]
    ax.scatter(xy[order, 0], xy[order, 1], s=3.2, c=[colour[c] for c in gname[order]], linewidths=0, zorder=2)
    lo, hi = np.quantile(xy[shown], 0.003, axis=0), np.quantile(xy[shown], 0.997, axis=0)
    pad = 0.04 * (hi - lo)
    ax.set_xlim(lo[0] - pad[0], hi[0] + pad[0])
    ax.set_ylim(lo[1] - pad[1], hi[1] + pad[1])
    majors = [c for c in names if c != "small"]
    centres = np.array([np.median(xy[(gname == c) & shown], axis=0) for c in majors])
    tags = spread(centres, 0.16 * (hi[0] - lo[0]), 0.055 * (hi[1] - lo[1]))
    for c, (cx, cy) in zip(majors, tags):
        words = ", ".join(str(comm.at[c, "top_words"]).split(", ")[:2])
        ax.text(cx, cy, f"{c} {words}", fontsize=6.4, ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=colour[c], lw=1.0, alpha=0.92))
    ax.set_aspect("equal")
    ax.axis("off")
    letter(fig, 0.0, 0.995, "a")
    n_edges = int(len(bb["i"])) if bb is not None else 0
    note = (f"{int(shown.sum()):,} folktales placed by the full 10% similarity network (ForceAtlas2); lines: disparity backbone of the "
            f"complete similarity graph (α = {ctx.paper['network']['backbone_drawn_alpha']}, {n_edges:,} edges). Communities: Louvain on the full network.")
    fig.text(0.0, 0.0, textwrap.fill(note, 105), fontsize=5.8, color=MUTED, va="bottom", ha="left", linespacing=1.2)

    # ---- b: the communities
    lx = fig.add_axes([0.6, 0.5, 0.4, 0.48])
    lx.axis("off")
    rows = names
    lx.set_xlim(0, 1)
    lx.set_ylim(len(rows) + 0.1, -1.3)
    lx.text(0.0, -0.85, "Communities: most distinctive words", fontsize=7.3, va="center")
    lx.text(1.0, -0.85, "tales", fontsize=6.3, va="center", ha="right", color=MUTED)
    for r, c in enumerate(rows):
        lx.scatter([0.02], [r], s=18, c=colour[c], linewidths=0)
        if c == "small":
            lx.text(0.06, r, "groups under 1% of the map", fontsize=6.4, va="center", color=MUTED)
        else:
            lx.text(0.06, r, c, fontsize=6.5, fontweight="bold", va="center")
            lx.text(0.15, r, ", ".join(str(comm.at[c, "top_words"]).split(", ")[:4]), fontsize=6.4, va="center")
        lx.text(1.0, r, f"{int(comm.at[c, 'size'])}", fontsize=6.3, va="center", ha="right", color=MUTED)
    letter(fig, 0.585, 0.995, "b")

    # ---- c, d: what the communities follow
    rows_ = null_rows(ctx, rep)
    cx_ = fig.add_axes([0.715, 0.285, 0.27, 0.12])
    label_panel(cx_, rows_, "nmi", "NMI with the communities")
    dx_ = fig.add_axes([0.715, 0.07, 0.27, 0.12])
    label_panel(dx_, rows_, "assortativity", "Attribute assortativity")
    letter(fig, 0.585, 0.475, "c")
    letter(fig, 0.585, 0.215, "d")
    n_lab = int(rows_["n"].iloc[0])
    fig.text(0.61, 0.472, f"What the communities follow ({n_lab:,} tales with all three labels)", fontsize=7.3, va="top")
    fig.text(0.61, 0.447, "dot: observed; dark bar: middle 95% of label shuffles;\nlight bar: same, shuffled within source collection",
             fontsize=5.8, color=MUTED, va="top", linespacing=1.2)
    save(fig, ctx, "fig1_map")


# ----------------------------------------------------------------- figure 2: the headline
def fig2(ctx: Ctx, variant: str, name: str) -> None:
    hb = pd.read_csv(ctx.results / "headline_by_tradition.csv")
    hb = hb[hb["variant"] == variant].set_index("tradition")
    cells = pd.read_csv(ctx.results / "headline_community_excess.csv")
    cells = cells[cells["variant"] == variant]
    types = pd.read_csv(ctx.results / "headline_atu_by_tradition.csv")
    types = types[(types["variant"] == variant) & (types["kind"] == "parable")]
    lc = pd.read_csv(ctx.results / "length_control.csv")
    rep = hb["rep"].iloc[0]
    lc = lc[(lc["rep"] == rep) & (lc["kind"] == "parable")].set_index("tradition")
    order = [t for t in headline_order(ctx, variant) if t in hb.index]
    comms = list(dict.fromkeys(cells["community"]))
    words = cells.drop_duplicates("community").set_index("community")["community_words"].astype(str)

    w = ctx.paper["figures"]["double_column_in"]
    fig = plt.figure(figsize=(w, w * 0.82))
    left, right, top, h = 0.135, 0.995, 0.875, 0.4
    gap = 0.012
    pw = (right - left - gap * (len(order) - 1)) / len(order)
    lim = float(np.nanmax(np.abs(cells[["excess_ci_low", "excess_ci_high"]].to_numpy()))) * 100 * 1.08
    for k, t in enumerate(order):
        ax = fig.add_axes([left + k * (pw + gap), top - h, pw, h])
        c = cells[cells["tradition"] == t].set_index("community").loc[comms]
        y = np.arange(len(comms))
        v = c["excess"].to_numpy() * 100
        sig = c["significant_bonferroni"].to_numpy(bool)
        sig05 = c["significant_05"].to_numpy(bool)
        cols = [to_rgba(BLUE if x >= 0 else ORANGE, 1.0 if s else (0.55 if s5 else 0.25)) for x, s, s5 in zip(v, sig, sig05)]
        ax.barh(y, v, height=0.62, color=cols, zorder=2)
        ax.hlines(y, c["excess_ci_low"] * 100, c["excess_ci_high"] * 100, color=INK, lw=0.5, zorder=3)
        for yy, x, s in zip(y, v, sig):
            if s:
                ax.text(x + (1.2 if x >= 0 else -1.2), yy, "*", ha="left" if x >= 0 else "right", va="center", fontsize=8, zorder=4)
        ax.axvline(0, color=INK, lw=0.6, zorder=1)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(len(comms) - 0.5, -0.6)
        ax.xaxis.grid(True, color=RULE, lw=0.4)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
        if k == 0:
            ax.set_yticks(y, [f"{cm}  {', '.join(str(words.get(cm, '')).split()[:2])}" if cm != "small" else "small groups" for cm in comms])
        else:
            ax.set_yticks(y, [""] * len(y))
        ax.spines["left"].set_visible(False)
        r = hb.loc[t]
        ax.set_title(f"{t}\n{int(r['n_parables'])} parables, {int(r['n_baseline'])} baseline", loc="center", fontsize=7, linespacing=1.15)
        tt = types[types["tradition"] == t].sort_values("rank").head(3)
        lines = [f"{s:.0%} {short_type(a, n, width=25)}" for a, n, s in zip(tt["atu_id"], tt["atu_name"], tt["share"])]
        ax.text(0.0, -0.19, "\n".join(lines), transform=ax.transAxes, ha="left", va="top", fontsize=5.4, linespacing=1.3)
        if k == len(order) // 2:
            ax.set_xlabel("parable share minus baseline share of links (percentage points)", labelpad=2)
    fig.text(left - 0.13, top - h - 0.075, "Most voted\ntale types\n(share of\nparables)", fontsize=5.8, color=MUTED, va="top", linespacing=1.15)
    letter(fig, 0.0, 0.995, "a")
    fig.text(0.03, 0.995, f"Where parables land, against non-story text of the same translation ({REP_NAME[variant]})", fontsize=7.6, va="top")
    fig.text(0.03, 0.968, "Blue: more parable links than baseline links; orange: fewer. Solid with *: p < 0.05 after Bonferroni "
             "correction; medium: p < 0.05; pale: not significant. Lines: 95% bootstrap intervals.", fontsize=5.8, color=MUTED, va="top")

    # ---- b: how much closer to folktales
    bx = fig.add_axes([left, 0.05, 0.52, 0.19])
    yb = np.arange(len(order))
    for dy, label, col, marker, get in (
            (-0.16, "minus non-story text of the same translation", BLUE, "o",
             lambda t: (hb.at[t, "diff"], hb.at[t, "diff_ci_low"], hb.at[t, "diff_ci_high"], hb.at[t, "diff_p_upper"] < 0.05)),
            (0.16, "minus folktale excerpts of the same length", ORANGE, "D",
             lambda t: (lc.at[t, "diff_median"], lc.at[t, "diff_ci_low"], lc.at[t, "diff_ci_high"], lc.at[t, "diff_ci_high"] < 0 or lc.at[t, "diff_ci_low"] > 0))):
        for yy, t in zip(yb, order):
            if t not in hb.index or (col == ORANGE and t not in lc.index):
                continue
            d, lo_, hi_, s = get(t)
            bx.plot([lo_, hi_], [yy + dy] * 2, color=col, lw=1.0, zorder=2)
            bx.scatter([d], [yy + dy], s=16, marker=marker, facecolors=col if s else "white", edgecolors=col, linewidths=0.9, zorder=3)
    bx.axvline(0, color=INK, lw=0.6, zorder=1)
    bx.set_yticks(yb, order)
    bx.set_ylim(len(order) - 0.5, -0.6)
    bx.tick_params(axis="y", length=0)
    bx.xaxis.grid(True, color=RULE, lw=0.4)
    bx.set_axisbelow(True)
    bx.set_xlabel(f"difference in folk-closeness, median ({REP_NAME[variant]})", labelpad=2)
    letter(fig, 0.0, 0.3, "b")
    fig.text(0.03, 0.3, "How much closer to folktales are the parables?", fontsize=7.6, va="top")
    handles = [plt.Line2D([], [], color=BLUE, marker="o", lw=1, ms=4, label="parables minus non-story text of the same translation"),
               plt.Line2D([], [], color=ORANGE, marker="D", lw=1, ms=3.5, label="parables minus folktale excerpts of the same length")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(left + 0.535, 0.23), frameon=False, fontsize=6.2, handlelength=1.8)
    fig.text(left + 0.545, 0.125, "Filled: permutation p < 0.05 (within tradition) or\n95% interval excludes 0. Right of 0: parables\n"
             "closer to folktales than the comparison.", fontsize=5.8, color=MUTED, va="top", linespacing=1.2)
    save(fig, ctx, name)


# ----------------------------------------------------------------- figure 3: validity
def fig3(ctx: Ctx) -> None:
    cal = pd.read_csv(ctx.results / "calibration.csv").set_index("representation")
    variants = [v for v in ("tfidf", "embedding", "tfidf_nouns_masked") if v in cal.index]
    w = ctx.paper["figures"]["double_column_in"]
    fig, axes = plt.subplots(1, 2, figsize=(w, w * 0.3), gridspec_kw=dict(wspace=0.35))
    labels = ["TF-IDF", "Embed-\ndings", "TF-IDF,\nnouns\nmasked"]
    for ax, (col, lo, hi, chance, chance_lo, chance_hi, title) in zip(axes, (
            ("recall_at_k", "ci_low", "ci_high", "chance_at_k", None, None, "Same-type folktale\namong the 10 nearest"),
            ("vote_accuracy", None, None, "vote_chance", "vote_chance_low", "vote_chance_high", "Type voted by the\n10 nearest is right"))):
        xs = np.arange(len(variants))
        vals = cal.loc[variants, col].to_numpy()
        ax.bar(xs, vals, width=0.6, color=BLUE, zorder=2)
        if lo:
            ax.vlines(xs, cal.loc[variants, lo], cal.loc[variants, hi], color=INK, lw=0.8, zorder=3)
        for x, v in zip(xs, vals):
            top = cal.loc[variants[x], hi] if hi else v
            ax.text(x, top + 0.025, f"{v:.2f}", ha="center", va="bottom", fontsize=6.5)
        ch = float(cal.loc[variants[0], chance])
        if chance_lo:
            ax.axhspan(cal.loc[variants[0], chance_lo], cal.loc[variants[0], chance_hi], color=BAND, zorder=0, lw=0)
        ax.axhline(ch, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=4)
        ax.text(len(variants) - 0.62, ch + 0.015, f"chance\n{ch:.3f}", fontsize=6, color=MUTED, ha="left", va="bottom", linespacing=1.0)
        ax.set_xticks(xs, labels[:len(variants)], linespacing=1.0)
        ax.set_xlim(-0.55, len(variants) - 0.05)
        ax.tick_params(axis="x", length=0)
        ax.set_ylim(0, 1)
        ax.set_title(title, loc="left", fontsize=7, linespacing=1.15)
    axes[0].set_ylabel(f"Share of the {int(cal.loc[variants[0], 'queries'])} religious retellings")
    for ax, s in zip(axes, "ab"):
        ax.annotate(s, xy=(0, 1), xycoords="axes fraction", xytext=(-22, 8), textcoords="offset points", fontsize=9,
                    fontweight="bold", va="bottom", ha="right", annotation_clip=False)
    save(fig, ctx, "fig3_validity")


# ----------------------------------------------------------------- supplementary S1: labels across edge constructions
def figS1(ctx: Ctx) -> None:
    nr = pd.read_csv(ctx.results / "network_robustness.csv")
    w = ctx.paper["figures"]["double_column_in"]
    fig, axes = plt.subplots(1, len(ctx.reps), figsize=(w, w * 0.32), sharey=True, squeeze=False)
    for ax, rep in zip(axes[0], ctx.reps):
        r = nr[nr["rep"] == rep].reset_index(drop=True)
        xt = [("10%,\nmasked" if "masked" in str(e) else (f"{v * 100:.0f}%" if e == "density" else f"k = {int(v)}")) for e, v in zip(r["edges_by"], r["value"])]
        xs = np.arange(len(r))
        for (label, name), col, dx in zip((("atu_type", "tale type"), ("region", "region"), ("source_collection", "source collection")),
                                          HUES, (-0.18, 0.0, 0.18)):
            ex = r[f"{label}_nmi"] - r[f"{label}_nmi_null_mean"]
            ax.scatter(xs + dx, ex, s=14, c=col, linewidths=0, zorder=3, label=f"{name}, over label shuffles")
            if f"{label}_nmi_within_collection_null_mean" in r:
                exw = r[f"{label}_nmi"] - r[f"{label}_nmi_within_collection_null_mean"]
                ax.scatter(xs + dx, exw, s=14, facecolors="white", edgecolors=col, linewidths=0.9, zorder=3,
                           label=f"{name}, over shuffles within collection")
        canon = int(np.flatnonzero(r["canonical"].to_numpy(bool))[0])
        ax.axvspan(canon - 0.45, canon + 0.45, color=BAND, zorder=0, lw=0)
        ax.axhline(0, color=INK, lw=0.6, zorder=1)
        ax.set_xticks(xs, xt, fontsize=6, linespacing=1.0)
        ax.tick_params(axis="x", length=0)
        ax.set_title(REP_NAME[rep], loc="left")
        ax.yaxis.grid(True, color=RULE, lw=0.4)
        ax.set_axisbelow(True)
    axes[0][0].set_ylabel("NMI with the communities\nminus the null mean")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.2), fontsize=6.2, columnspacing=1.4)
    for ax, s in zip(axes[0], "ab"):
        ax.annotate(s, xy=(0, 1), xycoords="axes fraction", xytext=(-18, 6), textcoords="offset points", fontsize=9,
                    fontweight="bold", va="bottom", ha="right", annotation_clip=False)
    fig.tight_layout(w_pad=1.5)
    save(fig, ctx, "figS1_labels")


def check_primary(ctx: Ctx) -> str:
    """The main figure uses the representation with the higher calibration recall@10 (ai-assist/DECISIONS.md R3); refuse to
    draw if paper.yaml says otherwise."""
    cal = pd.read_csv(ctx.results / "calibration.csv").set_index("representation")
    best = max(ctx.reps, key=lambda r: cal.at[r, "recall_at_k"])
    assert best == ctx.primary, f"calibration now favours {best}; update primary_representation in paper.yaml"
    return best


def run(ctx: Ctx) -> dict:
    style()
    primary = check_primary(ctx)
    fig1(ctx, primary)
    fig2(ctx, primary, "fig2_headline")
    for o in [r for r in ctx.reps if r != primary]:
        fig2(ctx, o, f"figS2_headline_{o}")
    fig3(ctx)
    figS1(ctx)
    from .report import write
    write(ctx)
    rel = lambda p: p.relative_to(p.parents[1 if ctx.sample else 0]).as_posix()
    print(f"  figures in {rel(ctx.figures)}/ ; report material (RESULTS.md, captions.md, short_update.md, numbers.tex, table1.tex) "
          f"in {rel(ctx.report)}/")
    return dict(primary=primary)
