import { useState } from "react";
import { useNear, useNetwork, useStory } from "../../data";
import { useRep } from "../../components/rep";
import { Failed, Loading, PageHead, Result } from "../../components/ui";
import { int, list } from "../../lib/format";
import { TextsSection } from "./TextsSection";
import { TestChapter } from "./TestChapter";
import { PlaceChapter } from "./PlaceChapter";
import { LandChapter } from "./LandChapter";
import { WordsSection } from "./WordsSection";
import { BreakChapter, CHECKS, HEADLINE, holds } from "./BreakChapter";

export const PARABLE_SECTIONS = [
  { id: "texts", label: "Parables and baseline" },
  { id: "test", label: "A test for the method" },
  { id: "place", label: "Closer than the baseline?" },
  { id: "land", label: "Where they land" },
  { id: "words", label: "What the resemblance rests on" },
  { id: "break", label: "Trying to break it" },
];

/** A tradition named in the address (#/parables/land?t=Sufi) is preselected. */
function tradFromHash(traditions: string[]): string {
  const t = new URLSearchParams(window.location.hash.split("?")[1] ?? "").get("t");
  return t && traditions.includes(t) ? t : "all";
}

export function ParablesPage() {
  const { data: d, error } = useStory();
  const { data: net, error: e2 } = useNetwork();
  const { data: near } = useNear();
  const { rep } = useRep();
  const [trad, setTrad] = useState<string | null>(null);          // shared by sections 3 and 4
  if (error || e2) return <Failed error={(error ?? e2) as string} />;
  if (!d || !net) return <Loading what="the parables" />;
  const t = trad ?? tradFromHash(d.traditions);
  const H = d.byRep[rep].headline, band = d.byRep[rep].folkBand;
  const below = H.filter((h) => h.par < band.q25).length;
  const standing = d.traditions.filter((x) => holds(d, x, (v) => v === HEADLINE) && CHECKS.every((c) => holds(d, x, c.match)));
  return (
    <>
      <PageHead page="parables" kicker="reIMAGINE · part 3" title="Placing the parables"
        lede={<>{int(d.corpus.parables)} parables from five religious traditions are placed among the {int(d.corpus.folktales)} folktales by text similarity and compared with {int(d.corpus.baseline)} non-story passages from the same traditions, from the same translation wherever possible. Are they closer to folktales than their own scripture, and which communities and tale types do they reach? Every text can be opened, read beside its nearest folktales, and followed to its source.</>}
        sections={PARABLE_SECTIONS} />
      <TextsSection d={d} near={near} />
      <TestChapter d={d} near={near} />
      <PlaceChapter d={d} near={near} trad={t} setTrad={setTrad} />
      <LandChapter d={d} net={net} near={near} trad={t} setTrad={setTrad} />
      <WordsSection d={d} near={near} />
      <BreakChapter d={d} />
      <section className="chapter" aria-label="Summary">
        <div className="wrap">
          <Result title="What the parables tell us">
            <p>{list(H.filter((h) => h.closer).map((h) => h.tradition))} parables sit closer to folktales than their own scripture's non-story text ({rep === "tfidf" ? "TF–IDF" : "embeddings"}), and only {list(standing)} {standing.length === 1 ? "does" : "do"} so under every check. Each tradition reaches its own communities and tale types.{below === H.length ? " None of them reads like a folktale: every tradition's parables stay below folktales compared with each other." : ""}</p>
          </Result>
          <div className="next-page"><a href="#/folktales">← Part 1 and 2: the folktale network</a><a href="#/explore">Explore the network</a><a href="#/">The answer, on the overview →</a></div>
        </div>
      </section>
    </>
  );
}
