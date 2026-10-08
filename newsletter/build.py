#!/usr/bin/env python3
"""Render a Rebuilders Anonymous newsletter issue into one self-contained HTML file.

    python3 newsletter/build.py --template broadsheet --data issue.json --out 2026-week5.html
    python3 newsletter/build.py --samples      # rebuild newsletter/templates/*.html
    python3 newsletter/build.py --lint issue.json

Templates live in newsletter/templates/src/. They use a small Mustache subset:
  {{key}} / {{a.b}}      insert a value (raw HTML, so copy may use <em>, &amp;)
  {{#key}}...{{/key}}    repeat for each list item, or render once if truthy
  {{^key}}...{{/key}}    render only if the value is missing-but-declared, empty, or false
  {{.}}                  the current scalar item; {{@index}} is the 1-based loop index
Every key a template references must exist in the data (null/[]/false are fine), so a
missing field fails the build instead of shipping a blank.

A template's fonts are declared in a comment such as
  <!-- fonts: newsreader-400-normal libre-franklin-800-normal -->
and inlined as base64 @font-face rules wherever the template says /*@font-faces*/.
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "templates" / "src"
FONTS = ROOT / "fonts"
SKILL = ROOT.parent / ".cursor" / "skills" / "newsletter" / "SKILL.md"

SAMPLE_DATA = ROOT / "sample" / "sample-issue.json"
SAMPLE_TEMPLATES = ["broadsheet", "ledger", "night-edition"]

FAMILY_NAMES = {
    "newsreader": "Newsreader",
    "libre-franklin": "Libre Franklin",
    "ibm-plex-sans": "IBM Plex Sans",
    "ibm-plex-mono": "IBM Plex Mono",
    "big-shoulders-display": "Big Shoulders Display",
    "source-serif-4": "Source Serif 4",
}

TAG = re.compile(r"{{\s*([#^/]?)\s*([\w.@]+)\s*}}")
MISSING = object()


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


def render(template_name, data):
    template = (SRC / f"{template_name}.html").read_text(encoding="utf-8")
    html = render_nodes(parse(template), [data])
    html = re.sub(r"\s*<!--\s*fonts:[^>]*-->", "", html, count=1)
    return html.replace("/*@font-faces*/", font_faces(template))


def banned_phrases():
    """Banned phrases are maintained in the newsletter skill, between banned:start/end markers."""
    if not SKILL.exists():
        return []
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(r"<!-- banned:start -->(.*?)<!-- banned:end -->", text, re.S)
    return re.findall(r"^- `([^`]+)`", m.group(1), re.M) if m else []


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


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
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", choices=[p.stem for p in SRC.glob("*.html")])
    ap.add_argument("--data", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--samples", action="store_true", help="rebuild the sample templates and index")
    ap.add_argument("--lint", type=Path, metavar="ISSUE_JSON", help="check copy against the skill's banned list")
    args = ap.parse_args()

    if args.lint:
        problems = lint(json.loads(args.lint.read_text(encoding="utf-8")))
        for p in problems:
            print(f"lint: {p}")
        sys.exit(1 if problems else 0)

    if args.samples:
        data = json.loads(SAMPLE_DATA.read_text(encoding="utf-8"))
        for name in SAMPLE_TEMPLATES:
            out = ROOT / "templates" / f"{name}.html"
            out.write_text(render(name, data), encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT.parent)}")
        out = ROOT / "templates" / "index.html"
        out.write_text(render("index", {}), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT.parent)}")
        for p in lint(data):
            print(f"lint: {p}")
        return

    if not (args.template and args.data and args.out):
        ap.error("--template, --data, and --out are required (or use --samples / --lint)")
    data = json.loads(args.data.read_text(encoding="utf-8"))
    args.out.write_text(render(args.template, data), encoding="utf-8")
    print(f"wrote {args.out}")
    for p in lint(data):
        print(f"lint: {p}")


if __name__ == "__main__":
    main()
