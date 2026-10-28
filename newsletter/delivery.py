#!/usr/bin/env python3
"""Plain publication/chat state. This helper never publishes or sends a message itself."""
import argparse
from pathlib import Path
import sys
import json
import weekly

STATE = weekly.ROOT / "data" / "publication-state.json"


def update(path, season, week, action, url=None, receipt=None, draft=None, scheduled=False):
    if str(season) != "2026" and not str(season).isdigit():
        raise ValueError("Invalid season")
    if not 1<=int(week)<=18:
        raise ValueError("Invalid NFL week")
    key=f"{season}-week{int(week)}"
    with weekly.run_lock(path):
        state=weekly.load(path) if path.exists() else {"league_id":weekly.load(weekly.ROOT/"config.json")["league_id"],"issues":{}}
        if state["league_id"] != "1319718857249665024":
            raise ValueError("Delivery state is only for Rebuilders Anonymous")
        issue=state["issues"].get(key)
        if action=="status":
            return issue or {"state":"not_published"}
        if action=="published":
            if draft is None:
                raise ValueError("published requires --draft with the finalized issue data")
            metadata=weekly.load(draft/"draft.json")
            if metadata.get("provisional"):
                raise ValueError("Provisional 07:00 data cannot be published")
            if str(metadata["season"])!=str(season) or int(metadata["week"])!=int(week):
                raise ValueError("Draft season/week differs from delivery state")
            if weekly.instant(metadata["cutoff"]) > weekly.dt.datetime.now(weekly.UTC):
                raise ValueError("Reporting cutoff has not arrived")
            expected=f"https://aj-flynn.github.io/Sleeper/{season}-week{int(week)}.html"
            if url!=expected:
                raise ValueError(f"Use the issue's live Pages URL: {expected}")
            if issue is None:
                issue={"url":url,"scheduled":scheduled,"chat":{"status":"not_sent"}}
                state["issues"][key]=issue
            issue.update(url=url,published_at=weekly.iso(weekly.dt.datetime.now(weekly.UTC)))
            # An edit/redeployment keeps the original delivery status; it creates no new announcement.
        else:
            if issue is None:
                raise ValueError("Record successful Pages publication first")
            status=issue.get("chat",{}).get("status","not_sent")
            if action=="begin-chat":
                if status=="sent":
                    return {"action":"skip","reason":"already announced","url":issue["url"]}
                if not issue.get("scheduled"):
                    return {"action":"skip","reason":"historical issue or silent correction"}
                if status in ("sending","unknown"):
                    raise ValueError("Previous send outcome is uncertain; inspect Sleeper chat and report before retrying")
                issue["chat"]={"status":"sending","sender":"JeffyWaterton","started_at":weekly.iso(weekly.dt.datetime.now(weekly.UTC))}
            elif action in ("sent","unknown"):
                if status not in ("sending","unknown"):
                    raise ValueError("No in-progress chat send to complete")
                if not receipt:
                    raise ValueError("Provide the actual visible chat receipt or uncertainty reason")
                issue["chat"].update(status=action,receipt=receipt,updated_at=weekly.iso(weekly.dt.datetime.now(weekly.UTC)))
            else:
                raise ValueError("Unknown delivery action")
        weekly.save(path,state)
        return issue


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["status","published","begin-chat","sent","unknown"])
    parser.add_argument("--season",required=True)
    parser.add_argument("--week",type=int,required=True)
    parser.add_argument("--state",type=Path,default=STATE)
    parser.add_argument("--url")
    parser.add_argument("--receipt")
    parser.add_argument("--draft",type=Path)
    parser.add_argument("--scheduled",action="store_true",help="Only for a new issue from the Wednesday publication run")
    args=parser.parse_args()
    try:
        result=update(args.state,args.season,args.week,args.action,args.url,args.receipt,args.draft,args.scheduled)
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (ValueError,KeyError,OSError) as exc:
        print(json.dumps({"state":"blocked","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__=="__main__":sys.exit(main())
