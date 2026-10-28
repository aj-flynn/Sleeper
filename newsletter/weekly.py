#!/usr/bin/env python3
"""Portable newsletter data preparation and rendering. See WORKFLOW.md for scheduled publication."""
import argparse
from contextlib import contextmanager
import copy
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc


@contextmanager
def run_lock(out):
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = out.parent / ("." + out.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError(f"Run lock exists: {lock}; check PID before manually removing stale lock")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps({"pid":os.getpid(),"started":iso(dt.datetime.now(UTC))}))
        yield
    finally:
        lock.unlink()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encoded(data):
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = encoded(data)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                     delete=False, suffix=".tmp") as handle:
        handle.write(text)
    Path(handle.name).replace(path)


def instant(value):
    date = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Timestamp needs an explicit UTC offset")
    return date.astimezone(UTC)


def iso(date):
    return date.astimezone(UTC).isoformat().replace("+00:00", "Z")


def eastern_zone():
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        with (ROOT/"timezones/America_New_York.tzif").open("rb") as handle:
            return ZoneInfo.from_file(handle,key="America/New_York")


def window(cutoff=None, now=None):
    """Wednesday 08:00 local calendar boundaries, including 167/169-hour DST weeks."""
    zone = eastern_zone()
    if cutoff:
        end = instant(cutoff).astimezone(zone)
        if (end.weekday(), end.hour, end.minute, end.second, end.microsecond) != (2, 8, 0, 0, 0):
            raise ValueError("Cutoff must be Wednesday 08:00 America/New_York")
    else:
        current = (now or dt.datetime.now(UTC)).astimezone(zone)
        end = current.replace(hour=8, minute=0, second=0, microsecond=0)
        end -= dt.timedelta(days=(end.weekday() - 2) % 7)
        if end > current:
            end -= dt.timedelta(days=7)
    start = end - dt.timedelta(days=7)
    return start.astimezone(UTC), end.astimezone(UTC)


def theme_for(date):
    """Wednesday on or directly before a supported US holiday, in that calendar year."""
    year=date.year
    november=dt.date(year,11,1)
    thanksgiving=november+dt.timedelta(days=(3-november.weekday())%7+21)
    holidays={"halloween":dt.date(year,10,31),"thanksgiving":thanksgiving,"christmas":dt.date(year,12,25)}
    for theme,holiday in holidays.items():
        publication_day=holiday-dt.timedelta(days=(holiday.weekday()-2)%7)
        if date==publication_day:
            return theme
    return "regular"


def reporting_end(planned_end, provisional, capture=None, now=None):
    current=now or dt.datetime.now(UTC)
    if not provisional:
        if planned_end>current:
            raise ValueError("Future reporting cutoff refused; use --provisional for 07:00 preparation")
        return planned_end
    if capture:
        metadata=load(capture/"capture.json")
        if not metadata.get("provisional") or metadata.get("scheduled_cutoff")!=iso(planned_end):
            raise ValueError("Provisional capture belongs to another scheduled cutoff")
        return instant(metadata["coverage_end_exclusive"])
    return min(planned_end,current)


def request(url, body=None, headers=None, timeout=45, _redirects=0):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
        headers={"User-Agent": "rebuilders-newsletter/1", **(headers or {})})
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code not in (307,308) or _redirects >= 2:
            raise
        target = urllib.parse.urljoin(url,error.headers["Location"])
        if urllib.parse.urlsplit(target).netloc != urllib.parse.urlsplit(url).netloc:
            raise ValueError("Cross-host POST redirect refused") from error
        return request(target,body,headers,timeout,_redirects+1)
    with response:
        payload = response.read().decode("utf-8")
        if payload.lstrip().startswith("data:") or "\ndata:" in payload:
            payload = [line[5:].strip() for line in payload.splitlines() if line.startswith("data:")][-1]
        return json.loads(payload), dict(response.headers)


def board_done(board, cutoff):
    events = board.get("events", [])
    return bool(events) and all(instant(e["date"]) < cutoff and
        e["competitions"][0]["status"]["type"].get("completed") for e in events)


def latest_week(boards, cutoff):
    """Walk the regular season in order; a postponed unfinished week blocks advancement."""
    found = 0
    for week in sorted(boards):
        board = boards[week]
        if not board_done(board, cutoff):
            break
        found = week
    if not found:
        raise ValueError("No fully completed NFL week before cutoff; wait or inspect schedule")
    return found


def trim_board(board, future=False):
    result = {k: board[k] for k in ("season", "week") if k in board}
    events = []
    for event in board.get("events", []):
        e = {k: event[k] for k in ("id", "date", "shortName") if k in event}
        competitions = []
        for competition in event["competitions"]:
            c = {k: competition[k] for k in ("status", "venue", "notes") if k in competition}
            c["competitors"] = [{"homeAway": t["homeAway"], "team": {"abbreviation": t["team"]["abbreviation"]},
                **({"score": t.get("score", "0")} if not future else {})} for t in competition["competitors"]]
            if future:
                c.pop("status", None)
            competitions.append(c)
        e["competitions"] = competitions
        events.append(e)
    result["events"] = events
    return result


def collect(out, config, start, end, mcp_url):
    """Capture sources once. A partial attempt remains an inspectable capture, never a brief."""
    raw = out / "raw"
    if raw.exists():
        raise ValueError("Capture exists; use prepare to replay it, or a fresh --out for a refresh")
    raw.mkdir(parents=True)
    evidence = []
    season, league = config["season"], config["league_id"]
    sleeper = config["sleeper_api"]
    espn = config["espn_api"]

    def pull(name, url, transform=lambda x: x):
        data, _ = request(url)
        save(raw / name, transform(data))
        evidence[:] = [entry for entry in evidence if entry["file"] != name]
        evidence.append({"file": name, "url": url, "retrieved_utc": iso(dt.datetime.now(UTC)),
                         "representation": "selected public fields; see weekly.py"})
        save(out / "sources.json", {"sources": evidence})
        return load(raw / name)

    league_url = f"{sleeper}/league/{league}"
    league_data = pull("sleeper_league.json", league_url)
    if str(league_data["season"]) != str(season) or league_data["total_rosters"] != config["teams"]:
        raise ValueError("League season/size mismatch; configure season rollover explicitly")
    pull("sleeper_users.json", league_url + "/users", lambda users: [
        {"user_id": u["user_id"], "display_name": u.get("display_name"),
         "metadata": {"team_name": (u.get("metadata") or {}).get("team_name")}} for u in users])
    rosters = pull("sleeper_rosters.json", league_url + "/rosters")
    boards = {}
    # Query dates and final status, never derive the week from league.week or today's number.
    for week in range(1, config["regular_season_weeks"] + 2):
        boards[week] = pull(f"espn_scoreboard_w{week}.json",
            f"{espn}/scoreboard?dates={season}&seasontype=2&week={week}", trim_board)
        if not board_done(boards[week], end):
            break
    week = latest_week(boards, end)
    if week > config["regular_season_weeks"]:
        raise ValueError("Regular season is complete; use an explicit playoff/rollover plan")
    for w in range(1, week + 2):
        pull(f"sleeper_matchups_w{w}.json", league_url + f"/matchups/{w}",
             (lambda rows: [{"roster_id": m["roster_id"], "matchup_id": m["matchup_id"]} for m in rows])
             if w == week + 1 else lambda x: x)
    for leg in range(0, week + 2):
        pull(f"sleeper_transactions_leg{leg}.json", league_url + f"/transactions/{leg}")
    pull(f"espn_scoreboard_w{week+1}.json", f"{espn}/scoreboard?dates={season}&seasontype=2&week={week+1}",
         lambda x: trim_board(x, future=True))
    pull(f"sleeper_stats_w{week}.json", f"https://api.sleeper.com/stats/nfl/{season}/{week}?season_type=regular")
    mentioned = {p for roster in rosters for p in (roster.get("players") or [])}
    for p in raw.glob("sleeper_matchups*.json"):
        mentioned.update(pid for row in load(p) for pid in row.get("players", []))
    for p in raw.glob("sleeper_transactions*.json"):
        mentioned.update(pid for row in load(p) for key in ("adds", "drops") for pid in (row.get(key) or {}))
    fields = ("first_name", "last_name", "position", "team", "fantasy_positions")
    pull("sleeper_players_rostered.json", sleeper + "/players/nfl", lambda players: {
        pid: {key: player.get(key) for key in fields} for pid, player in players.items() if pid in mentioned})
    for event in boards[week]["events"]:
        pull(f"espn_summary_{event['id']}.json", espn + f"/summary?event={event['id']}",
             lambda x: {key: x[key] for key in ("article", "scoringPlays") if key in x})
    save(out / "capture.json", {"season": season, "league_id": league, "week": week,
        "coverage_start": iso(start), "coverage_end_exclusive": iso(end)})
    # Supplemental service; raw responses stay private and never silently become historical facts.
    mcp = {"url": mcp_url, "status": "unavailable", "limitations": []}
    if mcp_url:
        try:
            headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
            _, response_headers = request(mcp_url, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "newsletter", "version": "1"}}}, headers)
            session = next((v for k, v in response_headers.items() if k.lower() == "mcp-session-id"), None)
            if session:
                headers["Mcp-Session-Id"] = session
            # Notifications may legitimately have an empty response body.
            try:
                request(mcp_url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers)
            except json.JSONDecodeError:
                pass
            schema, _ = request(mcp_url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, headers)
            save(out / "mcp-tools.json", schema)
            available = {t["name"] for t in schema.get("result", {}).get("tools", [])}
            calls = [(f"get_usage_trends_roster{roster['roster_id']}","get_usage_trends",
                {"league_id":league,"roster_id":roster["roster_id"],"season":int(season),"through_week":week,"weeks":4}) for roster in rosters]
            calls += [("get_injury_trends","get_injury_trends",{"lookback_hours":math.ceil((dt.datetime.now(UTC)-start).total_seconds()/3600)}),
                      ("get_player_news","get_player_news",{"league_id":league,"days":math.ceil((dt.datetime.now(UTC)-start).total_seconds()/86400)})]
            for i, (filename,name,args) in enumerate(calls,3):
                if name in available:
                    response, _ = request(mcp_url, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                        "params": {"name": name, "arguments": args}}, headers)
                    save(out / "mcp" / f"{filename}.json", response)
                    structured=response.get("result",{}).get("structuredContent") or {}
                    if structured.get("success") is False or response.get("result",{}).get("isError"):
                        mcp["limitations"].append(f"{filename}: {structured.get('error','tool error')}")
                    mcp["limitations"].extend(structured.get("warnings") or [])
            mcp["status"] = "captured"
        except Exception as exc:
            mcp["limitations"].append(str(exc))
    mcp["limitations"].append("Timestamp-filter and verify player identity before using supplemental claims; empty feeds prove nothing")
    save(out / "mcp-status.json", mcp)
    return week


def transaction_ledger(raw, end):
    indexed = {}
    for path in sorted(raw.glob("sleeper_transactions_leg*.json")):
        for row in load(path):
            tid = str(row["transaction_id"])
            if tid in indexed and indexed[tid] != row:
                raise ValueError(f"Conflicting transaction {tid}; inspect source versions")
            indexed[tid] = row
    all_rows = sorted(indexed.values(), key=lambda t: (t["status_updated"], str(t["transaction_id"])))
    return [t for t in all_rows if t["status_updated"] < end.timestamp()*1000], all_rows


def games_and_totals(rows, expected):
    ids = [row["roster_id"] for row in rows]
    if len(set(ids)) != expected or len(ids) != expected:
        raise ValueError(f"Expected {expected} distinct rosters")
    pairs = {}
    for row in rows:
        score = row.get("points")
        starter_points = row.get("starters_points")
        if score is None or not math.isfinite(score) or starter_points is None:
            raise ValueError("Missing or non-finite fantasy score/starter totals")
        if len(row["starters"]) != len(starter_points) or abs(round(sum(starter_points), 2)-score) > 0.005:
            raise ValueError(f"Roster {row['roster_id']} starter sum does not match score")
        player_points = row.get("players_points") or {}
        for pid, points in zip(row["starters"], starter_points):
            if pid not in (None, "0") and (pid not in player_points or abs(player_points[pid]-points) > 0.005):
                raise ValueError(f"Roster {row['roster_id']} starter {pid} disagrees with players_points")
        if row["matchup_id"] is None:
            raise ValueError("Missing matchup ID")
        pairs.setdefault(row["matchup_id"], []).append(row)
    if len(pairs) != expected//2 or any(len(pair) != 2 for pair in pairs.values()):
        raise ValueError("Expected six complete two-team matchups")
    return pairs


def history(raw, week, config, baseline, end, sources):
    import elo
    expected = config["teams"]
    settings = load(raw / "sleeper_league.json")["settings"]
    if settings.get("league_average_match",0):
        raise ValueError("League median scoring enabled; explicit rules migration required")
    if week >= settings.get("playoff_week_start",99):
        raise ValueError("Playoffs require bracket-specific rules; regular-season ledger stopped")
    rosters, users = load(raw / "sleeper_rosters.json"), load(raw / "sleeper_users.json")
    names_by_owner = {u["user_id"]: (u.get("metadata") or {}).get("team_name") or u.get("display_name") for u in users}
    names = {r["roster_id"]: names_by_owner.get(r["owner_id"]) or f"Roster {r['roster_id']}" for r in rosters}
    ids = sorted(names)
    if len(ids) != expected:
        raise ValueError("Roster snapshot size mismatch")
    if str(baseline["season"]) != str(config["season"]) or baseline["league_id"] != config["league_id"]:
        raise ValueError("Elo baseline belongs to a different season/league")
    if baseline["k"] != 32 or baseline["start"] != 1000 or baseline["margin_of_victory"]:
        raise ValueError("Unexpected Elo configuration")
    if max(map(int,baseline["weeks"])) > week:
        raise ValueError("Baseline has later weeks; use a deliberate historical baseline for backfill")
    document = copy.deepcopy(baseline)
    if set(document["weeks"]["0"]) != {str(r) for r in ids}:
        raise ValueError("Elo roster identity mismatch")
    ratings = {r: 1000.0 for r in ids}
    standings = {r: {"roster_id": r, "team": names[r], "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "results": []} for r in ids}
    weeks = {}
    for w in range(1, week+1):
        rows = load(raw / f"sleeper_matchups_w{w}.json")
        pairs = games_and_totals(rows, expected)
        if set(row["roster_id"] for row in rows) != set(ids):
            raise ValueError("Matchup roster IDs changed")
        ratings, change = elo.apply_week(rows, ratings)
        key = str(w)
        if key in baseline["weeks"]:
            if any(abs(baseline["weeks"][key][str(r)]["elo"]-ratings[r]) > .005 for r in ids):
                raise ValueError(f"Elo history correction at week {w}; explicit correction required")
        else:
            document["weeks"][key] = {str(r): {"team": names[r], "elo": ratings[r]} for r in ids}
        results = []
        for mid, (a, b) in sorted(pairs.items()):
            for me, them in ((a,b),(b,a)):
                rid = me["roster_id"]
                result = "W" if me["points"] > them["points"] else "L" if me["points"] < them["points"] else "T"
                record = standings[rid]
                record[result.lower()] += 1
                record["pf"] = round(record["pf"] + me["points"], 2)
                record["pa"] = round(record["pa"] + them["points"], 2)
                record["results"].append(result)
                results.append({"roster_id": rid, "opponent_id": them["roster_id"], "matchup_id": mid,
                    "points": me["points"], "points_against": them["points"], "result": result,
                    "starter_total": round(sum(me["starters_points"]), 2), "elo": ratings[rid], "elo_change": change[rid]})
        weeks[key] = {"results": sorted(results, key=lambda r:r["roster_id"]),
                      "standings": sorted(copy.deepcopy(list(standings.values())), key=lambda r:(-r["w"]-.5*r["t"],-r["pf"],r["roster_id"]))}
        if abs(sum(ratings.values()) - 1000*expected) > .005:
            raise ValueError("Elo mass changed")
    tx, all_tx = transaction_ledger(raw, end)
    budget = load(raw / "sleeper_league.json")["settings"]["waiver_budget"]
    faab = {str(r): {"spent": 0, "net_transfers": 0, "remaining": budget} for r in ids}
    for move in tx:
        if move["status"] != "complete":
            continue
        if move["type"] == "waiver":
            bidders = set((move.get("adds") or {}).values())
            if not bidders and (move.get("settings") or {}).get("waiver_bid"):
                raise ValueError("Completed waiver with bid but no acquiring roster")
            for rid in bidders:
                faab[str(rid)]["spent"] += (move.get("settings") or {}).get("waiver_bid",0) or 0
        for transfer in move.get("waiver_budget") or []:
            faab[str(transfer["sender"])]["net_transfers"] -= transfer["amount"]
            faab[str(transfer["receiver"])]["net_transfers"] += transfer["amount"]
    # Reconcile API counter to captured moves, undoing any completed moves after cutoff.
    for adjustment in config.get("faab_adjustments",[]):
        if not adjustment.get("reason") or not adjustment.get("evidence"):
            raise ValueError("FAAB adjustment requires reason and evidence")
        if instant(adjustment["effective_at"]) < end:
            faab[str(adjustment["roster_id"])]["net_transfers"] += adjustment["amount"]
    for roster in rosters:
        rid = str(roster["roster_id"])
        row = faab[rid]
        row["remaining"] = budget-row["spent"]+row["net_transfers"]
        later_spend = sum((t.get("settings") or {}).get("waiver_bid",0) or 0 for t in all_tx
            if t["status"] == "complete" and t["type"] == "waiver" and t["status_updated"] >= end.timestamp()*1000
            and int(rid) in (t.get("adds") or {}).values())
        row["api_spent_at_fetch"] = roster["settings"].get("waiver_budget_used")
        row["reconciled"] = row["api_spent_at_fetch"] == row["spent"]+later_spend
        if not row["reconciled"]:
            raise ValueError(f"FAAB ledger incomplete for roster {rid}; inspect missing legs or commissioner adjustment")
    return {"schema": 1, "league_id": config["league_id"], "season": config["season"], "through_week": week,
        "cutoff": iso(end), "observation_kind":"retrospective_retrieval",
        "retrieved_utc":max(s["retrieved_utc"] for s in sources), "weeks": weeks, "elo": document, "transactions": tx, "faab": faab,
        "team_names_observed": [{"roster_id": rid, "team": names[rid], "observed_at": max(s["retrieved_utc"] for s in sources),
                                 "historical_effective_from": None} for rid in ids],
        "limitations": ["Earlier team-name effective dates unavailable; observed labels are not historical claims",
                         "IR/taxi history unavailable; retrospective live APIs may include later stat corrections"]}


def read_sources(folder):
    return load(folder / "sources.json")["sources"]


def _prepare(capture, out, config, start, end, baseline):
    import elo
    import fetch_week
    sources = read_sources(capture)
    metadata = load(capture / "capture.json")
    if (metadata["coverage_start"],metadata["coverage_end_exclusive"]) != (iso(start),iso(end)):
        raise ValueError("Capture belongs to a different reporting window")
    if metadata["league_id"] != config["league_id"] or str(metadata["season"]) != str(config["season"]):
        raise ValueError("Capture league/season mismatch")
    week = metadata["week"]
    original = capture / "raw"
    if not board_done(load(original / f"espn_scoreboard_w{week}.json"), end):
        raise ValueError("Selected NFL week not final before cutoff")
    if (original / f"espn_scoreboard_w{week+1}.json").exists() and board_done(load(original / f"espn_scoreboard_w{week+1}.json"),end):
        raise ValueError("Capture selected an older week although a later week is complete")
    # A late status read alone cannot prove a game finished before the historical cutoff.
    board_source = next((s for s in sources if s["file"] == f"espn_scoreboard_w{week}.json"),None)
    if board_source is None:
        raise ValueError("Selected scoreboard has no source evidence")
    if instant(board_source["retrieved_utc"]) > end:
        for event in load(original / f"espn_scoreboard_w{week}.json")["events"]:
            summary_path = original / f"espn_summary_{event['id']}.json"
            article = (load(summary_path).get("article") or {}) if summary_path.exists() else {}
            published = article.get("published")
            if article.get("type") != "Recap" or not published or instant(published) >= end:
                raise ValueError(f"Game {event['id']} lacks dated pre-cutoff final recap; historical completion uncertain")
    candidate = history(original, week, config, baseline, end, sources)
    before, all_moves = transaction_ledger(original, end)
    period = [t for t in before if t["status_updated"] >= start.timestamp()*1000]
    if any(t["status"] in ("pending", "queued") and t["type"] == "waiver" for t in before):
        raise ValueError("Waiver processing pending at cutoff; resolve before drafting")
    out.mkdir(parents=True,exist_ok=True)
    # Existing confirmed state is never a side effect of brief generation.
    with tempfile.TemporaryDirectory(prefix=".newsletter-raw-",dir=out.parent) as temporary:
        work = Path(temporary)
        raw = work / "raw"
        raw.mkdir()
        for p in original.glob("*.json"):
            shutil.copyfile(p, raw / p.name)
        rosters = load(raw / "sleeper_rosters.json")
        by_id = {r["roster_id"]: r for r in rosters}
        # Restore ownership as of cutoff; slots cannot be reconstructed and are not used.
        for t in reversed(all_moves):
            if t["status"] == "complete" and t["status_updated"] >= end.timestamp()*1000:
                for pid,rid in (t.get("adds") or {}).items():
                    by_id[rid]["players"] = [p for p in by_id[rid].get("players",[]) if p != pid]
                for pid,rid in (t.get("drops") or {}).items():
                    by_id[rid]["players"] = sorted(set(by_id[rid].get("players",[])+[pid]))
        save(raw / "sleeper_rosters.json",rosters)
        save(raw / f"sleeper_transactions_leg{week}.json",period)
        save(raw / f"sleeper_transactions_leg{week+1}.json",[])
        future = load(raw / f"sleeper_matchups_w{week+1}.json")
        save(raw / f"sleeper_matchups_w{week+1}.json",[{"roster_id":m["roster_id"],"matchup_id":m["matchup_id"]} for m in future])
        players = load(raw / "sleeper_players_rostered.json")
        for player in players.values():
            for key in list(player):
                if key.startswith("injury_"):
                    player.pop(key)
        save(raw / "sleeper_players_rostered.json",players)
        games, articles = [], []
        for event in load(raw / f"espn_scoreboard_w{week}.json")["events"]:
            path = raw / f"espn_summary_{event['id']}.json"
            summary = load(path) if path.exists() else {}
            article = summary.get("article") or {}
            timestamp = article.get("lastModified") or article.get("published")
            valid = timestamp and instant(timestamp) < end
            articles.append({"event_id":event["id"],"published":article.get("published"),
                "last_modified":article.get("lastModified"),"usable_as_of_cutoff":bool(valid)})
            if not valid:
                summary = {}
            summary.pop("injuries",None)
            game = fetch_week.espn_game(event,summary)
            # Scoring plays have no independent publication timestamps; actual game already final.
            games.append(game)
        save(raw / f"espn_games_w{week}.json",games)
        save(raw / "fetch_meta.json",{"fetched_at":max(s["retrieved_utc"] for s in sources)})
        old = elo.record_week
        try:
            elo.record_week = lambda *args,**kwargs: candidate["elo"]
            brief = fetch_week.build_brief(work,week,str(config["season"]),config["league_id"])
        finally:
            elo.record_week = old
    # Add continuity and cutoff context to the fact-checking brief.
    brief["coverage"] = {"start":iso(start),"end_exclusive":iso(end),"timezone":"America/New_York"}
    brief["faab_as_of_cutoff"] = candidate["faab"]
    brief["article_evidence"] = articles
    brief["limitations"] = candidate["limitations"] + ["Current injury snapshots excluded; use dated pre-cutoff reports",
        "Supplemental MCP responses require manual identity/timestamp verification before use"]
    save(out / "brief.json",brief)
    (out / "brief.md").write_text(fetch_week.render_md(brief),encoding="utf-8")
    save(out / "candidate-history.json",candidate)
    save(out / "elo.json",candidate["elo"])
    save(out / "period-transactions.json",{"completed":[t for t in period if t["status"]=="complete"],
        "failed_bids":[t for t in period if t["type"]=="waiver" and t["status"]=="failed"],
        "other_statuses":[t for t in period if t["status"] not in ("complete","failed")]})
    save(out / "draft.json",{"season":config["season"],"week":week,"cutoff":iso(end),
        "theme":"regular","provisional":metadata.get("provisional",False),
        "scheduled_cutoff":metadata.get("scheduled_cutoff",iso(end)),"capture":os.path.relpath(capture,out)})
    return {"week":week,"rosters":config["teams"],"elo_sum":round(sum(row["elo"] for row in candidate["elo"]["weeks"][str(week)].values()),2),
            "period_completed":sum(t["status"]=="complete" for t in period),"period_failed":sum(t["status"]=="failed" for t in period)}


def prepare(capture, out, config, start, end, baseline):
    """Publish a complete draft directory atomically; retries compare, never double-count."""
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".weekly-stage-",dir=out.parent) as name:
        staging = Path(name) / out.name
        result = _prepare(capture,staging,config,start,end,baseline)
        metadata = load(staging/"draft.json")
        metadata["capture"] = os.path.relpath(Path(capture).resolve(),out)
        save(staging/"draft.json",metadata)
        if out.exists():
            for file in ("brief.json","brief.md","candidate-history.json","elo.json","period-transactions.json"):
                if not (out/file).exists() or (out/file).read_bytes() != (staging/file).read_bytes():
                    raise ValueError("Draft differs or is partial; use a new revision directory and inspect the changes")
            result["rerun"] = "identical_existing_draft_preserved"
        else:
            staging.replace(out)
        return result


def render_issue(folder, theme="auto", trial=False):
    import build
    import elo
    issue = load(folder / "issue.json")
    metadata = load(folder / "draft.json")
    if (issue.get("preview") or {}).get("is_sample"):
        raise ValueError("Upcoming matchups are placeholders; obtain the actual schedule")
    if theme=="auto":
        theme=theme_for(instant(metadata.get("scheduled_cutoff",metadata["cutoff"])).astimezone(eastern_zone()).date())
    if int(issue["meta"]["week"]) != metadata["week"] or str(issue["meta"]["season"]) != str(metadata["season"]):
        raise ValueError("Issue week/season differs from its data")
    old = elo.history_path
    try:
        elo.history_path = lambda season: folder / "elo.json"
        problems = build.schema_problems(issue) + build.check_facts(folder/"issue.json") + build.lint(issue,legacy_average=False)
        if problems:
            raise ValueError("\n".join(problems))
        html = build.render(build.derive(issue),theme="regular")
        if theme in ("thanksgiving","christmas","halloween"):
            directory=ROOT/"themes"/theme
            if theme == "halloween":
                directory=directory/"redesign"
            css=(directory/"theme.css").read_text(encoding="utf-8")
            for asset in ("background.svg","field-pattern.svg","corner.svg"):
                graphic=(directory/asset).read_text(encoding="utf-8")
                css=css.replace(f'url("{asset}")','url("data:image/svg+xml,'+urllib.parse.quote(graphic,safe='')+'")')
            left=(directory/"margin-left.svg").read_text(encoding="utf-8")
            right=(directory/"margin-right.svg").read_text(encoding="utf-8")
            html=html.replace("</style>",css+"\n</style>",1)
            html=html.replace("<body>",f'<body><div class="season-margins" aria-hidden="true"><div class="margin-scene margin-left">{left}</div><div class="margin-scene margin-right">{right}</div></div>',1)
    finally:
        elo.history_path = old
    text = re.sub(r"<[^>]+>"," ",html)
    if "<footer" in html or re.search(r",\s*,|DEF DEF|DEF \(DEF\)",text):
        raise ValueError("Visible footer or malformed player metadata")
    (folder / "issue.html").write_text(html,encoding="utf-8",newline="\n")
    metadata.update(theme=theme,trial=trial)
    save(folder/"draft.json",metadata)
    return {"state":"draft_ready","path":str(folder/"issue.html")}


def record_history(folder,config):
    """Persist season data once per roster/week."""
    if load(folder/"draft.json").get("provisional"):
        raise ValueError("Provisional preparation cannot update the final season ledger")
    candidate=load(folder/"candidate-history.json")
    destination=ROOT/"data"/str(config["season"])/"history.json"
    with run_lock(destination):
        if destination.exists():
            previous=load(destination)
            if previous["through_week"] > candidate["through_week"]:
                raise ValueError("A newer week is already recorded")
            for week,old in previous["weeks"].items():
                if old["results"] != candidate["weeks"][week]["results"]:
                    raise ValueError(f"Recorded results changed at week {week}; use correction/backfill instructions")
                candidate["weeks"][week]=old
            observations=previous.get("team_names_observed",[])
            latest={row["roster_id"]:row["team"] for row in observations}
            candidate["team_names_observed"]=observations+[row for row in candidate["team_names_observed"] if latest.get(row["roster_id"])!=row["team"]]
        save(destination,candidate)
        save(ROOT/"elo"/f"{config['season']}.json",candidate["elo"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=["capture","prepare","render"])
    parser.add_argument("--config",type=Path,default=ROOT/"config.json")
    parser.add_argument("--cutoff",help="Wednesday 08:00 Eastern, ISO timestamp with offset; defaults latest past boundary")
    parser.add_argument("--capture",type=Path,help="Immutable capture folder for offline prepare")
    parser.add_argument("--out",type=Path,required=True,help="Explicit draft directory; never the website root")
    parser.add_argument("--baseline",type=Path,default=ROOT/"elo/2026.json")
    parser.add_argument("--mcp-url",default=os.environ.get("NFL_MCP_URL","http://127.0.0.1:9000/mcp/"))
    parser.add_argument("--theme",choices=["auto","regular","halloween","thanksgiving","christmas"],default="auto")
    parser.add_argument("--trial",action="store_true",help="Render an explicitly requested holiday comparison")
    parser.add_argument("--record",action="store_true",help="prepare: save validated weekly data to the season ledger")
    parser.add_argument("--provisional",action="store_true",help="07:00 preparation only; requires the upcoming Wednesday cutoff")
    args = parser.parse_args()
    try:
        config = load(args.config)
        start,planned_end = window(args.cutoff)
        if args.provisional and (not args.cutoff or args.record):
            raise ValueError("Provisional preparation requires --cutoff and cannot --record")
        end=reporting_end(planned_end,args.provisional,args.capture if args.stage=="prepare" else None)
        with run_lock(args.out):
            if args.stage == "capture":
                result = {"week":collect(args.out,config,start,end,args.mcp_url),"next":"prepare"}
                if args.provisional:
                    metadata=load(args.out/"capture.json")
                    metadata.update(provisional=True,scheduled_cutoff=iso(planned_end))
                    save(args.out/"capture.json",metadata)
                    result["provisional"]=True
            elif args.stage == "prepare":
                if not args.capture:
                    parser.error("prepare requires --capture")
                result = prepare(args.capture,args.out,config,start,end,load(args.baseline))
                if args.record:
                    record_history(args.out,config)
            else:
                result = render_issue(args.out,args.theme,args.trial)
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,KeyError,OSError) as exc:
        print(json.dumps({"state":"blocked","reason":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
