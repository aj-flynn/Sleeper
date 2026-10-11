#!/usr/bin/env python3
"""Render a Rebuilders Anonymous newsletter issue into one self-contained HTML file.

    python3 newsletter/build.py --data newsletter/issues/2026-week5/issue.json --out 2026-week5.html
    python3 newsletter/build.py --data newsletter/issues/2026-week4/issue.json   # writes issue.html next to it
    python3 newsletter/build.py --lint newsletter/issues/2026-week5/issue.json
    python3 newsletter/build.py --check-facts newsletter/issues/2026-week5/issue.json

The template is newsletter/templates/card-back.html. It uses a small Mustache subset:
  {{key}} / {{a.b}}      insert a value (raw HTML, so copy may use <em>, &amp;)
  {{#key}}...{{/key}}    repeat for each list item, or render once if truthy
  {{^key}}...{{/key}}    render only if the value is missing-but-declared, empty, or false
  {{.}}                  the current scalar item; {{@index}} is the 1-based loop index
Every key a template references must exist in the data (null/[]/false are fine), so a
missing field fails the build instead of shipping a blank.

Every issue must weave real NFL box-score lines into the fantasy numbers, and order the
power rankings by Elo. validate() enforces that (schema 3) before anything renders, and
check_elo() matches the Elo figures against the brief; see the newsletter skill.

A template's fonts are declared in a comment such as
  <!-- fonts: alfa-slab-one-400-normal archivo-narrow-700-normal -->
and inlined as base64 @font-face rules wherever the template says /*@font-faces*/.
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
TEMPLATE = "card-back"
FONTS = ROOT / "fonts"
SKILL = ROOT.parent / ".cursor" / "skills" / "newsletter" / "SKILL.md"

FAMILY_NAMES = {
    "alfa-slab-one": "Alfa Slab One",
    "archivo-narrow": "Archivo Narrow",
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


def render(data, template=TEMPLATE):
    source = (TEMPLATES / f"{template}.html").read_text(encoding="utf-8")
    html = render_nodes(parse(source), [data])
    html = re.sub(r"\s*<!--\s*fonts:[^>]*-->", "", html, count=1)
    return html.replace("/*@font-faces*/", font_faces(source))


def num(value):
    return float(str(value).replace("$", "").replace(",", ""))


def derive(data):
    """Add layout-only fields computed from the issue's own data."""
    data = json.loads(json.dumps(data))
    # The jump list: every team, alphabetically, pointing at its own recap card.
    teams = []
    for i, r in enumerate(data.get("recaps", []), 1):
        teams.append({"team": r["winner"], "manager": r["w_manager"], "score": r["w_score"], "won": True, "game": i})
        teams.append({"team": r["loser"], "manager": r["l_manager"], "score": r["l_score"], "won": False, "game": i})
    data["recap_index"] = sorted(teams, key=lambda t: re.sub(r"[^a-z0-9]", "", t["team"].lower()))
    for r in data.get("rankings", []):
        r["elo_up"] = signed(r["elo_change"]) >= 0
    return data


def signed(value):
    return num(str(value).replace("\u2212", "-"))


def validate(data):
    """Schema 3: fantasy numbers travel with the real NFL lines behind them; rankings follow Elo."""
    problems = []

    def need(cond, msg):
        if not cond:
            problems.append(msg)

    need(data.get("schema") == 3, "schema must be 3 (NFL box-score lines woven in, rankings ordered by Elo)")
    lead = " ".join((data.get("lead") or {}).get("body", []))
    need(BOX_SCORE.search(lead), "lead.body never cites a box-score stat (yards, catches, carries, TDs, snaps...)")

    rankings = data.get("rankings", [])
    need(len(rankings) == 12, f"rankings: expected 12 teams, found {len(rankings)}")
    elos = []
    for i, r in enumerate(rankings, 1):
        where = f"rankings[{i}] {r.get('team', '?')}"
        need(r.get("rank") == i, f"{where}: rank should be {i}")
        try:
            elos.append(num(r["elo"]))
            signed(r["elo_change"])
        except (KeyError, ValueError):
            problems.append(f"{where}: needs elo and elo_change as numbers from the brief")
    need(elos == sorted(elos, reverse=True), "rankings must be in Elo order, highest first")

    recaps = data.get("recaps", [])
    need(len(recaps) == 6, f"recaps: expected 6 matchups, found {len(recaps)}")
    for i, r in enumerate(recaps, 1):
        where = f"recaps[{i}] {r.get('winner', '?')} v. {r.get('loser', '?')}"
        need(BOX_SCORE.search(r.get("body", "")), f"{where}: body explains the score with fantasy points only; cite the real stat line")
        need(bool(r.get("w_manager")) and bool(r.get("l_manager")), f"{where}: needs w_manager and l_manager")
        for side in ("w_keys", "l_keys"):
            keys = r.get(side) or []
            need(len(keys) >= 2, f"{where}: {side} needs two key performers")
            for k in keys:
                need(bool(k.get("line")), f"{where}: {side} {k.get('player', '?')} has no NFL stat line")
                need(bool(k.get("nfl_team")), f"{where}: {side} {k.get('player', '?')} has no NFL team")

    for a in data.get("awards", []):
        need(BOX_SCORE.search(a.get("body", "")), f"awards: {a.get('name', '?')} body never cites a box-score stat")

    standouts = data.get("standouts", [])
    need(bool(standouts), "standouts: list the top starter at each position")
    for s in standouts:
        need(bool(s.get("line")), f"standouts: {s.get('player', '?')} has no NFL stat line")

    need(isinstance(data.get("injuries"), list), "injuries must be a list (use [] if no rostered player was hurt)")

    preview = data.get("preview") or {}
    need(len(preview.get("games", [])) == 6, "preview.games: expected the six next-week matchups")
    return problems


def check_elo(data, brief_json):
    """Every ranking's Elo, change, and position must match the Elo block in the brief."""
    if not brief_json.exists():
        return [f"no brief at {brief_json} to check Elo against"]
    elo = json.loads(brief_json.read_text(encoding="utf-8")).get("elo")
    if not elo:
        return [f"{brief_json} has no Elo block; rerun fetch_week.py (or --elo-from-raw)"]
    problems = []
    for r, b in zip(data.get("rankings", []), elo["table"]):
        if r.get("team") != b["team"]:
            problems.append(f"rankings[{r.get('rank')}] is {r.get('team')}, but the brief's Elo order has {b['team']}")
            continue
        try:
            same = abs(num(r["elo"]) - b["elo"]) < 0.005 and abs(signed(r["elo_change"]) - b["change"]) < 0.005
        except (KeyError, ValueError):
            continue
        if not same:
            problems.append(f"rankings: {b['team']} Elo should be {b['elo']:.2f} ({b['change']:+.2f}), per the brief")
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


def lint(data, issue_path=None):
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
    problems += validate(data)
    if issue_path:
        problems += check_elo(data, issue_path.with_name("brief.json"))
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
    ap.add_argument("--data", type=Path, metavar="ISSUE_JSON", help="the issue to render")
    ap.add_argument("--out", type=Path, help="output HTML (default: issue.html next to the issue)")
    ap.add_argument("--lint", type=Path, metavar="ISSUE_JSON", help="check copy against the skill's rules, schema 3, and the brief's Elo")
    ap.add_argument("--check-facts", type=Path, metavar="ISSUE_JSON", help="list numbers not found in the brief")
    ap.add_argument("--brief", type=Path, help="brief.md to check against (default: next to the issue)")
    args = ap.parse_args()

    if args.lint:
        problems = lint(json.loads(args.lint.read_text(encoding="utf-8")), args.lint)
        for p in problems:
            print(f"lint: {p}")
        sys.exit(1 if problems else 0)

    if args.check_facts:
        unknown = check_facts(args.check_facts, args.brief)
        for tok, ctx in sorted(unknown.items(), key=lambda kv: kv[0]):
            print(f"not in brief: {tok:>8}  {ctx}")
        print(f"{len(unknown)} numbers to verify by hand (derived or outside the brief)")
        return

    if not args.data:
        ap.error("--data is required (or use --lint / --check-facts)")
    data = json.loads(args.data.read_text(encoding="utf-8"))
    problems = lint(data, args.data)
    for p in problems:
        print(f"lint: {p}")
    if validate(data) or check_elo(data, args.data.with_name("brief.json")):
        sys.exit("build stopped: the issue does not meet schema 3 (see lint output)")
    write(args.out or args.data.with_name("issue.html"), render(derive(data)))


if __name__ == "__main__":
    main()
