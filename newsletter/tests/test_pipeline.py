"""Pipeline tests on the committed Week 4 issue folder.

Run: python3 -m pytest newsletter/tests -q
Mutating tests work on a copy in tmp_path; the committed folder is only read.
"""

import copy
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NEWSLETTER = HERE.parent
REPO = NEWSLETTER.parent
sys.path.insert(0, str(NEWSLETTER))

import build  # noqa: E402
import fetch_week  # noqa: E402
import run as pipeline  # noqa: E402

WEEK4 = NEWSLETTER / "issues" / "2026-week4"
GUIDE = REPO / ".cursor" / "skills" / "newsletter" / "voice" / "boston-connor.md"
GUIDE_SHA256 = "2067e47e74fc4a45a857569fa13e197667cdb7052de16700e7e957680dfb6ea2"

ELO_WEEK4 = {
    "Micah parsons fan club": (1029.33, 14.80),
    "Split Safety Syndicate": (1027.62, -18.91),
    "hammball": (1004.08, 17.21),
    "Kingslayers": (1002.84, 15.93),
    "Dak Side of the Sun": (1001.51, 18.91),
    "WELL! It's The Big Shough": (1001.34, 17.34),
    "ThePeopleBeaters": (1000.07, 17.54),
    "Mendozareamazingpicks": (998.46, -17.54),
    "J’Allen Waffle Stompers": (995.88, -17.21),
    "Unsportsmanlike Conduct": (995.81, -17.34),
    "Skat’s BruteForce Theorem": (973.52, -14.80),
    "Rams of Steel": (969.54, -15.93),
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def playwright_ready():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


needs_browser = pytest.mark.skipif(not playwright_ready(), reason="Playwright or Chromium not installed")


@pytest.fixture
def week(tmp_path):
    """A writable copy of the Week 4 folder and a Run pointed at it."""
    out = tmp_path / "2026-week4"
    shutil.copytree(WEEK4, out, ignore=shutil.ignore_patterns("screenshots"))
    return pipeline.Run(4, "2026", out=out)


@pytest.fixture
def issue():
    return load(WEEK4 / "issue.json")


def facts_of(tmp_path, data):
    """check_facts on a modified issue, with the committed brief beside it."""
    d = tmp_path / "facts"
    d.mkdir(exist_ok=True)
    for f in ("brief.json", "brief.md"):
        shutil.copy(WEEK4 / f, d / f)
    (d / "issue.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return build.check_facts(d / "issue.json")


# ---------------------------------------------------------------- Elo

def raw_matchups(through):
    return {w: load(WEEK4 / "raw" / f"sleeper_matchups_w{w}.json") for w in range(1, through + 1)}


def roster_ids():
    return [r["roster_id"] for r in load(WEEK4 / "raw" / "sleeper_rosters.json")]


def test_elo_week4_reproduces_pinned_values():
    table = {t["team"]: (t["elo"], t["change"]) for t in load(WEEK4 / "brief.json")["elo"]["table"]}
    assert table == ELO_WEEK4
    rating, change, _ = fetch_week.elo_ratings(raw_matchups(4), roster_ids(), 4)
    assert sorted(rating.values()) == sorted(v[0] for v in ELO_WEEK4.values())
    assert sorted(change.values()) == sorted(v[1] for v in ELO_WEEK4.values())


def test_elo_week1_is_plus_and_minus_16_and_zero_sum():
    rating, change, _ = fetch_week.elo_ratings(raw_matchups(1), roster_ids(), 1)
    assert sorted(rating.values()) == [984.0] * 6 + [1016.0] * 6
    assert abs(sum(change.values())) < 0.011


def test_elo_every_week_is_zero_sum():
    for w in range(1, 5):
        _, change, _ = fetch_week.elo_ratings(raw_matchups(w), roster_ids(), w)
        assert abs(sum(change.values())) < 0.011, w


# ---------------------------------------------------------------- brief

def test_brief_rebuild_is_deterministic_and_matches_committed(week):
    fetch_week.build_brief(week.dir, 4, "2026")
    assert (week.dir / "brief.json").read_bytes() == (WEEK4 / "brief.json").read_bytes()
    assert (week.dir / "brief.md").read_bytes() == (WEEK4 / "brief.md").read_bytes()
    assert pipeline.stage_brief(week) == "pass"


def test_fetch_is_cached_without_network(week, monkeypatch):
    monkeypatch.setattr(fetch_week, "get", lambda url: pytest.fail(f"network call: {url}"))
    assert fetch_week.fetch_raw(4, "2026", out=week.dir) == "cached"


def test_check_brief_passes(week):
    assert pipeline.brief_problems(week) == []
    assert pipeline.stage_check_brief(week) == "pass"


def test_check_brief_fails_on_tampering(week):
    b = load(week.dir / "brief.json")
    b["fantasy_matchups"][0]["winner"]["points"] += 10
    b["elo"]["table"][0]["elo"] = 1100.0
    (week.dir / "brief.json").write_text(json.dumps(b), encoding="utf-8")
    problems = pipeline.brief_problems(week)
    assert any("margin" in p for p in problems)
    assert any("elo" in p for p in problems)
    assert any("brief.md doesn't match" in p for p in problems)
    assert pipeline.stage_check_brief(week) == "fail"


# ---------------------------------------------------------------- unfinished week

def event(status="Final", completed=True, date="2026-10-06T00:15Z"):
    return {"id": "1", "shortName": "CHI @ PHI", "date": date,
            "competitions": [{"status": {"type": {"completed": completed, "description": status}}}]}


def test_unfinished_flags_games_and_zero_matchups():
    left = fetch_week.unfinished({"events": [event("In Progress", False)]}, [{"points": 0}])
    assert any("In Progress" in x for x in left)
    assert any("without points" in x for x in left)
    assert fetch_week.unfinished({"events": []}, [{"points": 1}])


def test_unfinished_waits_for_waivers_with_grace():
    board = {"events": [event()]}
    ms = [{"points": 100.0}]
    kick = dt.datetime(2026, 10, 6, 0, 15, tzinfo=dt.timezone.utc)
    assert fetch_week.unfinished(board, ms, [], now=kick + dt.timedelta(hours=12))
    assert fetch_week.unfinished(board, ms, [], now=kick + dt.timedelta(hours=37)) == []
    assert fetch_week.unfinished(board, ms, [{"type": "waiver"}], now=kick + dt.timedelta(hours=1)) == []


# ---------------------------------------------------------------- issue gates

def test_committed_issue_passes_schema_lint_and_facts(issue):
    assert build.schema_problems(issue) == []
    assert build.lint(issue) == []
    assert build.check_facts(WEEK4 / "issue.json") == []


def test_guide_words_are_not_banned():
    banned = {p.lower() for p in build.banned_phrases()}
    for word in ("fraud", "bum", "disaster", "embarrassing", "unbelievable", "pathetic", "wicked", "chowdahead"):
        assert word not in banned


def test_filler_and_cliches_stay_banned():
    banned = {p.lower() for p in build.banned_phrases()}
    for phrase in ("delve", "testament to", "nail-biter", "stellar"):
        assert phrase in banned


def test_lint_fails_banned_phrase(issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][0]["body"] += " It was a testament to grit."
    assert any("testament to" in p for p in build.lint(bad))


def test_lint_fails_too_many_caps(issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][1]["body"] += " WOW. LOOK. AT. THIS. GARBAGE."
    assert any("ALL-CAPS" in p for p in build.lint(bad))


def test_lint_fails_repeated_catchphrase(issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][0]["body"] += " Wicked fraud alert."
    bad["recaps"][3]["body"] += " Wicked fraud alert."
    assert any("catchphrase repeated" in p for p in build.lint(bad))


def test_injury_status_lines_may_repeat(issue):
    ok = copy.deepcopy(issue)
    for inj in ok["injuries"][:3]:
        inj["note"] = inj["note"].rstrip() + " Sleeper: questionable (hamstring)."
    assert not any("catchphrase" in p for p in build.lint(ok))


def test_lint_fails_long_sentence_and_long_average(issue):
    bad = copy.deepcopy(issue)
    bad["lead"]["body"][0] += " " + " ".join(["and then the team kept on playing"] * 6) + "."
    assert any("-word sentence" in p for p in build.lint(bad))
    wordy = "The team scored a lot of points in a game this week against a good opponent"
    for i, r in enumerate(bad["recaps"]):
        r["body"] = " ".join(f"{wordy} number {i}{j}." for j in range(8))
    for i, r in enumerate(bad["rankings"]):
        r["take"] = " ".join(f"{wordy} ranked {i}{j}." for j in range(4))
    bad["lead"]["body"] = [" ".join(f"{wordy} lead {i}{j}." for j in range(5)) for i in range(4)]
    assert any("average sentence" in p for p in build.lint(bad))


def test_lint_fails_profanity_over_cap(issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][2]["body"] += " Damn. Hell. Crap. Damn it. Hell no."
    assert any("swear words" in p for p in build.lint(bad))


def test_schema_fails_on_missing_section(issue):
    bad = copy.deepcopy(issue)
    del bad["recaps"]
    assert build.schema_problems(bad)


def test_facts_fail_on_wrong_score(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][0]["w_score"] = "170.00"
    assert facts_of(tmp_path, bad)


def test_facts_fail_on_wrong_margin(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][0]["margin"] = "31.58"
    assert facts_of(tmp_path, bad)


def test_facts_fail_on_invented_number(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["recaps"][0]["body"] += " He also ran for 417 yards on the side."
    assert any("417" in p for p in facts_of(tmp_path, bad))


def test_facts_fail_on_bad_derived_arithmetic(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["derived"][0]["expr"] = "200 - 180"
    assert facts_of(tmp_path, bad)


def test_facts_fail_on_derived_operand_not_in_brief(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["derived"].append({"value": "4321.5", "expr": "4321.5 - 0", "why": "made up"})
    bad["recaps"][0]["body"] += " That is 4321.5 of something."
    assert facts_of(tmp_path, bad)


def test_facts_fail_on_wrong_elo(tmp_path, issue):
    bad = copy.deepcopy(issue)
    bad["rankings"][0]["elo"] = "1031.00"
    assert facts_of(tmp_path, bad)


def test_render_is_deterministic_and_matches_committed_html(issue):
    html = build.render(build.derive(issue))
    assert html == build.render(build.derive(issue))
    assert "{{" not in html.split("<body", 1)[1]
    assert html == (WEEK4 / "issue.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- editor gate

def passing_review(blocking=()):
    items = [{"id": i, "result": "pass", "evidence": "quoted line"} for i in pipeline.voice_items()]
    units = [{"unit": u, "result": "pass", "steps": {str(s): f"step {s}" for s in range(1, 6)}} for u in pipeline.UNITS]
    for it in items:
        if it["id"] == "delivery":
            it["units"] = units
    notes = [{"id": n, "severity": "blocking", "section": "lead", "problem": "p", "fix": "f"} for n in blocking]
    return {"verdict": "revise" if blocking else "approve", "summary": "s", "notes": notes,
            "voice_fidelity": {"guide": pipeline.VOICE_GUIDE, "items": items}}


def test_voice_items_cover_the_guide():
    items = pipeline.voice_items()
    assert len(items) == len(set(items)) >= 25
    for must in ("delivery", "rhythm.short_blunt", "rhythm.sparing_caps", "constraints.not_every_sentence_a_joke",
                 "constraints.no_yelling_or_catchphrases", "constraints.commentary_not_news"):
        assert must in items


def test_review_shape_accepts_complete_verdict():
    assert pipeline.review_shape(passing_review()) == []


def test_review_shape_rejects_gaps():
    r = passing_review()
    r["voice_fidelity"]["items"] = [i for i in r["voice_fidelity"]["items"] if i["id"] != "rhythm.sparing_caps"]
    assert any("rhythm.sparing_caps" in p for p in pipeline.review_shape(r))

    r = passing_review()
    r["voice_fidelity"]["items"][0]["result"] = "miss"
    assert any("must cite" in p for p in pipeline.review_shape(r))

    r = passing_review()
    del r["voice_fidelity"]
    assert pipeline.review_shape(r)

    r = passing_review(blocking=["n1"])
    r["verdict"] = "approve"
    assert any("verdict" in p for p in pipeline.review_shape(r))

    r = passing_review()
    delivery = next(i for i in r["voice_fidelity"]["items"] if i["id"] == "delivery")
    delivery["units"][2]["steps"]["4"] = ""
    assert any("steps 1-5" in p for p in pipeline.review_shape(r))


def write_review(run, review, sha):
    review = {"agent": "editor", "model": pipeline.agent_model("editor"), "round": 1, "issue_sha256": sha, **review}
    (run.dir / "review.json").write_text(json.dumps(review), encoding="utf-8")


def test_review_gate_approve_then_issue_changes(week):
    write_review(week, passing_review(), pipeline.sha(week.issue))
    assert pipeline.stage_check_review(week) == "pass"
    data = load(week.issue)
    data["lead"]["dek"] += " "
    week.issue.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert pipeline.stage_check_review(week) == "fail"


def test_review_gate_needs_every_blocking_note_answered(week):
    old = pipeline.sha(week.issue)
    write_review(week, passing_review(blocking=["n1", "n2"]), old)
    assert pipeline.stage_check_review(week) == "fail"
    data = load(week.issue)
    data["lead"]["dek"] += " "
    week.issue.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    writer = {"agent": "writer", "model": pipeline.agent_model("writer"), "round": 2, "responds_to_review": 1,
              "responses": [{"note_id": "n1", "status": "fixed", "change": "rewrote it"}]}
    (week.dir / "writer.json").write_text(json.dumps(writer), encoding="utf-8")
    assert pipeline.stage_check_review(week) == "fail"
    writer["responses"].append({"note_id": "n2", "status": "fixed", "change": "cut it"})
    (week.dir / "writer.json").write_text(json.dumps(writer), encoding="utf-8")
    assert pipeline.stage_check_review(week) == "pass"


def test_committed_review_passes():
    review = load(WEEK4 / "review.json")
    assert pipeline.review_shape(review) == []
    assert review["model"] == pipeline.agent_model("editor")


# ---------------------------------------------------------------- agents and voice file

def frontmatter(name):
    text = (REPO / ".cursor" / "agents" / f"{name}.md").read_text(encoding="utf-8")
    return text.split("---", 2)[1]


def test_agents_pin_their_models():
    assert pipeline.agent_model("writer") == "claude-opus-5-5[effort=high]"
    assert pipeline.agent_model("editor") == "claude-sonnet-5-5[effort=high]"
    assert "readonly: true" in frontmatter("editor")
    assert "name: writer" in frontmatter("writer") and "name: editor" in frontmatter("editor")


def test_agents_point_at_the_voice_guide():
    for name in ("writer", "editor"):
        assert ".cursor/skills/newsletter/voice/boston-connor.md" in (REPO / ".cursor" / "agents" / f"{name}.md").read_text()


def test_voice_guide_is_the_verbatim_upload():
    assert hashlib.sha256(GUIDE.read_bytes()).hexdigest() == GUIDE_SHA256


# ---------------------------------------------------------------- HTML

@needs_browser
def test_html_checks_pass_on_the_render():
    import verify_html

    checks = verify_html.verify(WEEK4 / "issue.html")
    assert [c for c in checks if c["status"] != "pass"] == []


@needs_browser
def test_html_checks_fail_on_broken_page(tmp_path):
    import verify_html

    page = tmp_path / "broken.html"
    page.write_text('<html><body><img src="https://example.com/x.png"><div style="width:3000px">wide</div>{{ lead.headline }}</body></html>')
    failed = {c["check"] for c in verify_html.verify(page) if c["status"] == "fail"}
    for vp in ("phone", "desktop"):
        assert {f"{vp}.no_network_requests", f"{vp}.no_horizontal_scroll", f"{vp}.no_template_leftovers",
                f"{vp}.find_your_team_links"} <= failed


@needs_browser
def test_full_run_is_idempotent(week, monkeypatch):
    monkeypatch.setattr(fetch_week, "get", lambda url: pytest.fail(f"network call: {url}"))
    assert pipeline.run_all(week, refresh=False) == 0
    first = {f: pipeline.sha(week.dir / f) for f in ("brief.json", "brief.md", "issue.html")}
    gates = [(g["gate"], g["status"]) for g in load(week.ver)["gates"]]
    again = pipeline.Run(4, "2026", out=week.dir)
    assert pipeline.run_all(again, refresh=False) == 0
    assert {f: pipeline.sha(week.dir / f) for f in first} == first
    assert [(g["gate"], g["status"]) for g in load(week.ver)["gates"]] == gates
    assert load(week.ver)["result"] == "pass"
