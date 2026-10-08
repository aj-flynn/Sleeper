#!/usr/bin/env python3
"""Pull one week of Rebuilders Anonymous data and write the data brief for that issue.

    python3 newsletter/fetch_week.py --week 4
    python3 newsletter/fetch_week.py --week 5 --season 2026 --out newsletter/issues/2026-week5

Sources (all public, no keys):
  Sleeper league API   https://api.sleeper.app/v1/league/<id>/...   league, users, rosters,
                       matchups (weeks 1..N and N+1), transactions (legs N and N+1)
  Sleeper players      https://api.sleeper.app/v1/players/nfl       names, positions, NFL teams,
                       injury status at fetch time (trimmed to rostered players)
  Sleeper stats        https://api.sleeper.com/stats/nfl/<season>/<week>   real box-score lines
  ESPN scoreboard      site.api.espn.com/.../nfl/scoreboard          NFL finals for week N, schedule N+1
  ESPN game summary    site.api.espn.com/.../nfl/summary?event=<id>  recap article, injury report,
                       scoring plays

Writes <out>/raw/*.json (trimmed copies of what was pulled), <out>/brief.json (everything joined:
fantasy points next to the real stat line for every rostered player), and <out>/brief.md (the same
brief, readable). Fantasy points always come from the league's matchup data, because league scoring
(e.g. -2 per interception) differs from Sleeper's defaults.
"""

import argparse
import datetime as dt
import html
import json
import re
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


def abbr(team):
    return ESPN_TO_SLEEPER.get(team["abbreviation"], team["abbreviation"])


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rebuilders-anonymous-newsletter"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


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
                parts.append(f"{n(g(k))} {label}")
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--season", default="2026")
    ap.add_argument("--league", default=LEAGUE_ID)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    week, season = a.week, a.season
    out = a.out or ROOT / "issues" / f"{season}-week{week}"
    raw = out / "raw"
    fetched_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    L = f"{SLEEPER}/league/{a.league}"

    league = get(L)
    users = get(f"{L}/users")
    rosters = get(f"{L}/rosters")
    matchups = {w: get(f"{L}/matchups/{w}") for w in range(1, week + 2)}
    transactions = {leg: get(f"{L}/transactions/{leg}") for leg in (week, week + 1)}
    stats = get(SLEEPER_STATS.format(season=season, week=week))
    players_all = get(f"{SLEEPER}/players/nfl")
    scoreboard = get(f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week}")
    next_board = get(f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week + 1}")
    summaries = {e["id"]: get(f"{ESPN}/summary?event={e['id']}") for e in scoreboard["events"]}

    user_by_id = {u["user_id"]: u for u in users}
    roster_by_id = {r["roster_id"]: r for r in rosters}

    def team_name(rid):
        u = user_by_id.get(roster_by_id[rid]["owner_id"], {})
        return ((u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Roster {rid}").strip()

    def manager(rid):
        return user_by_id.get(roster_by_id[rid]["owner_id"], {}).get("display_name")

    rostered = {p for r in rosters for p in (r.get("players") or [])}
    for w in matchups.values():
        for m in w:
            rostered.update(m.get("players") or [])
    players = {pid: players_all[pid] for pid in rostered if pid in players_all}
    stats_by_id = {s["player_id"]: s for s in stats}

    def pinfo(pid):
        p = players.get(pid) or players_all.get(pid) or {}
        if p.get("position") == "DEF" or pid.isalpha():
            return {"name": f"{pid} DEF", "pos": "DEF", "nfl_team": pid}
        return {"name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or pid,
                "pos": p.get("position"), "nfl_team": p.get("team"), "eligible": p.get("fantasy_positions")}

    # NFL games for the week
    games, game_by_team = [], {}
    for e in scoreboard["events"]:
        c = e["competitions"][0]
        home = next(t for t in c["competitors"] if t["homeAway"] == "home")
        away = next(t for t in c["competitors"] if t["homeAway"] == "away")
        sm = summaries[e["id"]]
        art = sm.get("article") or {}
        g = {
            "espn_id": e["id"], "date_utc": e["date"],
            "away": abbr(away["team"]), "away_score": int(away["score"]),
            "home": abbr(home["team"]), "home_score": int(home["score"]),
            "status": c["status"]["type"]["description"],
            "venue": (c.get("venue") or {}).get("fullName"),
            "notes": [x.get("headline") for x in c.get("notes", []) if x.get("headline")],
            "recap_headline": art.get("headline"),
            "recap_text": plain(art.get("story")),
            "scoring_plays": [p.get("text") for p in sm.get("scoringPlays", [])],
            "injury_report": [
                {"team": abbr(t["team"]), "player": i["athlete"]["displayName"], "status": i.get("status"),
                 "injury": (i.get("details") or {}).get("type")}
                for t in sm.get("injuries", []) for i in t.get("injuries", [])
            ],
        }
        w, l = (g["home"], g["away"]) if g["home_score"] > g["away_score"] else (g["away"], g["home"])
        g["final"] = f"{w} {max(g['home_score'], g['away_score'])}, {l} {min(g['home_score'], g['away_score'])}"
        games.append(g)
        game_by_team[g["home"]] = game_by_team[g["away"]] = g

    def nfl_entry(pid, fpts):
        info = pinfo(pid)
        s = stats_by_id.get(pid)
        team = (s or {}).get("team") or info.get("nfl_team")
        game = game_by_team.get(team)
        line = stat_line(info["pos"], (s or {}).get("stats")) if s else ("bye week" if team and not game else "no stat record")
        return {**info, "player_id": pid, "fantasy_pts": round(fpts, 2), "line": line,
                "opponent": (s or {}).get("opponent"), "nfl_game": game["final"] if game else None}

    # Fantasy matchups for the week
    slots = [p for p in league["roster_positions"] if p != "BN"]
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
    table = {r["roster_id"]: {"team": team_name(r["roster_id"]), "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "results": []} for r in rosters}
    for w in range(1, week + 1):
        g = defaultdict(list)
        for m in matchups[w]:
            g[m["matchup_id"]].append(m)
        for a_, b_ in (v for v in g.values() if len(v) == 2):
            for me, them in ((a_, b_), (b_, a_)):
                t = table[me["roster_id"]]
                t["pf"] += me["points"]; t["pa"] += them["points"]
                r = "W" if me["points"] > them["points"] else "L" if me["points"] < them["points"] else "T"
                t[r.lower()] += 1; t["results"].append(r)
    standings = sorted(table.values(), key=lambda t: (-t["w"], -t["pf"]))
    for i, t in enumerate(standings, 1):
        t.update(rank=i, record=f"{t['w']}-{t['l']}" + (f"-{t['t']}" if t["t"] else ""), pf=round(t["pf"], 2), pa=round(t["pa"], 2))

    # Transactions: leg N is the week's moves; waivers that run after week N land in leg N+1
    def decode(t):
        names = lambda d: [{"player": pinfo(p)["name"], "pos": pinfo(p)["pos"], "team": team_name(r)} for p, r in (d or {}).items()]
        return {
            "type": t["type"], "status": t["status"], "leg": t.get("leg"),
            "processed_utc": dt.datetime.fromtimestamp(t["status_updated"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "teams": [team_name(r) for r in t["roster_ids"]],
            "adds": names(t.get("adds")), "drops": names(t.get("drops")),
            "faab_bid": (t.get("settings") or {}).get("waiver_bid"),
            "draft_picks": [{"season": p["season"], "round": p["round"], "original_team": team_name(p["roster_id"]),
                             "from": team_name(p["previous_owner_id"]), "to": team_name(p["owner_id"])} for p in t.get("draft_picks") or []],
            "faab_moved": t.get("waiver_budget") or [],
            "note": (t.get("metadata") or {}).get("notes"),
        }
    tx = sorted((decode(t) for leg in transactions.values() for t in leg), key=lambda t: t["processed_utc"])

    # Next week
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
    playing = {t for g in next_nfl for t in (g["home"], g["away"])}
    all_teams = {g["home"] for g in games} | {g["away"] for g in games}

    injuries_now = sorted(
        ({"player": pinfo(pid)["name"], "pos": pinfo(pid)["pos"], "nfl_team": p.get("team"), "status": p.get("injury_status"),
          "body_part": p.get("injury_body_part"), "fantasy_team": next((team_name(r["roster_id"]) for r in rosters if pid in (r.get("players") or [])), None)}
         for pid, p in players.items() if p.get("injury_status")),
        key=lambda x: (x["fantasy_team"] or "", x["player"]))

    brief = {
        "league": {"name": league["name"], "league_id": a.league, "season": season, "week": week,
                   "roster_positions": league["roster_positions"],
                   "scoring": {k: league["scoring_settings"].get(k) for k in ("rec", "pass_td", "pass_yd", "pass_int", "rush_yd", "rec_yd", "fum_lost", "bonus_rec_te")},
                   "waiver_budget": league["settings"].get("waiver_budget")},
        "fetched_at": fetched_at,
        "sources": {
            "sleeper_league": f"{L} (+ /users, /rosters, /matchups/1..{week + 1}, /transactions/{week}, /transactions/{week + 1})",
            "sleeper_players": f"{SLEEPER}/players/nfl (trimmed to rostered players)",
            "sleeper_stats": SLEEPER_STATS.format(season=season, week=week),
            "espn_scoreboard": f"{ESPN}/scoreboard?dates={season}&seasontype=2&week={week} (and week {week + 1})",
            "espn_summaries": f"{ESPN}/summary?event=<id> for each week {week} game",
        },
        "teams": [{"team": team_name(r["roster_id"]), "manager": manager(r["roster_id"]), "roster_id": r["roster_id"],
                   "faab_used_at_fetch": r["settings"].get("waiver_budget_used")} for r in rosters],
        "standings": standings,
        "fantasy_matchups": fantasy,
        "nfl_games": games,
        "transactions": tx,
        "next_week": {"week": week + 1, "fantasy_matchups": [v for _, v in sorted(nb.items())], "nfl_games": next_nfl,
                      "nfl_byes": sorted(all_teams - playing)},
        "injury_status_at_fetch": injuries_now,
    }

    save(raw / "sleeper_league.json", league)
    save(raw / "sleeper_users.json", users)
    save(raw / "sleeper_rosters.json", rosters)
    for w, m in matchups.items():
        save(raw / f"sleeper_matchups_w{w}.json", m)
    for leg, t in transactions.items():
        save(raw / f"sleeper_transactions_leg{leg}.json", t)
    save(raw / f"sleeper_stats_w{week}.json", [s for s in stats if s["player_id"] in rostered or (s.get("stats") or {}).get("pts_ppr", 0) >= 15])
    save(raw / "sleeper_players_rostered.json", players)
    save(raw / f"espn_scoreboard_w{week}.json", scoreboard)
    save(raw / f"espn_scoreboard_w{week + 1}.json", next_board)
    save(raw / f"espn_games_w{week}.json", [{k: g[k] for k in g} for g in games])
    save(out / "brief.json", brief)
    (out / "brief.md").write_text(render_md(brief), encoding="utf-8")
    print(f"wrote {out}/brief.json, brief.md, and raw/ ({len(fantasy)} matchups, {len(games)} NFL games, {len(tx)} transactions)")


def render_md(b):
    L = b["league"]
    o = [f"# {L['name']} · {L['season']} Week {L['week']} data brief", "",
         f"Fetched {b['fetched_at']}. Every number in the issue must trace to this file or `brief.json`.", "",
         "## Sources", ""] + [f"- {k}: {v}" for k, v in b["sources"].items()]
    o += ["", "## Standings after this week", "", "| # | Team | W-L | PF | PA | Results |", "|---|---|---|---|---|---|"]
    o += [f"| {t['rank']} | {t['team']} | {t['record']} | {t['pf']:.2f} | {t['pa']:.2f} | {''.join(t['results'])} |" for t in b["standings"]]
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


if __name__ == "__main__":
    main()
