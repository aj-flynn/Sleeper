#!/usr/bin/env python3
"""Check and render a Rebuilders Anonymous newsletter issue into one self-contained HTML file.

    python3 newsletter/build.py --schema newsletter/issues/2026-week5/issue.json
    python3 newsletter/build.py --lint newsletter/issues/2026-week5/issue.json
    python3 newsletter/build.py --check-facts newsletter/issues/2026-week5/issue.json
    python3 newsletter/build.py --data newsletter/issues/2026-week5/issue.json   # writes issue.html next to it

Each check prints one problem per line and exits 1 if there are any, 0 if there are none.
run.py calls the same functions and records the results in verification.json.

The template is newsletter/templates/card-back.html. It uses a small Mustache subset:
  {{key}} / {{a.b}}      insert a value (raw HTML, so copy may use <em>, &amp;)
  {{#key}}...{{/key}}    repeat for each list item, or render once if truthy
  {{^key}}...{{/key}}    render only if the value is missing-but-declared, empty, or false
  {{.}}                  the current scalar item; {{@index}} is the 1-based loop index
Every key a template references must exist in the data (null/[]/false are fine), so a
missing field fails the build instead of shipping a blank.

A template's fonts are declared in a comment such as
  <!-- fonts: alfa-slab-one-400-normal archivo-narrow-700-normal -->
and inlined as base64 @font-face rules wherever the template says /*@font-faces*/.
"""

import argparse
import ast
import base64
import json
import operator
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
TEMPLATE = "card-back"
FONTS = ROOT / "fonts"
VOICE = ROOT.parent / ".cursor" / "skills" / "newsletter" / "reference" / "voice.md"

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

# Fields that hold no copy: skipped by the linter and the number trace.
NOT_COPY = ("url", "derived")
NOT_FACTS = NOT_COPY + ("rank", "issue_number", "week", "schema", "season")


# ---------------------------------------------------------------- template

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


def template_fonts(template=TEMPLATE):
    """The font families a template declares, e.g. {'Alfa Slab One', 'Archivo Narrow'}."""
    source = (TEMPLATES / f"{template}.html").read_text(encoding="utf-8")
    m = re.search(r"<!--\s*fonts:([^>]*)-->", source)
    return sorted({FAMILY_NAMES[f.rsplit("-", 2)[0]] for f in m.group(1).split()}) if m else []


def render(data, template=TEMPLATE):
    source = (TEMPLATES / f"{template}.html").read_text(encoding="utf-8")
    html = render_nodes(parse(source), [data])
    html = re.sub(r"\s*<!--\s*fonts:[^>]*-->", "", html, count=1)
    return html.replace("/*@font-faces*/", font_faces(source))


def num(value):
    return float(str(value).replace("$", "").replace(",", ""))


def signed(value):
    return num(str(value).replace("\u2212", "-"))


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


# ---------------------------------------------------------------- gate: schema

def validate(data):
    """Schema 3: fantasy numbers travel with the real NFL lines behind them; rankings follow Elo."""
    problems = []

    def need(cond, msg):
        if not cond:
            problems.append(msg)

    need(data.get("schema") == 3, "schema must be 3 (NFL box-score lines woven in, rankings ordered by Elo)")
    lead = data.get("lead") or {}
    need(BOX_SCORE.search(" ".join(lead.get("body", []))), "lead.body never cites a box-score stat (yards, catches, carries, TDs, snaps...)")
    need(3 <= len(lead.get("body", [])) <= 4, "lead.body needs three or four paragraphs")
    need(len(lead.get("stats", [])) == 3, "lead.stats needs exactly three {value, label}")
    need(len(re.sub(r"<[^>]+>", "", lead.get("headline", ""))) < 60, "lead.headline must be under 60 characters")

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

    awards = data.get("awards", [])
    need(4 <= len(awards) <= 5, f"awards: expected four or five, found {len(awards)}")
    for a in awards:
        need(BOX_SCORE.search(a.get("body", "")), f"awards: {a.get('name', '?')} body never cites a box-score stat")

    standouts = data.get("standouts", [])
    need(bool(standouts), "standouts: list the top starter at each position")
    for s in standouts:
        need(bool(s.get("line")), f"standouts: {s.get('player', '?')} has no NFL stat line")

    need(isinstance(data.get("injuries"), list), "injuries must be a list (use [] if no rostered player was hurt)")

    preview = data.get("preview") or {}
    need(len(preview.get("games", [])) == 6, "preview.games: expected the six next-week matchups")
    return problems


def schema_problems(data):
    """Schema 3 rules plus a dry-run render, so a missing template key fails here, not at render time."""
    problems = validate(data)
    try:
        render(derive(data))
    except (KeyError, TypeError, AttributeError) as e:
        problems.append(f"template: {e}")
    return problems


# ---------------------------------------------------------------- gate: lint

def banned_phrases(path=VOICE):
    """Banned phrases live in the skill's voice reference, between banned:start/end markers."""
    if not path.exists():
        return []
    m = re.search(r"<!-- banned:start -->(.*?)<!-- banned:end -->", path.read_text(encoding="utf-8"), re.S)
    return re.findall(r"^- `([^`]+)`", m.group(1), re.M) if m else []


def strings(value, skip=NOT_COPY):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in skip:
                yield from strings(v, skip)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v, skip)


EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")
LABELS = re.compile(r"\b(?:W\d{1,2}|PF|PA|EP|PF/PA)\b")
NOT_X_ITS_Y = re.compile(r"\b(?:it|this|that)(?:'|’)?s not [^.]{1,80}\.\s+(?:it|this|that)(?:'|’)?s\b", re.I)

# Thresholds for the Boston Connor checks (.cursor/skills/newsletter/voice/boston-connor.md). Tuned on the
# 2026 Week 4 issue; reference/voice.md documents what each one supports and the values it measured.
VOICE = {
    "caps_per_section": 3,       # "occasional ALL CAPS for emotional outbursts"
    "caps_per_issue": 10,
    "avg_sentence_words": 13.0,  # "short, blunt, declarative statements"
    "max_sentence_words": 32,
    "exclamations": 4,           # "avoid excessive yelling"
    "profanity": 4,              # "occasional profanity"
    "em_dashes": 3,
}
# Words in capitals that are labels, not yelling.
ACRONYMS = set(
    "QB RB WR TE K DEF FLEX SF TD TDS INT INTS FG FGS XP PAT FAAB ESPN NFL PPR UC MVP PR UTC OT IR PUP "
    "AFC NFC MNF TNF SNF ET EDT EST PT AM PM II III IV JR SR NGS YAC DST HC OC DC "
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX JAC KC LA LAC LAR LV MIA MIN NE NO NYG NYJ "
    "PHI PIT SEA SF TB TEN WAS WSH".split()
)
PROFANITY = re.compile(r"\b(?:damn|dammit|goddamn|hell|shit\w*|crap\w*|ass|asses|bastards?|piss\w*|freaking|friggin\w*)\b", re.I)
STOPWORDS = set(
    "a an the and or but of to in on at for with from by as is was were are be been it its it's that this "
    "they them their he his him she her we you i not no so than then just all one two three up out off".split()
)
# Prose the voice checks measure, by section. Data fields (lines, points, names, records) aren't prose.
PROSE = {
    "lead": [("lead", "dek"), ("lead", "body"), ("asides", "lead", "text")],
    "rankings": [("rankings", "*", "take"), ("asides", "rankings", "text")],
    "recaps": [("recaps", "*", "headline"), ("recaps", "*", "body"), ("asides", "recaps", "text")],
    "awards": [("awards", "*", "body"), ("bench_note",), ("injuries", "*", "note"), ("asides", "awards", "text")],
    "transactions": [("transactions", "waivers", "*", "note"), ("transactions", "free_agents", "*", "note"),
                     ("transactions", "trades", "*", "summary"), ("transactions", "trades", "*", "note"),
                     ("asides", "transactions", "text")],
    "preview": [("preview", "note"), ("preview", "games", "*", "line"), ("asides", "preview", "text")],
}
# Every field shown on the page, by section, for the ALL-CAPS count.
SECTIONS = {
    "lead": ["lead", ("asides", "lead")], "rankings": ["rankings", ("asides", "rankings")],
    "recaps": ["recaps", ("asides", "recaps")],
    "awards": ["awards", "standouts", "bench_note", "injuries", ("asides", "awards")],
    "transactions": ["transactions", ("asides", "transactions")], "preview": ["preview", ("asides", "preview")],
}


def team_names(data):
    return {r.get("team", "") for r in data.get("rankings", [])}


def pick(data, path):
    """Every string at a path like ('recaps', '*', 'body'), as (location, text)."""
    found = [("", data)]
    for key in path:
        nxt = []
        for where, v in found:
            if key == "*" and isinstance(v, list):
                nxt += [(f"{where}[{i + 1}]", x) for i, x in enumerate(v)]
            elif isinstance(v, dict) and key in v:
                nxt.append((f"{where}.{key}".lstrip("."), v[key]))
        found = nxt
    out = []
    for where, v in found:
        if isinstance(v, str):
            out.append((where, v))
        elif isinstance(v, list):
            out += [(f"{where}[{i + 1}]", x) for i, x in enumerate(v) if isinstance(x, str)]
    return out


def clean(text, names):
    text = re.sub(r"<[^>]+>", "", text).replace("&amp;", "&")
    for t in names:
        if t:
            text = text.replace(t, "Team")
    return text


ABBREV = re.compile(r"\b(?:vs|Jr|Sr|St|Mr|No|Dr)\.|\b[A-Z]\.(?=[A-Z]?\.?\s)")


def sentences(text):
    """Split prose into sentences without breaking on 23.8, T.J., or vs."""
    guarded = ABBREV.sub(lambda m: m.group(0).replace(".", "\u2024"), text)
    parts = re.split(r"(?<=[.?!])[\"”’)]*\s+", guarded)
    return [p.replace("\u2024", ".").strip() for p in parts if re.search(r"[A-Za-z0-9]", p)]


def words(sentence):
    return re.findall(r"[A-Za-z0-9’'$.\-]+", sentence)


def caps_words(text):
    """Words in capitals that read as yelling: three or more capital letters and not an acronym.
    Two-letter capitals are almost always initials or nicknames (AJ, PB), so they don't count."""
    hits = []
    for m in re.finditer(r"(?<![\w’'])[A-Z]{3,}(?:[’'][A-Z]+)?(?![\w’'])", text):
        w = m.group(0).replace("’", "'")
        if w in ACRONYMS or (w.endswith("S") and w[:-1] in ACRONYMS) or w.split("'")[0] in ACRONYMS:
            continue
        hits.append(m.group(0))
    return hits


STATUS = {"questionable", "doubtful", "out", "probable", "injured reserve", "on ir", "out for the season"}


def voice_metrics(data):
    """What the Boston Connor checks measure: capitals by section, sentence length, repeated phrasing."""
    names = sorted(team_names(data), key=len, reverse=True)
    caps = {}
    for sec, parts in SECTIONS.items():
        found = []
        for part in parts:
            node = data.get(part) if isinstance(part, str) else (data.get(part[0]) or {}).get(part[1])
            for s in strings(node or ""):
                found += caps_words(clean(s, names))
        caps[sec] = found
    items = [(where, clean(text, names)) for paths in PROSE.values() for path in paths for where, text in pick(data, path)]
    sents = [(where, s) for where, text in items for s in sentences(text)]
    lengths = [len(words(s)) for _, s in sents]
    short = {}
    for where, s in sents:
        key = re.sub(r"[^a-z' ]", "", s.lower().replace("’", "'")).strip()
        if 0 < len(key.split()) <= 6 and key not in STATUS:
            short.setdefault(key, []).append(where)
    grams = {}
    for where, text in items:
        toks = re.findall(r"[A-Za-z’']+|\S", text)
        for i in range(len(toks) - 3):
            g = toks[i:i + 4]
            if all(re.fullmatch(r"[a-z’']+", t) for t in g) and sum(t not in STOPWORDS for t in g) >= 3:
                grams.setdefault(" ".join(g), set()).add(where)
    return {
        "caps_by_section": caps,
        "sentences": len(lengths),
        "avg_sentence_words": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
        "longest": max(sents, key=lambda x: len(words(x[1])), default=("", "")),
        "repeated_short_sentences": {k: v for k, v in short.items() if len(v) > 1},
        "repeated_phrases": {k: sorted(v) for k, v in grams.items() if len(v) > 1},
    }


def lint(data):
    """The mechanical rules a script can check for certain: banned filler, punctuation, and the measurable
    parts of the Boston Connor voice. The editor checks the rest against the guide itself."""
    prose = re.sub(r"<[^>]+>", "", "\n".join(strings(data)))
    names = sorted(team_names(data), key=len, reverse=True)
    unnamed = prose
    for t in names:
        if t:
            unnamed = unnamed.replace(t, "")
    problems = []
    for phrase in banned_phrases():
        hits = len(re.findall(r"\b" + re.escape(phrase) + r"\b", unnamed, re.I))
        if hits:
            problems.append(f"banned phrase x{hits}: {phrase!r}")
    dashes = prose.count("\u2014")
    if dashes > VOICE["em_dashes"]:
        problems.append(f"{dashes} em dashes in the issue (limit {VOICE['em_dashes']})")
    heads = [data.get("lead", {}).get("headline", "")] + [r.get("headline", "") for r in data.get("recaps", [])]
    if any("\u2014" in h for h in heads):
        problems.append("em dash in a headline (none allowed)")
    if unnamed.count("!") > VOICE["exclamations"]:
        problems.append(f"{unnamed.count('!')} exclamation marks outside team names (limit {VOICE['exclamations']}; that's excessive yelling)")
    if EMOJI.search(unnamed):
        problems.append("emoji in the copy (none allowed)")
    swears = PROFANITY.findall(unnamed)
    if len(swears) > VOICE["profanity"]:
        problems.append(f"{len(swears)} swear words (limit {VOICE['profanity']}; profanity is occasional): {', '.join(swears)}")
    if len(NOT_X_ITS_Y.findall(unnamed)) > 1:
        problems.append("the \"It's not X. It's Y.\" move appears more than once")
    labels = sorted(set(LABELS.findall(unnamed)))
    if labels:
        problems.append(f"internal labels in prose: {', '.join(labels)} (write them out)")
    firsts = {}
    for r in data.get("rankings", []):
        word = re.sub(r"<[^>]+>", "", r.get("take", "")).split(" ", 1)[0].strip("“\"'’,.").lower()
        firsts.setdefault(word, []).append(r.get("team", "?"))
    for word, teams in firsts.items():
        if len(teams) > 1:
            problems.append(f"ranking takes for {', '.join(teams)} all start with {word!r}; vary the openings")

    v = voice_metrics(data)
    total = 0
    for sec, hits in v["caps_by_section"].items():
        total += len(hits)
        if len(hits) > VOICE["caps_per_section"]:
            problems.append(f"{len(hits)} ALL-CAPS words in {sec} (limit {VOICE['caps_per_section']} per section): {', '.join(hits)}")
    if total > VOICE["caps_per_issue"]:
        problems.append(f"{total} ALL-CAPS words in the issue (limit {VOICE['caps_per_issue']}); caps are for the occasional outburst")
    if v["avg_sentence_words"] > VOICE["avg_sentence_words"]:
        problems.append(f"average sentence is {v['avg_sentence_words']} words (limit {VOICE['avg_sentence_words']}); go shorter and blunter")
    where, longest = v["longest"]
    if len(words(longest)) > VOICE["max_sentence_words"]:
        problems.append(f"{where}: a {len(words(longest))}-word sentence (limit {VOICE['max_sentence_words']}): “{longest[:80]}…”")
    for s, spots in v["repeated_short_sentences"].items():
        problems.append(f"catchphrase repeated: “{s}” in {', '.join(spots)}")
    for g, spots in v["repeated_phrases"].items():
        problems.append(f"phrase repeated across items: “{g}” in {', '.join(spots)}")
    return problems


# ---------------------------------------------------------------- gate: facts

NUMBER = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?")
SMALL = {str(i) for i in range(0, 11)}


def canon(token):
    t = str(token).lstrip("$").replace(",", "")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"


def brief_numbers(brief_json, brief_md=None):
    """Every number the brief states, in canonical form (31.30 and 31.3 are the same number)."""
    known = set()

    def walk(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            known.add(canon(f"{v:.2f}") if isinstance(v, float) else str(v))
            if isinstance(v, float):
                known.add(canon(repr(v)))
        elif isinstance(v, str):
            known.update(canon(t) for t in NUMBER.findall(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(brief_json)
    if brief_md:
        known.update(canon(t) for t in NUMBER.findall(brief_md))
    return known


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def evaluate(expr, known):
    """Evaluate a +-*/ expression whose every operand is a brief number (or a count up to 10)."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            literal = ast.get_source_segment(expr, node) or str(node.value)
            if canon(literal) not in known and canon(literal) not in SMALL:
                raise ValueError(f"operand {literal} is not in the brief")
            return node.value
        raise ValueError("only numbers, + - * / and parentheses are allowed")
    return ev(ast.parse(expr.replace("$", "").replace(",", ""), mode="eval"))


def check_derived(data, known):
    """Each ledger entry recomputes from brief numbers to the value printed in the copy."""
    problems, ok = [], set()
    for i, d in enumerate(data.get("derived") or [], 1):
        value, expr = str(d.get("value", "")), str(d.get("expr", ""))
        try:
            got = evaluate(expr, known)
        except (ValueError, SyntaxError, ZeroDivisionError) as e:
            problems.append(f"derived[{i}] {value} = {expr}: {e}")
            continue
        places = len(canon(value).split(".")[1]) if "." in canon(value) else 0
        want = num(value)
        if abs(round(got, places) - want) > 1e-9 and abs(round(abs(got), places) - want) > 1e-9:
            problems.append(f"derived[{i}] {value} = {expr}: the expression comes to {got:.4f}, not {value}")
        else:
            ok.add(canon(value))
    return problems, ok


def norm_name(name):
    name = re.sub(r"<[^>]+>", "", str(name)).replace("’", "'").lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)
    return re.sub(r"[^a-z0-9]", "", name)


def two(x):
    return f"{float(x):.2f}"


def check_structured(data, brief):
    """Facts with one right answer, matched field by field against brief.json."""
    problems = []
    elo = brief.get("elo")
    if not elo:
        problems.append("brief.json has no Elo block; rebuild the brief")
    else:
        for r, b in zip(data.get("rankings", []), elo["table"]):
            if r.get("team") != b["team"]:
                problems.append(f"rankings[{r.get('rank')}] is {r.get('team')}, but the brief's Elo order has {b['team']}")
                continue
            try:
                same = abs(num(r["elo"]) - b["elo"]) < 0.005 and abs(signed(r["elo_change"]) - b["change"]) < 0.005
            except (KeyError, ValueError):
                same = False
            if not same:
                problems.append(f"rankings: {b['team']} Elo should be {b['elo']:.2f} ({b['change']:+.2f}), per the brief")
            if r.get("record") != b["record"]:
                problems.append(f"rankings: {b['team']} record should be {b['record']}")
    managers = {t["team"]: t["manager"] for t in brief.get("teams", [])}
    for r in data.get("rankings", []):
        if r.get("team") in managers and r.get("manager") != managers[r["team"]]:
            problems.append(f"rankings: {r['team']} manager should be {managers[r['team']]}")

    by_winner = {m["winner"]["team"]: m for m in brief.get("fantasy_matchups", [])}
    for i, r in enumerate(data.get("recaps", []), 1):
        where = f"recaps[{i}] {r.get('winner')}"
        m = by_winner.get(r.get("winner"))
        if not m or m["loser"]["team"] != r.get("loser"):
            problems.append(f"{where}: no matchup in the brief where {r.get('winner')} beat {r.get('loser')}")
            continue
        for field, want in (("w_score", two(m["winner"]["points"])), ("l_score", two(m["loser"]["points"])),
                            ("margin", two(m["margin"])), ("w_manager", m["winner"]["manager"]), ("l_manager", m["loser"]["manager"])):
            if str(r.get(field)) != want:
                problems.append(f"{where}: {field} is {r.get(field)!r}, the brief says {want!r}")
        for side_key, side in (("w_keys", m["winner"]), ("l_keys", m["loser"])):
            pool = side["starters"] + side["bench"]
            for k in r.get(side_key) or []:
                p = next((x for x in pool if norm_name(x["name"]) == norm_name(k.get("player"))), None)
                if p is None:
                    p = next((x for x in pool if x["pos"] == "DEF" and x["nfl_team"] == k.get("nfl_team")), None)
                if p is None:
                    problems.append(f"{where}: {k.get('player')} is not on {side['team']}'s roster in the brief")
                    continue
                if abs(num(k.get("pts", "nan")) - p["fantasy_pts"]) > 0.005:
                    problems.append(f"{where}: {k.get('player')} scored {two(p['fantasy_pts'])}, not {k.get('pts')}")
                if p["nfl_team"] and k.get("nfl_team") != p["nfl_team"]:
                    problems.append(f"{where}: {k.get('player')} plays for {p['nfl_team']}, not {k.get('nfl_team')}")

    starters = [(s, side["team"]) for m in brief.get("fantasy_matchups", []) for side in (m["winner"], m["loser"]) for s in side["starters"]]
    for s in data.get("standouts", []):
        pos = s.get("pos")
        best = max((p["fantasy_pts"] for p, _ in starters if p["pos"] == pos), default=None)
        match = next(((p, t) for p, t in starters if p["pos"] == pos and abs(p["fantasy_pts"] - num(s.get("pts", "nan"))) < 0.005
                      and (norm_name(p["name"]) == norm_name(s.get("player")) or (pos == "DEF" and p["nfl_team"] == s.get("nfl_team")))), None)
        if match is None:
            problems.append(f"standouts: {pos} {s.get('player')} with {s.get('pts')} is not a {pos} starter in the brief")
            continue
        if best is not None and abs(match[0]["fantasy_pts"] - best) > 0.005:
            problems.append(f"standouts: the top {pos} starter scored {two(best)}, not {s.get('pts')}")
        if s.get("team") != match[1]:
            problems.append(f"standouts: {s.get('player')} started for {match[1]}, not {s.get('team')}")

    want_pairs = {frozenset(p) for p in brief.get("next_week", {}).get("fantasy_matchups", [])}
    got_pairs = {frozenset((g.get("a"), g.get("b"))) for g in (data.get("preview") or {}).get("games", [])}
    if want_pairs and got_pairs != want_pairs:
        problems.append("preview.games: the six pairings don't match the brief's next-week matchups")

    claims = [t for t in brief.get("transactions", []) if t["type"] == "waiver" and t["status"] == "complete"]
    for w in (data.get("transactions") or {}).get("waivers", []):
        hit = [t for t in claims if w.get("team") in t["teams"] and any(norm_name(a["player"]) == norm_name(w.get("add")) for a in t["adds"])]
        if not hit and w.get("pos") != "DEF":
            problems.append(f"waivers: no completed claim of {w.get('add')} by {w.get('team')} in the brief")
        elif hit and not any(t["faab_bid"] is not None and abs(t["faab_bid"] - num(w.get("faab", "nan"))) < 0.005 for t in hit):
            problems.append(f"waivers: {w.get('team')} bid ${hit[0]['faab_bid']} on {w.get('add')}, not {w.get('faab')}")
    return problems


def trace_numbers(data, known, derived_ok):
    """Numbers in the copy that are neither in the brief nor recomputed in the derived ledger."""
    unknown = {}
    for s in strings(data, skip=NOT_FACTS):
        for tok in NUMBER.findall(re.sub(r"<[^>]+>", "", s)):
            t = canon(tok)
            if t in SMALL or t in known or t in derived_ok or tok.startswith(("2026", "2027")) and len(tok) == 4:
                continue
            unknown.setdefault(t, s.strip()[:90])
    return unknown


def check_facts(issue_path, brief_json_path=None, brief_md_path=None):
    """Every number traces to the brief, every derived number recomputes, every structured fact matches."""
    issue_path = Path(issue_path)
    data = json.loads(issue_path.read_text(encoding="utf-8"))
    bj = Path(brief_json_path or issue_path.with_name("brief.json"))
    bm = Path(brief_md_path or issue_path.with_name("brief.md"))
    if not bj.exists():
        return [f"no brief at {bj}"]
    brief = json.loads(bj.read_text(encoding="utf-8"))
    known = brief_numbers(brief, bm.read_text(encoding="utf-8") if bm.exists() else None)
    problems, derived_ok = check_derived(data, known)
    problems += check_structured(data, brief)
    for tok, ctx in sorted(trace_numbers(data, known, derived_ok).items()):
        problems.append(f"not in brief: {tok} in “{ctx}” (add it to derived with the arithmetic, or fix it)")
    return problems


# ---------------------------------------------------------------- CLI

def write(out, html):
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")


def report(problems, label):
    for p in problems:
        print(f"{label}: {p}")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, metavar="ISSUE_JSON", help="render this issue (after schema, lint and facts pass)")
    ap.add_argument("--out", type=Path, help="output HTML (default: issue.html next to the issue)")
    ap.add_argument("--schema", type=Path, metavar="ISSUE_JSON", help="check schema 3 and that the template renders")
    ap.add_argument("--lint", type=Path, metavar="ISSUE_JSON", help="check copy against the voice rules a script can verify")
    ap.add_argument("--check-facts", type=Path, metavar="ISSUE_JSON", help="trace every number and fact to the brief")
    args = ap.parse_args()

    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    if args.schema:
        sys.exit(report(schema_problems(load(args.schema)), "schema"))
    if args.lint:
        sys.exit(report(lint(load(args.lint)), "lint"))
    if args.check_facts:
        sys.exit(report(check_facts(args.check_facts), "facts"))
    if not args.data:
        ap.error("pass --data, --schema, --lint or --check-facts")
    data = load(args.data)
    problems = schema_problems(data) + lint(data) + check_facts(args.data)
    if report(problems, "build"):
        sys.exit("build stopped: fix the problems above first")
    write(args.out or args.data.with_name("issue.html"), render(derive(data)))


if __name__ == "__main__":
    main()
