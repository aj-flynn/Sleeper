#!/usr/bin/env python3
"""Pull one week of Rebuilders Anonymous data and write the data brief for that issue.

Two stages, so the network part is the only part that can change between runs:

    python3 newsletter/fetch_week.py --week 4            # fetch raw/ (skipped if already there), then build the brief
    python3 newsletter/fetch_week.py --week 4 --refresh  # fetch raw/ again even if it exists
    python3 newsletter/fetch_week.py --week 4 --brief-only   # rebuild brief.json/brief.md from raw/, no network

Sources (all public, no keys):
  Sleeper league API   https://api.sleeper.app/v1/league/<id>/...   league, users, rosters,
                       matchups (weeks 1..N and N+1), transactions (legs N and N+1)
  Sleeper players      https://api.sleeper.app/v1/players/nfl       names, positions, NFL teams,
                       injury status at fetch time (trimmed to the players the brief mentions)
  Sleeper stats        https://api.sleeper.com/stats/nfl/<season>/<week>   real box-score lines
  ESPN scoreboard      site.api.espn.com/.../nfl/scoreboard          NFL finals for week N, schedule N+1
  ESPN game summary    site.api.espn.com/.../nfl/summary?event=<id>  recap article, injury report,
                       scoring plays

fetch_raw() refuses to write anything until every NFL game of week N is final and every fantasy
matchup has a score, so a half-finished week can't produce a brief. build_brief() reads only raw/ and
is deterministic: the same raw/ always produces byte-identical brief.json and brief.md. Fantasy points
always come from the league's matchup data, because league scoring (e.g. -2 per interception) differs
from Sleeper's defaults. The brief also carries each team's Elo (see elo_ratings), which orders the
power rankings, and appends this week to newsletter/elo/<season>.json (see elo.record_week).
"""

import argparse
import datetime as dt
import html
import json
import re
import shutil
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path

LEAGUE_ID = "1319718857249665024"
SLEEPER = "https://api.sleeper.app/v1"
SLEEPER_STATS = "https://api.sleeper.com/stats/nfl/{season}/{week}?season_type=regular" + "".join(
    f"&position[]={p}" for p in ("QB", "RB", "WR", "TE", "K", "DEF")
)
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ROOT = Path(__file__).resolve().parent
ESPN_TO_SLEEPER = {"WSH": "WAS"}
META = "fetch_meta.json"


class WeekNotComplete(Exception):
    """The week still has games or fantasy matchups without a final score."""


def abbr(team):
    return ESPN_TO_SLEEPER.get(team["abbreviation"], team["abbreviation"])


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rebuilders-anonymous-newsletter"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def n(x):
    """Format a stat number without a trailing .0."""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def stat_line(pos, s):
    """A box-score line in plain words, e.g. '14 rec (16 tgt), 192 yds, 2 TD'."""
    if not s or not (s.get("gp") or s.get("gms_active")):
        return "did not play"
    g = lambda k: s.get(k, 0) or 0
    parts = []
    if pos == "DEF":
        parts.append(f"{n(g('pts_allow'))} pts allowed, {n(g('yds_allow'))} yds allowed")
        for k, label in (("sack", "sacks"), ("int", "INT"), ("fum_rec", "fumble rec"), ("def_td", "def TD"), ("st_td", "ST TD"), ("safe", "safety")):
            if g(k):
                unit = "sack" if k == "sack" and g(k) == 1 else label
                parts.append(f"{n(g(k))} {unit}")
        return ", ".join(parts)
    if pos == "K":
        line = f"FG {n(g('fgm'))}/{n(g('fga'))}"
        if g("fgm_lng"):
            line += f" (long {n(g('fgm_lng'))})"
        parts.append(line)
        if g("xpa"):
            parts.append(f"XP {n(g('xpm'))}/{n(g('xpa'))}")
        return ", ".join(parts)
    if g("pass_att"):
        p = f"{n(g('pass_cmp'))}/{n(g('pass_att'))}, {n(g('pass_yd'))} pass yds, {n(g('pass_td'))} TD"
        if g("pass_int"):
            p += f", {n(g('pass_int'))} INT"
        parts.append(p)
    if g("rush_att"):
        r = f"{n(g('rush_att'))} car, {n(g('rush_yd'))} rush yds"
        if g("rush_td"):
            r += f", {n(g('rush_td'))} TD"
        parts.append(r)
    if g("rec_tgt") or g("rec"):
        c = f"{n(g('rec'))} rec ({n(g('rec_tgt'))} tgt), {n(g('rec_yd'))} rec yds"
        if g("rec_td"):
            c += f", {n(g('rec_td'))} TD"
        parts.append(c)
    if g("fum_lost"):
        parts.append(f"{n(g('fum_lost'))} fumble lost")
    if not parts:
        parts.append("no stats")
    if g("off_snp") and g("tm_off_snp"):
        parts.append(f"{n(g('off_snp'))} of {n(g('tm_off_snp'))} snaps")
    return "; ".join(parts)


def plain(text):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


ELO_START, ELO_K = 1000.0, 32


def elo_ratings(matchups, roster_ids, through):
    """Standard Elo over the season's head-to-head results, weeks 1..through.

    Every team starts the season at 1000. For each game, expected = 1 / (1 + 10^((opp - own) / 400)),
    actual is 1 for a win, 0.5 for a tie, 0 for a loss, and the change is K * (actual - expected) with
    K = 32, rounded to two decimals. Margin of victory doesn't count. All of a week's changes apply at
    once, from the ratings both teams had going into that week.
    """
    rating = {rid: ELO_START for rid in roster_ids}
    history = {rid: [] for rid in roster_ids}
    change = {rid: 0.0 for rid in roster_ids}
    for w in range(1, through + 1):
        games = defaultdict(list)
        for m in matchups[w]:
            games[m["matchup_id"]].append(m)
        change = {rid: 0.0 for rid in roster_ids}
        for a, b in (g for g in games.values() if len(g) == 2):
            ra, rb = rating[a["roster_id"]], rating[b["roster_id"]]
            expected = 1 / (1 + 10 ** ((rb - ra) / 400))
            actual = 1.0 if a["points"] > b["points"] else 0.0 if a["points"] < b["points"] else 0.5
            d = round(ELO_K * (actual - expected), 2)
            change[a["roster_id"]], change[b["roster_id"]] = d, -d
        for rid in roster_ids:
            rating[rid] = round(rating[rid] + change[rid], 2)
            history[rid].append(rating[rid])
    return rating, change, history


def elo_table(matchups, rosters, standings, team_name, week):
    """The brief's Elo block, ordered the way the power rankings must be: Elo, then wins, then points for."""
    rating, change, history = elo_ratings(matchups, [r["roster_id"] for r in rosters], week)
    by_team = {t["team"]: t for t in standings}
    rows = []
    for r in rosters:
        rid = r["roster_id"]
        t = by_team[team_name(rid)]
        rows.append({"team": t["team"], "elo": rating[rid], "change": change[rid], "history": history[rid],
                     "record": t["record"], "w": t["w"], "pf": t["pf"]})
    rows.sort(key=lambda x: (-x["elo"], -x["w"], -x["pf"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return {"start": ELO_START, "k": ELO_K, "margin_of_victory": False, "through_week": week, "table": rows}


def espn_game(event, summary):
    """One NFL game as the brief stores it: final, venue, ESPN recap, scoring plays, injury report."""
    c = event["competitions"][0]
    home = next(t for t in c["competitors"] if t["homeAway"] == "home")
    away = next(t for t in c["competitors"] if t["homeAway"] == "away")
    art = summary.get("article") or {}
    g = {
        "espn_id": event["id"], "date_utc": event["date"],
        "away": abbr(away["team"]), "away_score": int(away["score"]),
        "home": abbr(home["team"]), "home_score": int(home["score"]),
        "status": c["status"]["type"]["description"],
        "venue": (c.get("venue") or {}).get("fullName"),
        "notes": [x.get("headline") for x in c.get("notes", []) if x.get("headline")],
        "recap_headline": art.get("headline"),
        "recap_text": plain(art.get("story")),
        "scoring_plays": [p.get("text") for p in summary.get("scoringPlays", [])],
        "injury_report": [
            {"team": abbr(t["team"]), "player": i["athlete"]["displayName"], "status": i.get("status"),
             "injury": (i.get("details") or {}).get("type")}
            for t in summary.get("injuries", []) for i in t.get("injuries", [])
        ],
    }
    w, l = (g["home"], g["away"]) if g["home_score"] > g["away_score"] else (g["away"], g["home"])
    g["final"] = f"{w} {max(g['home_score'], g['away_score'])}, {l} {min(g['home_score'], g['away_score'])}"
    return g


WAIVER_GRACE = dt.timedelta(hours=36)


def unfinished(scoreboard, week_matchups, next_leg=None, now=None):
    """Everything the issue still waits on: NFL games not final, fantasy matchups at zero, and the
    waiver run after the week (it shows up as waiver moves in leg N+1; a week with no claims at all
    counts as run 36 hours after the last kickoff)."""
    events = scoreboard.get("events", [])
    left = [f"{e.get('shortName', e['id'])} ({e['competitions'][0]['status']['type']['description']})"
            for e in events if not e["competitions"][0]["status"]["type"].get("completed")]
    if not events:
        left.append("ESPN lists no games for this week")
    if not week_matchups or any(not m.get("points") for m in week_matchups):
        left.append("Sleeper matchups without points")
    if not left and next_leg is not None and not any(t.get("type") == "waiver" for t in next_leg):
        last = max(dt.datetime.strptime(e["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc) for e in events)
        if (now or dt.datetime.now(dt.timezone.utc)) < last + WAIVER_GRACE:
            left.append(f"the waiver run after the week hasn't processed (no waiver moves yet; "
                        f"fetch after {(last + WAIVER_GRACE):%Y-%m-%d %H:%M} UTC if nobody bid)")
    return left


def raw_complete(raw, week, season, league):
    """True when raw/ already holds a finished fetch of this exact week, so a rerun can skip the network."""
    meta = raw / META
    if not meta.exists():
        return False
    m = load(meta)
    need = ["sleeper_league.json", "sleeper_users.json", "sleeper_rosters.json", "sleeper_players_rostered.json",
            f"sleeper_stats_w{week}.json", f"espn_games_w{week}.json", f"espn_scoreboard_w{week + 1}.json",
            f"sleeper_transactions_leg{week}.json", f"sleeper_transactions_leg{week + 1}.json"]
    need += [f"sleeper_matchups_w{w}.json" for w in range(1, week + 2)]
    return (m.get("week"), str(m.get("season")), m.get("league")) == (week, str(season), league) and all((raw / f).exists() for f in need)


def fetch_raw(week, season="2026", league=LEAGUE_ID, out=None, refresh=False):
    """Download week N into <out>/raw/. Returns 'cached' or 'fetched'. Raises WeekNotComplete before writing."""
    out = Path(out or ROOT / "issues" / f"{season}-week{week}")
    raw = out / "raw"
    if not refresh and raw_complete(raw, week, season, league):
        return "cached"
    L = f"{SLEEPER}/league/{league}"
    scoreboard = get(f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week}")
    matchups = {w: get(f"{L}/matchups/{w}") for w in range(1, week + 2)}
    transactions = {leg: get(f"{L}/transactions/{leg}") for leg in (week, week + 1)}
    left = unfinished(scoreboard, matchups[week], transactions[week + 1])
    if left:
        raise WeekNotComplete(f"week {week} is not ready: " + "; ".join(left))

    fetched_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    league_data = get(L)
    users = get(f"{L}/users")
    rosters = get(f"{L}/rosters")
    stats = get(SLEEPER_STATS.format(season=season, week=week))
    players_all = get(f"{SLEEPER}/players/nfl")
    next_board = get(f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week + 1}")
    games = [espn_game(e, get(f"{ESPN}/summary?event={e['id']}")) for e in scoreboard["events"]]

    rostered = {p for r in rosters for p in (r.get("players") or [])}
    for w in matchups.values():
        for m in w:
            rostered.update(m.get("players") or [])
    mentioned = rostered | {p for leg in transactions.values() for t in leg
                            for d in (t.get("adds") or {}, t.get("drops") or {}) for p in d}
    players = {pid: players_all[pid] for pid in sorted(mentioned) if pid in players_all}

    tmp = Path(tempfile.mkdtemp(prefix="raw-", dir=out.parent if out.parent.exists() else None))
    try:
        save(tmp / "sleeper_league.json", league_data)
        save(tmp / "sleeper_users.json", users)
        save(tmp / "sleeper_rosters.json", rosters)
        for w, m in matchups.items():
            save(tmp / f"sleeper_matchups_w{w}.json", m)
        for leg, t in transactions.items():
            save(tmp / f"sleeper_transactions_leg{leg}.json", t)
        save(tmp / f"sleeper_stats_w{week}.json",
             [s for s in stats if s["player_id"] in rostered or (s.get("stats") or {}).get("pts_ppr", 0) >= 15])
        save(tmp / "sleeper_players_rostered.json", players)
        save(tmp / f"espn_scoreboard_w{week}.json", scoreboard)
        save(tmp / f"espn_scoreboard_w{week + 1}.json", next_board)
        save(tmp / f"espn_games_w{week}.json", games)
        save(tmp / META, {"fetched_at": fetched_at, "season": str(season), "week": week, "league": league})
        out.mkdir(parents=True, exist_ok=True)
        if raw.exists():
            shutil.rmtree(raw)
        shutil.move(str(tmp), str(raw))
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    return "fetched"


def build_brief(out, week, season="2026", league=LEAGUE_ID):
    """Join raw/ into the brief. Reads no network and writes brief.json and brief.md deterministically."""
    out = Path(out)
    raw = out / "raw"
    r = lambda name: load(raw / name)
    league_data, users, rosters = r("sleeper_league.json"), r("sleeper_users.json"), r("sleeper_rosters.json")
    matchups = {w: r(f"sleeper_matchups_w{w}.json") for w in range(1, week + 2)}
    transactions = {leg: r(f"sleeper_transactions_leg{leg}.json") for leg in (week, week + 1)}
    stats = r(f"sleeper_stats_w{week}.json")
    players = r("sleeper_players_rostered.json")
    games = r(f"espn_games_w{week}.json")
    next_board = r(f"espn_scoreboard_w{week + 1}.json")
    if (raw / META).exists():
        fetched_at = r(META)["fetched_at"]
    elif (out / "brief.json").exists():
        fetched_at = load(out / "brief.json")["fetched_at"]
    else:
        fetched_at = "unknown"
    L = f"{SLEEPER}/league/{league}"

    user_by_id = {u["user_id"]: u for u in users}
    roster_by_id = {x["roster_id"]: x for x in rosters}

    def team_name(rid):
        u = user_by_id.get(roster_by_id[rid]["owner_id"], {})
        return ((u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Roster {rid}").strip()

    def manager(rid):
        return user_by_id.get(roster_by_id[rid]["owner_id"], {}).get("display_name")

    rostered = {p for x in rosters for p in (x.get("players") or [])}
    for w in matchups.values():
        for m in w:
            rostered.update(m.get("players") or [])
    stats_by_id = {s["player_id"]: s for s in stats}

    def pinfo(pid):
        p = players.get(pid) or {}
        if p.get("position") == "DEF" or pid.isalpha():
            return {"name": f"{pid} DEF", "pos": "DEF", "nfl_team": pid}
        return {"name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or pid,
                "pos": p.get("position"), "nfl_team": p.get("team"), "eligible": p.get("fantasy_positions")}

    game_by_team = {}
    for g in games:
        game_by_team[g["home"]] = game_by_team[g["away"]] = g

    def nfl_entry(pid, fpts):
        info = pinfo(pid)
        s = stats_by_id.get(pid)
        team = (s or {}).get("team") or info.get("nfl_team")
        game = game_by_team.get(team)
        line = stat_line(info["pos"], (s or {}).get("stats")) if s else ("bye week" if team and not game else "no stat record")
        return {**info, "player_id": pid, "fantasy_pts": round(fpts, 2), "line": line,
                "opponent": (s or {}).get("opponent"), "nfl_game": game["final"] if game else None}

    slots = [p for p in league_data["roster_positions"] if p != "BN"]
    by_mid = defaultdict(list)
    for m in matchups[week]:
        by_mid[m["matchup_id"]].append(m)
    fantasy = []
    for mid, pair in sorted(by_mid.items()):
        pair.sort(key=lambda m: -m["points"])
        sides = []
        for m in pair:
            pts = m.get("players_points") or {}
            starters = [dict(nfl_entry(p, pts.get(p, 0)), slot=slots[i] if i < len(slots) else None)
                        for i, p in enumerate(m["starters"])]
            bench = sorted((nfl_entry(p, pts.get(p, 0)) for p in m["players"] if p not in m["starters"]),
                           key=lambda x: -x["fantasy_pts"])
            sides.append({"team": team_name(m["roster_id"]), "manager": manager(m["roster_id"]),
                          "roster_id": m["roster_id"], "points": m["points"], "starters": starters,
                          "bench": bench, "bench_points": round(sum(b["fantasy_pts"] for b in bench), 2)})
        fantasy.append({"matchup_id": mid, "winner": sides[0], "loser": sides[1],
                        "margin": round(sides[0]["points"] - sides[1]["points"], 2)})

    # Standings computed from matchups so a late fetch can't leak later weeks
    table = {x["roster_id"]: {"team": team_name(x["roster_id"]), "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "results": []} for x in rosters}
    for w in range(1, week + 1):
        g = defaultdict(list)
        for m in matchups[w]:
            g[m["matchup_id"]].append(m)
        for a_, b_ in (v for v in g.values() if len(v) == 2):
            for me, them in ((a_, b_), (b_, a_)):
                t = table[me["roster_id"]]
                t["pf"] += me["points"]; t["pa"] += them["points"]
                res = "W" if me["points"] > them["points"] else "L" if me["points"] < them["points"] else "T"
                t[res.lower()] += 1; t["results"].append(res)
    standings = sorted(table.values(), key=lambda t: (-t["w"], -t["pf"]))
    for i, t in enumerate(standings, 1):
        t.update(rank=i, record=f"{t['w']}-{t['l']}" + (f"-{t['t']}" if t["t"] else ""), pf=round(t["pf"], 2), pa=round(t["pa"], 2))

    # Transactions: leg N is the week's moves; waivers that run after week N land in leg N+1. Leg N+1 is
    # cut off at week N+1's first kickoff so a late fetch doesn't pull next week's moves into this issue.
    next_kickoff = min((e["date"] for e in next_board["events"]), default="9999")
    cutoff_ms = dt.datetime.strptime(next_kickoff, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc).timestamp() * 1000 \
        if next_kickoff != "9999" else float("inf")

    def decode(t):
        names = lambda d: [{"player": pinfo(p)["name"], "pos": pinfo(p)["pos"], "team": team_name(rid)} for p, rid in (d or {}).items()]
        return {
            "type": t["type"], "status": t["status"], "leg": t.get("leg"),
            "processed_utc": dt.datetime.fromtimestamp(t["status_updated"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "teams": [team_name(rid) for rid in t["roster_ids"]],
            "adds": names(t.get("adds")), "drops": names(t.get("drops")),
            "faab_bid": (t.get("settings") or {}).get("waiver_bid"),
            "draft_picks": [{"season": p["season"], "round": p["round"], "original_team": team_name(p["roster_id"]),
                             "from": team_name(p["previous_owner_id"]), "to": team_name(p["owner_id"])} for p in t.get("draft_picks") or []],
            "faab_moved": t.get("waiver_budget") or [],
            "note": (t.get("metadata") or {}).get("notes"),
        }
    kept = [t for leg, ts in transactions.items() for t in ts if leg == week or t["status_updated"] < cutoff_ms]
    tx = sorted((decode(t) for t in kept), key=lambda t: t["processed_utc"])

    nb = defaultdict(list)
    for m in matchups[week + 1]:
        nb[m["matchup_id"]].append(team_name(m["roster_id"]))
    next_nfl = []
    for e in next_board["events"]:
        c = e["competitions"][0]
        home = abbr(next(t for t in c["competitors"] if t["homeAway"] == "home")["team"])
        away = abbr(next(t for t in c["competitors"] if t["homeAway"] == "away")["team"])
        next_nfl.append({"away": away, "home": home, "date_utc": e["date"], "venue": (c.get("venue") or {}).get("fullName"),
                         "notes": [x.get("headline") for x in c.get("notes", []) if x.get("headline")]})
    next_nfl.sort(key=lambda g: (g["date_utc"], g["away"]))
    playing = {t for g in next_nfl for t in (g["home"], g["away"])}
    all_teams = {g["home"] for g in games} | {g["away"] for g in games}

    injuries_now = sorted(
        ({"player": pinfo(pid)["name"], "pos": pinfo(pid)["pos"], "nfl_team": p.get("team"), "status": p.get("injury_status"),
          "body_part": p.get("injury_body_part"), "fantasy_team": next((team_name(x["roster_id"]) for x in rosters if pid in (x.get("players") or [])), None)}
         for pid, p in players.items() if pid in rostered and p.get("injury_status")),
        key=lambda x: (x["fantasy_team"] or "", x["player"]))

    # Record this week's Elo in the season history file. Reads weeks 0..N-1 from the
    # file and writes only week N. A past-week mismatch raises EloHistoryError.
    import elo
    elo.record_week(str(season), week, matchups, [x["roster_id"] for x in rosters], team_name)

    brief = {
        "league": {"name": league_data["name"], "league_id": league, "season": str(season), "week": week,
                   "roster_positions": league_data["roster_positions"],
                   "scoring": {k: league_data["scoring_settings"].get(k) for k in ("rec", "pass_td", "pass_yd", "pass_int", "rush_yd", "rec_yd", "fum_lost", "bonus_rec_te")},
                   "waiver_budget": league_data["settings"].get("waiver_budget")},
        "fetched_at": fetched_at,
        "sources": {
            "sleeper_league": f"{L} (+ /users, /rosters, /matchups/1..{week + 1}, /transactions/{week}, /transactions/{week + 1})",
            "sleeper_players": f"{SLEEPER}/players/nfl (trimmed to rostered players)",
            "sleeper_stats": SLEEPER_STATS.format(season=season, week=week),
            "espn_scoreboard": f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week} (and week {week + 1})",
            "espn_summaries": f"{ESPN}/summary?event=<id> for each week {week} game",
        },
        "teams": [{"team": team_name(x["roster_id"]), "manager": manager(x["roster_id"]), "roster_id": x["roster_id"],
                   "faab_used_at_fetch": x["settings"].get("waiver_budget_used")} for x in rosters],
        "standings": standings,
        "elo": elo_table(matchups, rosters, standings, team_name, week),
        "fantasy_matchups": fantasy,
        "nfl_games": games,
        "transactions": tx,
        "next_week": {"week": week + 1, "fantasy_matchups": [v for _, v in sorted(nb.items())], "nfl_games": next_nfl,
                      "nfl_byes": sorted(all_teams - playing)},
        "injury_status_at_fetch": injuries_now,
    }
    save(out / "brief.json", brief)
    (out / "brief.md").write_text(render_md(brief), encoding="utf-8")
    return brief


def render_md(b):
    L = b["league"]
    o = [f"# {L['name']} · {L['season']} Week {L['week']} data brief", "",
         f"Fetched {b['fetched_at']}. Every number in the issue must trace to this file or `brief.json`.", "",
         "## Sources", ""] + [f"- {k}: {v}" for k, v in b["sources"].items()]
    o += ["", "## Standings after this week", "", "| # | Team | W-L | PF | PA | Results |", "|---|---|---|---|---|---|"]
    o += [f"| {t['rank']} | {t['team']} | {t['record']} | {t['pf']:.2f} | {t['pa']:.2f} | {''.join(t['results'])} |" for t in b["standings"]]
    if "elo" in b:
        e = b["elo"]
        weeks = range(1, e["through_week"] + 1)
        o += ["", "## Elo after this week (power rankings order)", "",
              f"Every team starts the season at {e['start']:.0f}. K = {e['k']}, wins and losses only (margin of victory "
              "doesn't count). Change = K x (result - expected), expected = 1 / (1 + 10^((opponent - own) / 400)). "
              "Order: Elo, then wins, then points for.", "",
              "| # | Team | Elo | Change this week | Record | " + " | ".join(f"After W{w}" for w in weeks) + " |",
              "|---|---|---|---|---|" + "---|" * len(weeks)]
        o += [f"| {t['rank']} | {t['team']} | {t['elo']:.2f} | {t['change']:+.2f} | {t['record']} | "
              + " | ".join(f"{h:.2f}" for h in t["history"]) + " |" for t in e["table"]]
    o += ["", "## Fantasy matchups, with real stat lines", ""]
    for m in b["fantasy_matchups"]:
        w, l = m["winner"], m["loser"]
        o += [f"### {w['team']} {w['points']:.2f} def. {l['team']} {l['points']:.2f} (margin {m['margin']:.2f})", ""]
        for side in (w, l):
            o += [f"**{side['team']}** ({side['manager']}) starters:", ""]
            o += [f"- {p['slot']}: {p['name']} ({p['pos']}, {p['nfl_team']}) **{p['fantasy_pts']:.2f}** | {p['line']} | {p['nfl_game'] or 'no game'}" for p in side["starters"]]
            top = [p for p in side["bench"] if p["fantasy_pts"] > 0][:6]
            o += [f"- Bench ({side['bench_points']:.2f} total): " + "; ".join(f"{p['name']} ({p['pos']}) {p['fantasy_pts']:.2f} [{p['line']}]" for p in top), ""]
    o += ["## NFL games", ""]
    for g in b["nfl_games"]:
        o += [f"### {g['final']} ({g['away']} at {g['home']}, {g['venue']}{', ' + ', '.join(g['notes']) if g['notes'] else ''})", "",
              f"ESPN recap: {g['recap_headline']}", "", g["recap_text"], ""]
        inj = [i for i in g["injury_report"] if i["status"] in ("Out", "Doubtful", "Injured Reserve")]
        if inj:
            o += ["Pregame injury report (Out/Doubtful/IR): " + "; ".join(f"{i['player']} ({i['team']}) {i['status']}, {i['injury']}" for i in inj), ""]
    o += ["## Transactions (this week's leg and the waiver run after it)", ""]
    for t in b["transactions"]:
        bits = []
        if t["adds"]:
            bits.append("adds " + ", ".join(f"{x['player']} ({x['pos']}) to {x['team']}" for x in t["adds"]))
        if t["drops"]:
            bits.append("drops " + ", ".join(f"{x['player']} ({x['pos']}) from {x['team']}" for x in t["drops"]))
        if t["draft_picks"]:
            bits.append("picks " + ", ".join(f"{p['season']} round {p['round']} ({p['original_team']}'s) from {p['from']} to {p['to']}" for p in t["draft_picks"]))
        bid = f", bid ${t['faab_bid']}" if t["faab_bid"] is not None else ""
        o.append(f"- {t['processed_utc']} UTC, {t['type']} {t['status']} ({', '.join(t['teams'])}{bid}): {'; '.join(bits)}" + (f". Note: {t['note']}" if t["note"] and t["status"] == "failed" else ""))
    o += ["", "## FAAB used (at fetch time)", ""] + [f"- {t['team']}: ${t['faab_used_at_fetch']} of ${b['league']['waiver_budget']}" for t in b["teams"]]
    nw = b["next_week"]
    o += ["", f"## Week {nw['week']} fantasy matchups", ""] + [f"- {a} vs. {c}" for a, c in nw["fantasy_matchups"]]
    o += ["", f"## Week {nw['week']} NFL schedule", ""] + [f"- {g['away']} at {g['home']} ({g['date_utc'][:10]}, {g['venue']}{', ' + ', '.join(g['notes']) if g['notes'] else ''})" for g in nw["nfl_games"]]
    o += [f"- Byes: {', '.join(nw['nfl_byes']) or 'none'}", "", "## Injury status of rostered players at fetch time", ""]
    o += [f"- {i['player']} ({i['pos']}, {i['nfl_team']}), {i['fantasy_team'] or 'free agent'}: {i['status']}{', ' + i['body_part'] if i['body_part'] else ''}" for i in b["injury_status_at_fetch"]]
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--season", default="2026")
    ap.add_argument("--league", default=LEAGUE_ID)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--refresh", action="store_true", help="fetch raw/ again even if a complete fetch is already there")
    ap.add_argument("--brief-only", action="store_true", help="rebuild brief.json and brief.md from raw/ without the network")
    a = ap.parse_args()
    out = a.out or ROOT / "issues" / f"{a.season}-week{a.week}"
    if not a.brief_only:
        try:
            status = fetch_raw(a.week, a.season, a.league, out, a.refresh)
        except WeekNotComplete as e:
            raise SystemExit(f"fetch stopped: {e}")
        print(f"raw/: {status}")
    b = build_brief(out, a.week, a.season, a.league)
    print(f"wrote {out}/brief.json and brief.md ({len(b['fantasy_matchups'])} matchups, "
          f"{len(b['nfl_games'])} NFL games, {len(b['transactions'])} transactions)")


if __name__ == "__main__":
    main()
