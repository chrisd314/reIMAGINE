import { useCallback, useMemo, useState } from "react";
import { communityName, communityOf, groupCentre, shortType, type NetMap, type Near, type Rep, type Story } from "../../data";
import { alignTones, NetCanvas, type MapLabel, type Tone } from "../../components/NetCanvas";
import { TalePanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, Result, Segmented, Why } from "../../components/ui";
import { fmt, int, pct } from "../../lib/format";

export type Mode = "community" | "type" | "region" | "collection";
export const MODES: { value: Mode; label: string }[] = [
  { value: "community", label: "Communities" }, { value: "type", label: "Tale types" },
  { value: "region", label: "Regions" }, { value: "collection", label: "Source books" },
];
const SHOWN = 10;

export function categoryOf(d: Story, map: NetMap, mode: Mode, i: number): string {
  const f = d.folktales;
  if (mode === "community") return communityOf(map.group[i]);
  if (mode === "type") return f.atu[i];
  if (mode === "region") return f.region[i];
  return f.collection[i];
}

export function nameOf(d: Story, map: NetMap, mode: Mode, key: string, rep: Rep): string {
  if (mode === "community") {
    const named = communityName(d, key, rep);
    if (named !== key) return named;
    const c = map.communities.find((x) => x.name === key);
    return c ? `${key} · ${c.words.split(", ").slice(0, 2).join(", ")}` : key;
  }
  if (mode === "type") return `ATU ${key} ${shortType(d.folktales.atuName[d.folktales.atu.indexOf(key)] ?? "")}`.trim();
  return mode === "collection" ? key.replace(/\b\w/g, (c) => c.toUpperCase()) : key;
}

export function topCategories(d: Story, map: NetMap, mode: Mode) {
  const counts = new Map<string, number>();
  map.x.forEach((_, i) => { const c = categoryOf(d, map, mode, i); if (c && c !== "small") counts.set(c, (counts.get(c) ?? 0) + 1); });
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, SHOWN).map(([key, count]) => ({ key, count }));
}

/** One framed label per picked group, at the middle of the tales coloured for it. */
export function groupLabels(d: Story, map: NetMap, mode: Mode, picks: string[], rep: Rep, toneOf?: ((i: number) => Tone) | null): MapLabel[] {
  return picks.flatMap((k, j) => {
    const members = map.x.map((_, i) => i).filter((i) => (toneOf ? toneOf(i) === j + 1 : categoryOf(d, map, mode, i) === k));
    const c = groupCentre(map, members);
    return c ? [{ ...c, text: nameOf(d, map, mode, k, rep), tone: (j + 1) as Tone }] : [];
  });
}

/** Words sized by rank: a plain-text word cloud of a community's most distinctive words. */
function WordCloud({ words }: { words: string[] }) {
  return (
    <div className="word-cloud" aria-label={`Top words: ${words.join(", ")}`}>
      {words.map((w, k) => <span key={w} style={{ fontSize: `${(1.3 - (0.5 * k) / Math.max(1, words.length - 1)).toFixed(2)}rem`, opacity: 1 - (0.35 * k) / words.length }}>{w}</span>)}
    </div>
  );
}

export function CommunitiesSection({ d, maps, near }: { d: Story; maps: Record<string, NetMap>; near: Near | null }) {
  const { rep } = useRep();
  const map = maps[rep];
  const [mode, setMode] = useState<Mode>("community");
  const [picks, setPicks] = useState<string[]>(["C1", "C2", "C3"]);
  const [seed, setSeed] = useState("42");
  const [tale, setTale] = useState<number | null>(null);
  const cats = useMemo(() => topCategories(d, map, mode), [d, map, mode]);
  const changeMode = (m: Mode) => { setMode(m); setPicks(topCategories(d, map, m).slice(0, 3).map((c) => c.key)); };
  const toggle = (key: string) => setPicks((p) => (p.includes(key) ? p.filter((k) => k !== key) : [...p, key].slice(-3)));
  const showCommunity = (name: string) => { setMode("community"); setPicks((p) => (mode === "community" ? (p.includes(name) ? p : [...p, name].slice(-3)) : [name])); };

  const pickGroups = useMemo(() => picks.map((k) => Number(k.slice(1)) - 1).filter((g) => g >= 0), [picks]);
  const seedTone = useMemo(() => (mode === "community" && seed !== "42" ? alignTones(map.seeds.partitions[seed], map.group, pickGroups) : null),
    [map, mode, seed, pickGroups]);
  const tone = useCallback((i: number): Tone => (seedTone ? seedTone(i) : (picks.indexOf(categoryOf(d, map, mode, i)) + 1) as Tone),
    [d, map, mode, picks, seedTone]);
  const labels = useMemo(() => groupLabels(d, map, mode, picks, rep, seedTone), [d, map, mode, picks, rep, seedTone]);
  const F = d.folktales, s = map.stats;
  const tip = (i: number) => (
    <><strong>{F.title[i]}</strong><br />{F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 70)}` : "no tale type"}<br />
      {F.region[i] || "no region"} · {communityName(d, communityOf(map.group[i]), rep)} · {map.degree[i]} links<br /><em>click to read it and its nearest tales</em></>
  );
  const majors = map.communities.filter((c) => c.name !== "small");
  const seedNmi = seed === "42" ? null : map.seeds.nmi[`42-${seed}`];

  return (
    <Chapter id="communities" num="Folktales · 4" title="Communities of folktales">
      <Why course="week 4 (modularity, Louvain, seed stability, drawing rules), week 6 (TF–IDF, LDA topics)"
        what={<>Louvain community detection splits the weighted network into groups of tales that are linked more among themselves than to the rest. We ran it with three seeds and compared modularity with {int(s.shuffles)} degree-preserving shuffles. Each community is described by its most distinctive words (highest mean TF–IDF weight against all tales, names removed), by the course's TF–IDF with the community as one document, and by its dominant LDA topic. The nine large TF–IDF communities also get a name: our reading of their dominant tale types and words.</>}
        why={<>Communities are the “regions” of the folklore map: the places a parable can land in. Before using them we need to know they are real (better than shuffles), stable (the same with another seed) and what they contain.</>} />
      <div className="controls-row">
        <RepToggle />
        <Segmented label="Colour the map by" value={mode} options={MODES} onChange={changeMode} />
        {mode === "community" && <Segmented label="Louvain run" value={seed} onChange={setSeed} options={[{ value: "42", label: "Seed 42" }, { value: "7", label: "Seed 7" }, { value: "19", label: "Seed 19" }]} />}
      </div>
      <div className="two-col">
        <figure className="figure">
          <NetCanvas map={map} tone={tone} tip={tip} labels={labels} selected={tale} onPick={setTale}
            label={`Network of ${d.corpus.folktales} folktales, coloured: ${picks.map((k) => nameOf(d, map, mode, k, rep)).join(", ")}`} />
          <div className="legend" aria-hidden>
            {picks.map((k, j) => <span key={k}><i className="swatch" style={{ background: `var(--c${j + 1})` }} />{nameOf(d, map, mode, k, rep)}{seedTone ? " (best match)" : ""}</span>)}
            <span><i className="swatch" style={{ background: "var(--neutral)" }} />everything else</span>
          </div>
          <p className="caption">Each dot is a tale, sized by its number of links and placed by a force layout of the whole network. Faint lines are each tale's strongest links, and each label sits at the middle of its coloured group. {seedNmi !== null && <>Seed {seed} against seed 42: NMI {fmt(seedNmi, 2)}. The colours follow the communities that overlap most with the picked ones.</>}</p>
        </figure>
        <div className="panel">
          <span className="label">Pick up to three to compare</span>
          <div className="chips">
            {cats.map((c) => (
              <button key={c.key} type="button" className="chip" aria-pressed={picks.includes(c.key)} onClick={() => toggle(c.key)}>
                {picks.includes(c.key) && <i className="swatch" style={{ background: `var(--c${picks.indexOf(c.key) + 1})` }} />}
                {nameOf(d, map, mode, c.key, rep)} <span className="muted">{c.count}</span>
              </button>
            ))}
          </div>
          <div style={{ marginTop: 14 }}>
            {tale !== null ? <TalePanel story={d} map={map} near={near} rep={rep} i={tale} onSelect={setTale} onClose={() => setTale(null)} />
              : <p className="sans small muted">Click any tale on the map to read its opening, see its ten nearest folktales and the words behind each link, and open both texts at the source.</p>}
          </div>
        </div>
      </div>

      <h3 style={{ marginTop: 28 }}>The {majors.length} large communities ({rep === "tfidf" ? "TF–IDF" : "embeddings"})</h3>
      <div className="cards-grid">
        {majors.map((c) => (
          <button key={c.name} type="button" className="community-card" aria-pressed={mode === "community" && picks.includes(c.name)} onClick={() => showCommunity(c.name)}>
            <div className="row" style={{ justifyContent: "space-between" }}><strong>{communityName(d, c.name, rep)}</strong><span className="muted small">{int(c.size)} tales · {pct(c.share)}</span></div>
            <WordCloud words={c.words.split(/[ ,]+/).filter(Boolean).slice(0, 8)} />
            <div className="small"><span className="muted">Course TF–IDF (community as one document):</span> {c.courseWords.split(" ").slice(0, 6).join(", ")}</div>
            <div className="small"><span className="muted">LDA topic:</span> {c.lda}</div>
            <div className="small"><span className="muted">Types:</span> {c.types.split("; ").slice(0, 2).map((t) => shortType(t.replace(/^\S+\s/, "").replace(/\s*\(\d+\)$/, ""), 30)).join(" · ")}</div>
            <div className="small"><span className="muted">Regions:</span> {c.regions.split("; ").slice(0, 2).join(" · ")}</div>
          </button>
        ))}
      </div>
      <Result>
        <p><strong>The communities are real and fairly stable.</strong> Louvain finds {s.communities} communities, {s.major} of them with at least 1% of the tales. Modularity is {fmt(s.modularity, 2)}, against {fmt(s.nullMean, 3)} in degree-preserving shuffles (z = {fmt(s.z, 0)}). Runs with other seeds agree at NMI {s.seedNmiMin}–{s.seedNmiMax}: switch the seed above to watch the edges of communities move while the large groups stay.</p>
        <p>Read by their words, the communities look like story genres rather than places: {majors.map((c) => `${communityName(d, c.name, rep)} (${c.words.split(", ").slice(0, 2).join(", ")})`).join(", ")}.{rep === d.primary ? " The names are our reading of each community's dominant tale types and words." : ""} Section 5 tests this with the labels.</p>
      </Result>
    </Chapter>
  );
}
