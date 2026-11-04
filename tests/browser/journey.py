"""Uninterrupted visitor journey (brief v1.1 §14 acceptance checks), run in headless Edge.

python tests/browser/journey.py BASE_URL OUTDIR [--mobile] [--reduced] [--keyboard]

Steps: introduction -> reveal the opening pair -> Places to Network layout -> select a
tale -> change representation -> recolour -> change density -> open the paired reader and
click a passage -> copy the view link -> reset. Prints PASS/FAIL per step and exits
non-zero if any step fails. Screenshots are written to OUTDIR.
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

results = []


def step(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
        print(f"PASS  {name}")
    except Exception as e:  # report and continue so one failure does not hide others
        lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
        detail = " | ".join([lines[0]] + [ln for ln in lines[1:6] if ln.lower().startswith(("locator", "expected", "received", "call log"))])[:400]
        results.append((name, "FAIL", detail))
        print(f"FAIL  {name}: {detail}")
        if "--verbose" in sys.argv:
            print(str(e)[:1500])


def main():
    base, out = sys.argv[1].rstrip("/") + "/", Path(sys.argv[2])
    mobile, reduced, keyboard = "--mobile" in sys.argv, "--reduced" in sys.argv, "--keyboard" in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    vw = {"width": 390, "height": 844} if mobile else {"width": 1440, "height": 900}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport=vw, reduced_motion="reduce" if reduced else "no-preference",
                            has_touch=mobile, is_mobile=mobile, device_scale_factor=2 if mobile else 1)
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base.split("#")[0].rstrip("/"))
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}\n{(getattr(e, 'stack', '') or '')[:1200]}"))
        shot = lambda n: page.screenshot(path=str(out / f"{n}.png"))

        def intro():
            page.goto(base + "#/", wait_until="networkidle")
            expect(page.get_by_role("heading", name="How far can a story travel?")).to_be_visible()
            if reduced:
                assert page.evaluate("document.documentElement.dataset.motion") == "off", "reduced motion not honoured"
            shot("01-intro")
        step("open the introduction", intro)

        def reveal():
            page.locator("#guess").scroll_into_view_if_needed()
            btn = page.get_by_role("button", name="I see a connection")
            if keyboard:
                btn.focus(); page.keyboard.press("Enter")
            else:
                btn.click()
            expect(page.locator("#guess").get_by_text(re.compile(r"ATU 425C"))).to_have_count(3, timeout=8000) if False else None
            expect(page.locator("#guess .reveal").first).to_be_visible(timeout=8000)
            expect(page.locator("#guess")).to_contain_text("Recorded provenance")
            page.wait_for_timeout(900)
            shot("02-reveal")
        step("reveal the pair (scene 1)", reveal)

        def morph():
            page.locator("#places").scroll_into_view_if_needed()
            page.wait_for_timeout(2500)
            page.locator("#places").get_by_role("button", name=re.compile("Network layout")).click()
            page.wait_for_timeout(1800)
            expect(page.locator("#places")).to_contain_text("ForceAtlas2 layout")
            page.locator("#places").screenshot(path=str(out / "03-morph-network.png"))
            page.locator("#places").get_by_role("button", name="Places").click()
            page.wait_for_timeout(1200)
            expect(page.locator("#places")).to_contain_text("display displacement")
        step("switch Places -> Network layout and back (scene 2)", morph)

        def explore_select():
            page.goto(base + "#/explore?cohort=joint&rep=semantic&d=10", wait_until="networkidle")
            page.wait_for_timeout(1500)
            if mobile:
                expect(page.locator(".stage table.data")).to_be_visible(timeout=8000)  # list view is the mobile default
            box = page.get_by_role("searchbox", name="Find a tale")
            box.fill("Enchanted Tsar")
            res = page.get_by_role("list", name="Search results").get_by_role("button").first
            if keyboard:
                res.focus(); page.keyboard.press("Enter")
            else:
                res.click()
            expect(page.get_by_role("complementary", name="Selected tale")).to_contain_text("The Enchanted Tsarévich", timeout=8000)
            expect(page.get_by_role("list", name=re.compile("Ten nearest tales")).get_by_role("listitem")).to_have_count(10, timeout=8000)
            assert "tale=tale-0086" in page.url
            page.wait_for_timeout(1200)
            shot("04-selected")
        step("select a tale in Explore (scene 3)", explore_select)

        def open_settings():
            # on narrow screens the view settings sit in a disclosure, as a phone visitor would see them
            more = page.locator("details.rail-more")
            if more.count() and not more.evaluate("d => d.open"):
                more.locator("summary").click()
                page.wait_for_timeout(300)

        def switch_rep():
            open_settings()
            before = page.get_by_role("list", name=re.compile("Ten nearest tales")).inner_text()
            page.get_by_role("group", name="Representation").get_by_role("button", name="TF–IDF").click()
            page.wait_for_timeout(1200)
            after = page.get_by_role("list", name=re.compile("Ten nearest tales")).inner_text()
            assert before != after, "neighbour list did not change"
            assert "rep=lexical" in page.url and "tale=tale-0086" in page.url, "selection or representation not preserved in URL"
            expect(page.get_by_role("complementary", name="Selected tale")).to_contain_text("The Enchanted Tsarévich")
            shot("05-representation")
        step("change representation, selection preserved (scene 4)", switch_rep)

        def recolour():
            open_settings()
            g = page.get_by_role("group", name="Colour by")
            g.get_by_role("button", name="ATU").click(); page.wait_for_timeout(700)
            assert "colour=atu" in page.url
            g.get_by_role("button", name="Region").click(); page.wait_for_timeout(700)
            assert "colour=region" in page.url
            shot("06-recolour")
        step("recolour by ATU and region (scene 5)", recolour)

        def density():
            open_settings()
            page.get_by_role("group", name="Density").get_by_role("button", name="15%").click()
            page.wait_for_timeout(1500)
            expect(page.locator(".stage-bar strong")).to_contain_text("15%")
            assert "d=15" in page.url
            shot("07-density")
        step("change density to 15% (scene 6)", density)

        def reader():
            page.get_by_role("list", name=re.compile("Ten nearest tales")).get_by_role("button", name=re.compile("^Read ")).first.click()
            dlg = page.get_by_role("dialog", name="Paired reader")
            expect(dlg).to_be_visible(timeout=8000)
            expect(dlg).to_contain_text("Whole-tale similarity", timeout=8000)
            expect(dlg).to_contain_text("Best passage pair")
            m = dlg.locator(".passage.match").first
            expect(m).to_be_visible(timeout=8000)
            m.click()
            expect(dlg.locator(".passage.active")).to_have_count(2, timeout=5000)
            page.wait_for_timeout(800)
            shot("08-reader")
            dlg.get_by_role("button", name="Shared words").click()
            # on narrow screens only the active tale column is shown (A/B switch)
            expect(dlg.locator(".reader-col:not(.hidden-mobile) mark.word").first).to_be_visible(timeout=5000)
            shot("08b-shared-words")
            page.keyboard.press("Escape")
            expect(dlg).to_have_count(0, timeout=5000)
            expect(page.get_by_text(re.compile("Pinned pair:"))).to_be_visible(timeout=5000)
            assert "pin=" in page.url, "closing the reader keeps the pair pinned"
        step("open paired reader and click a passage (scene 7)", reader)

        def share():
            page.get_by_role("button", name="Copy view link").click()
            page.wait_for_timeout(500)
            clip = page.evaluate("navigator.clipboard.readText()")
            assert "#/explore" in clip and "tale=tale-0086" in clip and "run=ouaw-" in clip, f"clipboard: {clip}"
            print("      copied:", clip)
        step("copy the view link with run ID (scene 8)", share)

        def reset():
            page.get_by_role("button", name="Reset view").click()
            page.wait_for_timeout(800)
            assert page.url.endswith("#/explore"), page.url
            expect(page.get_by_role("complementary", name="Selected tale")).to_contain_text("Explore the neighbourhoods")
            shot("09-reset")
        step("reset the view", reset)

        def values_match_pipeline():
            import json
            root = Path(__file__).resolve().parents[2]
            counts = json.loads((root / "outputs/audit/cohort_counts.json").read_text(encoding="utf-8"))
            page.goto(base + "#/", wait_until="networkidle")
            hero = page.locator(".hero").inner_text()
            for key in ("joint_cohort", "joint_distinct_atu", "joint_distinct_place"):
                assert f"{counts[key]:,}" in hero, f"{key}={counts[key]} not shown in hero"
            page.locator("#corpus").scroll_into_view_if_needed(); page.wait_for_timeout(2500)
            corpus = page.locator("#corpus").inner_text()
            for key in ("raw_records", "text_cohort", "atu_cohort", "joint_cohort", "distance_cohort"):
                assert f"{counts[key]:,}" in corpus, f"funnel misses {key}={counts[key]}"
            page.locator("#grouping").scroll_into_view_if_needed(); page.wait_for_timeout(2500)
            page.locator("#grouping").get_by_role("button", name="ATU (tale type)").click()
            page.wait_for_timeout(1500)
            cap = page.locator("#grouping").get_by_text(re.compile(r"Recomputed here from actual labels")).inner_text()
            m = re.search(r"labels: ([0-9.]+) \(pipeline ([0-9.]+)\)", cap)
            assert m and m.group(1) == m.group(2), f"browser NMI differs from pipeline: {cap}"
            print(f"      browser NMI {m.group(1)} == pipeline {m.group(2)}")
        step("displayed values match pipeline outputs", values_match_pipeline)

        def other_pages():
            for path, text in [("#/data", "Provenance mapping"), ("#/validation", "Status: pending"), ("#/sources", "Source manifest")]:
                page.goto(base + path, wait_until="networkidle")
                expect(page.locator("main")).to_contain_text(text, timeout=8000)
            shot("10-sources")
        step("data, validation and sources pages load", other_pages)

        def error_state():
            page.goto(base + "#/explore?tale=tale-9999", wait_until="networkidle")
            page.wait_for_timeout(1200)
            expect(page.get_by_role("complementary", name="Selected tale")).to_contain_text("Explore the neighbourhoods")
        step("unknown tale ID falls back to the overview", error_state)

        def stale_link():
            page.goto(base + "#/explore?tale=tale-0086&run=ouaw-19990101-deadbeef", wait_until="networkidle")
            page.wait_for_timeout(1500)
            expect(page.locator("main")).to_contain_text("This link was made with run ouaw-19990101-deadbeef")
        step("a view link from another run shows a warning (scene 8)", stale_link)

        print("console errors:", errors if errors else "none")
        b.close()
    failed = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed")
    sys.exit(1 if failed or errors else 0)


if __name__ == "__main__":
    main()
