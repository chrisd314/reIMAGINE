import { useCallback, useState } from "react";
import type { Rep } from "../data/types";
import { useData } from "../data/load";
import type { SummaryPayload } from "../data/types";
import { PairReader } from "../components/PairReader";
import { ErrorState, Loading } from "../components/ui";
import { int } from "../lib/format";
import type { Route } from "../lib/router";
import { Chapter, WhenVisible } from "./story/shared";
import { SectionBoundary } from "../components/SectionBoundary";
import { OpeningScene } from "./story/OpeningScene";
import { CorpusChapter } from "./story/CorpusChapter";
import { MorphScene } from "./story/MorphScene";
import { NeighbourScene } from "./story/NeighbourScene";
import { GroupingScene } from "./story/GroupingScene";
import { DensityScene } from "./story/DensityScene";
import { ReaderChapter } from "./story/ReaderChapter";
import { DistanceChapter } from "./story/DistanceChapter";
import { RobustnessChapter } from "./story/RobustnessChapter";

const CHAPTERS = [
  { id: "guess", title: "Guess the connection" },
  { id: "corpus", title: "Meet the corpus" },
  { id: "places", title: "From places to textual neighbourhoods" },
  { id: "neighbours", title: "Words versus meaning" },
  { id: "grouping", title: "Geography or tale family?" },
  { id: "density", title: "How much similarity earns an edge" },
  { id: "read", title: "Read why two stories connect" },
  { id: "distance", title: "Compare distances" },
  { id: "challenge", title: "Challenge the result" },
  { id: "limits", title: "What we can and cannot say" },
];

export function Story({ route, navigate }: { route: Route; navigate: (p: string, params?: Record<string, string | null | undefined>, replace?: boolean) => void }) {
  const summary = useData<SummaryPayload>("summary.json");
  const [current, setCurrent] = useState("guess");
  const onVisible = useCallback((id: string) => setCurrent(id), []);
  const pair = route.params.pair?.split(",");
  const openPair = (a: string, b: string) => navigate("/", { ...route.params, pair: `${a},${b}` }, true);
  const toExplore = (id: string, rep: Rep) => navigate("/explore", { tale: id, rep });
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: document.documentElement.dataset.motion === "off" ? "auto" : "smooth" });
  if (summary.error) return <div className="page"><ErrorState message={summary.error} /></div>;
  if (!summary.data) return <div className="page"><Loading what="the story" /></div>;
  const s = summary.data;
  const c = s.counts;
  const sp = s.story_pairs ?? {};
  const pairs: Record<string, { a: string; b: string }> = { ...(s.opening ? { opening: { a: s.opening.a, b: s.opening.b } } : {}), ...sp };
  const nav = (k: number) => (
    <nav className="chapter-nav" aria-label="Chapter navigation">
      {k > 0 ? <button className="btn small ghost" onClick={() => go(CHAPTERS[k - 1].id)}>← {CHAPTERS[k - 1].title}</button> : <span />}
      {k < CHAPTERS.length - 1 ? <button className="btn small ghost" onClick={() => go(CHAPTERS[k + 1].id)}>{CHAPTERS[k + 1].title} →</button> : <a className="btn small" href="#/explore">Open Explore →</a>}
    </nav>
  );
  return (
    <>
      <header className="hero">
        <div className="kicker">A literary atlas of {int(c.text_cohort)} recorded folktales</div>
        <h1>How far can a story travel?</h1>
        <p className="lede">The same tale turns up in very different places: a father who picks a forbidden flower, a heroine whose hands are cut off, a rabbit stuck to a tar figure. This site measures how the texts of {int(c.text_cohort)} recorded folktales resemble one another, and asks whether those resemblances follow geography or the kind of story.</p>
        <div className="questions">
          <div className="question"><div className="tag">The question</div>Do folktales form communities primarily around their geographical origins or around recurring narrative motifs?</div>
          <div className="question"><div className="tag">What we can actually test</div>Do communities in a folktale <em>text-similarity network</em> align more closely with <em>recorded</em> geographical provenance or with established <em>tale types</em> (ATU), and does the answer differ between word-based (TF–IDF) and meaning-based (embedding) representations?</div>
        </div>
        <p className="prose small sans muted">“Recorded provenance” is where a collector placed a tale, not where it began. “Tale type” is a family of related stories in the Aarne–Thompson–Uther index, assigned here by the source website's page structure, not motif-by-motif annotation. Similarity is a measurement under a representation, not proof of shared ancestry.</p>
        <div className="row" style={{ marginTop: 18 }}>
          <button className="btn primary" onClick={() => go("guess")}>Begin the story ↓</button>
          <a className="btn" href="#/explore">Go straight to Explore</a>
          <a className="btn ghost" href="#/data">Data &amp; methods</a>
        </div>
        <div className="tiles" style={{ maxWidth: 900 }}>
          <div className="tile"><div className="v">{int(c.joint_cohort)}</div><div className="l">tales in the comparison cohort</div></div>
          <div className="tile"><div className="v">{c.joint_distinct_atu}</div><div className="l">ATU tale types</div></div>
          <div className="tile"><div className="v">{c.joint_distinct_place}</div><div className="l">recorded places &amp; communities</div></div>
          <div className="tile"><div className="v">2</div><div className="l">text representations, compared separately</div></div>
        </div>
      </header>
      <nav className="toc" aria-label="Chapters">{CHAPTERS.map((ch) => <a key={ch.id} href={`#/`} onClick={(e) => { e.preventDefault(); go(ch.id); }} aria-current={current === ch.id} title={ch.title} aria-label={ch.title} />)}</nav>

      <Chapter id="guess" num="Chapter 1" title="Guess the connection" onVisible={onVisible}>
        <SectionBoundary name="opening"><OpeningScene summary={s} onRead={openPair} /></SectionBoundary>{nav(0)}
      </Chapter>
      <Chapter id="corpus" num="Chapter 2" title="Meet the corpus" onVisible={onVisible}>
        <WhenVisible><SectionBoundary name="chapter"><CorpusChapter summary={s} /></SectionBoundary></WhenVisible>{nav(1)}
      </Chapter>
      <Chapter id="places" num="Chapter 3" title="From places to textual neighbourhoods" onVisible={onVisible}>
        <p className="prose">If geography shaped the texts strongly, tales recorded in the same region would also sit together when the same tales are arranged by textual similarity. Switch the arrangement and follow the ringed tale.</p>
        <WhenVisible minHeight={520}><SectionBoundary name="chapter"><MorphScene focusId={s.opening?.a ?? "tale-0086"} /></SectionBoundary></WhenVisible>{nav(2)}
      </Chapter>
      <Chapter id="neighbours" num="Chapter 4" title="Words versus meaning" onVisible={onVisible}>
        <p className="prose">Each tale has its ten nearest tales, measured in the full feature space. Switch between counting distinctive words and comparing meaning, and see which neighbours persist.</p>
        <WhenVisible minHeight={520}><SectionBoundary name="chapter"><NeighbourScene onRead={openPair} onExplore={toExplore} /></SectionBoundary></WhenVisible>{nav(3)}
      </Chapter>
      <Chapter id="grouping" num="Chapter 5" title="Geography or tale family?" onVisible={onVisible}>
        <p className="prose">Louvain community detection groups the network without knowing any labels. We then ask how much those communities know about the recorded labels, compared with shuffled labels that keep every category's size.</p>
        <WhenVisible minHeight={560}><SectionBoundary name="chapter"><GroupingScene /></SectionBoundary></WhenVisible>{nav(4)}
      </Chapter>
      <Chapter id="density" num="Chapter 6" title="How much similarity earns an edge" onVisible={onVisible}>
        <p className="prose">A similarity network needs a rule for which pairs become edges. We keep the strongest 5%, 10% (the setting fixed in advance) or 15% of all pairs. Step between them and watch what changes.</p>
        <WhenVisible minHeight={520}><SectionBoundary name="chapter"><DensityScene /></SectionBoundary></WhenVisible>{nav(5)}
      </Chapter>
      <Chapter id="read" num="Chapter 7" title="Read why two stories connect" onVisible={onVisible}>
        <WhenVisible><SectionBoundary name="chapter"><ReaderChapter pairs={pairs} onRead={openPair} /></SectionBoundary></WhenVisible>{nav(6)}
      </Chapter>
      <Chapter id="distance" num="Chapter 8" title="Compare distances" onVisible={onVisible}>
        <p className="prose">Another way to ask about geography: are tales recorded far apart less similar than tales recorded close together?</p>
        <WhenVisible minHeight={600}><SectionBoundary name="chapter"><DistanceChapter onRead={openPair} /></SectionBoundary></WhenVisible>{nav(7)}
      </Chapter>
      <Chapter id="challenge" num="Chapter 9" title="Challenge the result" onVisible={onVisible}>
        <p className="prose">Every number above comes from one pre-declared setting. Here are all the precomputed variations side by side.</p>
        <WhenVisible minHeight={500}><SectionBoundary name="chapter"><RobustnessChapter /></SectionBoundary></WhenVisible>{nav(8)}
      </Chapter>
      <Chapter id="limits" num="Chapter 10" title="What we can and cannot say" onVisible={onVisible}>
        <div className="grid-2">
          <div className="prose">
            <h3>Supported by this analysis</h3>
            <ul>
              <li>In this sample of {int(c.joint_cohort)} English-language texts, textual neighbourhoods are associated with <strong>both</strong> tale type and recorded geography, far beyond label-shuffle expectations, under both representations.</li>
              <li>Per tale, <strong>tale type is the much sharper signal</strong>: nearest neighbours share a tale's ATU type many times more often than chance, while geography's lift is modest.</li>
              <li>Geography acts as a <strong>broad, diffuse</strong> signal. Because regions are few and large, it accounts for a comparable or larger share of same-label edges (assortativity), so the pre-declared verdict for type vs region is <strong>mixed</strong>.</li>
              <li>Similarity declines weakly with distance between recorded points, and same-type pairs stay far more similar at every distance.</li>
            </ul>
          </div>
          <div className="prose">
            <h3>Not supported</h3>
            <ul>
              <li>Where any tale originated, how tales travelled, or who borrowed from whom. Recorded provenance is a collector's attribution, and a distance correlation is not transmission.</li>
              <li>Claims about world folklore: the sample is curated, translated, and {">"}70% European.</li>
              <li>Motif-level claims: ATU labels are page-level assignments, and type-level motif lists are not tale annotations.</li>
              <li>Human judgement of what similar pairs share: the validation study is <strong>{s.validation_status}</strong>; no annotations exist yet. <a href="#/validation">Help annotate</a>.</li>
            </ul>
            <p className="small sans muted">Further limitations, including source licensing, truncated texts and source-dependence, are listed in Data &amp; Methods and in LIMITATIONS.md.</p>
          </div>
        </div>
        <div className="callout neutral" style={{ marginTop: 20 }}>
          <strong>Next: religious parables on this map.</strong> Do the teaching stories of five religions tell the same kinds of stories as the folktales, and do they land in the same part of the map? <a href="#/parables">Read part two</a>.
        </div>
        {nav(9)}
      </Chapter>
      {pair && pair.length === 2 && <PairReader a={pair[0]} b={pair[1]} onClose={() => navigate("/", { ...route.params, pair: null }, true)} onSwap={() => openPair(pair[1], pair[0])} />}
    </>
  );
}
