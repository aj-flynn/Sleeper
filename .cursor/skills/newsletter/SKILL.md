---
name: newsletter
description: Write and build the weekly Rebuilders Anonymous fantasy football newsletter from a week's data brief. Use for any request to draft, write, edit, fact-check, or render a Rebuilders Anonymous issue, recap, power rankings, or awards.
---

# Rebuilders Anonymous newsletter

The weekly newsletter for **Rebuilders Anonymous**, a 12-team dynasty league on Sleeper. Each week you get a data brief and produce one self-contained HTML issue. The owner's two complaints about past issues were that the design was poor and the writing was poor. The design is solved by the templates. The writing is on you, every week. This file is the bar.

## Chosen template

<!-- The owner has not picked yet. When they do, replace TBD with broadsheet, ledger, or night-edition. -->

```
CHOSEN_TEMPLATE: TBD
```

| Template | Source | Sample |
| --- | --- | --- |
| The Broadsheet | `newsletter/templates/src/broadsheet.html` | `newsletter/templates/broadsheet.html` |
| The Ledger | `newsletter/templates/src/ledger.html` | `newsletter/templates/ledger.html` |
| Night Edition | `newsletter/templates/src/night-edition.html` | `newsletter/templates/night-edition.html` |

While `CHOSEN_TEMPLATE` is `TBD`, render the issue in all three templates (step 7) and say in the PR that the owner still needs to pick. Once it is set, render only the chosen one and do not restyle it per issue.

## The league

- 12 teams, dynasty, Superflex, full PPR, 4-point passing touchdowns.
- Starting lineup: QB, Superflex, 2 RB, 2 WR, TE, 2 FLEX, K, DEF.
- $200 FAAB per season. Startup was a $1,000 auction (the draft review is `rebuilders-anonymous-draft-review.html`).
- The newsletter is "Presented by Unsportsmanlike Conduct" (UC), the house brand. UC gets roasted like everyone else, a little harder if anything.
- Team names change. Use exactly the display names in the brief, with their casing and punctuation (`hammball` is lowercase, `Micah parsons fan club` has one capital, `J’Alle` uses a curly apostrophe, `WELL! It's The Big Shough` keeps its exclamation mark). The Week 2 names were: Unsportsmanlike Conduct, J’Alle, Split Safety Syndicate, Micah parsons fan club, Dak Side of the Sun, Mendozareamazingpicks, ThePeopleBeaters, WELL! It's The Big Shough, Skat’s BruteForce Theorem, hammball, Kingslayers, Rams of Steel. The draft review uses older names; never use those unless the brief does.
- Past issues: `2026-week2.html` (published, repo root). Read it for data shape, not for voice.

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

### Examples that hit the bar

All of these use real Week 2 facts.

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
- **Invented context.** Why a player scored 0.0 (injury, bye, benching by his NFL coach) is not in the brief, so you don't know. Say what happened, not why.
- **Rhetorical questions.** Answer them instead.
- **Clones.** Twelve blurbs of the same length, built the same way, starting with the same word.
- **Mean for no reason.** If a line would sting without being funny, cut it.
- **Labels instead of English.** No "W2," "PF/PA," "EP," or internal jargon in prose. "Points against" is fine; "PA" belongs in a table header.

## Section order (fixed)

Every issue has these sections in this order. Never reorder, rename, or drop one.

1. **Masthead**: league name, week, season, "Presented by Unsportsmanlike Conduct."
2. **Lead story**: one headline, one dek, three or four paragraphs, and up to three big stats. Pick the single most surprising specific fact of the week and build around it.
3. **Power rankings**: all 12 teams, each with record, week score, Elo (if the brief has it), and a two-to-three-sentence take. The order is opinion; say so in the intro line.
4. **Matchup recaps**: all six games, each with a headline, final score, margin, one paragraph, and two key performers per side.
5. **Awards and standouts**: four or five awards, then the top starter at each position, then one bench note.
6. **Transactions**: a one-paragraph summary, then waiver claims with FAAB and a letter grade, then trades, then free-agent adds. If there were no trades, say so in one line; don't drop the block.
7. **Next week**: all six upcoming matchups with one line each.

## Facts: the brief is the only source

- **Every number must come from the week's data brief** or be simple arithmetic on brief numbers (sums, differences, ranks). Check every derived number twice; the Week 2 issue shipped a wrong one.
- **Don't use outside knowledge.** No NFL news, injuries, depth charts, projections, trade values, or player first names the brief doesn't give, unless you are certain (e.g., the brief says "D. Smith" for UC and the roster makes it DeVonta Smith). When in doubt, use the initial and last name as written.
- **Superlatives need the full list.** Before writing "highest," "lowest," or "only," sort the full data and confirm.
- **Copy numbers as given.** Team scores in tables use two decimals (`147.60`). Prose can use the brief's own precision (`147.6`).
- **Keep transaction windows straight.** Label which waiver run or week each move belongs to, and don't add free-agent moves into FAAB totals.
- **Missing data is marked, never invented.** If the brief lacks something a section needs (e.g., next week's schedule), either leave the item out or fill it with placeholder content and set the section's `is_sample` flag, which prints a visible "Sample data" label, plus a note that says what is placeholder. Never present an invented number as real.
- **Opinions are labeled as opinions.** Rankings order and waiver grades are takes; scores, records, Elo, and FAAB are facts.

### What the brief should contain

Ask for, or look for, the following. If something is missing, note it in the PR as a gap.

- Final scores for all six matchups and each team's record afterward.
- Starter and bench points by player for every team (needed for lineup-crime and bench notes).
- Elo or any ratings the owner wants carried forward.
- Waiver claims with team, add, drop, FAAB bid, failed competing bids, and the claim date or week.
- Trades and free-agent adds with dates.
- Next week's matchups.
- Season points for and against, if the owner wants them cited.

## Producing an issue from a brief

1. **Read the brief end to end.** Then write a private fact sheet: every team's score, record, top and bottom starters, notable bench points, and every transaction. You will check copy against this sheet.
2. **Find the story.** List the three most surprising facts of the week. The best one is the lead; the others become awards or ranking blurbs. Prefer a fact that says something about a team, not just a big number.
3. **Start from the sample.** Copy `newsletter/sample/sample-issue.json` to `newsletter/issues/<season>-week<N>.json` and replace every field. Keep the structure; the templates fail the build on missing keys.
4. **Write in section order.** Lead first, then rankings, recaps, awards, transactions, next week. Use the field guide below.
5. **Edit pass.** Read every item against the voice rules, the anti-patterns list, and the fact sheet. Cut the weakest sentence in each blurb. Make sure no two ranking blurbs start the same way.
6. **Lint.** `python3 newsletter/build.py --lint newsletter/issues/<season>-week<N>.json` must print nothing. Fix the copy, don't edit the banned list to get it to pass.
7. **Render.**
   - If `CHOSEN_TEMPLATE` is set: `python3 newsletter/build.py --template <CHOSEN_TEMPLATE> --data newsletter/issues/<season>-week<N>.json --out <season>-week<N>.html` (repo root, same as `2026-week2.html`).
   - If it is `TBD`: render each of `broadsheet`, `ledger`, and `night-edition` to `newsletter/issues/<season>-week<N>-<template>.html`.
8. **Check it on a phone width.** Open the output headless at 390px wide; confirm no horizontal scroll, no `{{` left in the page, and no requests other than `data:` URLs. Take a full-page screenshot for the PR.
9. **Fact-check last.** Go through the rendered page top to bottom and tick every number against the fact sheet.
10. **Ship as a draft PR.** New branch, commit the JSON and the HTML, open a draft PR with the screenshot. Do not merge: GitHub Pages serves `main`, so merging publishes. Never edit an already-published week unless the owner asks.

### Field guide

| Field | What goes in it |
| --- | --- |
| `meta` | `title`, `league`, `issue` ("Week 3"), `issue_number`, `season`, `dateline`, `format_line`, `presented_by`, and `sample_notice` (set to `null` or a short note; it prints under the masthead). |
| `lead` | `kicker`, `headline` (under 60 characters, a fact plus a turn), `dek` (one sentence), `byline`, `stats` (exactly three `{value, label}`; the first is the hero number), `body` (three or four paragraphs). |
| `rankings_intro` | One sentence saying the order is opinion. |
| `rankings` | Twelve `{rank, team, record, pts, elo, take}`. `take` is two or three sentences. |
| `recaps` | Six `{headline, winner, w_score, loser, l_score, margin, body, w_keys, l_keys}`. Keys are two `{player, pts}` per side. |
| `awards` | Four or five `{name, winner, stat, body}`. Keep award names consistent week to week where they fit (Manager of the Week, Lineup Crime, Floor of the Week, Best Performance in a Loss). |
| `standouts_intro`, `standouts`, `bench_note` | Top starter at QB, RB, WR, TE, K, DEF as `{pos, player, team, pts}`, plus one bench sentence. |
| `transactions` | `summary`, `stats` (three `{value, label}`), `waivers` (`{team, add, pos, drop, faab, grade, note}`; `drop` is `null` when nothing was dropped), `free_agents_label`, `free_agents`, `trades` (`{teams, summary, grade, note}`, or `[]`), and `no_trades` (the line shown when `trades` is empty). |
| `preview` | `is_sample` (true if any pairing is placeholder), `label`, `note`, and six `{home, away, line}`. |
| `footer` | `methods` (one or two sentences on sources) and `credit`. |

Copy is inserted as raw HTML, so you can use `<em>` or `<strong>`, and you must write `&amp;` for a literal ampersand.
