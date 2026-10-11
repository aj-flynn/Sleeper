---
name: newsletter
description: Fetch the week's data, then write and build the weekly Rebuilders Anonymous fantasy football newsletter, weaving real NFL box-score lines into the fantasy numbers. Use for any request to draft, write, edit, fact-check, or render a Rebuilders Anonymous issue, recap, power rankings, or awards.
---

# Rebuilders Anonymous newsletter

The weekly newsletter for **Rebuilders Anonymous**, a 12-team dynasty league on Sleeper. Each week you pull a data brief with `newsletter/fetch_week.py`, write the issue as JSON, and build one self-contained HTML file. Every issue tells the fantasy story through the real football: a score is explained by the stat line and the game that produced it. The owner's two complaints about past issues were that the design was poor and the writing was poor. The design is solved by the Card Back template. The writing is on you, every week. This file is the bar.

## Chosen template

```
CHOSEN_TEMPLATE: card-back
```

The owner picked **Card Back**, the only template: `newsletter/templates/card-back.html`, with its two fonts (Alfa Slab One, Archivo Narrow) in `newsletter/fonts/` and their licenses in `newsletter/fonts/licenses/`. The rendered Week 4 sample is `newsletter/issues/2026-week4/issue.html`. Render every issue with it and don't restyle it per issue. Design changes follow `.cursor/skills/frontend-design/SKILL.md` and need the owner's sign-off. The owner's standing design notes:

- Recap cards must let a manager find their own team fast while scrolling on a phone. Team names are the biggest type on each card, the winner always sits on top, and the section opens with the "Find your team" list that links to every card (`build.py` builds that list from `recaps`).
- No provenance paragraph, format line, or byline on the page, no intro lines under section headings, and no standalone NFL results section. The football goes inside the recaps, lead, awards, and standouts.

## The league

- Sleeper league ID `1319718857249665024` (2026 season). `fetch_week.py` uses it by default.
- 12 teams, dynasty, Superflex, full PPR. Scoring: 1 per catch, 0.1 per rushing or receiving yard, 6 per rushing or receiving TD, 0.04 per passing yard, 4 per passing TD, minus 2 per interception or lost fumble.
- Starting lineup: QB, 2 RB, 2 WR, TE, 2 FLEX, Superflex, K, DEF, plus 8 bench spots. Playoffs start in Week 15.
- $200 FAAB per season, blind bids. Startup was a $1,000 auction (the draft review is `rebuilders-anonymous-draft-review.html`).
- The newsletter is "Presented by Unsportsmanlike Conduct" (UC), the house brand. UC gets roasted like everyone else, a little harder if anything.
- Team names change. Use exactly the names in the brief, with their casing and punctuation (`hammball` is lowercase, `Micah parsons fan club` has one capital, `J’Allen Waffle Stompers` and `Skat’s BruteForce Theorem` use curly apostrophes, `WELL! It's The Big Shough` keeps its exclamation mark). The brief uses the Sleeper team name and falls back to the manager's display name when a team has none.
- Week 4 teams and managers: Split Safety Syndicate (kylejones10), Micah parsons fan club (Packersfan1992), Dak Side of the Sun (SweetRavenge84), Mendozareamazingpicks (DarknessMonster), J’Allen Waffle Stompers (BigJohnDeBo008, called J’Alle in Week 2), Unsportsmanlike Conduct (JeffyWaterton), Kingslayers (maierz3948), hammball (hammball), ThePeopleBeaters (ThePeopleBeaters), WELL! It's The Big Shough (KaranLuvSport), Rams of Steel (iemerson969), Skat’s BruteForce Theorem (LittleTimmyFlynn). The draft review uses older names; never use those unless the brief does.
- Past issues: `2026-week2.html` (published, repo root) and the Week 4 sample in `newsletter/issues/2026-week4/`. Read Week 2 for data shape only; it predates the voice and the NFL-stat rules.

## Voice

Write like the best columnist in a group chat of people who have known each other for years: smart, funny, specific, and sure of yourself. You are roasting friends, so the jokes are about their decisions, built on their own numbers, and the reader should laugh because it is true.

1. **Lead with the take.** The first sentence of every item says what you think. The numbers come in as evidence.
2. **Every joke rides on a fact.** If you can't point to the number that makes it funny, cut it.
3. **Specific beats clever.** "Started Nacua and got 0.0" is better than any metaphor about Nacua.
4. **Roast decisions, not people.** Benched the wrong guy, overpaid on waivers, left the kicker slot empty: fair game. Jobs, families, looks, and real-life stuff: never.
5. **Be confident.** Declarative sentences. No "arguably," "kind of," "it seems," "might be." If you aren't sure, check the brief; if the brief doesn't say, don't write it.
6. **Short sentences do the punching.** Set up with a normal sentence, land with a short one. Don't explain the joke after it lands.
7. **One idea per item.** A ranking blurb is two or three sentences with one point. Not a list of everything that happened.
8. **Vary the shape.** Twelve ranking blurbs should not all start with the team's score. Some start with a player, some with the decision, some with the punchline.
9. **Plain words.** No sportscaster clichés, no corporate words, no accounting metaphors. Write the way a sharp person talks.
10. **Football first, then fantasy.** A fantasy score is the result; the stat line and the game are the story. "Kyren Williams scored 36.7" is a number. "Kyren Williams ran for two touchdowns in the last four minutes of the Rams’ comeback and caught 10 passes" is why the number happened. Every recap and the lead must cite real box-score numbers (yards, catches, carries, touchdowns, snaps, field goals), and the build fails if they don't.

### Examples that hit the bar

The first two use real Week 4 facts and show the NFL weaving every issue needs. The rest are real Week 2 facts, written before the NFL rule; they still show the voice.

> Rams of Steel had a running back on each side of Monday night’s Falcons-Saints game and started the one on the losing side. Kendre Miller ran 6 times for 9 yards and lost a fumble for New Orleans (1.9). Brian Robinson ran for three touchdowns in Atlanta’s 45-24 win, from the Rams’ bench (25.7). That one swap is worth 23.8 in a 16.2-point loss.

> Micah parsons fan club played Week 4 with ten working starters and won by 29.58. The eleventh was Case Keenum at Superflex. According to ESPN, Keenum lined up under center for Chicago’s first play, pitched to D’Andre Swift for 2 yards, and Tyson Bagent played quarterback for the rest of the game. Keenum’s line for the week is 1 snap and 0.0 points.

> Split Safety Syndicate scored 166.06 this week, the most in the league, with Travis Kelce, Stefon Diggs, and Denzel Boston on the bench. Those three scored 67.3 points while sitting. That is most of what ThePeopleBeaters scored as an entire team, left in a drawer, and it didn’t matter, because Mahomes, Chase, Young, Walker, and Gibbs all cleared 23.

> Four teams are undefeated, and one of them should not feel great about it. Micah parsons fan club is 2-0 after scoring 95.58, tenth-best of twelve, against a hammball lineup with no kicker and three starters who scored zero. Undefeated is undefeated. In this case it also came with a gift receipt.

> Unsportsmanlike Conduct, which presents this newsletter and therefore deserves extra scrutiny, spent $16 on D. Wicks to beat a $0 bid from Micah parsons fan club. Then it spent another $16 on A. Mitchell, a claim nobody else made. That is $32 to outbid one person who bid nothing and a room with nobody in it.

> Smith-Njigba scored 42.5, the best individual number of the week, and Mendoza still lost. White (14.3) and Worthy (13.5) sat while Stevenson (3.6) and Wilson (3.8) started. That swap was worth 20.4 points in an 11.44-point loss.

> Davante Adams scored 39.5, second-best in the league, and lost to a team whose second-best scorer was a defense. After Adams, the Rams’ next starter scored 17.5. In Superflex, one star and a shrug gets you to 0-2.

### What it should not sound like

| Instead of this | Write this |
| --- | --- |
| Split Safety Syndicate had a dominant performance, putting up an impressive 166.06 points. Patrick Mahomes led the way with 28.98. | Five Split Safety starters cleared 23 points. Skat’s third-best scorer was the kicker. |
| Sixty-five points is not a bad matchup. It is a solvency event. | ThePeopleBeaters started Dart (0.8), Goedert (1.4), and the Chiefs defense (1.0). |
| Undefeated on 95.58 is a warning label, not a coronation. | Their top scorer had 18.1 and they won because the other team didn’t start a kicker. |
| White alone clears the margin. (It doesn’t: swapping White’s 14.3 for either benched starter gains at most 10.7, under 11.44.) | That swap was worth 20.4 points in an 11.44-point loss. |

## Banned phrases

The build linter (`python3 newsletter/build.py --lint`) reads this list. Keep one phrase per line in the format shown. Matching is case-insensitive and whole-word.

<!-- banned:start -->
- `dominant performance`
- `statement win`
- `make a statement`
- `on notice`
- `let that sink in`
- `make no mistake`
- `at the end of the day`
- `it is what it is`
- `a win is a win`
- `showed up and showed out`
- `came to play`
- `brought their A game`
- `firing on all cylinders`
- `led the way`
- `put up`
- `impressive`
- `incredible`
- `insane`
- `massive`
- `huge`
- `elite`
- `solid performance`
- `masterclass`
- `clinic`
- `game-changer`
- `league winner`
- `went off`
- `exploded for`
- `feast`
- `smash`
- `cooked`
- `chef's kiss`
- `beast mode`
- `levels to this`
- `buckle up`
- `strap in`
- `without further ado`
- `in the books`
- `another week in the books`
- `when the dust settled`
- `a tale of two halves`
- `the rest is history`
- `only time will tell`
- `time will tell`
- `remains to be seen`
- `looking to`
- `bounce back`
- `silence the critics`
- `doubters`
- `arguably`
- `on paper`
- `receipts`
- `the receipt`
- `audit`
- `solvency`
- `insolvent`
- `filing`
- `process failure`
- `autopsy`
<!-- banned:end -->

## Anti-patterns

These are the habits that made past issues read badly. The linter catches some; you catch the rest on the edit pass.

- **Filler.** Openers like "What a week it was" or "Week 3 is in the books." Start with the story.
- **Restating stats without a take.** "Allen scored 40.82. McCaffrey scored 22.6." is a box score, not writing. Every number needs a reason to be in the sentence.
- **Vague praise or hype.** "Impressive," "huge," "dominant," "elite." Say what happened instead.
- **Em dashes.** No more than three in the whole issue, none in headlines. Use a period or a comma.
- **Exclamation marks and emoji.** None, except inside team names.
- **The "It's not X. It's Y." move.** Once per issue at most. Past issues leaned on it until it stopped meaning anything.
- **Extended metaphors.** No running bits about ledgers, audits, filings, solvency, receipts, or autopsies. One image, once, then move on.
- **Number soup.** More than three numbers in one sentence. Pick the one that makes the point.
- **Invented context.** Only say why something happened (injury, bye, a benching, a career high) if the brief says so, from the ESPN recap or the Sleeper injury status. If the brief has a stat line but no reason, give the line and stop. "Rice played 6 snaps" is a fact; "Rice got hurt" needs the recap that says it.
- **Fantasy points with no football.** A recap that only trades fantasy scores ("won 162.88 to 133.30 behind 31.3 from Williams") is half the job. Say what Williams did on the field.
- **Rhetorical questions.** Answer them instead.
- **Clones.** Twelve blurbs of the same length, built the same way, starting with the same word.
- **Mean for no reason.** If a line would sting without being funny, cut it.
- **Labels instead of English.** No "W2," "PF/PA," "EP," or internal jargon in prose. "Points against" is fine; "PA" belongs in a table header.

## Section order (fixed)

Every issue has these sections in this order. Never reorder, rename, or drop one.

1. **Masthead**: league name, then one line with the week, month, and "presented by Unsportsmanlike Conduct." Nothing else: no format line, no note about data sources.
2. **Lead story**: one headline, one dek, three or four paragraphs, and up to three big stats. No byline. Pick the single most surprising specific fact of the week and build around it.
3. **Power rankings**: all 12 teams **in Elo order** (see "Elo" below), each with manager, record, Elo rating, this week's Elo change, and a two-to-three-sentence take. No intro line. The order is not opinion; the takes are. Takes can still talk about points.
4. **Matchup recaps**: the "Find your team" list (built automatically), then all six games, each with both team names and managers, final score, margin, a headline, one paragraph that explains the result through real stat lines and game context, and two key performers per side, each with NFL team, fantasy points, and box-score line.
5. **Awards and standouts**: four or five awards, each citing at least one real box-score stat, then the top starter at each position with its stat line, then one bench note, then the injuries to rostered players that the brief reports. No intro lines, and no standalone list of NFL results.
6. **Transactions**: the callout (`asides.transactions`), then waiver claims with FAAB and a letter grade, then trades, then free-agent adds. No summary paragraph. If there were no trades, say so in one line; don't drop the block.
7. **Next week**: all six upcoming matchups with one line each.

## Elo

The power rankings are ordered by Elo, computed by `fetch_week.py` (`elo_ratings`) from the league's real head-to-head results for weeks 1 through N and written into the brief's **Elo** table. Never compute it by hand and never reorder the rankings for taste. `build.py` stops the build if the rankings don't match the brief's Elo order and values.

- **Starting rating:** every team starts the season at 1000.
- **Expected score:** for team A against team B, \(E_A = 1 / (1 + 10^{(R_B - R_A)/400})\).
- **Result:** 1 for a win, 0.5 for a tie, 0 for a loss, from the two teams' fantasy scores that week.
- **Update:** \(\Delta = K \times (S_A - E_A)\) with **K = 32**, rounded to two decimals. The loser's change is exactly the negative of the winner's. All of a week's games update at once from the ratings going into that week, and each week's new rating is stored to two decimals.
- **Margin of victory doesn't count.** Winning by 0.5 or by 60 moves the rating the same. That's why a team can rank high on few points; say so in the take when it matters.
- **Ties in the order** are broken by wins, then season points for.
- This is the method behind the published Week 2 issue (`2026-week2.html`): it reproduces that issue's post-Week 2 Elo for all 12 teams.

In the issue, `elo` is the rating with two decimals ("1029.33") and `elo_change` is this week's change with a sign ("+14.80", or "−18.91" with a real minus sign). Copy both from the brief.

## Facts: the brief is the only source

- **Every number must come from the week's data brief** (`brief.md` / `brief.json` next to the issue) or be simple arithmetic on brief numbers (sums, differences, ranks). Check every derived number twice; the Week 2 issue shipped a wrong one. `python3 newsletter/build.py --check-facts <issue.json>` lists every number in the copy that isn't in the brief verbatim. Each one it prints is either derived (recompute it by hand) or wrong.
- **Which source wins.** Each kind of fact has one source of truth:
  - Fantasy points, lineups, bench, standings, records, transactions, and FAAB: the league on Sleeper. Fantasy points always come from the league matchups (`players_points`), never from Sleeper's generic PPR totals, because this league's scoring differs (Burrow scored 23.72 here and 25.72 under Sleeper's default).
  - Box-score lines (yards, catches, targets, carries, touchdowns, interceptions, snaps, kicks, sacks): Sleeper's NFL weekly stats. When ESPN prints a different number, use Sleeper's. In Week 4 ESPN's recap gave Tee Higgins 151 receiving yards; Sleeper has 157, which is what his 26.7 fantasy points add up to.
  - Game results, venues, game context, quotes, injuries during the game, career highs, and records: ESPN's scoreboard and game recaps. Attribute anything you'd only know from a recap ("according to ESPN", "per ESPN").
  - Injury status for next week: Sleeper's status at fetch time (Questionable, Out, IR), as listed in the brief.
- **Don't use outside knowledge.** No NFL news, depth charts, projections, trade values, or reasons that the brief doesn't contain. If it isn't in the stat lines or the ESPN text in the brief, it isn't in the issue.
- **Match players by ID, not name.** Sleeper has duplicate names (two Kenneth Walkers, several Johnsons). The fetcher joins on `player_id`; if you look something up by hand, do the same. ESPN and Sleeper also disagree on some team codes (ESPN `WSH` is Sleeper `WAS`); the fetcher maps them.
- **Superlatives need the full list.** Before writing "highest," "lowest," "only," or "career high," sort the full data and confirm, or quote the recap that says it.
- **Copy numbers as given.** Team scores in tables use two decimals (`147.60`). Prose can use the brief's own precision (`147.6`).
- **Keep transaction windows straight.** Label which waiver run each move belongs to (the brief gives the processed time in UTC), and don't add free-agent moves into FAAB totals.
- **Missing data is marked, never invented.** If something can't be fetched (an API is down, a game hasn't finished), leave it out or fill it with placeholder content and set that section's `is_sample` flag, which prints a visible "Sample data" label, plus a note that says what is placeholder. Say so in the PR. Never present an invented number as real.
- **Opinions are labeled as opinions.** Ranking takes and grades are opinion; the rankings order (Elo), scores, records, stat lines, and FAAB are facts.
- **The NFL games block in the brief is context, not a section.** Use it for finals, game situations, and ESPN quotes inside the recaps, lead, and awards. The issue no longer lists every NFL result.

### What the brief must contain

Run `python3 newsletter/fetch_week.py --week <N>` (defaults: season 2026, the league above, output `newsletter/issues/<season>-week<N>/`). It writes `brief.md` (read this), `brief.json` (the same data, structured), and `raw/` (every API response it used, trimmed to rostered players). Commit all three with the issue. The brief must contain:

| Part | What it holds | Source |
| --- | --- | --- |
| Sources and fetch time | Every URL used and when it was pulled | the fetcher |
| Standings | W-L, points for and against, and week-by-week results for all 12 teams | Sleeper `/league/<id>/matchups/1..N` and `/rosters`, `/users` for names |
| Elo | Every team's rating, this week's change, and its rating after each week, in power-rankings order, with the formula | Computed by `fetch_week.py` from Sleeper `/league/<id>/matchups/1..N` (see "Elo") |
| Fantasy matchups | All six games: final, margin, every starter and bench player with league fantasy points | Sleeper `/league/<id>/matchups/<N>` |
| NFL stat line per player | For each of those players: NFL team, a plain-words box-score line (passing, rushing, receiving, fumbles, snaps, kicks, defense), and their NFL game's final | Sleeper `api.sleeper.com/stats/nfl/<season>/<N>`, joined on `player_id`; players from `/v1/players/nfl` |
| NFL games | Every final, date, venue, ESPN's recap headline and text, scoring plays, and the pregame injury report (context for the copy, not printed as a list) | ESPN `site.api.espn.com/.../nfl/scoreboard` and `/summary?event=<id>` |
| Transactions | Waivers (with bids, failed competing bids and their reasons), free agents, and trades (players and picks), with UTC times, for this week's leg and the waiver run after it | Sleeper `/league/<id>/transactions/<N>` and `/<N+1>` |
| FAAB used | Per team, at fetch time | Sleeper rosters |
| Next week | The six fantasy pairings, the NFL schedule, and byes | Sleeper `/matchups/<N+1>`, ESPN scoreboard for week N+1 |
| Injury status | Every rostered player with a Sleeper injury status at fetch time | Sleeper `/v1/players/nfl` |

A brief fetched before Elo was added can get its Elo table offline from its saved matchups: `python3 newsletter/fetch_week.py --week <N> --elo-from-raw`.

If the fetcher fails on a source, fix and rerun it rather than writing around the gap. If a source really is unavailable, note the gap at the top of `brief.md`, mark the affected sections as sample data, and say so in the PR.

## Producing an issue from a brief

1. **Fetch.** `python3 newsletter/fetch_week.py --week <N>` after the Wednesday waiver run has processed (in Week 4 it ran at 07:04 UTC Wednesday), so the brief has the final scores and the claims. Check the brief's standings against Sleeper's app if anything looks off.
2. **Read the brief end to end.** Then write a private fact sheet: every team's score, record, top and bottom starters with their stat lines, notable bench points, every transaction, and the injuries the recaps mention. You will check copy against this sheet.
3. **Find the story.** List the three most surprising facts of the week, fantasy or football. The best one is the lead; the others become awards or ranking blurbs. The best stories usually sit where the two meet: a fantasy decision that the box score made look terrible, or a real game that swung a fantasy one.
4. **Start from the last issue.** Copy `newsletter/issues/2026-week4/issue.json` to `newsletter/issues/<season>-week<N>/issue.json` and replace every field. Keep the structure; the template fails the build on missing keys.
5. **Write in section order.** Lead first, then rankings (copy the order, `elo`, and `elo_change` from the brief's Elo table, then write the takes), recaps, awards and standouts, injuries, transactions, next week. For every recap, open the brief's matchup block and pull the stat lines of the players who decided it before you write a word.
6. **Edit pass.** Read every item against the voice rules, the anti-patterns list, and the fact sheet. Cut the weakest sentence in each blurb. Make sure no two ranking blurbs start the same way.
7. **Lint.** `python3 newsletter/build.py --lint newsletter/issues/<season>-week<N>/issue.json` must print nothing. It checks the banned list and punctuation, and that the issue meets schema 3: the lead, every recap, and every award cite box-score stats; every key performer and standout has an NFL team and stat line; recaps name both managers; and the rankings are in Elo order with the same ratings and changes as `brief.json`. Fix the copy, don't edit the banned list to get it to pass.
8. **Check the numbers.** `python3 newsletter/build.py --check-facts newsletter/issues/<season>-week<N>/issue.json` and recompute every number it lists.
9. **Render.** `python3 newsletter/build.py --data newsletter/issues/<season>-week<N>/issue.json --out <season>-week<N>.html` (repo root, same as `2026-week2.html`). Without `--out` it writes `issue.html` next to the issue JSON, which is how to preview a draft without touching the repo root. The build refuses to render an issue that fails schema 3 or whose Elo doesn't match the brief.
10. **Check it on a phone width.** Open the output headless at 390px wide; confirm no horizontal scroll, no `{{` left in the page, no requests other than `data:` URLs, and that every name in "Find your team" jumps to that team's card. Take full-page and first-screen screenshots at phone and desktop widths for the PR.
11. **Fact-check last.** Go through the rendered page top to bottom and tick every number against the fact sheet.
12. **Ship as a draft PR.** New branch, commit the brief, `raw/`, the JSON, and the HTML, and open a draft PR with the screenshot. Do not merge: GitHub Pages serves `main`, so merging publishes. Never edit an already-published week unless the owner asks.

### Field guide (schema 3)

Copy is inserted as raw HTML, so you can use `<em>` or `<strong>`, and you must write `&amp;` for a literal ampersand.

| Field | What goes in it |
| --- | --- |
| `schema` | `3`. The build refuses to render anything else. |
| `meta` | `title`, `league`, `issue` ("Week 5"), `issue_number`, `season`, `week`, `dateline`, and `presented_by`. |
| `lead` | `kicker`, `headline` (under 60 characters, a fact plus a turn), `dek` (one sentence), `stats` (exactly three `{value, label}`; the first is the hero number), `body` (three or four paragraphs, at least one real stat line). |
| `asides` | One short note per section: `lead`, `rankings`, `recaps`, `awards`, `transactions`, `preview`, each `{figure, text}`. `figure` is a number from the brief ("23.8", "$5"); `text` finishes the sentence. Card Back prints these as callouts; the transactions one is the section's opener. |
| `rankings` | Twelve `{rank, team, manager, record, elo, elo_change, take}` in the brief's Elo order. `elo` and `elo_change` are copied from the brief's Elo table; `take` is two or three sentences of opinion and may cite points. |
| `recaps` | Six `{headline, winner, w_manager, w_score, loser, l_manager, l_score, margin, body, w_keys, l_keys}`. Managers are display names from the brief. `body` explains the result through real stat lines. Keys are two per side, `{player, nfl_team, pts, line}`, where `line` is the box-score line in short form ("13 rec on 13 targets, 119 yds"). |
| `awards` | Four or five `{name, winner, stat, body}`; every `body` cites a real box-score stat. Keep award names consistent week to week where they fit (Manager of the Week, Lineup Crime, Floor of the Week, Best Performance in a Loss). |
| `standouts`, `bench_note` | Top starter at QB, RB, WR, TE, K, DEF as `{pos, player, nfl_team, team, pts, line}`, plus one bench sentence. |
| `injuries` | `{player, nfl_team, team, note}` for rostered players the recaps or Sleeper report hurt; `[]` if none. |
| `transactions` | `stats` (three `{value, label}`), `waivers` (`{team, add, pos, nfl_team, drop, faab, grade, note}`; `drop` and `nfl_team` may be `null`), `free_agents_label`, `free_agents` (`{team, add, pos, nfl_team, drop, note}`), `trades` (`{teams, date, summary, grade, note}`, or `[]`), and `no_trades` (the line shown when `trades` is empty). Notes should cite the player's real line where it matters. |
| `preview` | `is_sample` (true if anything is placeholder), `label`, `note` (byes and anything unusual, like a London game), and six `{a, b, line}`. |
| `footer` | `methods` (how the sources were used), `sources` (`{name, url}` list), and `credit`. |

`build.py` adds layout-only fields before rendering: `recap_index` (the "Find your team" list, every team alphabetically with its result and card) and `elo_up` on rankings. Don't write those by hand.
