import { useCallback, useMemo, useState } from "react";
import { ATU_CHAPTERS, atuChapter, communityOf, REP_NAME, shortType, type NetMap, type Near, type Story } from "../../data";
import { NetCanvas, type Tone } from "../../components/NetCanvas";
import { NearList, PairCard, ReadLinks } from "../../components/panels";
import { useRep } from "../../components/rep";
import { Search } from "../../components/Search";
import { BarList, Chapter, DataTable, Result, Why } from "../../components/ui";
import { fmt, int, pct } from "../../lib/format";

type Pick = { kind: "chapter" | "type" | "region" | "book"; key: string } | null;

export function CorpusSection({ d, maps }: { d: Story; maps: Record<string, NetMap> }) {
  const { rep } = useRep();
  const map = maps[rep];
  const F = d.folktales, c = d.corpus;
  const [pick, setPick] = useState<Pick>({ kind: "chapter", key: "Animal tales" });
  const chapters = useMemo(() => ATU_CHAPTERS.map((ch) => ({ key: ch.name, label: ch.name, value: F.atu.filter((a) => a && atuChapter(a) === ch.name).length,
    note: `ATU ${ch.lo}–${ch.hi}` })), [F]);
  const typeCounts = useMemo(() => {
    const n = new Map<string, number>();
    F.atu.forEach((a) => a && n.set(a, (n.get(a) ?? 0) + 1));
    return [...n.entries()].sort((a, b) => b[1] - a[1]);
  }, [F]);
  const types = typeCounts.slice(0, 10).map(([a, v]) => {
    const name = F.atuName[F.atu.indexOf(a)];
    return { key: a, label: `${a} ${shortType(name, 36)}`, value: v, note: `ATU ${a} ${name}` };
  });
  const over20 = typeCounts.filter(([, v]) => v > 20).length, single = typeCounts.filter(([, v]) => v === 1).length;
  const regions = Object.entries(c.regionCounts).sort((a, b) => b[1] - a[1]).map(([label, value]) => ({ key: label, label, value }));
  const books = useMemo(() => {
    const n = new Map<string, number>();
    F.collection.forEach((b) => b && n.set(b, (n.get(b) ?? 0) + 1));
    return [...n.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([b, v]) => ({ key: b, label: b.replace(/\b\w/g, (x) => x.toUpperCase()), value: v }));
  }, [F]);
  const magic = chapters.find((x) => x.label === "Tales of magic")?.value ?? 0;
  const inPick = useCallback((i: number) => {
    if (!pick) return false;
    if (pick.kind === "chapter") return !!F.atu[i] && atuChapter(F.atu[i]) === pick.key;
    if (pick.kind === "type") return F.atu[i] === pick.key;
    if (pick.kind === "region") return F.region[i] === pick.key;
    return F.collection[i] === pick.key;
  }, [F, pick]);
  const tone = useCallback((i: number): Tone => (inPick(i) ? 1 : 0), [inPick]);
  const members = useMemo(() => F.title.map((_, i) => i).filter(inPick), [F, inPick]);
  const spread = useMemo(() => {
    const by = new Map<string, number>();
    members.forEach((i) => { const g = communityOf(map.group[i]); by.set(g, (by.get(g) ?? 0) + 1); });
    return [...by.entries()].sort((a, b) => b[1] - a[1]);
  }, [members, map]);
  const pickName = pick ? (pick.kind === "type" ? `ATU ${pick.key} ${shortType(F.atuName[F.atu.indexOf(pick.key)] ?? "", 40)}` : pick.kind === "book" ? pick.key.replace(/\b\w/g, (x) => x.toUpperCase()) : pick.key) : "";
  const choose = (kind: NonNullable<Pick>["kind"]) => (key: string) => setPick((p) => (p && p.kind === kind && p.key === key ? null : { kind, key }));
  const tip = (i: number) => <><strong>{F.title[i]}</strong><br />{F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 60)}` : "no tale type"}<br />{F.region[i] || "no region"} · {communityOf(map.group[i])}</>;

  return (
    <Chapter id="corpus" num="Folktales · 1" title="The folktales and their tale types">
      <Why course="week 5, document checks before modelling"
        what={<>We take {int(c.folktales)} English folktale versions from <em>Annotated Folktales</em> (Hagedorn &amp; Darányi 2022), built on D. L. Ashliman's <em>Folktexts</em>. Each carries up to three labels: its ATU tale type ({int(c.typed)} tales, {int(c.types)} types), the region where it was recorded ({int(c.withRegion)} tales, {c.regions} regions) and the book it was printed in ({int(c.collectionKnown)} tales, {int(c.collections)} books).</>}
        why={<>The ATU index (Aarne–Thompson–Uther) is the folklorists' own grouping of stories by plot. It is the ground truth we compare the network against. Region is the “location” a tale belongs to; the source book is what might fake both.</>} />
      <div className="tiles">
        <div className="tile"><div className="v">{int(c.folktales)}</div><div className="l">folktale versions</div></div>
        <div className="tile"><div className="v">{int(c.types)}</div><div className="l">ATU tale types ({int(c.typed)} tales have one)</div></div>
        <div className="tile"><div className="v">{pct(c.europeShare)}</div><div className="l">of tales with a region are European</div></div>
        <div className="tile"><div className="v">{int(c.collections)}</div><div className="l">source books ({int(c.collectionKnown)} tales have one)</div></div>
      </div>
      <p className="sans small muted" style={{ margin: "0 0 10px" }}>Click any bar to see where those tales sit in the network.</p>
      <div className="three-col">
        <figure className="figure">
          <p className="figure-title">Tales per ATU chapter</p>
          <BarList label="Tales per ATU chapter" items={chapters} format={int} onPick={choose("chapter")} selected={pick?.kind === "chapter" ? pick.key : null} />
          <p className="figure-title" style={{ marginTop: 16 }}>The ten most common tale types</p>
          <BarList label="Most common tale types" items={types} format={int} onPick={choose("type")} selected={pick?.kind === "type" ? pick.key : null} />
        </figure>
        <figure className="figure">
          <p className="figure-title">Where the tales were recorded</p>
          <BarList label="Tales per region" items={regions} format={int} tone="c2" onPick={choose("region")} selected={pick?.kind === "region" ? pick.key : null} />
          <p className="figure-title" style={{ marginTop: 16 }}>The books that supply most tales</p>
          <BarList label="Tales per source book" items={books} format={int} tone="c3" onPick={choose("book")} selected={pick?.kind === "book" ? pick.key : null} />
        </figure>
        <figure className="figure">
          <p className="figure-title">{pick ? `${pickName}: ${int(members.length)} tales` : "Pick a bar"}</p>
          <NetCanvas map={map} tone={tone} tip={tip} size="none" aspect={0.9} label={`Network with ${pickName || "nothing"} highlighted`} />
          {pick && <p className="caption">Their largest communities: {spread.slice(0, 3).map(([g, n]) => `${g} ${pct(n / Math.max(1, members.length))}`).join(", ")}. Compare a tale type with a region: section 5 measures the difference.</p>}
        </figure>
      </div>
      <Result>
        <p>Tales of magic make up {pct(magic / Math.max(1, c.typed))} of the typed tales. Tale types differ widely in size: {over20} have more than 20 versions, {single} have only one. The collection leans on Europe and on a few editors ({books.slice(0, 3).map((b) => b.label).join(", ")}), which is why every later test also asks whether the source book, not the story, explains a pattern.</p>
      </Result>
    </Chapter>
  );
}

export function SimilaritySection({ d, near }: { d: Story; near: Near | null }) {
  const { rep } = useRep();
  const F = d.folktales, c = d.calibration;
  const [tale, setTale] = useState(() => Math.max(0, F.title.findIndex((t) => /^cinderella/i.test(t))));
  const [pair, setPair] = useState<{ rep: "tfidf" | "embedding"; k: number } | null>(null);
  const reps = (["tfidf", "embedding", "tfidf_nouns_masked"] as const).filter((r) => c.byRep[r]);
  const sm = d.secondMethod.find((s) => s.scope === "all parables");
  const items = useMemo(() => F.title.map((t, i) => ({ key: String(i), label: t, sub: F.atu[i] ? `ATU ${F.atu[i]}` : "folktale" })), [F]);
  const lists = (["tfidf", "embedding"] as const).map((r) => near ? near.folk[r].idx[tale].map((j, k) => ({ i: j, cos: near.folk[r].cos[tale][k], words: r === "tfidf" ? near.folk[r].words[tale][k] : undefined })) : []);
  const both = new Set(lists[0].map((x) => x.i).filter((i) => lists[1].some((y) => y.i === i)));
  return (
    <Chapter id="similarity" num="Folktales · 2" title="From words to similarity">
      <Why course="week 5 (cosine similarity, nearest neighbours), week 6 (TF–IDF), week 7 (sentence embeddings, chunking)"
        what={<>Folktales are not linked to each other, so we measure how alike their texts are. Each tale becomes a vector of TF–IDF word weights (stop words removed, negations kept), and two tales are as similar as the cosine of their vectors. As a second method, a pretrained sentence encoder (all-MiniLM-L6-v2) turns each tale into one “meaning” vector, averaged over passages of at most 200 tokens.</>}
        why={<>The network is built from these similarities, so they are the measuring instrument of the whole project. Using two instruments shows which results depend on how text is measured.</>} />
      <figure className="figure">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <p className="figure-title" style={{ margin: 0 }}>One tale, two instruments: its {d.settings.nearK} nearest folktales</p>
          <div className="row">
            <Search items={items} onPick={(k) => { setTale(Number(k)); setPair(null); }} placeholder="Pick a folktale by title…" label="Pick a folktale" />
            <button type="button" className="btn" onClick={() => { setTale(Math.floor(Math.random() * F.title.length)); setPair(null); }}>Random tale</button>
          </div>
        </div>
        <div className="sans" style={{ marginBottom: 8 }}><strong>{F.title[tale]}</strong> <span className="muted small">· {F.atu[tale] ? `ATU ${F.atu[tale]} ${shortType(F.atuName[tale], 50)}` : "no tale type"}</span> <ReadLinks story={d} atu={F.atu[tale]} title={F.title[tale]} /></div>
        {!near ? <p className="muted small">Loading the neighbours…</p> : (
          <>
            <div className="two-col even">
              {(["tfidf", "embedding"] as const).map((r, k) => (
                <div key={r}>
                  <span className="label">{REP_NAME[r]}</span>
                  <NearList story={d} items={lists[k]} sameType={F.atu[tale]} onOpen={(j) => { setTale(j); setPair(null); }}
                    onPair={(q) => setPair(pair && pair.rep === r && pair.k === q ? null : { rep: r, k: q })} pairOpen={pair?.rep === r ? pair.k : null} />
                </div>
              ))}
            </div>
            <p className="sans small" style={{ margin: "8px 0 0" }}>{both.size} of the {d.settings.nearK} nearest tales are the same under both instruments; {lists[0].filter((x) => F.atu[x.i] && F.atu[x.i] === F.atu[tale]).length} (TF–IDF) and {lists[1].filter((x) => F.atu[x.i] && F.atu[x.i] === F.atu[tale]).length} (embeddings) share its tale type.</p>
            {pair && <PairCard story={d} near={near} left={{ kind: "tale", i: tale }} right={lists[pair.rep === "tfidf" ? 0 : 1][pair.k].i} cosine={lists[pair.rep === "tfidf" ? 0 : 1][pair.k].cos}
              words={near.folk.tfidf.words[tale][near.folk.tfidf.idx[tale].indexOf(lists[pair.rep === "tfidf" ? 0 : 1][pair.k].i)] ?? undefined} onClose={() => setPair(null)} />}
          </>
        )}
      </figure>
      <div className="two-col" style={{ marginTop: 18 }}>
        <figure className="figure">
          <p className="figure-title">Which instrument recognises stories better?</p>
          <p className="figure-sub">Share of {c.queries} held-out religious retellings with a folktale of the same tale type among their {c.k} most similar folktales</p>
          <BarList label="Recall by representation" items={reps.map((r) => ({ label: REP_NAME[r] ?? r, value: c.byRep[r].recall }))} max={1} format={(v) => pct(v)} />
          <p className="caption">Chance with {c.k} random folktales: {pct(c.chance, 1)}. The test itself is on the Parables page.</p>
          <DataTable head={["Representation", "Recall", "95% interval"]} rows={reps.map((r) => [REP_NAME[r] ?? r, pct(c.byRep[r].recall), `${pct(c.byRep[r].low)}–${pct(c.byRep[r].high)}`])} />
        </figure>
        <Result title="What we chose">
          <p><strong>TF–IDF is the main instrument</strong>: it finds the right tale type more often ({pct(c.byRep.tfidf.recall)} against {pct(c.byRep.embedding.recall)} for embeddings). Embeddings stay as the second method everywhere: the switch at the top of each section turns the whole site to them{rep === "embedding" ? " (it is on now)" : ""}.</p>
          {sm && <p>The two agree only moderately on which parables are most folk-like (Spearman {fmt(sm.spearman, 2)}), so results that hold under both are the ones we trust most.</p>}
        </Result>
      </div>
    </Chapter>
  );
}
