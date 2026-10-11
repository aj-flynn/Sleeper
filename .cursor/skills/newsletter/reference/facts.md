# Facts: the brief is the only source

Read by the writer and the editor. The `issue.facts` gate (`python3 newsletter/build.py --check-facts`) enforces the parts with one right answer; the editor checks the rest.

## The rules

- **Every number must come from the week's data brief** (`brief.md` / `brief.json` next to the issue) or be simple arithmetic on brief numbers (sums, differences, ranks). The Week 2 issue shipped a wrong derived number, which is why derived numbers now have to show their work: every number in the copy that isn't printed in the brief goes in the issue's `derived` list with the arithmetic (see "The derived list" below). The fact check recomputes each one.
- **Which source wins.** Each kind of fact has one source of truth:
  - Fantasy points, lineups, bench, standings, records, transactions, and FAAB: the league on Sleeper. Fantasy points always come from the league matchups (`players_points`), never from Sleeper's generic PPR totals, because this league's scoring differs (Burrow scored 23.72 here and 25.72 under Sleeper's default).
  - Box-score lines (yards, catches, targets, carries, touchdowns, interceptions, snaps, kicks, sacks): Sleeper's NFL weekly stats. When ESPN prints a different number, use Sleeper's. In Week 4 ESPN's recap gave Tee Higgins 151 receiving yards; Sleeper has 157, which is what his 26.7 fantasy points add up to.
  - Game results, venues, game context, quotes, injuries during the game, career highs, and records: ESPN's scoreboard and game recaps. Attribute anything you'd only know from a recap ("according to ESPN", "per ESPN").
  - Injury status for next week: Sleeper's status at fetch time (Questionable, Out, IR), as listed in the brief.
- **Don't use outside knowledge.** No NFL news, depth charts, projections, trade values, or reasons that the brief doesn't contain. If it isn't in the stat lines or the ESPN text in the brief, it isn't in the issue.
- **Match players by ID, not name.** Sleeper has duplicate names (two Kenneth Walkers, several Johnsons). The fetcher joins on `player_id`; if you look something up by hand, do the same. ESPN and Sleeper also disagree on some team codes (ESPN `WSH` is Sleeper `WAS`); the fetcher maps them.
- **Superlatives need the full list.** Before writing "highest," "lowest," "only," or "career high," sort the full data and confirm, or quote the recap that says it.
- **Copy numbers as given.** Team scores in tables use two decimals (`147.60`). Prose can use the brief's own precision (`147.6`).
- **Keep transaction windows straight.** Label which waiver run each move belongs to (the brief gives the processed time in UTC), and don't add free-agent moves into FAAB totals. The brief covers this week's leg plus next week's leg up to next week's first kickoff.
- **Missing data is marked, never invented.** If something can't be fetched, leave it out or fill it with placeholder content and set that section's `is_sample` flag, which prints a visible "Sample data" label, plus a note that says what is placeholder. The final checklist fails while anything is marked as sample, so the PR has to say so. Never present an invented number as real.
- **Opinions are labeled as opinions.** Ranking takes and grades are opinion; the rankings order (Elo), scores, records, stat lines, and FAAB are facts.
- **The NFL games block in the brief is context, not a section.** Use it for finals, game situations, and ESPN quotes inside the recaps, lead, and awards. The issue doesn't list every NFL result.

## What the fact check verifies

`issue.facts` fails the issue on any of these:

| Check | One right answer |
| --- | --- |
| Number trace | Every number in the copy (except counts up to 10 and the season year) appears in `brief.md`/`brief.json`, or in the `derived` list. |
| Derived arithmetic | Each `derived` entry's `expr` uses only brief numbers and recomputes to its `value` at the printed precision. |
| Rankings | Team order, `elo`, `elo_change`, `record`, and `manager` match the brief's Elo table and team list. |
| Recaps | Winner, loser, both managers, both scores, and the margin match a brief matchup exactly (two decimals). |
| Key performers | Each player is on that side's roster in the brief, with the same fantasy points and NFL team. |
| Standouts | Each is the actual top-scoring starter at that position, on the fantasy team named. |
| Preview | The six pairings are next week's six fantasy matchups. |
| Waivers | Each claim is a completed claim in the brief, by that team, at that bid. |

What it can't verify, and the editor must: that a number is attached to the right player or game in the sentence, that a reason or context comes from the ESPN text, that a superlative is true, and that a derived number means what the sentence says.

## The derived list

Every number in the copy that the brief doesn't print goes in `issue.json` under `derived`:

```json
"derived": [
  {"value": "23.8", "expr": "25.7 - 1.9", "why": "Robinson's bench points minus Miller's"},
  {"value": "$101", "expr": "70 + 25 + 5 + 0 + 0 + 0 + 1", "why": "the seven Wednesday claims"},
  {"value": "72.1", "expr": "41.3 + 30.8", "why": "Lamb plus Collins"}
]
```

`expr` allows numbers, `+ - * /`, and parentheses. Each number must be a brief number or a count up to 10. The template never prints `derived`.

## What the brief contains

`python3 newsletter/run.py fetch --week <N>` and `brief --week <N>` write `brief.md` (read this), `brief.json` (the same data, structured), and `raw/` (every API response used, trimmed to the players the brief mentions, plus `fetch_meta.json` with the fetch time). All three are committed with the issue.

| Part | What it holds | Source |
| --- | --- | --- |
| Sources and fetch time | Every URL used and when it was pulled | the fetcher |
| Standings | W-L, points for and against, and week-by-week results for all 12 teams | Sleeper `/league/<id>/matchups/1..N` and `/rosters`, `/users` for names |
| Elo | Every team's rating, this week's change, and its rating after each week, in power-rankings order, with the formula | Computed from Sleeper `/league/<id>/matchups/1..N` (see [league.md](league.md#elo)) |
| Fantasy matchups | All six games: final, margin, every starter and bench player with league fantasy points | Sleeper `/league/<id>/matchups/<N>` |
| NFL stat line per player | For each of those players: NFL team, a plain-words box-score line, and their NFL game's final | Sleeper `api.sleeper.com/stats/nfl/<season>/<N>`, joined on `player_id`; players from `/v1/players/nfl` |
| NFL games | Every final, date, venue, ESPN's recap headline and text, scoring plays, and the pregame injury report | ESPN `site.api.espn.com/.../nfl/scoreboard` and `/summary?event=<id>` |
| Transactions | Waivers (with bids, failed competing bids and their reasons), free agents, and trades (players and picks), with UTC times, for this week's leg and next week's leg up to its first kickoff | Sleeper `/league/<id>/transactions/<N>` and `/<N+1>` |
| FAAB used | Per team, at fetch time | Sleeper rosters |
| Next week | The six fantasy pairings, the NFL schedule, and byes | Sleeper `/matchups/<N+1>`, ESPN scoreboard for week N+1 |
| Injury status | Every rostered player with a Sleeper injury status at fetch time | Sleeper `/v1/players/nfl` |
