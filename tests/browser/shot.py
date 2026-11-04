"""Open a page in headless Edge, report console errors and save a screenshot.

Usage: python tests/browser/shot.py URL OUT.png [width height] [--full] [--wait ms] [--scroll selector]
"""
import sys
from playwright.sync_api import sync_playwright


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url, out = args[0], args[1]
    w = int(args[2]) if len(args) > 2 else 1440
    h = int(args[3]) if len(args) > 3 else 900
    full = "--full" in sys.argv
    wait = 2500
    scroll = None
    for i, a in enumerate(sys.argv):
        if a == "--wait":
            wait = int(sys.argv[i + 1])
        if a == "--scroll":
            scroll = sys.argv[i + 1]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_page(viewport={"width": w, "height": h})
        msgs = []
        page.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait)
        if scroll:
            page.locator(scroll).scroll_into_view_if_needed()
            page.wait_for_timeout(wait)
        page.screenshot(path=out, full_page=full)
        print("console:", msgs if msgs else "clean")
        b.close()


if __name__ == "__main__":
    main()
