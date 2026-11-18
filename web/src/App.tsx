import { useEffect, useMemo, useState } from "react";
import { MotionContext, motionEnabled, readMotionPref, writeMotionPref, type MotionPref } from "./lib/motion";
import { useRoute } from "./lib/router";
import { onRunMismatch, useData } from "./data/load";
import type { ManifestPayload } from "./data/types";
import { ToastHost } from "./components/ui";
import { SectionBoundary } from "./components/SectionBoundary";
import { Story } from "./pages/Story";
import { Explore } from "./pages/Explore";
import { DataMethods } from "./pages/DataMethods";
import { Validation } from "./pages/Validation";
import { Sources } from "./pages/Sources";
import { Parables } from "./pages/Parables";
import { Home } from "./pages/Home";

const NAV = [
  { path: "/", label: "Overview" },
  { path: "/parables", label: "Parables" },
  { path: "/story", label: "Folklore map" },
  { path: "/explore", label: "Explore" },
  { path: "/data", label: "Data & Methods" },
  { path: "/validation", label: "Validation" },
  { path: "/sources", label: "Sources" },
];
const TITLES: Record<string, string> = Object.fromEntries(NAV.map((n) => [n.path, n.label]));

/** An open storybook with a castle rising from it and a gilt star: the reIMAGINE mark. */
export function Logo() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden>
      <path d="M10.5 13V7.4h1.6v1.5h1.6V6.3h1.3L16 4l1 2.3h1.3v2.6h1.6V7.4h1.6V13z" fill="#9b3a30" />
      <path d="M16 26c-3.4-2.4-7.4-2.9-12-2.2V12.1c4.6-.7 8.6-.2 12 2.2 3.4-2.4 7.4-2.9 12-2.2v11.7c-4.6-.7-8.6-.2-12 2.2z" fill="#fbf6ea" stroke="#1e2340" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 14.3V26" stroke="#1e2340" strokeWidth="1.2" />
      <path d="M25.5 2.8l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" fill="#a87b22" />
    </svg>
  );
}

export default function App() {
  const [route, navigate] = useRoute();
  const [pref, setPrefState] = useState<MotionPref>(readMotionPref());
  const enabled = motionEnabled(pref);
  const manifest = useData<ManifestPayload>("manifest.json");
  const [mismatch, setMismatch] = useState<string | null>(null);
  useEffect(() => onRunMismatch(setMismatch), []);
  useEffect(() => { document.documentElement.dataset.motion = enabled ? "on" : "off"; }, [enabled]);
  const setPref = (p: MotionPref) => { setPrefState(p); writeMotionPref(p); };
  const motionCtx = useMemo(() => ({ enabled, pref, setPref }), [enabled, pref]);
  const path = route.path === "" ? "/" : route.path;
  useEffect(() => {
    document.title = path === "/" ? "reIMAGINE · where parables land in the world of folktales" : `${TITLES[path] ?? "Overview"} · reIMAGINE`;
    window.scrollTo({ top: 0 });
  }, [path]);

  let page;
  switch (path) {
    case "/parables": page = <Parables route={route} navigate={navigate} />; break;
    case "/story": page = <Story route={route} navigate={navigate} />; break;
    case "/explore": page = <Explore route={route} navigate={navigate} />; break;
    case "/data": page = <DataMethods route={route} navigate={navigate} />; break;
    case "/validation": page = <Validation />; break;
    case "/sources": page = <Sources />; break;
    default: page = <Home />;
  }

  return (
    <MotionContext.Provider value={motionCtx}>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <header className="site-header">
        <a className="brand" href="#/" aria-label="reIMAGINE, overview"><Logo /><span><span className="re">re</span><span className="imagine">IMAGINE</span></span></a>
        <nav className="site-nav" aria-label="Main">
          {NAV.map((n) => <a key={n.path} href={`#${n.path}`} aria-current={path === n.path ? "page" : undefined}>{n.label}</a>)}
        </nav>
        <div className="header-tools">
          <button className="btn small" aria-pressed={enabled} onClick={() => setPref(enabled ? "off" : "on")} title={pref === "system" ? "Following your system motion setting" : "Motion preference saved in this browser"}>
            <span aria-hidden>{enabled ? "◐" : "○"}</span><span className="lbl">Motion {enabled ? "on" : "off"}</span>
          </button>
        </div>
      </header>
      {mismatch && <div className="callout warn sans small" role="alert" style={{ margin: 0, borderRadius: 0 }}>Data mismatch: {mismatch} Rebuild the site with a single pipeline export.</div>}
      <main id="main" tabIndex={-1}><SectionBoundary key={path} name={`page ${path}`}>{page}</SectionBoundary></main>
      {path !== "/explore" && (
        <footer className="site-footer">
          <div className="inner">
            <div>
              <strong>reIMAGINE</strong> — a DTU 02805 course project on where religious parables land in the world of folktales. Folktale texts and labels: Annotated Folktales (Hagedorn &amp; Darányi 2022) from D. L. Ashliman's Folktexts, CC BY-NC-SA 4.0 per the repository LICENSE.md; parables from public-domain translations. Noncommercial, educational use with attribution. See <a href="#/sources">Sources</a>.
            </div>
            <div className="mono">run {manifest.data?.run_id ?? "…"} · schema {manifest.data?.schema_version ?? "…"} · {manifest.data?.public_build ? "public build, excerpts only" : "local preview"}</div>
          </div>
        </footer>
      )}
      <ToastHost />
    </MotionContext.Provider>
  );
}
