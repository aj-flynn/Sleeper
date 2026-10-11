#!/usr/bin/env python3
"""Open a rendered issue in headless Chromium and check it the way a reader's phone will see it.

    python3 newsletter/verify_html.py newsletter/issues/2026-week4/issue.html
    python3 newsletter/verify_html.py newsletter/issues/2026-week4/issue.html --screenshots newsletter/issues/2026-week4/screenshots

Checks, at 390px (phone) and 1280px (desktop) wide:
  no horizontal scroll, no network requests (only data: URLs and the file itself), every
  template font loaded from the embedded data, no console errors or page errors, no {{ left
  over, every "Find your team" link lands on a recap card, and the Elo chart is present
  (12 lines, weekly points, 12-name legend).
Prints one JSON object (the checks and their results) and exits 1 if any check failed.
Needs Playwright with Chromium: pip install -r newsletter/requirements.txt && python3 -m playwright install chromium
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import template_fonts  # noqa: E402

VIEWPORTS = {"phone": {"width": 390, "height": 844}, "desktop": {"width": 1280, "height": 900}}


def check_page(browser, url, name, viewport, shots=None):
    ctx = browser.new_context(viewport=viewport, device_scale_factor=1)
    page = ctx.new_page()
    requests, console = [], []

    def route(r):
        u = r.request.url
        if u.startswith("data:") or u == url:
            return r.continue_()
        requests.append(u)
        return r.abort()

    page.route("**/*", route)
    page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    page.goto(url, wait_until="load")
    families = template_fonts()
    fonts = page.evaluate(
        """async (families) => {
            const faces = [...document.fonts];
            await Promise.all(faces.map(f => f.load().catch(() => null)));
            await document.fonts.ready;
            return {
              faces: faces.map(f => ({family: f.family.replace(/["']/g, ''), weight: f.weight, style: f.style, status: f.status})),
              available: Object.fromEntries(families.map(n => [n, document.fonts.check(`16px "${n}"`)])),
            };
        }""",
        families,
    )
    layout = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            leftovers: ((document.body.outerHTML + document.title).match(/{{/g) || []).length,
            finder: [...document.querySelectorAll('#teams a')].map(a => ({
              text: a.querySelector('.nm')?.textContent, href: a.getAttribute('href'),
              lands: !!document.querySelector(a.getAttribute('href')),
            })),
            elo: {
              svg: !!document.querySelector('#elo-chart'),
              lines: document.querySelectorAll('#elo-chart path.elo-line').length,
              points: document.querySelectorAll('#elo-chart circle.elo-point').length,
              legend: document.querySelectorAll('.elo-legend li').length,
              colorMatch: (() => {
                const line = {};
                document.querySelectorAll('#elo-chart path.elo-line').forEach(p => {
                  line[p.dataset.team] = p.getAttribute('stroke');
                });
                const rows = [...document.querySelectorAll('.elo-legend li')].map(li => {
                  const team = li.dataset.team || li.querySelector('.nm')?.textContent;
                  const stroke = li.querySelector('.elo-key path')?.getAttribute('stroke');
                  return {team, stroke, ok: !!(team && stroke && line[team] === stroke)};
                });
                return {ok: rows.length === 12 && rows.every(r => r.ok), rows};
              })(),
            },
        })"""
    )
    results = []

    def gate(check, ok, detail):
        results.append({"check": f"{name}.{check}", "status": "pass" if ok else "fail", "detail": detail})

    gate("no_horizontal_scroll", layout["scrollWidth"] <= layout["clientWidth"],
         f"scrollWidth {layout['scrollWidth']} vs viewport {layout['clientWidth']}")
    gate("no_network_requests", not requests, requests or "only data: URLs")
    bad_faces = [f for f in fonts["faces"] if f["status"] != "loaded"]
    gate("fonts_loaded", fonts["faces"] and not bad_faces and all(fonts["available"].values()),
         {"faces": len(fonts["faces"]), "not_loaded": bad_faces, "families": fonts["available"]})
    gate("no_console_errors", not console, console or "none")
    gate("no_template_leftovers", layout["leftovers"] == 0, f"{layout['leftovers']} unrendered '{{{{' in the page")
    lost = [f for f in layout["finder"] if not f["lands"]]
    gate("find_your_team_links", len(layout["finder"]) == 12 and not lost,
         f"{len(layout['finder'])} links, {len(lost)} broken" + (f": {lost}" if lost else ""))
    elo = layout["elo"]
    gate("elo_chart", elo["svg"] and elo["lines"] == 12 and elo["legend"] == 12 and elo["points"] >= 24
         and elo.get("colorMatch", {}).get("ok"),
         f"svg={elo['svg']} lines={elo['lines']} points={elo['points']} legend={elo['legend']} "
         f"colors={elo.get('colorMatch', {}).get('ok')}")
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shots / f"{name}-first-screen.png"))
        page.screenshot(path=str(shots / f"{name}-full.png"), full_page=True)
        gate("screenshots", True, [f"{name}-first-screen.png", f"{name}-full.png"])
    ctx.close()
    return results


def verify(html_path, shots=None):
    from playwright.sync_api import sync_playwright

    url = Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            results = [r for name, vp in VIEWPORTS.items() for r in check_page(browser, url, name, vp, shots)]
        finally:
            browser.close()
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("--screenshots", type=Path, help="also save first-screen and full-page PNGs here")
    a = ap.parse_args()
    results = verify(a.html, a.screenshots)
    failed = [r for r in results if r["status"] != "pass"]
    print(json.dumps({"html": str(a.html), "result": "fail" if failed else "pass", "checks": results}, indent=1, ensure_ascii=False))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
