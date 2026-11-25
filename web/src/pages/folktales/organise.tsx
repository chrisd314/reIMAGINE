import { useCallback, useMemo, useState } from "react";
import { communityName, communityOf, shortType, type NetMap, type Network, type Story, type SweepRow } from "../../data";
import { alignTones, NetCanvas, type Tone } from "../../components/NetCanvas";
import { RepToggle, useRep } from "../../components/rep";
import { ShuffleLab } from "../../components/ShuffleLab";
import { Chapter, DataTable, Result, Segmented, Why } from "../../components/ui";
import { codes, nmi, rng, shuffled, shuffledWithin } from "../../lib/stats";
import { fmt, int, pct, pMin } from "../../lib/format";

const LABEL: Record<string, string> = { atu_type: "Tale type", region: "Region", source_collection: "Source book" };
const COL: Record<string, "atu" | "region" | "collection"> = { atu_type: "atu", region: "region", source_collection: "collection" };

function OrganiseChart({ rows }: { rows: { name: string; plain: number; within: number | null }[] }) {
  const W = 520, L = 96, R = 40, bh = 14, gap = 16, H = rows.length * (2 * bh + gap) + 26;
  const max = Math.max(...rows.map((r) => r.plain)) * 1.08;
  const x = (v: number) => L + (W - L - R) * Math.max(0, v) / max;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Excess NMI of tale type, region and source book">
      {rows.map((r, k) => {
        const y = 6 + k * (2 * bh + gap);
        return (
          <g key={r.name}>
            <text x={L - 8} y={y + bh + 4} textAnchor="end" fontSize={13}>{r.name}</text>
            <rect x={L} y={y} width={x(r.plain) - L} height={bh} fill="var(--c1)" rx={2} />
            <text x={x(r.plain) + 5} y={y + bh - 3} className="tick">{r.plain.toFixed(2)}</text>
            {r.within !== null && <>
              <rect x={L} y={y + bh + 2} width={Math.max(1.5, x(r.within) - L)} height={bh} fill="var(--c2)" rx={2} />
              <text x={x(r.within) + 5} y={y + 2 * bh - 1} className="tick">{r.within.toFixed(3)}</text>
            </>}
          </g>
        );
      })}
      <g transform={`translate(${L} ${H - 12})`} fontSize={11.5}>
        <rect width={10} height={10} y={-9} fill="var(--c1)" /><text x={14} className="tick">labels shuffled across all tales</text>
        <rect x={210} width={10} height={10} y={-9} fill="var(--c2)" /><text x={224} className="tick">shuffled within each book</text>
      </g>
    </svg>
  );
}

export function OrganiseSection({ d, maps }: { d: Story; maps: Record<string, NetMap> }) {
  const { rep } = useRep();
  const map = maps[rep];
  const [label, setLabel] = useState<"atu_type" | "region" | "source_collection">("region");
  const [within, setWithin] = useState(false);
  const org = (l: string, w = false, measure = "nmi") =>
    map.organise.find((o) => o.label === l && o.measure === measure && o.null === (w ? "within-collection shuffle" : "label shuffle"));
  const type = org("atu_type"), typeW = org("atu_type", true), region = org("region"), regionW = org("region", true), coll = org("source_collection");

  // the label test, rerun in the browser on the same tales and partition as the pipeline
  const F = d.folktales, lt = map.labelTest;
  const part = useMemo(() => Int32Array.from(lt.part), [lt]);
  const labels = useMemo(() => codes(lt.nodes.map((i) => F[COL[label]][i])), [lt, F, label]);
  const strata = useMemo(() => lt.nodes.map((i) => F.collection[i]), [lt, F]);
  const observed = useMemo(() => nmi(part, labels), [part, labels]);
  const rand = useMemo(() => rng(20261029), [label, within, rep]);   // eslint-disable-line react-hooks/exhaustive-deps
  const runOne = useCallback(() => nmi(part, within ? shuffledWithin(labels, strata, rand) : shuffled(labels, rand)), [part, labels, strata, within, rand]);
  const ref = org(label, within && label !== "source_collection");
  const canWithin = label !== "source_collection";

  return (
    <Chapter id="organise" num="Folktales · 5" title="What do the communities follow: story, place or book?">
      <Why course="week 3 (attribute assortativity, label shuffles), week 4 (NMI with ground truth)"
        what={<>We compare the communities with three labels of the same {int(type?.n)} tales (those with all three): ATU tale type, region, and source book. Agreement is measured by normalised mutual information (NMI) and by attribute assortativity, each against {int(d.settings.labelShuffles)} label shuffles. A second, stricter shuffle moves labels only among tales of the same book.</>}
        why={<>This is the “location” question of the outline. A book is usually one editor, one translator and one place, so a book's style could make tales look alike and fake both “type” and “region”. Shuffling within books removes that.</>} />
      <div className="controls-row"><RepToggle /></div>
      <div className="two-col even">
        <figure className="figure">
          <p className="figure-title">Shuffle the labels yourself</p>
          <div className="controls-row">
            <Segmented label="Label" value={label} onChange={(l) => { setLabel(l); if (l === "source_collection") setWithin(false); }}
              options={[{ value: "atu_type", label: "Tale type" }, { value: "region", label: "Region" }, { value: "source_collection", label: "Source book" }]} />
            <Segmented label="Shuffle" value={within && canWithin ? "within" : "all"} onChange={(v) => setWithin(v === "within")}
              options={canWithin ? [{ value: "all", label: "across all tales" }, { value: "within", label: "within each book" }] : [{ value: "all", label: "across all tales" }]} />
          </div>
          <ShuffleLab observed={observed} runOne={runOne} reset={`${rep}-${label}-${within}`} label={`NMI of the communities with ${LABEL[label].toLowerCase()}`}
            pipeline={ref ? `The pipeline's ${int(d.settings.labelShuffles)} shuffles: mean ${fmt(ref.nullMean, 3)}${ref.nullLow !== null ? `, 95% between ${fmt(ref.nullLow, 3)} and ${fmt(ref.nullHigh, 3)}` : ""}, p ${ref.p < 1.5 / (d.settings.labelShuffles + 1) ? pMin(d.settings.labelShuffles) : `= ${fmt(ref.p, 3)}`}.` : undefined} />
          <p className="caption">Each shuffle gives every tale a random {LABEL[label].toLowerCase()} {within && canWithin ? "from its own book" : "from the pool"} and recomputes NMI with the {map.stats.major}-community partition. Try region within each book: the gap between the observed value and the shuffles almost closes.</p>
        </figure>
        <figure className="figure">
          <p className="figure-title">Agreement above shuffled labels</p>
          <p className="figure-sub">NMI minus its mean under shuffling</p>
          <OrganiseChart rows={[
            { name: "Tale type", plain: type?.excess ?? 0, within: typeW?.excess ?? null },
            { name: "Region", plain: region?.excess ?? 0, within: regionW?.excess ?? null },
            { name: "Source book", plain: coll?.excess ?? 0, within: null },
          ]} />
          <DataTable head={["Label", "NMI", "Shuffled", "Within-book shuffle", "Assortativity", "Shuffled"]} rows={["atu_type", "region", "source_collection"].map((l) => [
            LABEL[l], fmt(org(l)?.observed, 3), fmt(org(l)?.nullMean, 3), org(l, true) ? fmt(org(l, true)?.nullMean, 3) : "–",
            fmt(org(l, false, "assortativity")?.observed, 3), fmt(org(l, false, "assortativity")?.nullMean, 3)])} />
        </figure>
      </div>
      <Result>
        <p><strong>Tale type organises the map most.</strong> Its agreement with the communities is {fmt(type?.excess, 2)} above shuffled labels, and still {fmt(typeW?.excess, 2)} when types are shuffled only among tales of the same book.</p>
        <p><strong>Location is mostly the book.</strong> Region looks organising ({fmt(region?.excess, 2)} above shuffles), but within books almost nothing is left ({fmt(regionW?.excess, 3)}): tales from one book sit together, and a book mostly covers one place. The map is a map of stories, not of places.</p>
      </Result>
    </Chapter>
  );
}

const graphName = (r: SweepRow) => (r.by === "density" ? `${Math.round(r.value * 100)}% strongest pairs` : `${r.value} nearest neighbours (kNN)`);

function SweepChart({ rows, selected, onPick }: { rows: SweepRow[]; selected: string; onPick: (key: string) => void }) {
  const W = 620, L = 190, R = 16, T = 8, rowH = 26, H = T + rows.length * rowH + 46;
  const max = Math.max(...rows.flatMap((r) => [r.type, r.region, r.collection])) * 1.1;
  const x = (v: number) => L + (W - L - R) * Math.max(0, v) / max;
  const ticks = [0, 0.05, 0.1, 0.15, 0.2, 0.25].filter((t) => t <= max);
  const series: [keyof SweepRow, string, string][] = [["type", "var(--c1)", "tale type"], ["region", "var(--c2)", "region"], ["collection", "var(--c3)", "source book"]];
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Excess NMI of tale type, region and source book in every graph. Click a row to see its communities">
      {ticks.map((t) => <g key={t}><line className="axis" x1={x(t)} x2={x(t)} y1={T} y2={T + rows.length * rowH} strokeDasharray="2 4" /><text className="tick" x={x(t)} y={T + rows.length * rowH + 14} textAnchor="middle">{t.toFixed(2)}</text></g>)}
      {rows.map((r, k) => {
        const y = T + k * rowH + rowH / 2, sel = r.key === selected;
        return (
          <g key={r.key} onClick={() => onPick(r.key)} style={{ cursor: "pointer" }} role="button" aria-pressed={sel} tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onPick(r.key); }}>
            <rect x={0} y={y - rowH / 2 + 1} width={W} height={rowH - 2} fill={sel ? "var(--paper-3)" : "transparent"} rx={4} />
            <text x={L - 8} y={y + 4} textAnchor="end" fontSize={12} fontWeight={sel || r.canonical ? 700 : 400}>{graphName(r)}{r.canonical ? " (main)" : ""}</text>
            <line x1={x(Math.min(r.type, r.region, r.collection))} x2={x(Math.max(r.type, r.region, r.collection))} y1={y} y2={y} stroke="var(--rule)" strokeWidth={2} />
            {series.map(([key, col]) => <circle key={key} cx={x(r[key] as number)} cy={y} r={5} fill={col} />)}
          </g>
        );
      })}
      <g transform={`translate(${L} ${H - 6})`} fontSize={11.5}>
        {series.map(([key, col, name], j) => <g key={key} transform={`translate(${j * 120} 0)`}><circle cx={5} cy={-4} r={5} fill={col} /><text x={14} className="tick">{name}</text></g>)}
      </g>
    </svg>
  );
}

export function ChoicesSection({ d, net }: { d: Story; net: Network }) {
  const { rep } = useRep();
  const map = net.maps[rep];
  const all = net.sweep.rows, rows = all.filter((r) => r.rep === rep);
  const [key, setKey] = useState("knn_10");
  const row = rows.find((r) => r.key === key) ?? rows[0];
  const part = map.partitions[row.key];
  const tone = useMemo(() => alignTones(part, map.group, [0, 1, 2]), [part, map]);
  const nmis = rows.filter((r) => !r.canonical).map((r) => r.nmiCanonical);   // the selected representation, as in the table of checks
  const avg = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
  const knnMore = avg(all.filter((r) => r.by === "knn").map((r) => r.communities)) > avg(all.filter((r) => r.by === "density").map((r) => r.communities));
  const bb = map.backbone, at = (f: string, a: number) => bb.find((b) => b.filtered.startsWith(f) && b.alpha === a);
  const thr05 = at("10%", 0.05), comp01 = at("complete", 0.01), comp05 = at("complete", 0.05);
  const F = d.folktales;
  const tip = (i: number) => <><strong>{F.title[i]}</strong><br />{F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 50)}` : "no tale type"}<br />main community {communityName(d, communityOf(map.group[i]), rep)}</>;
  const toneFn = useCallback((i: number): Tone => tone(i), [tone]);
  return (
    <Chapter id="choices" num="Folktales · 6" title="Edges are a modelling choice">
      <Why course="week 4 (weights, global threshold and its flaws, the disparity filter backbone)"
        what={<>We rebuilt the network {net.sweep.graphs} ways: keeping the strongest 5%, 10% or 15% of pairs, or linking each tale to its 5, 10 or 20 nearest neighbours, with both TF–IDF and embeddings. Louvain was rerun on each, and the label tests repeated. We also tried the disparity filter to extract a backbone.</>}
        why={<>No one handed us these links: we chose a rule for drawing them. A finding that holds only for one threshold would be a finding about the threshold.</>} />
      <div className="controls-row"><RepToggle /></div>
      <div className="two-col">
        <figure className="figure">
          <p className="figure-title">Tale type, region and source book in every graph</p>
          <p className="figure-sub">NMI with the communities minus its mean under label shuffles · click a graph to see its communities</p>
          <SweepChart rows={rows} selected={row.key} onPick={setKey} />
          <DataTable head={["Graph", "Links", "Large communities", "NMI with main partition", "Type", "Region", "Book"]}
            rows={rows.map((r) => [graphName(r), int(r.edges), r.communities, fmt(r.nmiCanonical, 2), fmt(r.type, 3), fmt(r.region, 3), fmt(r.collection, 3)])} />
        </figure>
        <figure className="figure">
          <p className="figure-title">Communities of “{graphName(row)}”</p>
          <p className="figure-sub">{row.communities} large communities · NMI {fmt(row.nmiCanonical, 2)} with the main partition · the three that overlap most with C1–C3 in colour</p>
          <NetCanvas map={map} tone={toneFn} tip={tip} size="none" aspect={0.8} label={`Network coloured by the communities of the ${graphName(row)} graph`} />
          <div className="legend" aria-hidden>{[1, 2, 3].map((k) => <span key={k}><i className="swatch" style={{ background: `var(--c${k})` }} />best match of {communityName(d, `C${k}`, rep)}</span>)}</div>
        </figure>
      </div>
      <div className="two-col" style={{ marginTop: 18 }}>
        <Result>
          <p><strong>Tale type beats region in {net.sweep.typeBeatsRegion} of {net.sweep.graphs} graphs.</strong> The communities themselves change with the rule (NMI {Math.min(...nmis).toFixed(2)}–{Math.max(...nmis).toFixed(2)} with the main {rep === "tfidf" ? "TF–IDF" : "embedding"} partition{knnMore ? ", and kNN graphs give more, smaller communities" : ""}), but what they follow does not.</p>
        </Result>
        <div className="card">
          <div className="tag">Backbone (disparity filter)</div>
          <p className="sans small" style={{ margin: 0 }}>On the thresholded graph the filter keeps only {thr05?.kept} of {int(thr05?.edgesIn)} links at α = 0.05: after thresholding, a tale's link weights are nearly equal, so few stand out. On the complete similarity graph it keeps {int(comp05?.kept)} (α = 0.05) or {int(comp01?.kept)} (α = 0.01) links, {pct(comp01?.within)} of them inside one community. The maps draw each tale's strongest links instead, for display only. Every statistic uses the full graph.</p>
        </div>
      </div>
    </Chapter>
  );
}
