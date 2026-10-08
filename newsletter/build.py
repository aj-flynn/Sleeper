#!/usr/bin/env python3
"""Render a Rebuilders Anonymous newsletter issue into one self-contained HTML file.

    python3 newsletter/build.py --template docket --data newsletter/issues/2026-week5/issue.json --out 2026-week5.html
    python3 newsletter/build.py --samples      # rebuild newsletter/prototypes/*.html from the Week 4 issue
    python3 newsletter/build.py --archive      # rebuild the three archived Week 2 designs
    python3 newsletter/build.py --lint newsletter/issues/2026-week5/issue.json
    python3 newsletter/build.py --check-facts newsletter/issues/2026-week5/issue.json

Templates live in newsletter/prototypes/src/. They use a small Mustache subset:
  {{key}} / {{a.b}}      insert a value (raw HTML, so copy may use <em>, &amp;)
  {{#key}}...{{/key}}    repeat for each list item, or render once if truthy
  {{^key}}...{{/key}}    render only if the value is missing-but-declared, empty, or false
  {{.}}                  the current scalar item; {{@index}} is the 1-based loop index
Every key a template references must exist in the data (null/[]/false are fine), so a
missing field fails the build instead of shipping a blank.

Every issue must weave real NFL box-score lines into the fantasy numbers. validate()
enforces that (schema 2) before anything renders; see the newsletter skill for the rules.

A template's fonts are declared in a comment such as
  <!-- fonts: courier-prime-400-normal kalam-700-normal -->
and inlined as base64 @font-face rules wherever the template says /*@font-faces*/.
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOTYPES = ROOT / "prototypes"
SRC = PROTOTYPES / "src"
ARCHIVE = PROTOTYPES / "archive"
FONTS = ROOT / "fonts"
SKILL = ROOT.parent / ".cursor" / "skills" / "newsletter" / "SKILL.md"

SAMPLE_DATA = ROOT / "issues" / "2026-week4" / "issue.json"
SAMPLE_TEMPLATES = ["minutes", "blueprint", "docket", "card-back", "downfield"]
ARCHIVE_DATA = ARCHIVE / "sample-issue-week2.json"
ARCHIVE_TEMPLATES = ["broadsheet", "ledger", "night-edition"]

FAMILY_NAMES = {
    "newsreader": "Newsreader",
    "libre-franklin": "Libre Franklin",
    "ibm-plex-sans": "IBM Plex Sans",
    "ibm-plex-mono": "IBM Plex Mono",
    "big-shoulders-display": "Big Shoulders Display",
    "source-serif-4": "Source Serif 4",
    "courier-prime": "Courier Prime",
    "kalam": "Kalam",
    "architects-daughter": "Architects Daughter",
    "barlow": "Barlow",
    "barlow-condensed": "Barlow Condensed",
    "libre-caslon-text": "Libre Caslon Text",
    "alfa-slab-one": "Alfa Slab One",
    "archivo-narrow": "Archivo Narrow",
    "saira-stencil-one": "Saira Stencil One",
    "atkinson-hyperlegible": "Atkinson Hyperlegible",
}

TAG = re.compile(r"{{\s*([#^/]?)\s*([\w.@]+)\s*}}")
MISSING = object()

# A recap or lead that never mentions one of these, next to a number, is fantasy points
# without the football that produced them.
BOX_SCORE_WORDS = (
    r"yards?|yds|carries|car|catch(?:es)?|rec(?:eptions?)?|targets?|tgt|touchdowns?|TDs?|"
    r"interceptions?|INTs?|snaps?|sacks?|field goals?|fumbles?|passes|attempts?|completions?|of \d+"
)
BOX_SCORE = re.compile(rf"\b\d[\d,.]*\s+(?:\w+\s+){{0,3}}?(?:{BOX_SCORE_WORDS})\b", re.I)


def parse(template):
    root = []
    stack = [("", root)]
    pos = 0
    for m in TAG.finditer(template):
        stack[-1][1].append(("text", template[pos:m.start()]))
        kind, name = m.group(1), m.group(2)
        if kind in "#^" and kind:
            node = ("section", name, kind == "^", [])
            stack[-1][1].append(node)
            stack.append((name, node[3]))
        elif kind == "/":
            if stack[-1][0] != name:
                raise SyntaxError(f"closing {{{{/{name}}}}} does not match {{{{#{stack[-1][0]}}}}}")
            stack.pop()
        else:
            stack[-1][1].append(("var", name))
        pos = m.end()
    if len(stack) != 1:
        raise SyntaxError(f"unclosed section {{{{#{stack[-1][0]}}}}}")
    root.append(("text", template[pos:]))
    return root


def lookup(name, stack):
    if name == ".":
        return stack[-1]
    head, *rest = name.split(".")
    for frame in reversed(stack):
        if isinstance(frame, dict) and head in frame:
            value = frame[head]
            for part in rest:
                if not isinstance(value, dict) or part not in value:
                    return MISSING
                value = value[part]
            return value
    return MISSING


def render_nodes(nodes, stack, path="root"):
    out = []
    for node in nodes:
        if node[0] == "text":
            out.append(node[1])
        elif node[0] == "var":
            value = lookup(node[1], stack)
            if value is MISSING:
                raise KeyError(f"missing key '{node[1]}' (inside {path})")
            out.append("" if value is None else str(value))
        else:
            _, name, inverted, children = node
            value = lookup(name, stack)
            if value is MISSING:
                raise KeyError(f"missing key '{name}' (inside {path})")
            if inverted:
                if not value:
                    out.append(render_nodes(children, stack, f"{path} > ^{name}"))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    meta = {"@index": i + 1, "@first": i == 0, "@last": i == len(value) - 1}
                    out.append(render_nodes(children, stack + [meta, item], f"{path} > {name}[{i}]"))
            elif value:
                frame = [value] if isinstance(value, dict) else []
                out.append(render_nodes(children, stack + frame, f"{path} > {name}"))
    return "".join(out)


def font_faces(template):
    m = re.search(r"<!--\s*fonts:([^>]*)-->", template)
    if not m:
        return ""
    rules = []
    for face in m.group(1).split():
        family, weight, style = face.rsplit("-", 2)
        data = base64.b64encode((FONTS / f"{face}.woff2").read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{FAMILY_NAMES[family]}';font-style:{style};"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
    return "\n".join(rules)


def render(template_name, data, src=SRC):
    template = (src / f"{template_name}.html").read_text(encoding="utf-8")
    html = render_nodes(parse(template), [data])
    html = re.sub(r"\s*<!--\s*fonts:[^>]*-->", "", html, count=1)
    return html.replace("/*@font-faces*/", font_faces(template))


def num(value):
    return float(str(value).replace("$", "").replace(",", ""))


def derive(data):
    """Add layout-only numbers (bar lengths, field positions) computed from the issue's own data."""
    data = json.loads(json.dumps(data))
    recaps = data.get("recaps", [])
    if recaps:
        top = max(num(r["w_score"]) for r in recaps)
        for r in recaps:
            r["w_pct"] = round(num(r["w_score"]) / top * 100, 2)
            r["l_pct"] = round(num(r["l_score"]) / top * 100, 2)
            r["margin_pct"] = round(r["w_pct"] - r["l_pct"], 2)
    rankings = data.get("rankings", [])
    if rankings and all("pf" in r for r in rankings):
        pfs = [num(r["pf"]) for r in rankings]
        lo, hi = min(pfs), max(pfs)
        for r in rankings:
            # 0 is the team with the fewest points for, 100 the most.
            r["pf_pct"] = round((num(r["pf"]) - lo) / ((hi - lo) or 1) * 100, 2)
            r["pf_rank"] = sorted(pfs, reverse=True).index(num(r["pf"])) + 1
    return data


def validate(data):
    """Schema 2: fantasy numbers must travel with the real NFL lines behind them."""
    problems = []

    def need(cond, msg):
        if not cond:
            problems.append(msg)

    need(data.get("schema") == 2, "schema must be 2 (fantasy points plus NFL box-score lines)")
    need(bool((data.get("meta") or {}).get("data_note")), "meta.data_note must say where the numbers come from")
    lead = " ".join((data.get("lead") or {}).get("body", []))
    need(BOX_SCORE.search(lead), "lead.body never cites a box-score stat (yards, catches, carries, TDs, snaps...)")

    recaps = data.get("recaps", [])
    need(len(recaps) == 6, f"recaps: expected 6 matchups, found {len(recaps)}")
    for i, r in enumerate(recaps, 1):
        where = f"recaps[{i}] {r.get('winner', '?')} v. {r.get('loser', '?')}"
        need(BOX_SCORE.search(r.get("body", "")), f"{where}: body explains the score with fantasy points only; cite the real stat line")
        for side in ("w_keys", "l_keys"):
            keys = r.get(side) or []
            need(len(keys) >= 2, f"{where}: {side} needs two key performers")
            for k in keys:
                need(bool(k.get("line")), f"{where}: {side} {k.get('player', '?')} has no NFL stat line")
                need(bool(k.get("nfl_team")), f"{where}: {side} {k.get('player', '?')} has no NFL team")

    for s in data.get("standouts", []):
        need(bool(s.get("line")), f"standouts: {s.get('player', '?')} has no NFL stat line")

    nfl = data.get("nfl") or {}
    need(bool(nfl.get("games")), "nfl.games must list the week's NFL results")
    for g in nfl.get("games", []):
        need(bool(g.get("final")) and bool(g.get("note")), f"nfl.games: {g.get('final', '?')} needs a final and a note")
    need("injuries" in nfl, "nfl.injuries must exist (use [] if no rostered player was hurt)")

    preview = data.get("preview") or {}
    need(len(preview.get("games", [])) == 6, "preview.games: expected the six next-week matchups")
    return problems


def banned_phrases():
    """Banned phrases are maintained in the newsletter skill, between banned:start/end markers."""
    if not SKILL.exists():
        return []
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(r"<!-- banned:start -->(.*?)<!-- banned:end -->", text, re.S)
    return re.findall(r"^- `([^`]+)`", m.group(1), re.M) if m else []


def strings(value, skip=("url",)):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in skip:
                yield from strings(v, skip)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v, skip)


def lint(data):
    copy = "\n".join(strings(data))
    plain = re.sub(r"<[^>]+>", "", copy)
    problems = []
    for phrase in banned_phrases():
        hits = len(re.findall(r"\b" + re.escape(phrase) + r"\b", plain, re.I))
        if hits:
            problems.append(f"banned phrase x{hits}: {phrase!r}")
    dashes = plain.count("\u2014")
    if dashes > 3:
        problems.append(f"{dashes} em dashes in the issue (limit 3)")
    exclaims = len(re.findall(r"!(?!\w)", plain.replace("WELL!", "")))
    if exclaims:
        problems.append(f"{exclaims} exclamation marks (limit 0 outside team names)")
    if data.get("schema") == 2:
        problems += validate(data)
    return problems


NUMBER = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?")


def check_facts(issue_path, brief_path=None):
    """List every number in the copy that doesn't appear verbatim in the data brief.

    Derived numbers (margins, sums, swaps) will show up here too. That's the point:
    each one listed is a number to recompute by hand before shipping.
    """
    data = json.loads(issue_path.read_text(encoding="utf-8"))
    brief_path = brief_path or issue_path.with_name("brief.md")
    brief = brief_path.read_text(encoding="utf-8")
    known = set()
    for tok in NUMBER.findall(brief):
        t = tok.lstrip("$").replace(",", "")
        known.add(t)
        if "." in t:
            known.add(t.rstrip("0").rstrip("."))
    ignore = {str(i) for i in range(0, 11)} | {"2026", "2027"}
    unknown = {}
    for s in strings(data, skip=("url", "rank", "issue_number", "week", "schema")):
        for tok in NUMBER.findall(re.sub(r"<[^>]+>", "", s)):
            t = tok.lstrip("$").replace(",", "")
            if t in ignore or t in known or t.rstrip("0").rstrip(".") in known:
                continue
            unknown.setdefault(t, s.strip()[:90])
    return unknown


def write(out, html):
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", choices=sorted(p.stem for p in SRC.glob("*.html") if p.stem != "index"))
    ap.add_argument("--data", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--samples", action="store_true", help="rebuild the prototypes and their index from the sample issue")
    ap.add_argument("--archive", action="store_true", help="rebuild the archived Week 2 designs")
    ap.add_argument("--lint", type=Path, metavar="ISSUE_JSON", help="check copy against the skill's rules and schema 2")
    ap.add_argument("--check-facts", type=Path, metavar="ISSUE_JSON", help="list numbers not found in the brief")
    ap.add_argument("--brief", type=Path, help="brief.md to check against (default: next to the issue)")
    args = ap.parse_args()

    if args.lint:
        problems = lint(json.loads(args.lint.read_text(encoding="utf-8")))
        for p in problems:
            print(f"lint: {p}")
        sys.exit(1 if problems else 0)

    if args.check_facts:
        unknown = check_facts(args.check_facts, args.brief)
        for tok, ctx in sorted(unknown.items(), key=lambda kv: kv[0]):
            print(f"not in brief: {tok:>8}  {ctx}")
        print(f"{len(unknown)} numbers to verify by hand (derived or outside the brief)")
        return

    if args.archive:
        data = json.loads(ARCHIVE_DATA.read_text(encoding="utf-8"))
        for name in ARCHIVE_TEMPLATES:
            write(ARCHIVE / f"{name}.html", render(name, data, ARCHIVE / "src"))
        return

    if args.samples:
        data = json.loads(SAMPLE_DATA.read_text(encoding="utf-8"))
        problems = lint(data)
        for p in problems:
            print(f"lint: {p}")
        if problems:
            sys.exit(1)
        for name in SAMPLE_TEMPLATES:
            write(PROTOTYPES / f"{name}.html", render(name, derive(data)))
        write(PROTOTYPES / "index.html", render("index", {}))
        return

    if not (args.template and args.data and args.out):
        ap.error("--template, --data, and --out are required (or use --samples / --archive / --lint / --check-facts)")
    data = json.loads(args.data.read_text(encoding="utf-8"))
    for p in lint(data):
        print(f"lint: {p}")
    if validate(data):
        sys.exit("build stopped: the issue does not meet schema 2 (see lint output)")
    write(args.out, render(args.template, derive(data)))


if __name__ == "__main__":
    main()
