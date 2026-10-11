# Voice, banned phrases, and anti-patterns

Read by the writer before every draft and by the editor before every review. `newsletter/build.py` reads the banned list from this file (between the `banned:start` and `banned:end` markers), so this is the one place to change it.

The owner's two complaints about past issues were that the design was poor and the writing was poor. The Card Back template solved the design. The writing has to be solved again every week, and this file is the bar.

## The voice

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
10. **Football first, then fantasy.** A fantasy score is the result; the stat line and the game are the story. "Kyren Williams scored 36.7" is a number. "Kyren Williams ran for two touchdowns in the last four minutes of the Rams’ comeback and caught 10 passes" is why the number happened. Every recap and the lead must cite real box-score numbers (yards, catches, carries, touchdowns, snaps, field goals), and the schema gate fails if they don't.

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

`python3 newsletter/build.py --lint` (and the `issue.lint` gate) fails the issue if any of these appear. Keep one phrase per line in the format shown. Matching is case-insensitive and whole-word, and team names are ignored. Fix the copy; never edit this list to get a draft through.

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

These are the habits that made past issues read badly. Items marked **(lint)** fail the `issue.lint` gate automatically; the editor catches the rest.

- **Filler.** Openers like "What a week it was" or "Week 3 is in the books." Start with the story.
- **Restating stats without a take.** "Allen scored 40.82. McCaffrey scored 22.6." is a box score, not writing. Every number needs a reason to be in the sentence.
- **Vague praise or hype.** "Impressive," "huge," "dominant," "elite." Say what happened instead. **(lint, for the banned words)**
- **Em dashes.** No more than three in the whole issue, none in headlines. Use a period or a comma. **(lint)**
- **Exclamation marks and emoji.** None, except inside team names. **(lint)**
- **The "It's not X. It's Y." move.** Once per issue at most. Past issues leaned on it until it stopped meaning anything. **(lint)**
- **Extended metaphors.** No running bits about ledgers, audits, filings, solvency, receipts, or autopsies. One image, once, then move on.
- **Number soup.** More than three numbers in one sentence. Pick the one that makes the point.
- **Invented context.** Only say why something happened (injury, bye, a benching, a career high) if the brief says so, from the ESPN recap or the Sleeper injury status. If the brief has a stat line but no reason, give the line and stop. "Rice played 6 snaps" is a fact; "Rice got hurt" needs the recap that says it.
- **Fantasy points with no football.** A recap that only trades fantasy scores ("won 162.88 to 133.30 behind 31.3 from Williams") is half the job. Say what Williams did on the field. **(schema gate, for recaps, the lead, and awards)**
- **Rhetorical questions.** Answer them instead. **(lint: no question marks)**
- **Clones.** Twelve blurbs of the same length, built the same way, starting with the same word. **(lint: no two ranking takes may start with the same word)**
- **Mean for no reason.** If a line would sting without being funny, cut it.
- **Labels instead of English.** No "W2," "PF/PA," "EP," or internal jargon in prose. "Points against" is fine; "PA" belongs in a table header. **(lint)**
