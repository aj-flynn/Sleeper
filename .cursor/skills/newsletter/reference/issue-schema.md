# The issue: section order and schema 3

`issue.json` is the writer's output and the template's input. The `issue.schema` gate checks it (`python3 newsletter/build.py --schema`), including a dry-run render, so a missing key fails before anything is drawn.

## Section order (fixed)

Every issue has these sections in this order. Never reorder, rename, or drop one.

1. **Masthead**: league name, then one line with the week, month, and "presented by Unsportsmanlike Conduct." Nothing else: no format line, no note about data sources.
2. **Lead story**: one headline, one dek, three or four paragraphs, and exactly three big stats. No byline. Pick the single most surprising specific fact of the week and build around it.
3. **Power rankings**: all 12 teams **in Elo order** (see [league.md](league.md#elo)), each with manager, record, Elo rating, this week's Elo change, and a two-to-three-sentence take. No intro line. The order is not opinion; the takes are. Takes can still talk about points. Directly under the list is the **Elo progression chart**: render draws it from `newsletter/elo/<season>.json` as inline SVG. Not a writer field. Do not put chart copy, a caption, or an `elo_chart` key in `issue.json`.
4. **Matchup recaps**: the "Find your team" list (built automatically), then all six games, each with both team names and managers, final score, margin, a headline, one paragraph that explains the result through real stat lines and game context, and two key performers per side, each with NFL team, fantasy points, and box-score line.
5. **Awards and standouts**: four or five awards, each citing at least one real box-score stat, then the top starter at each position with its stat line, then one bench note, then the injuries to rostered players that the brief reports. No intro lines, and no standalone list of NFL results.
6. **Transactions**: the callout (`asides.transactions`), then waiver claims with FAAB and a letter grade, then trades, then free-agent adds. No summary paragraph. If there were no trades, say so in one line; don't drop the block.
7. **Next week**: all six upcoming matchups with one line each.

## Field guide (schema 3)

Copy is inserted as raw HTML, so you can use `<em>` or `<strong>`, and you must write `&amp;` for a literal ampersand.

| Field | What goes in it |
| --- | --- |
| `schema` | `3`. The build refuses to render anything else. |
| `meta` | `title`, `league`, `issue` ("Week 5"), `issue_number`, `season`, `week`, `dateline`, and `presented_by`. |
| `lead` | `kicker`, `headline` (under 60 characters, a fact plus a turn), `dek` (one sentence), `stats` (exactly three `{value, label}`; the first is the hero number), `body` (three or four paragraphs, at least one real stat line). |
| `asides` | One short note per section: `lead`, `rankings`, `recaps`, `awards`, `transactions`, `preview`, each `{figure, text}`. `figure` is a number from the brief ("23.8", "$5"); `text` finishes the sentence. Card Back prints these as callouts; the transactions one is the section's opener. |
| `rankings` | Twelve `{rank, team, manager, record, elo, elo_change, take}` in the brief's Elo order. `elo` and `elo_change` are copied from the brief's Elo table; `take` is two or three sentences of opinion and may cite points. `elo` has two decimals ("1029.33"); `elo_change` has a sign ("+14.80", or "−18.91" with a real minus sign). |
| `recaps` | Six `{headline, winner, w_manager, w_score, loser, l_manager, l_score, margin, body, w_keys, l_keys}`. Managers are display names from the brief. Scores and margin have two decimals. `body` explains the result through real stat lines. Keys are two per side, `{player, nfl_team, pts, line}`, where `line` is the box-score line in short form ("13 rec on 13 targets, 119 yds"). |
| `awards` | Four or five `{name, winner, stat, body}`; every `body` cites a real box-score stat. Keep award names consistent week to week where they fit (Manager of the Week, Lineup Crime, Floor of the Week, Best Performance in a Loss). |
| `standouts`, `bench_note` | Top starter at QB, RB, WR, TE, K, DEF as `{pos, player, nfl_team, team, pts, line}`, plus one bench sentence. |
| `injuries` | `{player, nfl_team, team, note}` for rostered players the recaps or Sleeper report hurt; `[]` if none. |
| `transactions` | `stats` (three `{value, label}`), `waivers` (`{team, add, pos, nfl_team, drop, faab, grade, note}`; `drop` and `nfl_team` may be `null`), `free_agents_label`, `free_agents` (`{team, add, pos, nfl_team, drop, note}`), `trades` (`{teams, date, summary, grade, note}`, or `[]`), and `no_trades` (the line shown when `trades` is empty). Notes should cite the player's real line where it matters. |
| `preview` | `is_sample` (true if anything is placeholder), `label`, `note` (byes and anything unusual, like a London game), and six `{a, b, line}`. |
| `footer` | `methods` (how the sources were used), `sources` (`{name, url}` list), and `credit`. |
| `derived` | The arithmetic behind every number the brief doesn't print. Not rendered. See [facts.md](facts.md#the-derived-list). |

`build.py` adds layout-only fields before rendering: `recap_index` (the "Find your team" list, every team alphabetically with its result and card), `elo_up` on rankings, and `elo_chart` (the inline SVG and legend). Don't write those by hand.
