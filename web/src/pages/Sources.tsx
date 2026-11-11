import { useData } from "../data/load";
import type { SourcesPayload, SummaryPayload } from "../data/types";
import { ErrorState, Loading } from "../components/ui";

export function Sources() {
  const s = useData<SourcesPayload>("sources.json");
  const summary = useData<SummaryPayload>("summary.json");
  if (s.error) return <div className="page"><ErrorState message={s.error} /></div>;
  if (!s.data) return <div className="page"><Loading /></div>;
  const m = s.data.manifest;
  return (
    <div className="page">
      <h1 style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}>Sources</h1>
      <div className="prose-wide">
        <h2>Please cite</h2>
        <ul>
          <li>Hagedorn, J. &amp; Darányi, S. (2022). Bearing a Bag-of-Tales: An Open Corpus of Annotated Folktales for Reproducible Research. <em>Journal of Open Humanities Data</em> 8: 16. <a href="https://doi.org/10.5334/johd.78">doi:10.5334/johd.78</a></li>
          <li>Repository: <a href={m.trilogy_repository}>j-hagedorn/trilogy</a>, pinned commit <span className="mono">{m.trilogy_commit}</span> (2024-05-27). Archived release v1.1: <a href="https://zenodo.org/records/6575263">Zenodo 6575263</a>; the pinned commit is later than v1.1.</li>
          <li>Ashliman, D. L. (1996–). <em>Folktexts: A library of folktales, folklore, fairy tales, and mythology.</em> University of Pittsburgh. <a href="https://sites.pitt.edu/~dash/folktexts.html">sites.pitt.edu/~dash/folktexts.html</a></li>
          <li>Uther, H.-J. (2004). <em>The Types of International Folktales</em> (FF Communications 284–286). ATU numbers and chapter ranges.</li>
          <li>Model: <a href={s.data.model.url}>{s.data.model.name}</a>, revision <span className="mono">{s.data.model.revision}</span> ({s.data.model.licence}).</li>
          <li>Maps: Natural Earth (public domain), via world-atlas (ISC) and Natural Earth v5.1.2 label points.</li>
          <li>Course: DTU 02805 Social Graphs and Interactions, <a href="https://sunelehmann.com/socialgraphs2026-web/index.html">course site</a> (content CC BY-SA 4.0).</li>
        </ul>
        <h2>Licences and publication questions</h2>
        <div className="callout warn">
          <p><strong>Discrepancy.</strong> The repository README says CC BY-SA 4.0, but its LICENSE.md contains CC BY-NC-SA 4.0. We follow the more restrictive terms: noncommercial, educational use with attribution, and share-alike for adapted data. Zenodo records the archived release as “other-open”.</p>
          <p>The texts come from Ashliman's site (© D. L. Ashliman, 1996–2026), including his own translations. Some tales from the Irish Schools' Collection (dúchas.ie) are separately CC BY-NC 4.0. {summary.data && !summary.data.full_texts_included
            ? <>This public build therefore does not republish the tales: it shows only the first {summary.data.excerpt_words ?? 120} words of each one with its source citation, plus the two passages quoted in the opening scene. Full texts are shown only in the local preview used for study and annotation (see LICENSE_NOTES.md).</>
            : <>This local preview shows full texts for study. Before any public deployment, set <span className="mono">include_full_texts: false</span> or obtain permission (see LICENSE_NOTES.md).</>} The software code is licensed separately from the data.</p>
        </div>
        <h2>Source manifest</h2>
      </div>
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>File</th><th>Role</th><th>Version</th><th>Retrieved</th><th className="num">Bytes</th><th>SHA-256</th><th>Stated licence</th></tr></thead>
          <tbody>
            {m.files.map((f) => (
              <tr key={f.filename}>
                <td><a href={f.url}>{f.filename}</a></td><td className="small">{f.role}</td><td className="small mono">{f.version.slice(0, 12)}</td>
                <td className="small">{f.retrieved_at}</td><td className="num">{f.bytes.toLocaleString()}</td>
                <td className="mono small" title={f.sha256}>{f.sha256.slice(0, 12)}…</td><td className="small">{f.stated_licence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
