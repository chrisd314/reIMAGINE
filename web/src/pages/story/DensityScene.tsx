import { useMemo, useState } from "react";
import type { Rep } from "../../data/types";
import { NetworkCanvas } from "../../components/NetworkCanvas";
import { backboneEdges, useGraphModel } from "../../components/useGraphModel";
import { HowMade, Legend, Loading, Segmented } from "../../components/ui";
import { fmt, int } from "../../lib/format";
import { useFindings } from "./shared";

export function DensityScene() {
  const [rep, setRep] = useState<Rep>("lexical");
  const [d, setD] = useState("10");
  const density = Number(d) / 100;
  const model = useGraphModel({ cohort: "joint", rep, density, colourBy: "community", layoutMode: "network" });
  const F = useFindings();
  const edges = useMemo(() => backboneEdges(model), [model]);
  const g = model.graph;
  const st = g?.partition_stats["42"];
  const gid = `joint-${rep}-d${d.padStart(2, "0")}`;
  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <Segmented label="Representation" value={rep} onChange={setRep} options={[{ value: "lexical", label: "TF–IDF" }, { value: "semantic", label: "Embeddings" }]} />
        <span className="control-label" style={{ margin: "0 0 0 8px" }}>Share of tale pairs that become edges</span>
        <Segmented label="Density" value={d} onChange={setD} options={[{ value: "5", label: "5%" }, { value: "10", label: "10% (primary)" }, { value: "15", label: "15%" }]} />
      </div>
      <div className="grid-main-side" style={{ ["--side" as string]: "360px" }}>
        <figure className="figure" style={{ margin: 0, padding: 10 }}>
          {!model.ready ? <Loading what={`the ${d}% graph`} /> : (
            <div style={{ height: 440, display: "flex" }}>
              <NetworkCanvas zoomMode="gentle" ariaLabel={`Joint-cohort ${rep} network at ${d}% density coloured by discovered community.`}
                n={model.nodes.length} positions={model.positions} colours={model.colours} edges={edges} edgeAlpha={0.06}
                tooltip={(i) => { const r = model.rows[i]; return r ? { title: r.title, lines: [`community ${g ? g.colour_index["42"][model.communities[i]] + 1 : ""}`] } : null; }}
                transition={{ key: `${rep}|${d}`, duration: 500 }} radius={2.5} />
            </div>
          )}
          <Legend title={model.legend.title} items={model.legend.items.slice(0, 12)} ring />
          <p className="caption">Colours are aligned to the 10% communities by overlap (a declared display mapping); community numbers have no meaning of their own. Faint lines: each tale's 5 strongest edges (drawing only).</p>
        </figure>
        <div>
          {g && st ? (
            <div className="table-wrap">
              <table className="data">
                <caption className="visually-hidden">Graph at {d}% density</caption>
                <tbody>
                  <tr><td>Edges kept</td><td className="num">{int(g.m)} of {int(g.n * (g.n - 1) / 2)} pairs</td></tr>
                  <tr><td>Similarity threshold</td><td className="num">cosine ≥ {fmt(g.similarity_threshold)}</td></tr>
                  <tr><td>Components / isolates</td><td className="num">{g.components} / {g.isolates.length}</td></tr>
                  <tr><td>Communities (≥ 5 tales)</td><td className="num">{st.communities} ({st.sizes.filter((s) => s >= 5).length})</td></tr>
                  <tr><td>Modularity Q</td><td className="num">{fmt(st.modularity)}</td></tr>
                  <tr><td>Q in degree-preserving shuffles</td><td className="num">{g.modularity_null ? `${fmt(g.modularity_null.null_mean)} ± ${fmt(g.modularity_null.null_sd)}` : "not computed"}</td></tr>
                  <tr><td>Seed agreement (NMI 42–7, 42–19)</td><td className="num">{fmt(g.seed_agreement_nmi["42-7"], 2)}, {fmt(g.seed_agreement_nmi["42-19"], 2)}</td></tr>
                  {(["atu", "place", "region"] as const).map((l) => {
                    const r = F.row(gid, l);
                    return <tr key={l}><td>NMI excess: {l === "atu" ? "ATU type" : l}</td><td className="num">{fmt(r?.nmi.excess)}</td></tr>;
                  })}
                </tbody>
              </table>
            </div>
          ) : <Loading />}
          {(() => {
            const main = (F.agreement?.rows ?? []).filter((r) => r.group === "main" && r.rep === rep);
            const settings = [...new Set(main.map((r) => `${r.density}|${r.seed}`))];
            const top = settings.filter((k) => {
              const ex = (l: string) => main.find((r) => `${r.density}|${r.seed}` === k && r.label === l)?.nmi.excess ?? -1;
              return ex("atu") > ex("place") && ex("atu") > ex("region");
            }).length;
            return <p className="sans small" style={{ marginTop: 10 }}>Denser graphs have more edges and fewer, larger communities; sparser ones leave more tales isolated. For {rep === "lexical" ? "TF–IDF" : "embeddings"}, ATU type has the largest NMI excess in {top} of the {settings.length} density × seed settings. The isolate count changes a lot, especially for embeddings, because one global threshold suits some tales better than others (week 4's warning about global thresholds).</p>;
          })()}
        </div>
      </div>
      <HowMade
        measured="For each precomputed density: the graph's edges, components, isolates, weighted Louvain communities and modularity, and the label-agreement excess."
        records="Joint cohort (1,133 tales). Graphs keep the strongest m = d·n(n−1)/2 pairs; ties are broken by tale ID."
        method="Global threshold and backbones (week 4, §8); Louvain and modularity, with a degree-preserving null for Q (week 4, §3–4)."
        infer="Which findings are stable across reasonable thresholds and which depend on the setting."
        cannot="Intermediate densities were not computed and are not interpolated. Modularity above its null indicates grouping, not 'true' communities." />
    </div>
  );
}
