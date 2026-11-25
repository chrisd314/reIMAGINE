import { useCallback, useEffect, useMemo, useState } from "react";
import { communityOf, shortType, useNear, useNetwork, useStory, type Story } from "../../data";
import { NetCanvas, placeOnMap, type Marker, type Tone } from "../../components/NetCanvas";
import { TalePanel, TextPanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { Search, type SearchItem } from "../../components/Search";
import { Failed, Loading, Segmented } from "../../components/ui";
import { categoryOf, nameOf, topCategories, type Mode } from "../folktales/communities";

type Sel = { kind: "tale"; i: number } | { kind: "text"; id: string } | null;

function readItem(): string | null {
  const q = window.location.hash.split("?")[1] ?? "";
  return new URLSearchParams(q).get("item");
}
function writeItem(key: string | null) {
  const base = window.location.hash.split("?")[0] || "#/explore";
  history.replaceState(null, "", key ? `${base}?item=${encodeURIComponent(key)}` : base);
}

function searchItems(s: Story): SearchItem[] {
  const F = s.folktales;
  return [
    ...F.title.map((t, i) => ({ key: F.id[i], label: t, sub: F.atu[i] ? `folktale, ATU ${F.atu[i]}` : "folktale" })),
    ...s.texts.map((t) => ({ key: t.id, label: t.title, sub: `${t.tradition} ${t.kind === "parable" ? "parable" : "passage"}` })),
  ];
}

export function ExplorePage() {
  const { data: d, error } = useStory();
  const { data: net, error: e2 } = useNetwork();
  const { data: near } = useNear();
  const { rep } = useRep();
  const [mode, setMode] = useState<Mode | "none">("community");
  const [picks, setPicks] = useState<string[]>([]);
  const [size, setSize] = useState<"degree" | "pagerank">("degree");
  const [overlay, setOverlay] = useState<string>("none");
  const [baseline, setBaseline] = useState(false);
  const [sel, setSel] = useState<Sel>(null);
  const [focus, setFocus] = useState<number | null>(null);

  // the selection in the address, so a view can be shared
  useEffect(() => {
    if (!d) return;
    const key = readItem();
    if (!key) return;
    const i = d.folktales.id.indexOf(key);
    if (i >= 0) { setSel({ kind: "tale", i }); setFocus(i); } else if (d.texts.some((t) => t.id === key)) setSel({ kind: "text", id: key });
  }, [d]);
  const select = useCallback((s: Sel) => {
    setSel(s);
    if (!d) return;
    writeItem(s === null ? null : s.kind === "tale" ? d.folktales.id[s.i] : s.id);
  }, [d]);
  useEffect(() => { if (d && net && picks.length === 0 && mode !== "none") setPicks(topCategories(d, net.maps[rep], mode).slice(0, 3).map((c) => c.key)); },
    [d, net, rep, mode, picks.length]);

  const map = net?.maps[rep];
  const cats = useMemo(() => (d && map && mode !== "none" ? topCategories(d, map, mode) : []), [d, map, mode]);
  const tone = useCallback((i: number): Tone => (d && map && mode !== "none" ? (picks.indexOf(categoryOf(d, map, mode, i)) + 1) as Tone : 0), [d, map, mode, picks]);
  const markers = useMemo<Marker[]>(() => {
    if (!d || !map || overlay === "none") return [];
    return d.texts.filter((t) => (overlay === "all" || t.tradition === overlay) && (t.kind === "parable" || baseline))
      .map((t) => ({ id: t.id, ...placeOnMap(map, t.rep[rep].nearest), tone: 0 as Tone, hollow: t.kind === "baseline", title: `${t.title} (${t.tradition}${t.kind === "baseline" ? ", non-story" : ""})` }));
  }, [d, map, overlay, baseline, rep]);
  const items = useMemo(() => (d ? searchItems(d) : []), [d]);
  if (error || e2) return <Failed error={(error ?? e2) as string} />;
  if (!d || !net || !map) return <Loading what="the network" />;
  const F = d.folktales;
  const selText = sel?.kind === "text" ? d.texts.find((t) => t.id === sel.id) : undefined;
  const pick = (key: string) => {
    const i = F.id.indexOf(key);
    if (i >= 0) { select({ kind: "tale", i }); setFocus(i); return; }
    const t = d.texts.find((x) => x.id === key);
    if (t) { select({ kind: "text", id: key }); setOverlay(t.tradition); if (t.kind === "baseline") setBaseline(true); setFocus(t.rep[rep].nearest[0]); }
  };
  const tip = (i: number) => (
    <><strong>{F.title[i]}</strong><br />{F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 60)}` : "no tale type"}<br />
      {F.region[i] || "no region"} · {communityOf(map.group[i])} · {map.degree[i]} links<br /><em>click to open it</em></>
  );
  const textRings = selText ? [{ counts: new Map(selText.rep[rep].nearest.slice(0, 5).map((j) => [j, 1] as [number, number])), tone: 1 as Tone }] : [];
  const labels = map.archetypes.slice(0, 3).map((a) => ({ node: a.node, text: a.title.replace(/\s*\(.*\)$/, "") }));

  return (
    <div className="explore">
      <div className="wrap">
        <div className="explore-head">
          <div><div className="kicker">reIMAGINE · explore</div><h1>Explore the network</h1></div>
          <Search items={items} onPick={pick} />
        </div>
        <div className="explore-controls">
          <RepToggle />
          <Segmented label="Colour by" value={mode} onChange={(m) => { setMode(m); setPicks([]); }}
            options={[{ value: "community", label: "Communities" }, { value: "type", label: "Tale types" }, { value: "region", label: "Regions" }, { value: "collection", label: "Books" }, { value: "none", label: "None" }]} />
          <Segmented label="Size by" value={size} onChange={setSize} options={[{ value: "degree", label: "Links" }, { value: "pagerank", label: "PageRank" }]} />
          <label className="sans small">Parables on the map{" "}
            <select value={overlay} onChange={(e) => setOverlay(e.target.value)}>
              <option value="none">none</option><option value="all">all five traditions</option>
              {d.traditions.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          {overlay !== "none" && <label className="sans small"><input type="checkbox" checked={baseline} onChange={(e) => setBaseline(e.target.checked)} /> with their non-story passages</label>}
        </div>
        {mode !== "none" && (
          <div className="chips" style={{ marginBottom: 10 }}>
            {cats.map((c) => (
              <button key={c.key} type="button" className="chip" aria-pressed={picks.includes(c.key)} onClick={() => setPicks((p) => (p.includes(c.key) ? p.filter((k) => k !== c.key) : [...p, c.key].slice(-3)))}>
                {picks.includes(c.key) && <i className="swatch" style={{ background: `var(--c${picks.indexOf(c.key) + 1})` }} />}{nameOf(d, map, mode, c.key)} <span className="muted">{c.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="explore-body">
        <div className="explore-map">
          <NetCanvas map={map} tone={tone} tip={tip} size={size} labels={labels} wheel="always" height={Math.max(420, Math.round(window.innerHeight * 0.72))}
            selected={sel?.kind === "tale" ? sel.i : null} focus={focus} markers={markers} rings={textRings}
            onPick={(i) => select({ kind: "tale", i })} onPickMarker={(id) => select({ kind: "text", id })}
            label={`Network of ${F.title.length} folktales${overlay !== "none" ? " with parables" : ""}`} />
          <div className="legend" aria-hidden>
            {mode !== "none" && picks.map((k, j) => <span key={k}><i className="swatch" style={{ background: `var(--c${j + 1})` }} />{nameOf(d, map, mode, k)}</span>)}
            {overlay !== "none" && <span><i className="diamond" />parable</span>}
            {overlay !== "none" && baseline && <span><i className="diamond hollow" />non-story passage</span>}
          </div>
          <p className="caption">Each dot is a folktale in the {rep === "tfidf" ? "TF–IDF" : "embedding"} network, placed by a force layout and sized by its {size === "degree" ? "number of links" : "PageRank"}. A parable sits at the mean position of its five nearest folktales: a display aid, never used in a statistic.</p>
        </div>
        <aside className="explore-panel">
          {sel?.kind === "tale" && <TalePanel story={d} map={map} near={near} rep={rep} i={sel.i} onSelect={(j) => { select({ kind: "tale", i: j }); setFocus(j); }} onClose={() => select(null)} />}
          {selText && <TextPanel story={d} near={near} rep={rep} t={selText} onSelectTale={(j) => { select({ kind: "tale", i: j }); setFocus(j); }} />}
          {!sel && (
            <div className="card">
              <h4>How to explore</h4>
              <ul className="sans small" style={{ paddingLeft: 18, margin: 0 }}>
                <li>Search any folktale or parable by title, or click a dot.</li>
                <li>Every tale opens with its nearest folktales and the words behind each match; <em>Read pair</em> puts two texts side by side, with links to read both in full at their source.</li>
                <li>Colour the network by community, tale type, region or book; pick up to three to compare.</li>
                <li>Put a tradition's parables on the map to see where they land; switch to embeddings to see the other network.</li>
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
