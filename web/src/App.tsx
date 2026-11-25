import { useEffect, useMemo, useState } from "react";
import type { Rep } from "./data";
import { RepContext } from "./components/rep";
import { useHashPath } from "./lib/router";
import { SectionBoundary } from "./components/SectionBoundary";
import { OverviewPage } from "./pages/overview/Overview";
import { FolktalesPage } from "./pages/folktales/Folktales";
import { ParablesPage } from "./pages/parables/Parables";
import { MethodsPage } from "./pages/Methods";
import { ExplorePage } from "./pages/explore/Explore";

const PAGES = [
  { path: "", label: "Overview", title: "reIMAGINE · where parables land in the world of folktales" },
  { path: "folktales", label: "Folktales", title: "The folktale network · reIMAGINE" },
  { path: "parables", label: "Parables", title: "Placing the parables · reIMAGINE" },
  { path: "explore", label: "Explore", title: "Explore the network · reIMAGINE" },
  { path: "methods", label: "Methods", title: "Methods and sources · reIMAGINE" },
];

/** An open storybook with a castle rising from it and a gilt star: the reIMAGINE mark. */
function Logo() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden>
      <path d="M10.5 13V7.4h1.6v1.5h1.6V6.3h1.3L16 4l1 2.3h1.3v2.6h1.6V7.4h1.6V13z" fill="#9b3a30" />
      <path d="M16 26c-3.4-2.4-7.4-2.9-12-2.2V12.1c4.6-.7 8.6-.2 12 2.2 3.4-2.4 7.4-2.9 12-2.2v11.7c-4.6-.7-8.6-.2-12 2.2z" fill="#fbf6ea" stroke="#1e2340" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 14.3V26" stroke="#1e2340" strokeWidth="1.2" />
      <path d="M25.5 2.8l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" fill="#a87b22" />
    </svg>
  );
}

function useScrollProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const on = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      setP(h > 0 ? Math.min(1, window.scrollY / h) : 0);
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return p;
}

export default function App() {
  const path = useHashPath();
  // #/page/section: the page to show, and a section of it to scroll to (an Overview section has no page part)
  const parts = path.split("/").filter(Boolean);
  const isPage = PAGES.some((p) => p.path && p.path === parts[0]);
  const page = isPage ? parts[0] : "";
  const section = isPage ? parts[1] : parts[0];
  const progress = useScrollProgress();
  const [rep, setRep] = useState<Rep>("tfidf");
  const repCtx = useMemo(() => ({ rep, setRep }), [rep]);

  useEffect(() => {
    document.title = PAGES.find((p) => p.path === page)?.title ?? PAGES[0].title;
    if (section) {
      // pages render after their data arrives, so wait for the section to exist
      let tries = 0;
      const go = () => {
        const el = document.getElementById(section);
        if (el) el.scrollIntoView({ block: "start" });
        else if (tries++ < 40) window.setTimeout(go, 50);
      };
      go();
    } else {
      window.scrollTo({ top: 0 });
    }
  }, [page, section]);

  const body = page === "folktales" ? <FolktalesPage /> : page === "parables" ? <ParablesPage /> : page === "explore" ? <ExplorePage />
    : page === "methods" ? <MethodsPage /> : <OverviewPage />;
  return (
    <RepContext.Provider value={repCtx}>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <header className="site-header">
        <a className="brand" href="#/" aria-label="reIMAGINE, overview"><Logo /><span><span className="re">re</span><span className="imagine">IMAGINE</span></span></a>
        <nav className="site-nav" aria-label="Main">
          {PAGES.map((p) => <a key={p.path} href={`#/${p.path}`} aria-current={page === p.path ? "page" : undefined}>{p.label}</a>)}
        </nav>
        <div className="progress" style={{ width: `${progress * 100}%` }} aria-hidden />
      </header>
      <main id="main" tabIndex={-1}>
        <SectionBoundary key={page} name={page || "overview"}>{body}</SectionBoundary>
      </main>
      <footer className="site-footer">
        <div className="inner">
          <div><strong>reIMAGINE</strong> · a DTU 02805 course project on where religious parables land in the world of folktales.</div>
          <div>Folktales: Annotated Folktales (Hagedorn &amp; Darányi 2022) from D. L. Ashliman's Folktexts, CC BY-NC-SA 4.0 · <a href="#/methods">Sources</a></div>
        </div>
      </footer>
    </RepContext.Provider>
  );
}
