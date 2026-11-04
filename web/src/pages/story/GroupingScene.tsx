import { useMemo, useState } from "react";
import type { Rep } from "../../data/types";
import { NetworkCanvas } from "../../components/NetworkCanvas";
import { useGraphModel, type ColourBy } from "../../components/useGraphModel";
import { NullHistogram } from "../../components/charts";
import { HowMade, Legend, Loading, Segmented } from "../../components/ui";
import { codes, nmi, shuffled } from "../../lib/stats";
import { fmt, labelName, times } from "../../lib/format";
import { useFindings, verdict } from "./shared";

export function GroupingScene() {
  const [rep, setRep] = useState<Rep>("semantic");
  const [colourBy, setColourBy] = useState<ColourBy>("community");
  const [shuffleSeed, setShuffleSeed] = useState<number | null>(null);
  const F = useFindings();
  const base = useGraphModel({ cohort: "joint", rep, density: 0.1, colourBy, layoutMode: "network" });
  const labelSys = colourBy === "region" ? "region" : "atu";
  // label vectors in model order (full ATU types for statistics, chapters only for colour)
  const actual = useMemo(() => base.rows.map((r) => (labelSys === "atu" ? r?.atu ?? null : r?.region ?? null)), [base.rows, labelSys]);
  const perm = useMemo(() => (shuffleSeed === null ? null : shuffled(actual.map((_, i) => i), shuffleSeed)), [shuffleSeed, actual]);
  const shuffledLabels = useMemo(() => (perm ? perm.map((k) => actual[k]) : null), [perm, actual]);
  const chapterOf = useMemo(() => new Map(base.rows.map((r) => [r?.atu ?? "", r?.atu_chapter ?? null])), [base.rows]);
  const override = useMemo(() => {
    if (!shuffledLabels || colourBy === "community") return null;
    return colourBy === "atu" ? shuffledLabels.map((a) => chapterOf.get(a ?? "") ?? null) : shuffledLabels;
  }, [shuffledLabels, colourBy, chapterOf]);
  const model = useGraphModel({ cohort: "joint", rep, density: 0.1, colourBy, layoutMode: "network", labelOverride: override });
  const graphId = `joint-${rep}-d10`;
  const browserNmi = useMemo(() => (base.communities.length ? nmi(base.communities, codes(actual)) : null), [base.communities, actual]);
  const drawNmi = useMemo(() => (shuffledLabels && base.communities.length ? nmi(base.communities, codes(shuffledLabels)) : null), [shuffledLabels, base.communities]);

  if (F.error) return <p className="state error">{F.error}</p>;
  const labels = ["atu", "place", "region"] as const;
  const stats = labels.map((l) => {
    const r = F.row(graphId, l);
    const nb = F.neighbours?.results[`joint|${rep}`]?.[l];
    return { l, r, nb, excess: r?.nmi.excess ?? 0, rr: r?.assortativity.observed ?? 0, lift: nb?.lift ?? 0 };
  });
  const src = F.row(graphId, "source");
  const v1 = verdict({ excess: stats[0].excess, r: stats[0].rr, lift: stats[0].lift }, { excess: stats[1].excess, r: stats[1].rr, lift: stats[1].lift }, "ATU type", "place");
  const v2 = verdict({ excess: stats[0].excess, r: stats[0].rr, lift: stats[0].lift }, { excess: stats[2].excess, r: stats[2].rr, lift: stats[2].lift }, "ATU type", "broad region");

  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <Segmented label="Representation" value={rep} onChange={(v) => { setRep(v); setShuffleSeed(null); }} options={[{ value: "lexical", label: "TF–IDF" }, { value: "semantic", label: "Embeddings" }]} />
        <Segmented label="Colour by" value={colourBy} onChange={(v) => { setColourBy(v); setShuffleSeed(null); }} options={[{ value: "community", label: "Discovered communities" }, { value: "atu", label: "ATU (tale type)" }, { value: "region", label: "Broad region" }]} />
        {colourBy !== "community" && (shuffleSeed === null
          ? <button className="btn accent" onClick={() => setShuffleSeed(Date.now() % 100000)}>Shuffle labels</button>
          : <>
              <button className="btn" onClick={() => setShuffleSeed((s) => (s ?? 0) + 1)}>Shuffle again</button>
              <button className="btn primary" onClick={() => setShuffleSeed(null)}>Restore actual labels</button>
            </>)}
      </div>
      <div className="grid-main-side" style={{ ["--side" as string]: "470px" }}>
        <figure className="figure" style={{ margin: 0, padding: 10 }}>
          {!model.ready ? <Loading what="the network" /> : (
            <div style={{ height: 440, display: "flex" }}>
              <NetworkCanvas zoomMode="gentle" ariaLabel={`Joint-cohort network (${rep}), coloured by ${colourBy}${shuffleSeed !== null ? " after shuffling the labels" : ""}.`}
                n={model.nodes.length} positions={model.positions} colours={model.colours}
                tooltip={(i) => { const r = model.rows[i]; return r ? { title: r.title, lines: [`ATU ${r.atu} · ${r.region}`] } : null; }}
                transition={{ key: `${colourBy}|${rep}|${shuffleSeed}`, duration: 500 }} radius={2.6} edges={[]} />
            </div>
          )}
          <Legend title={shuffleSeed !== null ? `${model.legend.title} — SHUFFLED (one draw)` : model.legend.title} items={model.legend.items.slice(0, 14)} ring={model.legend.ring} />
          {colourBy === "atu" && <p className="caption">For readability, colours show the 7 ATU chapters; the statistics use all {F.summary?.counts.joint_distinct_atu ?? "164"} tale types.</p>}
        </figure>
        <div>
          {colourBy !== "community" && F.nulls && (() => {
            const key = `${graphId}|${labelSys}`;
            const vals = F.nulls!.nmi[key];
            const row = F.row(graphId, labelSys);
            return vals && row ? (
              <div className="figure" style={{ marginTop: 0 }}>
                <div className="figure-title">NMI between communities and {labelName(labelSys).toLowerCase()}</div>
                <NullHistogram values={vals} observed={row.nmi.observed} draw={drawNmi} label={`NMI ${labelSys}`} />
                <div className="caption">
                  Grey: 1,000 saved label shuffles (graph and communities fixed). {drawNmi !== null ? <>Your shuffled draw: <strong>{fmt(drawNmi)}</strong>, one draw, not a new analysis.</> : "Press “Shuffle labels” to make one draw in your browser."}
                  {" "}Recomputed here from actual labels: {fmt(browserNmi)} (pipeline {fmt(row.nmi.observed)}).
                </div>
              </div>
            ) : null;
          })()}
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Label system ({rep === "lexical" ? "TF–IDF" : "embeddings"}, 10%)</th><th className="num">NMI (shuffled)</th><th className="num">Excess</th><th className="num">r</th><th className="num">Top-10 lift (excl. same src)</th></tr></thead>
              <tbody>
                {stats.map(({ l, r, nb }) => (
                  <tr key={l}>
                    <td>{labelName(l)} <span className="muted">· {r?.categories} cat.</span></td>
                    <td className="num">{fmt(r?.nmi.observed)} <span className="muted">({fmt(r?.nmi.null_mean)})</span></td>
                    <td className="num"><strong>{fmt(r?.nmi.excess)}</strong></td>
                    <td className="num">{fmt(r?.assortativity.observed)}</td>
                    <td className="num">{times(nb?.lift)} <span className="muted">({times(nb?.lift_excl_same_source)})</span></td>
                  </tr>
                ))}
                {src && <tr className="muted"><td>Source (diagnostic only)</td><td className="num">{fmt(src.nmi.observed)} ({fmt(src.nmi.null_mean)})</td><td className="num">{fmt(src.nmi.excess)}</td><td className="num">{fmt(src.assortativity.observed)}</td><td className="num">–</td></tr>}
              </tbody>
            </table>
          </div>
          <ul className="sans small" style={{ paddingLeft: 18 }}>
            <li>Every label system beats all 1,000 shuffles on NMI and assortativity: {stats.every((s) => s.r?.nmi.exceeds_all && s.r?.assortativity.exceeds_all) ? "yes" : "no"}.</li>
            <li>ATU type vs place: <strong>{v1.text}</strong>.</li>
            <li>ATU type vs broad region: <strong>{v2.text}</strong>.</li>
            <li>Source dependence: {fmt((F.neighbours?.results[`joint|${rep}`]?.share_neighbours_same_source ?? 0) * 100, 1)}% of nearest neighbours come from the same bibliographic source. Excluding them changes the lifts only to the values in brackets.</li>
            <li>Not driven by a few big categories: {fmt((stats[0].nb?.share_of_categories_above_baseline ?? 0) * 100, 0)}% of ATU types and {fmt((stats[1].nb?.share_of_categories_above_baseline ?? 0) * 100, 0)}% of places (with ≥ 2 tales) have a same-label neighbour rate above their own baseline.</li>
          </ul>
          {stats[0].nb && (
            <details className="sans small">
              <summary style={{ cursor: "pointer", color: "var(--teal)", fontWeight: 600 }}>Per-category neighbour rates (largest categories)</summary>
              <div className="table-wrap" style={{ maxHeight: 260, marginTop: 6 }}>
                <table className="data">
                  <thead><tr><th>Category</th><th className="num">Tales</th><th className="num">Share of top-10 with same label</th><th className="num">Chance baseline</th></tr></thead>
                  <tbody>
                    {(["atu", "region"] as const).flatMap((lab) => (F.neighbours?.results[`joint|${rep}`]?.[lab].per_category ?? []).slice(0, lab === "atu" ? 12 : 13).map((c) => (
                      <tr key={lab + c.category}><td>{lab === "atu" ? `ATU ${c.category}` : c.category}</td><td className="num">{c.n}</td><td className="num">{fmt(c.rate * 100, 1)}%</td><td className="num">{fmt(c.baseline * 100, 1)}%</td></tr>
                    )))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </div>
      </div>
      <div className="prose-wide" style={{ marginTop: 16 }}>
        {(() => {
          const typeLeadsBoth = stats[0].excess > Math.max(stats[1].excess, stats[2].excess) && stats[0].lift > Math.max(stats[1].lift, stats[2].lift);
          const regionLeadsR = stats[2].rr > stats[0].rr;
          return (
            <p><strong>Reading the three measures.</strong> <em>NMI excess</em> is how much more the discovered communities tell you about a label than shuffled labels would. <em>Top-10 lift</em> is how many times more often a tale's ten nearest tales share its label than chance would. {typeLeadsBoth
              ? <>On both, <strong>tale type is far stronger than geography</strong> here.</>
              : <>On these two measures the ordering is not uniform here.</>}{" "}A tale's close textual neighbours are {times(stats[0].lift, 1)} more likely than chance to share its ATU type, against {times(stats[1].lift)} for place and {times(stats[2].lift)} for broad region. <em>Assortativity r</em> instead measures the share of all edges that are “extra” same-label edges. {regionLeadsR
              ? <>Because there are only {F.summary?.counts.joint_distinct_region ?? 13} regions and some are very large, geography accounts for a larger share of edges (r {fmt(stats[2].rr)} vs {fmt(stats[0].rr)} for type).</>
              : <>Here type also has the larger r ({fmt(stats[0].rr)} vs {fmt(stats[2].rr)} for region).</>}{" "}By the rule fixed in advance (all three measures must agree), type versus broad region is <strong>{v2.consistent ? v2.text : "mixed"}</strong> and type versus place is <strong>{v1.consistent ? v1.text : "mixed"}</strong>.{typeLeadsBoth && regionLeadsR && " The summary: type is the sharper signal per tale; geography is a broad, diffuse one."}</p>
          );
        })()}
      </div>
      <HowMade
        measured="Agreement between the Louvain partition (weighted, seed 42, 10% density) and each label system: NMI, attribute assortativity (unweighted), and the ten-nearest-neighbour label rate against its frequency baseline."
        records="Joint cohort, 1,133 tales: identical node set and partition for every label system."
        method="NMI against ground-truth labels (week 4, §4); attribute assortativity and label shuffling (week 3, §7 and Goodies ‘Shuffling the labels’); permutation logic (week 2, §7); neighbour check (weeks 5–7)."
        infer="Whether, and how strongly, each recorded label is associated with textual neighbourhoods beyond what label frequencies produce on this fixed graph."
        cannot="Population-wide claims or independence: tales share sources, translators and ancestry, which the shuffle does not remove. Scores for label systems with different category counts are not directly comparable effect sizes." />
    </div>
  );
}
