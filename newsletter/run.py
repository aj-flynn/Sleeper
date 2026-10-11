#!/usr/bin/env python3
"""One entry point for the Rebuilders Anonymous newsletter pipeline.

    python3 newsletter/run.py --week 5              # every stage in order; stops at the first gate that isn't a pass
    python3 newsletter/run.py fetch --week 5        # or one stage at a time
    python3 newsletter/run.py brief --week 5
    python3 newsletter/run.py check-brief --week 5
    python3 newsletter/run.py check-issue --week 5          # the writer's gate: schema, lint, facts
    python3 newsletter/run.py record-review --week 5 --from /tmp/editor-verdict.json
    python3 newsletter/run.py check-review --week 5         # the editor's gate, then the writer's revision gate
    python3 newsletter/run.py render --week 5
    python3 newsletter/run.py verify --week 5               # headless phone/desktop checks and screenshots
    python3 newsletter/run.py checklist --week 5
    python3 newsletter/run.py approval --week 5             # the owner's PR approval, read from GitHub
    python3 newsletter/run.py handoff --agent writer --week 5   # print exactly what to give a subagent

Every stage ends in named gates. Each gate's result, a timestamp, the command that reproduces it,
and machine-readable details go into newsletter/issues/<season>-week<N>/verification.json.

Exit codes: 0 every gate so far passed (a full run then waits only on the owner), 1 a gate failed,
3 waiting on a model step (the writer's issue.json or the editor's verdict isn't there yet).
Rerunning is safe: fetch is skipped when raw/ already holds the finished week (use --refresh to
pull again), and the brief and HTML rebuild byte for byte from the same inputs.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import fetch_week  # noqa: E402

AGENTS = REPO / ".cursor" / "agents"
PROTECTED = ["2026-week2.html", "rebuilders-anonymous-draft-review.html", "README.md",
             "newsletter/templates/card-back.html", "newsletter/fonts"]
SHOTS = ["phone-first-screen.png", "phone-full.png", "desktop-first-screen.png", "desktop-full.png"]
WAITING, FAILED = 3, 1

# step, owner, gates. The owner is who produces the step's output; every gate is checked by a script.
STEPS = [
    ("fetch", "script", ["fetch.week_final"]),
    ("brief", "script", ["brief.reproducible"]),
    ("check-brief", "script", ["brief.valid"]),
    ("write", "writer (claude-opus-5-5)", ["issue.present", "issue.schema", "issue.lint", "issue.facts"]),
    ("review", "editor (claude-sonnet-5-5)", ["review.verdict"]),
    ("revise", "writer (claude-opus-5-5)", ["review.addressed"]),
    ("render", "script", ["render.reproducible"]),
    ("verify", "script", ["html.phone", "html.desktop", "html.screenshots"]),
    ("checklist", "script", ["checklist.final"]),
    ("approve", "human (owner)", ["owner.approved"]),
]
OWNER = {g: owner for _, owner, gates in STEPS for g in gates}
STEP = {g: step for step, _, gates in STEPS for g in gates}


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def agent_model(name):
    """The model pinned in .cursor/agents/<name>.md frontmatter."""
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    front = re.match(r"---\n(.*?)\n---", text, re.S)
    m = re.search(r"^model:\s*(\S+)\s*$", front.group(1) if front else "", re.M)
    return m.group(1) if m else None


class Run:
    def __init__(self, week, season, out=None):
        self.week, self.season = week, str(season)
        self.dir = Path(out or HERE / "issues" / f"{self.season}-week{week}")
        self.ver = self.dir / "verification.json"
        self.base = f"python3 newsletter/run.py {{}} --week {week}" + ("" if self.season == "2026" else f" --season {self.season}")
        old = load(self.ver) if self.ver.exists() else {}
        self.gates = {g["gate"]: g for g in old.get("gates", [])}
        self.next_action = None

    @property
    def issue(self):
        return self.dir / "issue.json"

    def cmd(self, stage):
        return self.base.format(stage)

    def record(self, gate, status, stage, details=None, next_action=None):
        self.gates[gate] = {"gate": gate, "step": STEP[gate], "owner": OWNER[gate], "status": status,
                            "checked_at": now(), "command": self.cmd(stage), "details": details}
        if status != "pass" and next_action:
            self.next_action = next_action
        mark = {"pass": "PASS", "fail": "FAIL", "waiting": "WAIT", "pending": "PEND"}[status]
        print(f"[{mark}] {gate}" + (f"  {next_action}" if status != "pass" and next_action else ""))
        if status == "fail" and isinstance(details, list):
            for d in details[:40]:
                print(f"         {d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)}")
        return status

    def save(self, stopped_at=None):
        order = [g for _, _, gates in STEPS for g in gates]
        gates = [self.gates[g] for g in order if g in self.gates]
        statuses = {g["status"] for g in gates if g["gate"] != "owner.approved"}
        result = "fail" if "fail" in statuses else "waiting" if "waiting" in statuses else "pass"
        self.dir.mkdir(parents=True, exist_ok=True)
        doc = {
            "issue": f"{self.season}-week{self.week}", "season": self.season, "week": self.week,
            "updated_at": now(), "result": result, "stopped_at": stopped_at, "next_action": self.next_action,
            "models": {"writer": agent_model("writer"), "editor": agent_model("editor")},
            "artifacts": {f: sha(self.dir / f) for f in ("brief.json", "brief.md", "issue.json", "review.json", "writer.json", "issue.html")},
            "gates": gates,
        }
        self.ver.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- stages

def stage_fetch(run, refresh=False):
    try:
        status = fetch_week.fetch_raw(run.week, run.season, out=run.dir, refresh=refresh)
    except fetch_week.WeekNotComplete as e:
        return run.record("fetch.week_final", "fail", "fetch", [str(e)],
                          f"Week {run.week} isn't ready (see details). Rerun after Monday night's game and the Wednesday waiver run.")
    except OSError as e:
        return run.record("fetch.week_final", "fail", "fetch", [f"network: {e}"], "A source didn't answer; rerun the fetch.")
    meta = load(run.dir / "raw" / fetch_week.META)
    return run.record("fetch.week_final", "pass", "fetch", {"raw": status, "fetched_at": meta["fetched_at"]})


def stage_brief(run):
    if not (run.dir / "raw").exists():
        return run.record("brief.reproducible", "fail", "brief", ["no raw/ folder"], "Run the fetch first.")
    fetch_week.build_brief(run.dir, run.week, run.season)
    first = (sha(run.dir / "brief.json"), sha(run.dir / "brief.md"))
    fetch_week.build_brief(run.dir, run.week, run.season)
    second = (sha(run.dir / "brief.json"), sha(run.dir / "brief.md"))
    ok = first == second
    return run.record("brief.reproducible", "pass" if ok else "fail", "brief",
                      {"brief.json": second[0], "brief.md": second[1]} if ok else ["two builds from the same raw/ differ"],
                      "The brief builder is not deterministic; fix fetch_week.build_brief.")


def brief_problems(run):
    b = load(run.dir / "brief.json")
    p = []
    teams = {t["team"] for t in b["teams"]}
    if len(teams) != 12:
        p.append(f"expected 12 teams, found {len(teams)}")
    ms = b["fantasy_matchups"]
    if len(ms) != 6:
        p.append(f"expected 6 fantasy matchups, found {len(ms)}")
    for m in ms:
        w, l = m["winner"], m["loser"]
        if w["points"] < l["points"] or abs(round(w["points"] - l["points"], 2) - m["margin"]) > 0.005:
            p.append(f"matchup {m['matchup_id']}: margin {m['margin']} doesn't match {w['points']} - {l['points']}")
        for side in (w, l):
            total = round(sum(s["fantasy_pts"] for s in side["starters"]), 2)
            if abs(total - side["points"]) > 0.02:
                p.append(f"{side['team']}: starters add up to {total}, team score is {side['points']}")
    st = b["standings"]
    if sum(t["w"] for t in st) != sum(t["l"] for t in st):
        p.append("standings: wins and losses don't balance")
    if abs(sum(t["pf"] for t in st) - sum(t["pa"] for t in st)) > 0.05:
        p.append("standings: points for and against don't balance")
    if any(len(t["results"]) != run.week for t in st):
        p.append(f"standings: every team should have {run.week} results")
    raw = run.dir / "raw"
    matchups = {w: load(raw / f"sleeper_matchups_w{w}.json") for w in range(1, run.week + 1)}
    rosters = load(raw / "sleeper_rosters.json")
    rating, change, _ = fetch_week.elo_ratings(matchups, [r["roster_id"] for r in rosters], run.week)
    if sorted(rating.values()) != sorted(t["elo"] for t in b["elo"]["table"]):
        p.append("elo: the brief's ratings don't match a fresh computation from raw/ matchups")
    if abs(sum(change.values())) > 0.011:
        p.append("elo: this week's changes don't sum to zero")
    order = [(-t["elo"], -t["w"], -t["pf"]) for t in b["elo"]["table"]]
    if order != sorted(order) or [t["rank"] for t in b["elo"]["table"]] != list(range(1, 13)):
        p.append("elo: table is not in Elo, wins, points-for order")
    not_final = [g["final"] for g in b["nfl_games"] if g["status"] != "Final"]
    if not_final:
        p.append(f"NFL games not final: {not_final}")
    if len(b["next_week"]["fantasy_matchups"]) != 6:
        p.append("next week: expected 6 fantasy pairings")
    if (run.dir / "brief.md").read_text(encoding="utf-8") != fetch_week.render_md(b):
        p.append("brief.md doesn't match brief.json; rebuild the brief instead of editing it")
    return p


def stage_check_brief(run):
    if not (run.dir / "brief.json").exists():
        return run.record("brief.valid", "fail", "check-brief", ["no brief.json"], "Run the brief stage first.")
    p = brief_problems(run)
    b = load(run.dir / "brief.json")
    missing_lines = sum(1 for m in b["fantasy_matchups"] for s in (m["winner"], m["loser"]) for x in s["starters"] if x["line"] == "no stat record")
    return run.record("brief.valid", "fail" if p else "pass", "check-brief",
                      p or {"teams": 12, "matchups": 6, "nfl_games": len(b["nfl_games"]), "transactions": len(b["transactions"]),
                            "starters_without_stat_record": missing_lines},
                      "Fix the fetcher or rerun it; never edit the brief by hand.")


def stage_check_issue(run):
    if not run.issue.exists():
        return run.record("issue.present", "waiting", "check-issue", [f"{run.issue} doesn't exist yet"],
                          f"Hand off to the writer subagent: {run.cmd('handoff --agent writer')}")
    try:
        data = load(run.issue)
    except json.JSONDecodeError as e:
        return run.record("issue.present", "fail", "check-issue", [f"issue.json is not valid JSON: {e}"], "Writer: fix the JSON.")
    run.record("issue.present", "pass", "check-issue", {"issue.json": sha(run.issue)})
    results = []
    for gate, problems in (("issue.schema", build.schema_problems(data)), ("issue.lint", build.lint(data)),
                           ("issue.facts", build.check_facts(run.issue))):
        results.append(run.record(gate, "fail" if problems else "pass", "check-issue",
                                  problems or {"problems": 0}, "Writer: fix every listed problem in issue.json, then rerun."))
    return "fail" if "fail" in results else "pass"


REVIEW_NOTE_KEYS = {"id", "severity", "section", "problem", "fix"}


def review_shape(review):
    p = []
    if review.get("verdict") not in ("approve", "revise"):
        p.append("verdict must be 'approve' or 'revise'")
    notes = review.get("notes")
    if not isinstance(notes, list):
        return p + ["notes must be a list"]
    ids = [n.get("id") for n in notes]
    if len(set(ids)) != len(ids):
        p.append("note ids must be unique")
    for n in notes:
        missing = REVIEW_NOTE_KEYS - set(n)
        if missing:
            p.append(f"note {n.get('id', '?')}: missing {sorted(missing)}")
        if n.get("severity") not in ("blocking", "non-blocking"):
            p.append(f"note {n.get('id', '?')}: severity must be 'blocking' or 'non-blocking'")
    blocking = [n for n in notes if n.get("severity") == "blocking"]
    if (review.get("verdict") == "approve") != (not blocking):
        p.append("verdict must be 'approve' exactly when there are no blocking notes")
    return p + voice_fidelity_shape(review.get("voice_fidelity"), {n.get("id") for n in blocking})


VOICE_GUIDE = ".cursor/skills/newsletter/voice/boston-connor.md"
FIDELITY = REPO / ".cursor" / "skills" / "newsletter" / "reference" / "voice-fidelity.md"
UNITS = ["lead"] + [f"recaps[{i}]" for i in range(1, 7)]


def voice_items():
    """The guide items the editor must check, read from the table in reference/voice-fidelity.md."""
    text = FIDELITY.read_text(encoding="utf-8")
    block = re.search(r"<!-- voice-items:start -->(.*?)<!-- voice-items:end -->", text, re.S).group(1)
    return re.findall(r"^\| `([\w.]+)` \|", block, re.M)


def voice_fidelity_shape(vf, blocking_ids):
    """Every guide item has a pass or miss with evidence; every miss points at a blocking note."""
    if not isinstance(vf, dict):
        return ["voice_fidelity section is missing (see reference/voice-fidelity.md)"]
    p = []
    if vf.get("guide") != VOICE_GUIDE:
        p.append(f"voice_fidelity.guide must be {VOICE_GUIDE}")
    items = {i.get("id"): i for i in vf.get("items") or [] if isinstance(i, dict)}
    for item_id in voice_items():
        it = items.get(item_id)
        if not it:
            p.append(f"voice_fidelity: no result for {item_id}")
            continue
        if it.get("result") not in ("pass", "miss") or not it.get("evidence"):
            p.append(f"voice_fidelity {item_id}: needs result 'pass' or 'miss' and evidence")
        if it.get("result") == "miss" and not set(it.get("note_ids") or []) & blocking_ids:
            p.append(f"voice_fidelity {item_id}: a miss must cite at least one blocking note")
    units = {u.get("unit"): u for u in (items.get("delivery") or {}).get("units") or [] if isinstance(u, dict)}
    for unit in UNITS:
        u = units.get(unit)
        if not u:
            p.append(f"voice_fidelity delivery: no check for {unit}")
            continue
        steps = u.get("steps") or {}
        if u.get("result") == "pass" and not all(steps.get(str(s)) for s in range(1, 6)):
            p.append(f"voice_fidelity delivery {unit}: a pass needs a quote for each of steps 1-5")
        if u.get("result") == "miss" and not set(u.get("note_ids") or []) & blocking_ids:
            p.append(f"voice_fidelity delivery {unit}: a miss must cite at least one blocking note")
        if u.get("result") not in ("pass", "miss"):
            p.append(f"voice_fidelity delivery {unit}: result must be 'pass' or 'miss'")
    if any(u.get("result") == "miss" for u in units.values()) and (items.get("delivery") or {}).get("result") != "miss":
        p.append("voice_fidelity delivery: a unit missed, so the item is a miss")
    return p


def stage_record_review(run, source):
    """Save the editor's verdict as review.json, stamped with the issue it reviewed and the editor's model."""
    text = Path(source).read_text(encoding="utf-8") if source != "-" else sys.stdin.read()
    m = re.search(r"\{.*\}", text, re.S)
    review = json.loads(m.group(0)) if m else {}
    problems = review_shape(review)
    if problems:
        for x in problems:
            print(f"review: {x}")
        sys.exit(FAILED)
    out = run.dir / "review.json"
    rnd = 1
    if out.exists():
        old = load(out)
        rnd = old.get("round", 1) + 1
        (run.dir / f"review.r{old.get('round', 1)}.json").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    review = {"agent": "editor", "model": agent_model("editor"), "round": rnd, "reviewed_at": now(),
              "issue_sha256": sha(run.issue), **{k: v for k, v in review.items() if k not in ("agent", "model", "round", "reviewed_at", "issue_sha256")}}
    out.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    blocking = [n["id"] for n in review["notes"] if n["severity"] == "blocking"]
    print(f"wrote {out} (round {rnd}, verdict {review['verdict']}, blocking: {blocking or 'none'})")


def stage_check_review(run):
    path = run.dir / "review.json"
    if not path.exists():
        return run.record("review.verdict", "waiting", "check-review", ["no review.json yet"],
                          f"Hand off to the editor subagent: {run.cmd('handoff --agent editor')}")
    review = load(path)
    p = review_shape(review)
    if review.get("model") != agent_model("editor"):
        p.append(f"review.json model {review.get('model')!r} is not the editor's pinned model {agent_model('editor')!r}")
    if run.record("review.verdict", "fail" if p else "pass", "check-review",
                  p or {"round": review.get("round"), "verdict": review["verdict"],
                        "blocking": [n["id"] for n in review["notes"] if n["severity"] == "blocking"],
                        "non_blocking": [n["id"] for n in review["notes"] if n["severity"] == "non-blocking"],
                        "voice_fidelity": {i["id"]: i["result"] for i in review["voice_fidelity"]["items"]}},
                  "Rerun the editor and record its verdict with record-review.") != "pass":
        return "fail"

    blocking = [n["id"] for n in review["notes"] if n["severity"] == "blocking"]
    current = sha(run.issue)
    if review["issue_sha256"] == current:
        if blocking:
            return run.record("review.addressed", "fail", "check-review", [f"open blocking notes: {blocking}"],
                              f"Hand off to the writer with review.json: {run.cmd('handoff --agent writer')}")
        return run.record("review.addressed", "pass", "check-review", {"editor_approved_sha256": current})
    if not blocking:
        return run.record("review.addressed", "fail", "check-review",
                          ["issue.json changed after the editor approved it"],
                          f"Send the current draft back to the editor: {run.cmd('handoff --agent editor')}")
    wpath = run.dir / "writer.json"
    writer = load(wpath) if wpath.exists() else {}
    answered = {r.get("note_id"): r for r in writer.get("responses", []) if r.get("status") == "fixed" and r.get("change")}
    p = [f"blocking note {i} has no 'fixed' response with a change in writer.json" for i in blocking if i not in answered]
    if writer.get("model") != agent_model("writer"):
        p.append(f"writer.json model {writer.get('model')!r} is not the writer's pinned model {agent_model('writer')!r}")
    if writer.get("responds_to_review") != review.get("round"):
        p.append(f"writer.json responds to review round {writer.get('responds_to_review')}, the latest is {review.get('round')}")
    return run.record("review.addressed", "fail" if p else "pass", "check-review",
                      p or {"fixed": blocking, "issue_sha256": current, "reviewed_sha256": review["issue_sha256"]},
                      "Writer: address every blocking note and record it in writer.json.")


def stage_render(run):
    data = load(run.issue)
    problems = build.schema_problems(data) + build.lint(data) + build.check_facts(run.issue)
    if problems:
        return run.record("render.reproducible", "fail", "render", problems, "The issue no longer passes its checks; rerun check-issue.")
    html = build.render(build.derive(data))
    if html != build.render(build.derive(data)):
        return run.record("render.reproducible", "fail", "render", ["two renders differ"], "Fix build.render.")
    out = run.dir / "issue.html"
    out.write_text(html, encoding="utf-8")
    return run.record("render.reproducible", "pass", "render", {"issue.html": sha(out), "bytes": len(html.encode())})


def stage_verify(run):
    html = run.dir / "issue.html"
    if not html.exists():
        for g in ("html.phone", "html.desktop", "html.screenshots"):
            run.record(g, "fail", "verify", ["no issue.html"], "Run the render stage first.")
        return "fail"
    try:
        import verify_html
        checks = verify_html.verify(html, run.dir / "screenshots")
    except Exception as e:  # missing Playwright or browser is a failed gate, not a crash
        for g in ("html.phone", "html.desktop", "html.screenshots"):
            run.record(g, "fail", "verify", [f"{type(e).__name__}: {e}"],
                       "Install the pinned requirements and Chromium (see newsletter/requirements.txt).")
        return "fail"
    results = []
    for g, prefix in (("html.phone", "phone."), ("html.desktop", "desktop.")):
        mine = [c for c in checks if c["check"].startswith(prefix) and not c["check"].endswith("screenshots")]
        bad = [c for c in mine if c["status"] != "pass"]
        results.append(run.record(g, "fail" if bad else "pass", "verify",
                                  bad or {"html_sha256": sha(html), "checks": {c["check"]: c["detail"] for c in mine}},
                                  "Fix the issue copy or report the template problem to the owner; don't restyle the template."))
    shots = {s: sha(run.dir / "screenshots" / s) for s in SHOTS}
    missing = [s for s, h in shots.items() if not h]
    results.append(run.record("html.screenshots", "fail" if missing else "pass", "verify",
                              [f"missing {s}" for s in missing] or {"html_sha256": sha(html), "files": shots},
                              "Rerun verify."))
    return "fail" if "fail" in results else "pass"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def stage_checklist(run):
    p, done = [], {}
    order = [g for _, _, gates in STEPS for g in gates if g not in ("checklist.final", "owner.approved")]
    for g in order:
        status = run.gates.get(g, {}).get("status")
        done[g] = status
        if status != "pass":
            p.append(f"gate {g} is {status or 'not run'}")
    data = load(run.issue) if run.issue.exists() else None
    html = run.dir / "issue.html"
    if data is not None:
        for name, problems in (("schema", build.schema_problems(data)), ("lint", build.lint(data)), ("facts", build.check_facts(run.issue))):
            if problems:
                p.append(f"issue.json fails {name} now ({len(problems)} problems)")
        if not html.exists() or html.read_text(encoding="utf-8") != build.render(build.derive(data)):
            p.append("issue.html is not the render of the current issue.json")
        if data.get("preview", {}).get("is_sample"):
            p.append("preview is marked as sample data; say so in the PR")
    if (run.dir / "brief.json").exists() and brief_problems(run):
        p.append("brief.json no longer passes check-brief")
    for g in ("html.phone", "html.desktop", "html.screenshots"):
        if (run.gates.get(g, {}).get("details") or {}).get("html_sha256") not in (None, sha(html)):
            p.append(f"{g} checked an older issue.html; rerun verify")
    if (run.gates.get("review.addressed", {}).get("status")) == "pass" and stage_check_review_quiet(run):
        p.append("the editor gate no longer passes for the current issue.json")
    base = git("merge-base", "HEAD", "origin/main").stdout.strip()
    if base:
        changed = git("diff", "--name-only", base, "--", *PROTECTED).stdout.split()
        p += [f"protected file changed: {f}" for f in changed]
        added_live = [f for f in git("diff", "--name-only", "--diff-filter=A", base, "--", "*.html").stdout.split() if "/" not in f]
        p += [f"new page at the repo root would publish on GitHub Pages: {f}" for f in added_live]
    else:
        p.append("can't find origin/main to compare protected files against; run git fetch origin main")
    live = [REPO / "README.md"] + sorted(REPO.glob("*.html"))
    linked = [f.name for f in live if f.exists() and "newsletter/issues/" in f.read_text(encoding="utf-8")]
    p += [f"live page {f} links to newsletter/issues/" for f in linked]
    return run.record("checklist.final", "fail" if p else "pass", "checklist",
                      p or {"gates": done, "protected_unchanged": PROTECTED, "published": False},
                      "Fix the listed items and rerun the pipeline.")


def stage_check_review_quiet(run):
    """True if the editor gates would fail now (used by the checklist without re-recording)."""
    saved, nxt = dict(run.gates), run.next_action
    out = sys.stdout
    try:
        sys.stdout = open("/dev/null", "w")
        status = stage_check_review(run)
    finally:
        sys.stdout.close()
        sys.stdout = out
        run.gates, run.next_action = saved, nxt
    return status != "pass"


def stage_approval(run, pr=None, record_pending=False):
    if record_pending:
        return run.record("owner.approved", "pending", "approval", ["waiting for the owner to approve the draft PR and its preview"],
                          "Open or update the draft PR with the screenshots; the owner approves it. Nothing publishes before that.")
    target = [pr] if pr else []
    res = subprocess.run(["gh", "pr", "view", *target, "--json", "url,reviewDecision,isDraft,state"], capture_output=True, text=True, cwd=REPO)
    if res.returncode != 0:
        return run.record("owner.approved", "pending", "approval", [res.stderr.strip() or "no PR found"], "Open the draft PR first.")
    info = json.loads(res.stdout)
    ok = info.get("reviewDecision") == "APPROVED"
    return run.record("owner.approved", "pass" if ok else "pending", "approval", info,
                      "Waiting for the owner's approval on the PR.")


HANDOFF = {
    "writer": {
        "model": "writer",
        "reads": [VOICE_GUIDE + " (follow exactly)", "brief.md", "brief.json", ".cursor/skills/newsletter/reference/voice.md",
                  ".cursor/skills/newsletter/reference/voice-fidelity.md",
                  ".cursor/skills/newsletter/reference/issue-schema.md", ".cursor/skills/newsletter/reference/facts.md",
                  "the previous issue.json (structure only)", "review.json (revision rounds only)"],
        "writes": ["issue.json", "writer.json"],
        "gate": "check-issue (first draft), check-review (revisions)",
    },
    "editor": {
        "model": "editor",
        "reads": [VOICE_GUIDE + " (review against it)", ".cursor/skills/newsletter/reference/voice-fidelity.md",
                  "brief.md", "brief.json", "issue.json", ".cursor/skills/newsletter/reference/voice.md",
                  ".cursor/skills/newsletter/reference/facts.md", "verification.json (script gate results)"],
        "writes": ["nothing; returns the verdict JSON, which the main agent saves with record-review"],
        "gate": "check-review",
    },
}


def stage_handoff(run, agent):
    h = HANDOFF[agent]
    rel = run.dir.relative_to(REPO) if run.dir.is_relative_to(REPO) else run.dir
    print(json.dumps({"agent": agent, "model": agent_model(h["model"]), "agent_file": f".cursor/agents/{agent}.md",
                      "issue_dir": str(rel), "reads": h["reads"], "writes": h["writes"], "gate": h["gate"],
                      "issue_sha256": sha(run.issue)}, indent=1))


# ---------------------------------------------------------------- driver

def run_all(run, refresh):
    run.gates = {}
    stages = [("fetch", lambda: stage_fetch(run, refresh)), ("brief", lambda: stage_brief(run)),
              ("check-brief", lambda: stage_check_brief(run)), ("check-issue", lambda: stage_check_issue(run)),
              ("check-review", lambda: stage_check_review(run)), ("render", lambda: stage_render(run)),
              ("verify", lambda: stage_verify(run)), ("checklist", lambda: stage_checklist(run))]
    for name, fn in stages:
        status = fn()
        if status != "pass":
            run.save(stopped_at=name)
            print(f"stopped at {name}: {run.next_action}")
            return WAITING if status == "waiting" else FAILED
    stage_approval(run, record_pending=True)
    run.save()
    print("every automated gate passed; waiting on the owner's PR approval")
    return 0


def main():
    stages = ["all", "fetch", "brief", "check-brief", "check-issue", "record-review", "check-review",
              "render", "verify", "checklist", "approval", "handoff"]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?", default="all", choices=stages)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--season", default="2026")
    ap.add_argument("--out", type=Path, help="issue folder (default newsletter/issues/<season>-week<N>)")
    ap.add_argument("--refresh", action="store_true", help="fetch: pull raw/ again even if the finished week is cached")
    ap.add_argument("--from", dest="source", help="record-review: the editor's verdict JSON file, or - for stdin")
    ap.add_argument("--agent", choices=sorted(HANDOFF), help="handoff: which subagent")
    ap.add_argument("--pr", help="approval: PR URL or number (default: the current branch's PR)")
    a = ap.parse_args()
    run = Run(a.week, a.season, a.out)

    if a.stage == "all":
        sys.exit(run_all(run, a.refresh))
    if a.stage == "handoff":
        if not a.agent:
            ap.error("handoff needs --agent writer|editor")
        return stage_handoff(run, a.agent)
    if a.stage == "record-review":
        if not a.source:
            ap.error("record-review needs --from FILE (or --from -)")
        return stage_record_review(run, a.source)
    status = {
        "fetch": lambda: stage_fetch(run, a.refresh), "brief": lambda: stage_brief(run),
        "check-brief": lambda: stage_check_brief(run), "check-issue": lambda: stage_check_issue(run),
        "check-review": lambda: stage_check_review(run), "render": lambda: stage_render(run),
        "verify": lambda: stage_verify(run), "checklist": lambda: stage_checklist(run),
        "approval": lambda: stage_approval(run, a.pr),
    }[a.stage]()
    run.save(stopped_at=None if status == "pass" else a.stage)
    sys.exit(0 if status in ("pass", "pending") else WAITING if status == "waiting" else FAILED)


if __name__ == "__main__":
    main()
