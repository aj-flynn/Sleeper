# Adapt the pipeline to another league

The steps after the brief do not know which fantasy site produced `raw/`. To retarget the league, change the inputs below and keep the gates.

1. Set the league id and season. Change `LEAGUE_ID` in `newsletter/fetch_week.py`, or pass `--league`, and pass `--season`. Sleeper scoring, lineup slots, and team names come from the league itself.
2. Replace the hardcoded 12 teams and 6 games. They live in `validate()` in `newsletter/build.py`, `brief_problems()` in `newsletter/run.py`, and the Find-your-team count in `newsletter/verify_html.py`. Read the team count from the brief.
3. Keep the rankings order in code. Elo with K of 32 fits a 14-week season. To use another order, change `elo_table()` and leave the order in code, so it stays a fact. Start a season file with `python3 newsletter/elo.py --backfill --season <year> --through 1` after week 1. Later weeks append themselves.
4. Replace the voice. Commit the new owner's guide under `voice/`. Point the writer and editor agent files and `VOICE_GUIDE` in `newsletter/run.py` at it. Rewrite the item table in [voice-fidelity.md](voice-fidelity.md), the examples and banned list in [voice.md](voice.md), and the `VOICE` thresholds in `newsletter/build.py` against a real issue.
5. Replace [league.md](league.md).
6. Pick a template with the owner, using `.cursor/skills/frontend-design/SKILL.md`, and set `TEMPLATE` in `newsletter/build.py`. The HTML gate needs the `#teams` jump list.
7. For ESPN or Yahoo, rewrite `fetch_raw()` so it saves the same `raw/` shapes, or adapt `build_brief()`. Leave every later step alone.
8. Run `python3 -m pytest newsletter/tests -q` with a finished week of the new league as the fixture. Pin its Elo values the way `test_elo_reproduces_week4` does.
