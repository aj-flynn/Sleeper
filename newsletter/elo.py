#!/usr/bin/env python3
"""Committed weekly Elo history and the inline SVG chart for Card Back.

The brief step records one week at a time into newsletter/elo/<season>.json. Past weeks
are never rewritten. If a recompute of a past week disagrees with the file, this module
raises EloHistoryError. Render reads the same file and draws the chart.

    python3 newsletter/elo.py --backfill --season 2026 --through 4
"""

import argparse
import json
import math
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fetch_week import ELO_K, ELO_START, LEAGUE_ID, elo_ratings, load  # noqa: E402

# Twelve card-ink hues, indexed by roster_id - 1. Spread around the wheel so a
# small swatch and a thin stroke still read as the same team. The 1000 baseline
# is dashed ink, not maroon — maroon is Split's color (roster 5).
TEAM_COLORS = (
    "#6B4510",  # 1 walnut
    "#0B7A78",  # 2 teal
    "#1D4E9B",  # 3 blue
    "#7A2E9B",  # 4 violet
    "#8A1C2B",  # 5 maroon (the template ink)
    "#5C7A8A",  # 6 steel
    "#D4B01A",  # 7 gold
    "#D6452F",  # 8 vermilion
    "#148F3D",  # 9 emerald
    "#262321",  # 10 near-black ink
    "#E05A00",  # 11 orange
    "#0A2F5C",  # 12 midnight
)
BASELINE_COLOR = "#262321"


class EloHistoryError(Exception):
    """The committed history disagrees with a recompute, or a required week is missing."""


def history_path(season):
    return ROOT / "elo" / f"{season}.json"


def team_color(roster_id):
    return TEAM_COLORS[(int(roster_id) - 1) % len(TEAM_COLORS)]


def name_key(team):
    """Same sort as the Find-your-team list in build.derive."""
    return re.sub(r"[^a-z0-9]", "", team.lower())


def xml(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def elo_num(value):
    return round(float(value), 2)


def empty_doc(season, league=LEAGUE_ID):
    return {"season": str(season), "league_id": league, "start": ELO_START, "k": ELO_K,
            "margin_of_victory": False, "weeks": {}}


def snapshot(ratings, team_name):
    """One week's map of roster_id -> {team, elo}, keys as strings, roster order numeric."""
    rows = {}
    for rid in sorted(ratings, key=lambda x: int(x)):
        rows[str(int(rid))] = {"team": team_name(int(rid)), "elo": elo_num(ratings[rid])}
    return rows


def dump_doc(doc):
    weeks = {}
    for w in sorted(doc["weeks"], key=lambda x: int(x)):
        week = doc["weeks"][w]
        weeks[str(int(w))] = {str(int(rid)): {"team": week[str(int(rid))]["team"],
                                              "elo": elo_num(week[str(int(rid))]["elo"])}
                              for rid in sorted(week, key=lambda x: int(x))}
    out = {"season": str(doc["season"]), "league_id": doc.get("league_id", LEAGUE_ID),
           "start": elo_num(doc.get("start", ELO_START)), "k": int(doc.get("k", ELO_K)),
           "margin_of_victory": False, "weeks": weeks}
    return json.dumps(out, indent=1, ensure_ascii=False) + "\n"


def save_doc(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_doc(doc)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".elo-", suffix=".tmp", delete=False) as tmp:
        tmp.write(text)
        tmp_name = tmp.name
    Path(tmp_name).replace(path)


def read_doc(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_week(week_matchups, ratings):
    """One week's games, from the ratings both teams had going in. Same math as fetch_week.elo_ratings."""
    games = defaultdict(list)
    for m in week_matchups:
        games[m["matchup_id"]].append(m)
    change = {rid: 0.0 for rid in ratings}
    for a, b in (g for g in games.values() if len(g) == 2):
        ra, rb = ratings[a["roster_id"]], ratings[b["roster_id"]]
        expected = 1 / (1 + 10 ** ((rb - ra) / 400))
        actual = 1.0 if a["points"] > b["points"] else 0.0 if a["points"] < b["points"] else 0.5
        d = round(ELO_K * (actual - expected), 2)
        change[a["roster_id"]], change[b["roster_id"]] = d, -d
    return {rid: round(ratings[rid] + change[rid], 2) for rid in ratings}, change


def _week_map(doc, week):
    raw = doc["weeks"].get(str(int(week)))
    if raw is None:
        return None
    return {int(rid): {"team": row["team"], "elo": elo_num(row["elo"])} for rid, row in raw.items()}


def _check_past(doc, matchups, roster_ids, week, path):
    """Fail if weeks 0..week-1 in the file don't match a from-scratch recompute."""
    zero = _week_map(doc, 0)
    if zero is None:
        raise EloHistoryError(f"{path} has no week 0 baseline")
    for rid in roster_ids:
        row = zero.get(rid)
        if row is None:
            raise EloHistoryError(f"{path} week 0 is missing roster {rid}")
        if abs(row["elo"] - ELO_START) >= 0.005:
            raise EloHistoryError(f"{path} week 0 roster {rid} ({row['team']}) is {row['elo']}, expected {ELO_START:.2f}")
    missing = [w for w in range(0, week) if _week_map(doc, w) is None]
    if missing:
        raise EloHistoryError(f"{path} is missing week(s) {missing}; cannot record week {week}")
    if week <= 1:
        return
    _, _, history = elo_ratings(matchups, roster_ids, week - 1)
    for w in range(1, week):
        recorded = _week_map(doc, w)
        for rid in roster_ids:
            computed = history[rid][w - 1]
            row = recorded.get(rid)
            if row is None:
                raise EloHistoryError(f"{path} week {w} is missing roster {rid}")
            if abs(computed - row["elo"]) >= 0.005:
                raise EloHistoryError(
                    f"{path} week {w} roster {rid} ({row['team']}) recomputes to {computed:.2f}, "
                    f"record has {row['elo']:.2f}"
                )


def record_week(season, week, matchups, roster_ids, team_name, path=None, league=LEAGUE_ID):
    """Read prior weeks from the history file, write only `week`. Idempotent for that week.

    Week N is computed from the recorded week N-1 ratings plus this week's games. Weeks
    0..N-1 are checked against a from-scratch recompute and never overwritten. A missing
    file is only allowed when recording week 1 (it creates the week 0 baseline).
    """
    path = Path(path or history_path(season))
    if path.exists():
        doc = read_doc(path)
    elif week == 1:
        doc = empty_doc(season, league)
        doc["weeks"]["0"] = snapshot({rid: ELO_START for rid in roster_ids}, team_name)
    else:
        raise EloHistoryError(f"{path} is missing; cannot record week {week} without weeks 0..{week - 1}. Backfill first.")
    _check_past(doc, matchups, roster_ids, week, path)
    prior = {rid: _week_map(doc, week - 1)[rid]["elo"] for rid in roster_ids}
    new_ratings, _ = apply_week(matchups[week], prior)
    # Overwrite this week only. Later weeks, if any, stay put.
    doc["weeks"][str(int(week))] = snapshot(new_ratings, team_name)
    save_doc(path, doc)
    return doc


def backfill(season, through, matchups, roster_ids, team_name, path=None, league=LEAGUE_ID):
    """Write weeks 0..through from the Elo calculation, once, to seed the history file."""
    path = Path(path or history_path(season))
    _, _, history = elo_ratings(matchups, roster_ids, through)
    doc = empty_doc(season, league)
    doc["weeks"]["0"] = snapshot({rid: ELO_START for rid in roster_ids}, team_name)
    for w in range(1, through + 1):
        doc["weeks"][str(w)] = snapshot({rid: history[rid][w - 1] for rid in roster_ids}, team_name)
    save_doc(path, doc)
    return doc


# Series that never separate by more than this (Elo) share a pixel on the plot.
TRACK_TOL = 1.0
# Visual lane gap for those twins, in SVG units. ~2 Elo at the usual vertical scale.
TRACK_GAP_PX = 6.0


def tracking_offsets(rows, tol=TRACK_TOL, gap_px=TRACK_GAP_PX):
    """Pixel y-offsets for series that stay stacked, so every color stays visible.

    UC and J'Allen differ by 0.07 Elo across weeks 0–4. At chart scale that is a
    fifth of a pixel, and the later-drawn line eats the other. Teams that actually
    diverge (max week-by-week gap > tol) stay on their true y.
    """
    n = len(rows)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            gap = max(abs(a - b) for a, b in zip(rows[i]["elos"], rows[j]["elos"]))
            if gap <= tol:
                a, b = find(i), find(j)
                if a != b:
                    parent[b] = a
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    off = {r["roster_id"]: 0.0 for r in rows}
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda i: name_key(rows[i]["team"]))
        mid = (len(members) - 1) / 2
        for k, i in enumerate(members):
            off[rows[i]["roster_id"]] = (k - mid) * gap_px
    return off


def series(doc, through=None):
    """[{roster_id, team, color, elos: [week0..weekN]}, ...] in Find-your-team name order."""
    weeks = sorted((int(w) for w in doc["weeks"]), key=int)
    if through is not None:
        weeks = [w for w in weeks if w <= int(through)]
    if not weeks:
        return []
    last = _week_map(doc, weeks[-1])
    rows = []
    for rid, row in last.items():
        elos = []
        for w in weeks:
            cell = _week_map(doc, w).get(rid)
            if cell is None:
                raise EloHistoryError(f"history is missing roster {rid} in week {w}")
            elos.append(cell["elo"])
        rows.append({"roster_id": rid, "team": row["team"], "color": team_color(rid), "elos": elos, "weeks": weeks})
    rows.sort(key=lambda r: name_key(r["team"]))
    return rows


# ---------------------------------------------------------------- monotone cubic → SVG path

def monotone_slopes(xs, ys):
    """Fritsch–Carlson tangents so the cubic stays monotone between samples."""
    n = len(xs)
    if n < 2:
        return [0.0] * n
    dx = [xs[i + 1] - xs[i] for i in range(n - 1)]
    delta = [(ys[i + 1] - ys[i]) / dx[i] if dx[i] else 0.0 for i in range(n - 1)]
    m = [0.0] * n
    m[0] = delta[0]
    m[-1] = delta[-1]
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0:
            m[i] = 0.0
        else:
            m[i] = (delta[i - 1] + delta[i]) / 2
    for i in range(n - 1):
        if abs(delta[i]) < 1e-12:
            m[i] = m[i + 1] = 0.0
            continue
        alpha = m[i] / delta[i]
        beta = m[i + 1] / delta[i]
        tau2 = alpha * alpha + beta * beta
        if tau2 > 9:
            tau = 3 / math.sqrt(tau2)
            m[i] = tau * alpha * delta[i]
            m[i + 1] = tau * beta * delta[i]
    return m


def monotone_cubic_beziers(points):
    """Cubic Bézier segments (c1x, c1y, c2x, c2y, x1, y1) that pass through every point."""
    if len(points) < 2:
        return []
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    m = monotone_slopes(xs, ys)
    segs = []
    for i in range(len(points) - 1):
        h = xs[i + 1] - xs[i]
        c1x, c1y = xs[i] + h / 3, ys[i] + m[i] * h / 3
        c2x, c2y = xs[i + 1] - h / 3, ys[i + 1] - m[i + 1] * h / 3
        segs.append((c1x, c1y, c2x, c2y, xs[i + 1], ys[i + 1]))
    return segs


def monotone_cubic_path(points):
    """SVG path `d` for a monotone cubic through `points` [(x, y), ...]."""
    if not points:
        return ""
    parts = [f"M {points[0][0]:.4f},{points[0][1]:.4f}"]
    for c1x, c1y, c2x, c2y, x1, y1 in monotone_cubic_beziers(points):
        parts.append(f"C {c1x:.4f},{c1y:.4f} {c2x:.4f},{c2y:.4f} {x1:.4f},{y1:.4f}")
    return " ".join(parts)


def path_anchors(d):
    """On-curve points of an M/C path: the initial M and the end of each C."""
    tokens = d.replace(",", " ").split()
    pts, i = [], 0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd == "M":
            pts.append((float(tokens[i + 1]), float(tokens[i + 2])))
            i += 3
        elif cmd == "C":
            pts.append((float(tokens[i + 5]), float(tokens[i + 6])))
            i += 7
        else:
            raise ValueError(f"unexpected path command {cmd!r}")
    return pts


# ---------------------------------------------------------------- chart

def _ticks(lo, hi):
    pad = max(8.0, (hi - lo) * 0.14 if hi > lo else 12.0)
    lo, hi = lo - pad, hi + pad
    step = 10 if (hi - lo) <= 140 else 20
    start = int(math.floor(lo / step) * step)
    end = int(math.ceil(hi / step) * step)
    return list(range(start, end + 1, step)), start, end


def chart_svg(doc, through):
    """Inline SVG: one monotone-cubic line per team, points on the recorded weeks."""
    rows = series(doc, through)
    if not rows:
        raise EloHistoryError("Elo history has no weeks to chart")
    weeks = rows[0]["weeks"]
    values = [e for r in rows for e in r["elos"]]
    yticks, y0, y1 = _ticks(min(values), max(values))
    # Wide viewBox, scales to the column. Room on the right for end labels on desktop.
    W, H = 680, 360
    left, right, top, bottom = 44, 14, 16, 38
    pw, ph = W - left - right, H - top - bottom
    x_at = lambda w: left + (0 if len(weeks) == 1 else (w - weeks[0]) / (weeks[-1] - weeks[0]) * pw)
    y_at = lambda e: top + (1 - (e - y0) / (y1 - y0)) * ph

    parts = [
        f'<svg id="elo-chart" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="elo-chart-title">',
        f'<title id="elo-chart-title">Elo ratings, week {weeks[0]} through week {weeks[-1]}</title>',
        '<rect class="elo-plot" x="0" y="0" width="100%" height="100%" fill="#F1E2DF"/>',
    ]
    for t in yticks:
        y = y_at(t)
        if t == 1000:
            parts.append(f'<line class="elo-base" x1="{left:.1f}" y1="{y:.2f}" x2="{left + pw:.1f}" '
                         f'y2="{y:.2f}" stroke="{BASELINE_COLOR}" stroke-width="1" '
                         f'stroke-dasharray="4 3" stroke-opacity=".4"/>')
        else:
            parts.append(f'<line x1="{left:.1f}" y1="{y:.2f}" x2="{left + pw:.1f}" y2="{y:.2f}" '
                         f'stroke="rgba(38,35,33,.22)" stroke-width="1"/>')
        parts.append(f'<text class="elo-tick" x="{left - 7:.1f}" y="{y + 3.5:.2f}" '
                     f'text-anchor="end">{t}</text>')
    for w in weeks:
        x = x_at(w)
        parts.append(f'<text class="elo-tick" x="{x:.2f}" y="{H - 10:.1f}" text-anchor="middle">{w}</text>')
    parts.append(f'<text class="elo-axis" x="14" y="{top + ph / 2:.1f}" text-anchor="middle" '
                 f'transform="rotate(-90 14 {top + ph / 2:.1f})">Elo</text>')
    parts.append(f'<text class="elo-axis" x="{left + pw / 2:.1f}" y="{H - 1:.1f}" text-anchor="middle">Week</text>')
    parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
                 f'fill="none" stroke="#262321" stroke-width="1.75"/>')

    # Draw lower-rated teams first so the current leader sits on top.
    # Names live in the HTML legend (Find-your-team order); 12 end labels will not fit.
    # Twins that never separate (UC / J'Allen at 0.07 Elo) get a lane so both inks show.
    lanes = tracking_offsets(rows)
    draw = sorted(rows, key=lambda r: r["elos"][-1])
    for r in draw:
        dy = lanes[r["roster_id"]]
        pts = [(x_at(w), y_at(e) + dy) for w, e in zip(r["weeks"], r["elos"])]
        d = monotone_cubic_path(pts)
        team = xml(r["team"])
        parts.append(f'<path class="elo-line" data-team="{team}" fill="none" stroke="{r["color"]}" '
                     f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" d="{d}"/>')
        for (x, y), e, w in zip(pts, r["elos"], r["weeks"]):
            parts.append(f'<circle class="elo-point" data-team="{team}" data-week="{w}" cx="{x:.2f}" '
                         f'cy="{y:.2f}" r="3.4" fill="{r["color"]}" stroke="#F1E2DF" stroke-width="1"/>')

    parts.append("</svg>")
    return "\n".join(parts)


def chart_html(season, week, path=None):
    """Figure + SVG + Find-your-team legend. Inserted under the power rankings."""
    path = Path(path or history_path(season))
    if not path.exists():
        raise EloHistoryError(f"{path} is missing; the brief step writes it before render")
    doc = read_doc(path)
    if _week_map(doc, week) is None:
        raise EloHistoryError(f"{path} has no week {week}; rerun the brief step")
    rows = series(doc, week)
    svg = chart_svg(doc, week)
    items = []
    for r in rows:
        # Same stroke + dot as the plot, so the key is the line, not a square of a
        # neighboring hue.
        items.append(
            f'<li data-team="{xml(r["team"])}">'
            f'<svg class="elo-key" viewBox="0 0 32 12" aria-hidden="true">'
            f'<path fill="none" stroke="{r["color"]}" stroke-width="2.5" '
            f'stroke-linecap="round" d="M1 6 H22"/>'
            f'<circle cx="22" cy="6" r="3.4" fill="{r["color"]}" stroke="#F1E2DF" stroke-width="1"/>'
            f'</svg>'
            f'<span class="nm">{xml(r["team"])}</span></li>'
        )
    return (
        f'<figure class="elo-chart" id="elo-chart-wrap">'
        f"{svg}"
        f'<figcaption><ul class="elo-legend">{"".join(items)}</ul></figcaption>'
        f"</figure>"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backfill", action="store_true", help="write weeks 0..--through from a week's raw/ matchups")
    ap.add_argument("--season", default="2026")
    ap.add_argument("--through", type=int, default=4)
    ap.add_argument("--from-issue", type=Path, help="issue folder that already has raw/ matchups (default: week --through)")
    ap.add_argument("--out", type=Path, help="history file (default newsletter/elo/<season>.json)")
    a = ap.parse_args()
    if not a.backfill:
        ap.error("only --backfill is implemented on the command line; weekly writes go through run.py brief")
    issue = a.from_issue or ROOT / "issues" / f"{a.season}-week{a.through}"
    rosters = load(issue / "raw" / "sleeper_rosters.json")
    users = load(issue / "raw" / "sleeper_users.json")
    matchups = {w: load(issue / "raw" / f"sleeper_matchups_w{w}.json") for w in range(1, a.through + 1)}
    user_by_id = {u["user_id"]: u for u in users}
    roster_by_id = {r["roster_id"]: r for r in rosters}

    def team_name(rid):
        u = user_by_id.get(roster_by_id[rid]["owner_id"], {})
        return ((u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Roster {rid}").strip()

    path = a.out or history_path(a.season)
    backfill(a.season, a.through, matchups, [r["roster_id"] for r in rosters], team_name, path=path)
    print(f"wrote weeks 0–{a.through} to {path}")


if __name__ == "__main__":
    main()
