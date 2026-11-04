import { useMemo, useState } from "react";
import { HowMade, Loading, Segmented, downloadText, toCsv } from "../../components/ui";
import { cohortName, fmt, repLabel, times } from "../../lib/format";
import { useFindings, verdict } from "./shared";

export function RobustnessChapter() {
  const F = useFindings();
  const [group, setGroup] = useState<"all" | "main" | "representation" | "cohort">("all");
  const rows = useMemo(() => {
    if (!F.agreement || !F.neighbours || !F.summary) return [];
    const by = new Map<string, Record<string, (typeof F.agreement.rows)[number]>>();
    F.agreement.rows.forEach((r) => {
      const k = `${r.graph_id}|${r.seed}`;
      if (!by.has(k)) by.set(k, {});
      by.get(k)![r.label] = r;
    });
    return [...by.entries()].map(([k, labs]) => {
      const a = labs.atu, p = labs.place, g = labs.region;
      const nbKey = `${a.cohort}|${a.rep}`;
      const nb = F.neighbours!.results[nbKey] ?? F.neighbours!.results[`${a.cohort}|${a.rep.startsWith("semantic") ? "semantic" : "lexical"}`];
      const m = (r: typeof a, lab: "atu" | "place" | "region") => ({ excess: r.nmi.excess, r: r.assortativity.observed, lift: nb?.[lab].lift ?? 0 });
      return {
        key: k, group: a.group, cohort: a.cohort, rep: a.rep, density: a.density, seed: a.seed,
        ex: [a.nmi.excess, p.nmi.excess, g.nmi.excess], exNI: [a.non_isolates?.nmi.excess, p.non_isolates?.nmi.excess, g.non_isolates?.nmi.excess],
        r: [a.assortativity.observed, p.assortativity.observed, g.assortativity.observed],
        lift: [nb?.atu.lift, nb?.place.lift, nb?.region.lift],
        allExceed: [a, p, g].every((x) => x.nmi.exceeds_all && x.assortativity.exceeds_all),
        vPlace: verdict(m(a, "atu"), m(p, "place"), "type", "place"), vRegion: verdict(m(a, "atu"), m(g, "region"), "type", "region"),
      };
    }).filter((r) => group === "all" || r.group === group);
  }, [F.agreement, F.neighbours, F.summary, group]);
  if (!F.agreement || !F.neighbours) return <Loading what="robustness results" />;
  const consistentPlace = rows.filter((r) => r.vPlace.consistent).length;
  const consistentRegion = rows.filter((r) => r.vRegion.consistent).length;
  const typeTopNmi = rows.filter((r) => r.ex[0] > r.ex[1] && r.ex[0] > r.ex[2]).length;
  return (
    <div>
      <div className="tiles">
        <div className="tile"><div className="v">{rows.filter((r) => r.allExceed).length}/{rows.length}</div><div className="l">settings where all three label systems beat every shuffle</div></div>
        <div className="tile"><div className="v">{typeTopNmi}/{rows.length}</div><div className="l">settings where ATU type has the largest NMI excess</div></div>
        <div className="tile"><div className="v">{consistentPlace}/{rows.length}</div><div className="l">settings where type vs place is consistent on all three measures</div></div>
        <div className="tile"><div className="v">{consistentRegion}/{rows.length}</div><div className="l">settings where type vs region is consistent (otherwise mixed)</div></div>
      </div>
      <div className="row" style={{ marginBottom: 8 }}>
        <Segmented label="Group" value={group} onChange={setGroup} options={[{ value: "all", label: "All" }, { value: "main", label: "Density × seed" }, { value: "representation", label: "Representation variants" }, { value: "cohort", label: "Cohort variants" }]} />
        <button className="btn small" onClick={() => downloadText("robustness.csv", toCsv([["cohort", "representation", "density", "seed", "nmi_excess_atu", "nmi_excess_place", "nmi_excess_region", "r_atu", "r_place", "r_region", "lift_atu", "lift_place", "lift_region", "type_vs_place", "type_vs_region"],
          ...rows.map((r) => [r.cohort, r.rep, r.density, r.seed, ...r.ex, ...r.r, ...r.lift, r.vPlace.text, r.vRegion.text])]))}>Download CSV</button>
      </div>
      <div className="table-wrap" style={{ maxHeight: 520 }}>
        <table className="data">
          <thead>
            <tr><th>Setting</th><th className="num" colSpan={3}>NMI excess over shuffles: type · place · region</th><th className="num" colSpan={3}>Assortativity r: type · place · region</th><th className="num" colSpan={3}>Top-10 lift: type · place · region</th><th>Type vs place</th><th>Type vs region</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td className="nowrap">{cohortName(r.cohort)} · {repLabel(r.rep)} · {Math.round(r.density * 100)}% · seed {r.seed}</td>
                {r.ex.map((v, k) => <td key={k} className="num" title={r.exNI[k] !== undefined ? `without isolates: ${fmt(r.exNI[k])}` : undefined} style={{ fontWeight: k === 0 ? 650 : 400 }}>{fmt(v)}</td>)}
                {r.r.map((v, k) => <td key={k} className="num">{fmt(v)}</td>)}
                {r.lift.map((v, k) => <td key={k} className="num">{times(v ?? null)}</td>)}
                <td><span className={`chip ${r.vPlace.consistent ? "ok" : "warn"}`}>{r.vPlace.consistent ? r.vPlace.text.replace(" on all three", "") : "mixed"}</span></td>
                <td><span className={`chip ${r.vRegion.consistent ? "ok" : "warn"}`}>{r.vRegion.consistent ? r.vRegion.text.replace(" on all three", "") : "mixed"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(() => {
        const n = rows.length;
        const all = rows.filter((r) => r.allExceed).length;
        const liftTop = rows.filter((r) => (r.lift[0] ?? 0) > (r.lift[1] ?? 0) && (r.lift[0] ?? 0) > (r.lift[2] ?? 0)).length;
        const regionTopR = rows.filter((r) => r.r[2] > r.r[0] && r.r[2] > r.r[1]).length;
        const main = (F.summary?.graphs ?? []).filter((g) => g.group === "main");
        const range = (rep: string) => {
          const v = main.filter((g) => g.rep === rep).flatMap((g) => Object.values(g.seed_agreement_nmi ?? {}));
          return v.length ? `${fmt(Math.min(...v), 2)}–${fmt(Math.max(...v), 2)}` : "–";
        };
        return (
          <>
            <div className="prose-wide" style={{ marginTop: 14 }}>
              <p><strong>What stays stable</strong> (counted over the {n} rows shown): all three recorded labels beat every one of their shuffles in {all} of {n}. ATU type has the largest NMI excess in {typeTopNmi} of {n} and the largest neighbour lift in {liftTop} of {n}. This holds after removing near-duplicates, suspected fragments or isolates, masking names, changing pooling or chunk size, and capping each region at {F.summary?.config.balanced_cap} tales.</p>
              <p><strong>What changes:</strong> the assortativity coefficient favours broad region in {regionTopR} of {n} rows. The pre-declared all-three-measures verdict is therefore consistent for type vs region in only {consistentRegion} of {n} rows and for type vs place in {consistentPlace} of {n}; elsewhere it is <em>mixed</em>. Louvain communities differ between seeds: seed-pair NMI is {range("lexical")} for TF–IDF graphs and {range("semantic")} for embedding graphs.</p>
            </div>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table className="data">
                <caption className="visually-hidden">Modularity against degree-preserving shuffles</caption>
                <thead><tr><th>Graph (joint cohort, seed 42)</th><th className="num">Communities</th><th className="num">Isolates</th><th className="num">Modularity Q</th><th className="num">Q in degree-preserving shuffles</th><th className="num">Seed-pair NMI</th></tr></thead>
                <tbody>
                  {main.map((g) => (
                    <tr key={g.graph_id}>
                      <td>{repLabel(g.rep)} · {Math.round(g.density * 100)}%</td><td className="num">{g.communities}</td><td className="num">{g.isolates}</td>
                      <td className="num">{fmt(g.modularity)}</td>
                      <td className="num">{g.modularity_null ? `${fmt(g.modularity_null.null_mean)} ± ${fmt(g.modularity_null.null_sd)} (${g.modularity_null.shuffles} shuffles)` : "not computed"}</td>
                      <td className="num">{Object.values(g.seed_agreement_nmi ?? {}).map((v) => fmt(v, 2)).join(" · ") || "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="caption">Modularity is compared with networks that keep every tale's number of edges and the set of edge weights but rewire who is joined to whom (week 4's “compared to what”). A gap shows grouping beyond what degrees produce; it does not make any partition the “true” one.</p>
          </>
        );
      })()}
      <HowMade
        measured="The same agreement measures recomputed for every precomputed variation, each with its own 1,000-shuffle reference."
        records="Joint cohort and its pre-declared variants (near-duplicate-reduced, fragment-free, region-balanced subset of at most 60 tales per region)."
        method="Stability across seeds via NMI (week 4, §4); null comparisons (weeks 2–4); sensitivity analysis as fixed in ANALYSIS_PLAN.md."
        infer="Which conclusions do not depend on reasonable analysis choices."
        cannot="Variations that were not computed. Each row is one partition; seeds are a stability check, not a significance test." />
    </div>
  );
}
