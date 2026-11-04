"""Scroll through the Story page and screenshot each chapter element.

Usage: python tests/browser/chapters.py BASE_URL OUTDIR [width height]
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CHAPTERS = ["guess", "corpus", "places", "neighbours", "grouping", "density", "read", "distance", "challenge", "limits"]


def main():
    base, outdir = sys.argv[1], Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 900
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_page(viewport={"width": w, "height": h})
        msgs = []
        page.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
        page.goto(base + "#/", wait_until="networkidle")
        page.wait_for_timeout(1500)
        for ch in CHAPTERS:
            loc = page.locator(f"#{ch}")
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(2500)
            loc.screenshot(path=str(outdir / f"{ch}.png"))
            print(ch, "height", round(loc.bounding_box()["height"]))
        print("console:", msgs if msgs else "clean")
        b.close()


if __name__ == "__main__":
    main()
