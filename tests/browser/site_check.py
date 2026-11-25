"""Check the built site: every page renders, links go somewhere, the console is clean, and every interaction works.

Usage (with `npm run preview` serving web/dist on port 4173):
    python tests/browser/site_check.py [BASE_URL] [--shots DIR]

For each page, at desktop and phone width: console errors and warnings, uncaught page errors, failed requests
(HTTP >= 400), internal links (#/...) to pages or sections the site does not have, the main heading, and a page
wider than the screen. Then it uses the controls of each page once: switches, maps, shuffles, games, reading panels,
and checks that opened tales link to their source. With --shots, one screenshot per section. Exit code 1 if anything failed.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SECTIONS = {
    "/": ["how", "headline", "holds", "answer"],
    "/folktales": ["corpus", "similarity", "network", "communities", "organise", "choices", "central"],
    "/parables": ["texts", "test", "place", "land", "words", "break"],
    "/explore": [],
    "/methods": [],
}
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}


def valid_links() -> set[str]:
    out = set()
    for page, secs in SECTIONS.items():
        out.add(page)
        out |= {f"{page.rstrip('/')}/{s}" for s in secs}
    return out


def click_map(page, scope: str) -> None:
    canvas = page.locator(f"{scope} canvas").first
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def expect(page, selector: str, what: str, errors: list[str], timeout: int = 4000) -> None:
    try:
        page.locator(selector).first.wait_for(timeout=timeout)
    except Exception:  # noqa: BLE001
        errors.append(f"{what}: {selector} did not appear")


def interact(page, route: str) -> list[str]:
    """Use the controls of a page once; return what did not work."""
    errors: list[str] = []
    try:
        if route == "/":
            page.locator("#headline .segmented button", has_text="Embeddings").click()
            expect(page, "#headline a.panel-link", "main figure panels", errors)
            page.locator("#headline .segmented button", has_text="TF–IDF").click()
        if route == "/folktales":
            page.locator("#corpus ul.barlist button").nth(3).click()
            page.locator("#similarity button", has_text="Random tale").click()
            expect(page, "#similarity ol.nearlist li", "similarity: neighbour lists", errors, 8000)
            page.locator("#similarity ol.nearlist button", has_text="Read pair").first.click()
            expect(page, "#similarity .pair .read-links a[href^='https://']", "similarity: pair with source links", errors)
            page.locator("#network").get_by_role("button", name="5% of pairs", exact=True).click()
            page.locator("#communities .segmented button", has_text="Seed 7").click()
            click_map(page, "#communities")
            expect(page, "#communities .tale-panel", "communities: clicking the map opens a tale", errors)
            expect(page, "#communities .tale-panel .read-links a[href*='pitt.edu']", "communities: tale links to Folktexts", errors)
            page.locator("#communities .tale-panel button", has_text="Read pair").first.click()
            expect(page, "#communities .pair", "communities: read a pair", errors)
            page.locator("#organise button", has_text="Shuffle 100 times").click()
            if "100 shuffles" not in page.locator("#organise .shufflelab").inner_text():
                errors.append("organise: shuffles did not run")
            page.locator("#choices svg g[role=button]").nth(4).click()
            page.locator("#central table.data tbody tr").nth(2).click()
            page.locator("#central .segmented button", has_text="Embeddings").click()
            page.locator("#central .segmented button", has_text="TF–IDF").click()
        if route == "/parables":
            page.locator("#texts .text-row").nth(5).click()
            expect(page, "#texts .tale-panel", "texts: open a text", errors)
            page.locator("#test .option").first.click()
            if not page.locator("#test .option.right").count():
                errors.append("game: the right answer was not revealed")
            page.locator("#test ol.nearlist button", has_text="Read pair").first.click()
            expect(page, "#test .pair", "game: read the retelling beside a folktale", errors)
            page.locator("#test button", has_text="Next story").click()
            page.locator("#place .segmented button", has_text="Sufi").first.click()
            page.locator("#place svg circle").nth(3).click(force=True)
            page.locator("#place button", has_text="Shuffle 100 times").click()
            if "100 shuffles" not in page.locator("#place .shufflelab").inner_text():
                errors.append("place: permutation shuffles did not run")
            page.locator("#land .segmented button", has_text="Christian").last.click()
            page.locator("#land svg g[role=button]").nth(2).click()
            expect(page, "#land .card .linklike", "land: community lists its texts", errors)
            page.locator("#words .word-btn").first.click()
            page.locator("#break button", has_text="All checks").click()
            if "Still standing" not in page.locator("#break .survivors").inner_text():
                errors.append("checks: no survivors line")
            page.locator("#break .cell-btn").nth(1).click()
            expect(page, "#break .card table.data", "checks: cell opens its numbers", errors)
        if route == "/explore":
            page.locator(".explore .search input").fill("cinder")
            page.locator(".search-list button").first.click()
            expect(page, ".explore-panel .tale-panel", "explore: search opens a tale", errors)
            page.locator(".explore select").first.select_option("Buddhist")
            page.locator(".explore .segmented button", has_text="Embeddings").click()
            page.locator(".explore .segmented button", has_text="PageRank").click()
    except Exception as e:  # noqa: BLE001  (report, do not crash the check)
        errors.append(f"interaction failed: {str(e).splitlines()[0]}")
    return errors


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = (args[0] if args else "http://localhost:4173/").rstrip("/") + "/"
    shots = Path(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    valid = valid_links()
    problems = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for vp, (w, h) in VIEWPORTS.items():
            for route, secs in SECTIONS.items():
                page = browser.new_page(viewport={"width": w, "height": h})
                msgs, failed = [], []
                page.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
                page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
                page.goto(f"{base}#{route}", wait_until="networkidle")
                page.wait_for_timeout(1500)
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")   # folded content counts too
                links = page.evaluate("[...document.querySelectorAll('a[href^=\"#/\"]')].map(a => a.getAttribute('href'))")
                bad_links = sorted({l for l in links if (l.split("?")[0][1:].rstrip("/") or "/") not in valid})
                missing = [s for s in secs if not page.locator(f"#{s}").count()]
                heading = page.evaluate("(document.querySelector('h1') || {}).textContent || ''")
                broken = interact(page, route)
                page.wait_for_timeout(400)
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                ok = not (msgs or failed or bad_links or broken or missing or not heading.strip() or overflow)
                problems += not ok
                print(f"[{vp}] {route:11s} {'ok ' if ok else 'FAIL'} h1={heading.strip()[:50]!r} links={len(links)} sections={len(secs) - len(missing)}/{len(secs)}"
                      + (" (page wider than the screen)" if overflow else ""))
                for label, items in (("console", msgs), ("failed requests", failed), ("unknown links", bad_links),
                                     ("missing sections", missing), ("interaction", broken)):
                    for it in items[:8]:
                        print(f"      {label}: {it}")
                if shots:
                    name = route.strip("/") or "overview"
                    page.add_style_tag(content=".site-header{position:static!important}")
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(path=str(shots / f"{vp}_{name}_top.png"))
                    for s in secs:
                        page.locator(f"#{s}").screenshot(path=str(shots / f"{vp}_{name}_{s}.png"))
                page.close()
        browser.close()
    print("all pages ok" if not problems else f"{problems} page check(s) failed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
