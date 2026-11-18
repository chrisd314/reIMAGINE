"""Check every page of the built site: it renders, its images load, its links go somewhere, the console is clean.

Usage (with `npm run preview` serving web/dist on port 4173):
    python tests/browser/site_check.py [BASE_URL] [--shots DIR]

For each route, at desktop and phone width: console errors and warnings, uncaught page errors, failed requests
(HTTP >= 400), images that did not load, internal links (#/...) to routes the site does not have, and the main
heading. Exit code 1 if anything failed.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROUTES = ["/", "/parables", "/story", "/explore", "/data", "/validation", "/sources"]
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = (args[0] if args else "http://localhost:4173/").rstrip("/") + "/"
    shots = Path(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    problems = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for vp, (w, h) in VIEWPORTS.items():
            for route in ROUTES:
                page = browser.new_page(viewport={"width": w, "height": h})
                msgs, failed = [], []
                page.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
                page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
                page.goto(f"{base}#{route}", wait_until="networkidle")
                page.wait_for_timeout(2500)
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")   # folded content counts too
                # scroll through the page so lazy images and sections load
                height = page.evaluate("document.body.scrollHeight")
                for y in range(0, height, h):
                    page.evaluate(f"window.scrollTo(0, {y})")
                    page.wait_for_timeout(150)
                page.wait_for_timeout(800)
                broken = page.evaluate("[...document.images].filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.src)")
                links = page.evaluate("[...document.querySelectorAll('a[href^=\"#/\"]')].map(a => a.getAttribute('href'))")
                bad_links = sorted({l for l in links if l.split("?")[0][1:] not in ROUTES})
                heading = page.evaluate("(document.querySelector('h1') || {}).textContent || ''")
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                ok = not (msgs or failed or broken or bad_links or not heading.strip() or overflow)
                problems += not ok
                print(f"[{vp}] {route:12s} {'ok ' if ok else 'FAIL'} h1={heading.strip()[:60]!r} images={page.evaluate('document.images.length')} "
                      f"links={len(links)}" + (" (page wider than the screen)" if overflow else ""))
                for label, items in (("console", msgs), ("failed requests", failed), ("broken images", broken), ("unknown routes", bad_links)):
                    for it in items[:8]:
                        print(f"      {label}: {it}")
                if shots:
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(path=str(shots / f"{vp}{route.replace('/', '_') if route != '/' else '_home'}.png"), full_page=False)
                page.close()
        browser.close()
    print("all pages ok" if not problems else f"{problems} page check(s) failed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
