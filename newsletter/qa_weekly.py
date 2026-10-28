#!/usr/bin/env python3
"""Browser checks and screenshots for the weekly newspaper at four widths."""
import argparse
import json
from pathlib import Path
import sys
from verify_html import check_page


def verify(html, out, channel=None):
    from playwright.sync_api import sync_playwright
    url = Path(html).resolve().as_uri()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"channel":channel} if channel else {}))
        try:
            for width in (320,390,768,1440):
                checks = check_page(browser,url,str(width),{"width":width,"height":900},out)
                result = {"width":width,"checks":checks,"pass":all(c["status"]=="pass" for c in checks)}
                page = browser.new_page(viewport={"width":width,"height":900})
                page.goto(url)
                result["newspaper"] = page.evaluate("""() => {
                  const full = s => {const e=document.querySelector(s); return e && Math.abs(e.getBoundingClientRect().width-e.parentElement.getBoundingClientRect().width)<2};
                  const columns = s => {const e=document.querySelector(s); return e ? getComputedStyle(e).gridTemplateColumns.split(' ').length : 0};
                  return {awardsColumns:columns('.awards'), recapCards:document.querySelectorAll('.newspaper').length,
                    footer:!!document.querySelector('footer'), visibleManager:!!document.querySelector('.newspaper .manager'),
                    reportColumns:columns('.report-main'), playerColumns:columns('.player-groups'),
                    playerGroups:document.querySelectorAll('.newspaper .player-group').length,
                    benchProse:!!document.querySelector('.bench-note'),
                    fullTables:full('.waivers')&&full('.standouts'),
                    sections:['s-lead','s-rank','s-recaps','s-awards','s-moves','s-next'].every(id=>!!document.getElementById(id)),
                    malformed:/,\\s*,|DEF DEF|DEF \\(DEF\\)/.test(document.body.innerText)};
                }""")
                page.close()
                layout = result["newspaper"]
                result["weekly_pass"] = layout["sections"] and layout["recapCards"]==6 and layout["playerGroups"]==12 and layout["reportColumns"]==(2 if width>688 else 1) and layout["playerColumns"]==(2 if width>688 else 1) and not layout["benchProse"] and layout["fullTables"] and not layout["footer"] and not layout["malformed"] and layout["awardsColumns"] == (2 if width>=832 else 1)
                results.append(result)
        finally:
            browser.close()
    report = {"manual_screenshot_review":"required", "viewports":results,
              "pass":all(r.get("pass",False) and r["weekly_pass"] for r in results)}
    (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--browser-channel",help="Optional installed Chromium channel, e.g. msedge or chrome")
    args=parser.parse_args()
    try:
        report=verify(args.html,args.out,args.browser_channel)
    except Exception as exc:
        print(json.dumps({"pass":False,"blocker":str(exc)}))
        return 1
    print(json.dumps({"pass":report["pass"],"report":str(args.out/"report.json")}))
    return 0 if report["pass"] else 1


if __name__=="__main__":
    sys.exit(main())
