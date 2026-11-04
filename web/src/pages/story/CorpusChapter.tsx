import { useMemo } from "react";
import { catalogueRows, useData } from "../../data/load";
import type { CataloguePayload, SummaryPayload } from "../../data/types";
import { BarList, CoverageMap, Funnel, pointsByCoordinate } from "../../components/charts";
import { useLand } from "../../components/useGraphModel";
import { HowMade, Loading } from "../../components/ui";
import { ATU_CHAPTER_COLOURS, ATU_CHAPTER_ORDER, REGION_COLOURS, REGION_ORDER } from "../../lib/colours";
import { int, pct } from "../../lib/format";

export function CorpusChapter({ summary }: { summary: SummaryPayload }) {
  const cat = useData<CataloguePayload>("catalogue.json");
  const land = useLand(true);
  const c = summary.counts;
  const d = useMemo(() => {
    if (!cat.data) return null;
    const rows = catalogueRows(cat.data);
    const joint = rows.filter((r) => r.in_joint);
    const regionCounts = REGION_ORDER.map((reg) => ({ label: reg, value: joint.filter((r) => r.region === reg).length, colour: REGION_COLOURS[reg] })).filter((x) => x.value > 0);
    const chapterCounts = ATU_CHAPTER_ORDER.map((ch) => ({ label: ch, value: joint.filter((r) => r.atu_chapter === ch).length, colour: ATU_CHAPTER_COLOURS[ch] }));
    const points = pointsByCoordinate(joint, (reg) => REGION_COLOURS[reg ?? ""] ?? "#2d6a6a");
    const kinds = new Map<string, number>();
    rows.forEach((r) => { const k = r.entity_kind.split(" | ")[0]; kinds.set(k, (kinds.get(k) ?? 0) + 1); });
    const kindOrder = ["country", "mixed", "community", "region", "author", "collection", "unknown"];
    const europe = joint.filter((r) => (r.region ?? "").includes("Europe")).length;
    const unlocatedJoint = joint.filter((r) => r.lat == null).length;
    const geoUnknownAtu = rows.filter((r) => r.in_atu && !r.in_joint).length;
    const topTypes = Object.entries(joint.reduce<Record<string, number>>((acc, r) => { acc[`${r.atu} ${r.atu_name ?? ""}`] = (acc[`${r.atu} ${r.atu_name ?? ""}`] ?? 0) + 1; return acc; }, {}))
      .sort((p, q) => q[1] - p[1]).slice(0, 8).map(([label, value]) => ({ label, value }));
    const sizes = (key: (r: (typeof joint)[number]) => string | null) => {
      const m = new Map<string, number>();
      joint.forEach((r) => { const k = key(r); if (k) m.set(k, (m.get(k) ?? 0) + 1); });
      const v = [...m.values()].sort((a, b) => a - b);
      return { categories: v.length, median: v[Math.floor(v.length / 2)] ?? 0, max: v[v.length - 1] ?? 0, singletons: v.filter((x) => x === 1).length };
    };
    const typeSizes = sizes((r) => r.atu), placeSizes = sizes((r) => r.place);
    return { typeSizes, placeSizes, regionCounts, chapterCounts, points, kinds: kindOrder.map((k) => ({ label: k, value: kinds.get(k) ?? 0 })), europe, joint: joint.length, unlocatedJoint, geoUnknownAtu, topTypes };
  }, [cat.data]);

  return (
    <div>
      <div className="grid-2">
        <div className="prose">
          <p>The corpus is the <em>Annotated Folktales</em> dataset (Hagedorn &amp; Darányi 2022). It was scraped from D. L. Ashliman's long-running web library <em>Folktexts</em>. Each record is one published English text, usually a nineteenth- or early twentieth-century translation, placed on a page devoted to one tale type.</p>
          <p>Cleaning removed navigation, citations and editorial notes that had leaked into the texts. It also merged identical copies and set aside nine records that are not narratives. Each later step keeps only tales whose labels can be defended.</p>
        </div>
        <figure className="figure" style={{ margin: 0 }}>
          <div className="figure-title">From raw records to the comparison cohort</div>
          <Funnel steps={[
            { label: "Raw records", value: c.raw_records, note: "pinned aft.csv, commit d57c2ce" },
            { label: "Usable narratives", value: c.text_cohort, note: `${c.records_excluded_non_narrative} non-narrative records excluded; ${c.exact_duplicate_records_merged} identical copies merged` },
            { label: "With one ATU label", value: c.atu_cohort, note: `${c.atu_conflicts} identical texts carry conflicting labels` },
            { label: "Defensible geography", value: c.joint_cohort, note: `${int(c.geo_unknown_in_atu_cohort)} have only an author, collection or unclear place` },
            { label: "Documented coordinates", value: c.distance_cohort, note: "for the distance comparison" },
          ]} />
        </figure>
      </div>
      {!d ? <Loading what="the catalogue" /> : (
        <>
          <figure className="figure">
            <div className="figure-title">Where the joint cohort's tales were recorded</div>
            <div className="figure-sub">{int(d.points.reduce((s, p) => s + p.count, 0))} tales at {d.points.length} representative points; {d.unlocatedJoint} more are labelled by community or multi-country region without a documented point; {int(d.geoUnknownAtu)} usable tales have no defensible geography at all.</div>
            <CoverageMap land={land} points={d.points} height={430} />
            <figcaption className="caption">Circle area shows the number of tales. Points are Natural Earth label points of the recorded country, nation or territory: they mark an association recorded by a collector, not a place of origin. Communities keep their own labels (e.g. Zuni, Basque) and appear on the map only when the source establishes a country of recording.</figcaption>
          </figure>
          <div className="grid-3">
            <figure className="figure" style={{ margin: 0 }}>
              <div className="figure-title">Broad regions (UN M49), joint cohort</div>
              <div className="figure-sub">{pct(d.europe / d.joint, 0)} of tales are from Europe: no global claim is possible.</div>
              <BarList items={d.regionCounts} />
            </figure>
            <figure className="figure" style={{ margin: 0 }}>
              <div className="figure-title">ATU chapters, joint cohort</div>
              <div className="figure-sub">{summary.counts.joint_distinct_atu} distinct tale types; the largest have about 20 tales each.</div>
              <BarList items={d.chapterCounts} />
              <div className="small sans muted" style={{ marginTop: 8 }}>Largest types: {d.topTypes.slice(0, 4).map((t) => `${t.label.split(" ")[0]} (${t.value})`).join(", ")}.</div>
              <div className="small sans muted" style={{ marginTop: 4 }}>Category sizes: {d.typeSizes.categories} types (median {d.typeSizes.median} tales, max {d.typeSizes.max}, {d.typeSizes.singletons} with one tale); {d.placeSizes.categories} places (median {d.placeSizes.median}, max {d.placeSizes.max}, {d.placeSizes.singletons} with one tale). Different category counts are why every comparison uses its own shuffle reference.</div>
            </figure>
            <figure className="figure" style={{ margin: 0 }}>
              <div className="figure-title">What the provenance field records</div>
              <div className="figure-sub">Usable narratives by kind of recorded provenance (first record of each).</div>
              <BarList items={d.kinds} colour="#6b767c" />
              <div className="small sans muted" style={{ marginTop: 8 }}>“Author” and “collection” (e.g. Aesop, the Grimms alone, the 1001 Nights) are kept as text but never turned into a story-origin location.</div>
            </figure>
          </div>
          <div className="callout warn" style={{ marginTop: 18 }}>
            <strong>Collection and translation bias.</strong> One editor selected these texts, mostly from English-language publications by European and American collectors. Many non-European tales reach us through colonial-era translators, and a few translators supply dozens of tales (the Grimms, Joseph Jacobs, T. F. Crane, Andrew Lang). Some tales lost their opening paragraphs during scraping; {summary.counts.suspected_fragments_text_cohort} are flagged. Read every result as describing <em>this curated, English-language sample</em>.
          </div>
        </>
      )}
      <HowMade
        measured="Counts of records and narratives at each cleaning and cohort step; tales per mapped place, region and ATU chapter."
        records="All 1,518 raw records for the funnel; the joint cohort for the map and bars; usable narratives for the provenance breakdown."
        method="Descriptive document checks before modelling (week 5, §4). The provenance mapping table is in Data & Methods."
        infer="Exactly which records enter each analysis and why; how unevenly geography is covered."
        cannot="Anything about the world's folklore as a whole, or where any story began." />
    </div>
  );
}
