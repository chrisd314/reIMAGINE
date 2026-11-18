import { useCallback, useMemo, useState } from "react";
import { communityOf, shortType, type NetMap, type Near, type Story } from "../../data";
import { NetCanvas, type Tone } from "../../components/NetCanvas";
import { TalePanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, DataTable, Result, Segmented, Why } from "../../components/ui";
import { fmt, int, pct } from "../../lib/format";

/** P(K >= k) of the observed degrees and of a Poisson random graph with the same mean degree (G(n, m)). */
function ccdf(degree: number[]) {
  const n = degree.length, sorted = [...degree].sort((a, b) => a - b);
  const obs: [number, number][] = [];
  for (let i = 0; i < n; i++) if (i === 0 || sorted[i] !== sorted[i - 1]) obs.push([sorted[i], (n - i) / n]);
  const lambda = degree.reduce((a, b) => a + b, 0) / n, kmax = Math.max(sorted[n - 1], Math.ceil(lambda + 12 * Math.sqrt(lambda)));
  const logp: number[] = [-lambda];
  for (let k = 1; k <= kmax; k++) logp.push(logp[k - 1] + Math.log(lambda) - Math.log(k));
  const tail: number[] = new Array(kmax + 2).fill(0);
  for (let k = kmax; k >= 0; k--) tail[k] = tail[k + 1] + Math.exp(logp[k]);
  const rnd: [number, number][] = [];
  for (let k = 1; k <= kmax; k++) if (tail[k] >= 1 / n) rnd.push([k, Math.min(1, tail[k])]);
  return { obs: obs.filter(([k]) => k > 0), rnd, lambda };
}

function DegreeChart({ degree, random }: { degree: number[]; random: boolean }) {
  const { obs, rnd } = useMemo(() => ccdf(degree), [degree]);
  const n = degree.length, W = 520, H = 300, L = 54, R = 14, T = 10, B = 40;
  const kmin = 1, kmax = 1500, pmin = 1 / n / 1.5;
  const x = (k: number) => L + (W - L - R) * (Math.log10(k) - Math.log10(kmin)) / (Math.log10(kmax) - Math.log10(kmin));
  const y = (p: number) => T + (H - T - B) * (Math.log10(1) - Math.log10(p)) / (Math.log10(1) - Math.log10(pmin));
  const xt = [1, 10, 100, 1000], yt = [1, 0.1, 0.01, 0.001].filter((p) => p >= pmin);
  const path = (pts: [number, number][]) => pts.map(([k, p], i) => `${i ? "L" : "M"}${x(k).toFixed(1)},${y(p).toFixed(1)}`).join("");
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Degree distribution, observed against a random graph">
      {xt.map((k) => <g key={k}><line className="axis" x1={x(k)} x2={x(k)} y1={T} y2={H - B} strokeDasharray="2 4" /><text className="tick" x={x(k)} y={H - B + 16} textAnchor="middle">{k}</text></g>)}
      {yt.map((p) => <g key={p}><line className="axis" x1={L} x2={W - R} y1={y(p)} y2={y(p)} strokeDasharray="2 4" /><text className="tick" x={L - 6} y={y(p) + 4} textAnchor="end">{p}</text></g>)}
      {random && <path d={path(rnd)} fill="none" stroke="var(--c2)" strokeWidth={2} strokeDasharray="5 3" />}
      <path d={path(obs)} fill="none" stroke="var(--c1)" strokeWidth={2} />
      <text className="tick" x={(L + W - R) / 2} y={H - 4} textAnchor="middle">degree k (links of a tale), log scale</text>
      <text className="tick" transform={`translate(12 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle">share of tales with degree ≥ k</text>
      <g transform={`translate(${L + 10} ${H - B - 34})`} fontSize={11.5}>
        <line x1={0} x2={18} y1={0} y2={0} stroke="var(--c1)" strokeWidth={2} /><text className="tick" x={24} y={4}>folktale network</text>
        {random && <><line x1={0} x2={18} y1={16} y2={16} stroke="var(--c2)" strokeWidth={2} strokeDasharray="5 3" /><text className="tick" x={24} y={20}>random graph, same n and m</text></>}
      </g>
    </svg>
  );
}

const MEASURE: Record<string, string> = {
  "degree: coefficient of variation": "Degree spread (coefficient of variation)",
  "degree: largest": "Largest degree",
  "degree: Gini": "Degree inequality (Gini)",
  "degree: skewness": "Degree skewness",
  "clustering (unweighted, mean over tales)": "Clustering (mean over tales)",
  "clustering (weighted, Onnela)": "Clustering, weighted (Onnela)",
};

export function NetworkSection({ maps }: { maps: Record<string, NetMap> }) {
  const { rep } = useRep();
  const map = maps[rep];
  const [dens, setDens] = useState(String(map.stats.density));
  const [random, setRandom] = useState(true);
  const st = map.densities.stats.find((x) => String(x.density) === dens) ?? map.densities.stats[0];
  const degree = map.densities.degrees[dens] ?? map.degree;
  const rows = map.structure;
  const get = (m: string) => rows.find((r) => r.measure === m);
  const clus = get("clustering (unweighted, mean over tales)"), cRandom = get("clustering expected in G(n, m) (= density)");
  const gini = get("degree: Gini"), largest = get("degree: largest");
  const shown = rows.filter((r) => MEASURE[r.measure] && r.nullMean !== null);
  const dl = map.degreeLength;
  const meanDeg = (2 * st.edges) / map.stats.n;
  const lo = map.densities.stats[0], hi = map.densities.stats[map.densities.stats.length - 1];
  return (
    <Chapter id="network" num="Folktales · 3" title="The network: hubs and clustering">
      <Why course="week 1 (degree distributions), week 2 (random graphs, clustering, degree-preserving shuffles), week 4 (weighted networks, global threshold)"
        what={<>Two tales are linked when their similarity is among the strongest {pct(map.stats.density)} of all pairs (cosine above {fmt(map.stats.threshold, 3)}): {int(map.stats.n)} tales, {int(map.stats.edges)} weighted links. We compare the network with a random graph of the same size, G(n, m), and with degree-preserving shuffles that keep every tale's number of links.</>}
        why={<>A similarity network always has links; the question is whether its shape says something beyond chance. The random graph shows what “no structure” looks like; the shuffles show how much follows from the degrees alone.</>} />
      <div className="controls-row">
        <RepToggle />
        <Segmented label="Keep the strongest pairs" value={dens} onChange={setDens}
          options={map.densities.stats.map((x) => ({ value: String(x.density), label: `${Math.round(x.density * 100)}% of pairs${x.density === map.stats.density ? " (main)" : ""}` }))} />
        <label className="sans small"><input type="checkbox" checked={random} onChange={(e) => setRandom(e.target.checked)} /> compare with a random graph</label>
      </div>
      <div className="tiles">
        <div className="tile"><div className="v">{int(st.edges)}</div><div className="l">links (cosine above {fmt(st.threshold, 3)})</div></div>
        <div className="tile"><div className="v">{fmt(meanDeg, 0)}</div><div className="l">links per tale on average</div></div>
        <div className="tile"><div className="v">{int(st.largest)}</div><div className="l">tales in the largest of {st.components} components ({st.isolates} isolated)</div></div>
        <div className="tile"><div className="v">{st.major}</div><div className="l">large communities (modularity {fmt(st.modularity, 2)} against {fmt(st.nullMean, 3)} in shuffles)</div></div>
      </div>
      <div className="two-col">
        <figure className="figure">
          <p className="figure-title">How many links does a tale have? ({Math.round(Number(dens) * 100)}% of pairs)</p>
          <p className="figure-sub">Cumulative degree distribution, log–log axes</p>
          <DegreeChart degree={degree} random={random} />
          <DataTable head={["Measure (main graph)", "Folktale network", "Reference", "Reference value", "z"]}
            rows={shown.map((r) => [MEASURE[r.measure], fmt(r.observed, 3), r.null ?? "", fmt(r.nullMean, 3), fmt(r.z, 1)])} />
        </figure>
        <Result>
          <p><strong>A few tales are hubs.</strong> In the main graph the most linked tale has {largest ? int(largest.observed) : "–"} links, where a random graph of the same size gives about {largest ? int(largest.nullMean ?? 0) : "–"}; degree inequality (Gini) is {fmt(gini?.observed, 2)} against {fmt(gini?.nullMean, 2)}. Hubs are the long tales: the 20 most linked have a median of {int(dl.hubTokens)} words against {int(dl.medianTokens)} for all tales (Spearman of links and length {fmt(dl.spearman, 2)}). Long texts share some words with almost everything, which is why every placement test later controls for length.</p>
          <p><strong>Tales cluster.</strong> Neighbours of a tale are linked to each other far more often than in a random graph ({fmt(clus?.observed, 2)} against {fmt(cRandom?.observed, 2)}), but less than in shuffles that keep the degrees ({fmt(clus?.nullMean, 2)}): much of the clustering comes from the hubs themselves.</p>
          <p>Move the threshold: with the strongest {pct(lo.density)} of pairs, {int(lo.isolates)} tales are isolated and Louvain finds {lo.communities} communities; with {pct(hi.density)}, {int(hi.isolates)} and {hi.communities}. The rule changes how finely the network splits, which is why section 6 repeats every test across thresholds.</p>
        </Result>
      </div>
    </Chapter>
  );
}

function NullHistogram({ values, observed }: { values: number[]; observed: number }) {
  const W = 360, H = 120, L = 8, R = 8, T = 14, B = 26, bins = 20;
  const lo = Math.min(...values, observed) * 0.95, hi = Math.max(...values, observed) * 1.05;
  const counts = new Array(bins).fill(0);
  values.forEach((v) => { counts[Math.min(bins - 1, Math.floor(((v - lo) / (hi - lo)) * bins))] += 1; });
  const max = Math.max(1, ...counts), x = (v: number) => L + (W - L - R) * (v - lo) / (hi - lo);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="PageRank in the shuffles against the observed PageRank">
      {counts.map((c, k) => c > 0 && <rect key={k} x={L + ((W - L - R) * k) / bins + 0.5} width={(W - L - R) / bins - 1} y={T + (H - T - B) * (1 - c / max)} height={(H - T - B) * c / max} fill="var(--c2)" opacity={0.75} />)}
      <line x1={x(observed)} x2={x(observed)} y1={T - 6} y2={H - B} stroke="var(--c1)" strokeWidth={2.5} />
      <text className="tick" x={x(observed) - 4} y={T - 4} textAnchor="end">observed {observed.toFixed(2)}</text>
      <line className="axis" x1={L} x2={W - R} y1={H - B} y2={H - B} />
      <text className="tick" x={(L + W - R) / 2} y={H - 6} textAnchor="middle">PageRank (× the average tale) in {values.length} degree-preserving shuffles</text>
    </svg>
  );
}

export function CentralSection({ d, maps, near }: { d: Story; maps: Record<string, NetMap>; near: Near | null }) {
  const { rep } = useRep();
  const map = maps[rep];
  const A = map.archetypes;
  const [size, setSize] = useState<"degree" | "pagerank">("pagerank");
  const [pick, setPick] = useState<number>(A[0]?.node ?? 0);
  const [tale, setTale] = useState<number | null>(null);
  const meanDeg = map.structure.find((r) => r.measure === "degree: mean")?.observed ?? Infinity;
  const a = A.find((x) => x.node === pick);
  const top = useMemo(() => new Set(A.map((x) => x.node)), [A]);
  const tone = useCallback((i: number): Tone => (i === pick ? 2 : top.has(i) ? 1 : 0), [pick, top]);
  const F = d.folktales;
  const labels = useMemo(() => A.slice(0, 5).map((x) => ({ node: x.node, text: x.title.replace(/\s*\(.*\)$/, "") })), [A]);
  const tip = (i: number) => <><strong>{F.title[i]}</strong><br />{map.degree[i]} links · PageRank {fmt(map.pagerank[i], 2)}× average · z {fmt(map.pagerankZ[i], 1)}<br />{communityOf(map.group[i])}</>;
  return (
    <Chapter id="central" num="Folktales · 7" title="Which tales are central?">
      <Why course="week 3 (PageRank, compared to what?)"
        what={<>PageRank scores every tale by how much of the network's “attention” flows to it. Because long tales collect links, each score is compared with the same tale's PageRank in degree-preserving shuffles; a high z means more central than its number of links explains.</>}
        why={<>Central tales are the archetypes of the map: the versions that sit between many others. They show what kind of story holds the network together.</>} />
      <div className="controls-row">
        <RepToggle />
        <Segmented label="Size the dots by" value={size} onChange={setSize} options={[{ value: "pagerank", label: "PageRank" }, { value: "degree", label: "Links" }]} />
      </div>
      <div className="two-col">
        <figure className="figure">
          <NetCanvas map={map} tone={tone} tip={tip} size={size} labels={labels} focus={pick} selected={tale} onPick={setTale}
            label="Network with the most central tales highlighted" />
          <div className="legend" aria-hidden>
            <span><i className="swatch" style={{ background: "var(--c1)" }} />the {A.length} most central tales</span>
            <span><i className="swatch" style={{ background: "var(--c2)" }} />the one picked below</span>
          </div>
          {tale !== null && <div style={{ marginTop: 12 }}><TalePanel story={d} map={map} near={near} rep={rep} i={tale} onSelect={setTale} onClose={() => setTale(null)} /></div>}
        </figure>
        <div>
          <div className="table-wrap">
            <table className="data clickable">
              <thead><tr><th>Tale</th><th>Tale type</th><th className="n">Links</th><th className="n">z</th></tr></thead>
              <tbody>{A.map((x) => (
                <tr key={x.node} className={x.node === pick ? "sel" : undefined} onClick={() => setPick(x.node)}>
                  <td><button type="button" className="linklike" onClick={() => setPick(x.node)}>{x.title}</button></td>
                  <td>{x.atu ? `ATU ${x.atu} ${shortType(F.atuName[x.node], 30)}` : "–"}</td><td className="n">{x.degree}</td><td className="n">{fmt(x.z, 1)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          {a && a.null.length > 0 && <figure className="figure" style={{ marginTop: 12 }}>
            <p className="figure-title">{a.title}: PageRank against its shuffles</p>
            <NullHistogram values={a.null} observed={a.pagerank} />
          </figure>}
        </div>
      </div>
      <Result>
        <p>Once their number of links is accounted for, the most central tales are retellings of a few widespread types ({[...new Set(A.slice(0, 5).filter((x) => x.atu).map((x) => shortType(F.atuName[x.node], 34)))].join("; ")}), led by <em>{A[0]?.title}</em>.{A.slice(0, 5).every((x) => x.degree < meanDeg) ? <> All of the top five have fewer links than the average tale ({A.slice(0, 5).map((x) => x.degree).join(", ")} against {Math.round(meanDeg)}), so their centrality comes from where they sit, not from size.</> : null}</p>
      </Result>
    </Chapter>
  );
}
