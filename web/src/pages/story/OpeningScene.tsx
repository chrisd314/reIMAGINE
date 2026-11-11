import { useEffect, useMemo, useState } from "react";
import { load, taleUrl } from "../../data/load";
import type { SummaryPayload, TalePayload } from "../../data/types";
import { lexicalCosine, passageMatches, passageText, semanticCosine } from "../../data/vectors";
import { CoverageMap } from "../../components/charts";
import { useLand } from "../../components/useGraphModel";
import { HowMade, Loading } from "../../components/ui";
import { fmt, int } from "../../lib/format";
import { REGION_COLOURS } from "../../lib/colours";
import { haversineKm } from "../../lib/geo";

type Choice = "connection" | "different" | "unsure";

export function OpeningScene({ summary, onRead }: { summary: SummaryPayload; onRead: (a: string, b: string) => void }) {
  const op = summary.opening;
  const [a, setA] = useState<TalePayload | null>(null);
  const [b, setB] = useState<TalePayload | null>(null);
  const [choice, setChoice] = useState<Choice | null>(null);
  const land = useLand(choice !== null);
  useEffect(() => {
    if (!op) return;
    Promise.all([load<TalePayload>(taleUrl(op.a)), load<TalePayload>(taleUrl(op.b))]).then(([x, y]) => { setA(x); setB(y); });
  }, [op]);
  const scores = useMemo(() => (a && b ? { sem: semanticCosine(a, b), lex: lexicalCosine(a, b), pass: passageMatches(a, b, 1).best[0] } : null), [a, b]);
  if (!op) return <p className="muted">No opening pair configured in this run.</p>;
  if (!a || !b || !scores) return <Loading what="two excerpts" />;
  const excerpt = (t: TalePayload, chunk: number) => passageText(t, chunk) ?? "[this passage is not included in this build]";
  const revealed = choice !== null;
  const km = a.provenance.lat != null && b.provenance.lat != null ? haversineKm(a.provenance.lat, a.provenance.lon!, b.provenance.lat, b.provenance.lon!) : null;
  const response: Record<Choice, string> = {
    connection: "Many readers notice the same thing. Here is what the records say.",
    different: "That is a fair reading too. The tales also differ in setting, characters and tone. Here is what the records say.",
    unsure: "Uncertainty is reasonable from one passage each. Here is what the records say.",
  };
  return (
    <div>
      <p className="prose">Here are two passages from the corpus. Before you see where they were recorded or what type of tale they belong to, read them and decide for yourself.</p>
      <div className="excerpts" style={{ gap: revealed ? 34 : 22 }}>
        {[{ t: a, c: op.a_chunk, k: "A" }, { t: b, c: op.b_chunk, k: "B" }].map(({ t, c, k }, idx) => (
          <article key={k} className="excerpt" style={{ transform: revealed ? `translateX(${idx === 0 ? -6 : 6}px)` : "none" }} aria-label={`Excerpt ${k}`}>
            <div className="who">Excerpt {k}</div>
            <p style={{ margin: 0 }}>“{excerpt(t, c)}”</p>
            {revealed && (
              <div className="reveal">
                <div style={{ fontFamily: "var(--serif)", fontSize: 18, fontWeight: 600 }}>{t.title}</div>
                <div><strong>Recorded provenance:</strong> {t.provenance.place}{t.provenance.region ? ` · ${t.provenance.region}` : ""}</div>
                <div><strong>Tale type:</strong> ATU {t.atu.id} — {t.atu.name}</div>
                <div className="muted">{t.source}</div>
              </div>
            )}
          </article>
        ))}
      </div>
      {!revealed ? (
        <div className="row" style={{ marginTop: 18 }} role="group" aria-label="Your impression">
          <button className="btn primary" onClick={() => setChoice("connection")}>I see a connection</button>
          <button className="btn" onClick={() => setChoice("different")}>They seem different</button>
          <button className="btn" onClick={() => setChoice("unsure")}>Unsure</button>
          <span className="small muted sans">Your answer stays in this browser tab and is not recorded or scored.</span>
        </div>
      ) : (
        <div className="grid-2" style={{ marginTop: 22, alignItems: "start" }}>
          <div>
            <p className="callout neutral">{response[choice!]}</p>
            <p>Both tales are catalogued as <strong>ATU {a.atu.id}, {a.atu.name}</strong>, but they were recorded about <strong>{km ? int(Math.round(km / 100) * 100) : "?"} km</strong> apart ({a.provenance.place} and {b.provenance.place}). Their whole-tale similarity is <strong>{fmt(scores.sem)}</strong> with embeddings and <strong>{fmt(scores.lex)}</strong> with TF–IDF. The closest pair of passages scores <strong>{fmt(scores.pass?.score)}</strong>.</p>
            <p className="small">Recorded provenance is where a collector placed the tale, not where it was invented. One striking pair is an illustration, not evidence that a story travelled. The rest of this page asks whether such resemblances follow <em>tale type</em> or <em>geography</em> across the whole corpus.</p>
            <div className="row">
              <button className="btn accent" onClick={() => onRead(a.id, b.id)}>Read both tales side by side</button>
              <button className="btn" onClick={() => setChoice(null)}>Try again</button>
            </div>
          </div>
          <figure className="figure" style={{ margin: 0 }}>
            <div className="figure-title">The two recorded locations</div>
            <CoverageMap land={land} height={300}
              points={[a, b].map((t) => ({ lat: t.provenance.lat!, lon: t.provenance.lon!, count: 6, label: t.provenance.place!, colour: REGION_COLOURS[t.provenance.region ?? ""] ?? "#2d6a6a", approximate: true }))}
              highlight={[a.provenance.place!, b.provenance.place!]}
              lines={[{ a: [a.provenance.lat!, a.provenance.lon!], b: [b.provenance.lat!, b.provenance.lon!] }]} />
            <figcaption className="caption">Dots are Natural Earth label points for the recorded countries (approximate). The dashed line marks a comparison, not a travel route.</figcaption>
          </figure>
        </div>
      )}
      <HowMade
        measured="Cosine similarity between whole tales (TF–IDF vectors and averaged sentence embeddings) and between the closest pair of ~200-token passages."
        records="Two tales from the joint cohort. Chosen after inspecting computed neighbours: the eighth most similar same-type pair from different continents among complete tales over 250 words from different sources."
        method="TF–IDF and cosine (week 6, §1); sentence embeddings with chunking (week 7, §1–2); passage retrieval (week 7, §6)."
        infer="These two recorded versions share a recognisable episode and are close under both representations."
        cannot="That the story moved from one place to the other, that it originated in either, or that this pair is typical (it was selected for clarity)." />
    </div>
  );
}
