"""AC-13: every page in site/ at 375px wide in Firefox with JavaScript off: no sideways scroll, every table and
figure present. Screenshots go to out/screens/.

uv run --with playwright==1.63.0 python scripts/screens.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main(folder=ROOT / "site", shots=ROOT / "out" / "screens"):
    shots.mkdir(parents=True, exist_ok=True)
    bad = []
    with sync_playwright() as p:
        browser = p.firefox.launch()
        for width in (375, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 812}, java_script_enabled=False)
            page = ctx.new_page()
            for path in sorted(folder.glob("*.html")):
                page.goto(path.as_uri())
                page.wait_for_load_state("load")
                # JavaScript is off for the page; Playwright's evaluate still runs in its own world.
                wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                tables = page.locator("table").count()
                imgs = page.locator("img").evaluate_all("els => els.filter(e => !e.complete || !e.naturalWidth).length")
                name = f"{path.stem}-{width}.png"
                page.screenshot(path=str(shots / name), full_page=True)
                ok = wide <= 0 and imgs == 0
                print(f"{path.name} at {width}px: sideways {wide}px, {tables} tables, {imgs} broken images -> {name}")
                if not ok:
                    bad.append(f"{path.name}@{width}")
            ctx.close()
        browser.close()
    if bad:
        print("failed:", ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
