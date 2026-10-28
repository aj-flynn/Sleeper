# Wednesday Rebuilders Anonymous newsletter

This is the entry point for any capable agent. AJ has authorized automatic publication of his Rebuilders Anonymous newsletter to GitHub Pages and a single link in its Sleeper league chat as JeffyWaterton. Prepare at 07:00 and publish at 08:00 America/New_York, allowing ordinary generation/deployment latency. The parent task manages the two schedules; do not create another scheduler. This authorization does not extend to ESPN/wife-league work, which remains separate and draft-only.

Use the original regular style. On the Wednesday on or immediately before US Halloween (October 31), Thanksgiving (fourth Thursday in November), or Christmas (December 25), automatically use that saved holiday theme. `--theme auto` is the render default and resolves the rule by year. In 2026 those dates are October 28, November 25 and December 23. Other holidays use regular. Week 7 on October 28 is already published and announced; do not post it again.

## 07:00 provisional preparation

Read `config.json`, [EDITORIAL.md](EDITORIAL.md), the previous issue and `data/<season>/history.json`. Preserve existing edits. Use Python 3.12+ on Office; Eastern timezone data is bundled for Windows. GitHub access, public Sleeper/ESPN APIs and the authenticated Sleeper browser are needed for the complete run. No named model, agent app or subscription is required.

For November 4, 2026 (08:00 EST = 13:00Z):

```powershell
python newsletter/weekly.py capture --provisional --cutoff 2026-11-04T13:00:00Z --out newsletter/work/2026-11-04-early-capture
python newsletter/weekly.py prepare --provisional --cutoff 2026-11-04T13:00:00Z --capture newsletter/work/2026-11-04-early-capture --out newsletter/work/2026-11-04-early-draft
```

Write the provisional `issue.json` using the brief and [ISSUE-SCHEMA.md](ISSUE-SCHEMA.md). Its data cutoff is the actual capture time; `draft.json` also records the scheduled 08:00 cutoff and provisional status. It is not the final reporting window and cannot update season history or be published. If an early run is missed, do the whole process at 08:00; never invent prepared work.

## 08:00 finalize, write and publish

At or after 08:00 capture fresh data and prepare a separate final directory:

```powershell
python newsletter/weekly.py capture --cutoff 2026-11-04T13:00:00Z --out newsletter/work/2026-11-04-final-capture
python newsletter/weekly.py prepare --cutoff 2026-11-04T13:00:00Z --capture newsletter/work/2026-11-04-final-capture --out newsletter/work/2026-11-04-final-draft --record
```

Refresh the provisional copy against the final brief: update scores, moves, FAAB, injuries/news and any affected jokes or claims. If preparing from scratch, use `examples/2026-week7-regular/issue.json` for structure and replace week-specific copy. Write complete, sharply funny league-specific paragraphs in a neutral voice. Individual managers use he/him/his; plural team/person references remain grammatical. Explain fantasy outcomes with real NFL stat lines. Keep future-week results out of previews. Do not render bench prose beneath Standouts or any preview/process/approval banner or reserved area.

```powershell
python newsletter/weekly.py render --out newsletter/work/2026-11-04-final-draft
```

Rendering catches missing fields and obvious factual inconsistencies. Read the page for correct names/scores and readable phone/desktop layout, fix obvious problems and publish without waiting for another weekly approval. Follow [PUBLISHING.md](PUBLISHING.md): host the page through the repo's Pages setup, then post one link in the verified Rebuilders Anonymous chat. Read/update `data/publication-state.json` to avoid duplicate delivery. Missing critical data, failed deployment, missing browser access or an uncertain send outcome means stop and report, not guess or blindly resend. Corrections and re-deployments remain silent in chat.

Public Sleeper API is authoritative for fantasy scores and moves; ESPN supplies dated finals/game reporting. Supplemental NFL MCP defaults to `http://127.0.0.1:9000/mcp/` (override `NFL_MCP_URL` or `--mcp-url`). It can be unavailable or have empty news/injury caches. Use available dated game reporting and preserve uncertainty; never treat today's injury flag as last Wednesday's fact. `healthcheck.py --live` is for setup/troubleshooting, not weekly paperwork.

## Windows, replay and maintenance

Reporting windows are half-open from the previous Wednesday at 08:00 local to this Wednesday at 08:00 local, spanning 167/169 hours across DST. A delayed run still uses its explicit intended Wednesday cutoff. Week 7 is October 21 at 12:00Z through October 28 at 12:00Z exclusive. Future final cutoffs are refused. NFL week selection uses dated final status, not the league's current week number. See [DATA.md](DATA.md) for continuity, recovery, corrections and rollover.

Offline replay (never publish or announce it):

```powershell
python newsletter/weekly.py prepare --capture newsletter/data/2026/week7-capture --out newsletter/work/week7-replay --cutoff 2026-10-28T12:00:00Z
Copy-Item newsletter/examples/2026-week7-regular/issue.json newsletter/work/week7-replay/issue.json
python newsletter/weekly.py render --out newsletter/work/week7-replay --theme regular
```

The retained capture reconstructs the historical window from later retrieval and dated sources; historical injury/name gaps are documented. Keep `newsletter/work/` untracked. For code changes run `python -m pytest newsletter/tests -q`. Browser tooling is optional for template development, not additional production ceremony.
