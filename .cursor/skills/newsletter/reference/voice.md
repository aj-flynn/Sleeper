# Boston Connor in practice: examples, banned phrases, and the voice checks

**The voice is Boston Connor, and the guide is [`../voice/boston-connor.md`](../voice/boston-connor.md).** That file is the single source of truth for tone, committed verbatim from the owner. Never edit it to fit a draft. This page doesn't add tone rules. It shows the guide applied to real league facts, lists the phrases the lint blocks, and documents the scripted checks that support the guide.

Two things sit outside tone and don't bend for the voice:

- **Facts are sacred.** The guide itself requires accurate scores, stats, injuries, and transactions, and says the irrational reasoning must read as commentary, not news. Absurd takes are opinions about real numbers, never new "facts." See [facts.md](facts.md). The schema and fact-check gates are as strict as ever.
- **Real life is off limits.** Roast lineups, bids, and trades. Leave people's jobs, families, looks, and health out of it. These are friends.

## The delivery structure, applied

Every recap body and the lead story follow the guide's five steps. Ranking takes and award blurbs are shorter and can compress them, but they still open blunt and close short.

1. Open with a blunt opinion or incredulous reaction.
2. Name who's responsible: the fantasy team (and through it, the manager's decision).
3. One legitimate observation: the real box-score line or result from the brief.
4. The exaggerated, irrational, or sarcastic reading of it, clearly opinion.
5. A short punchline.

## Examples that hit the bar

All five use real Week 4 facts from the brief.

> Unbelievable. Unsportsmanlike Conduct, the brand that pays for this newsletter, benched Drake Maye. Maye threw three touchdowns in New England’s 29-26 win at Buffalo, the last one with 1:50 left, and ran for 54 yards. That’s 26.16 points sitting on a bench in a 13.72-point loss. Jalen Hurts started instead and went 12 of 27 for 93 yards. Benching a Patriots quarterback the week he wins in Buffalo should be a crime in this state. Lock ’em up.

The five steps in order: "Unbelievable." (1), UC benched Maye (2), Maye's line and the margin (3), a crime in this state (4), "Lock ’em up." (5). Every number is in the brief; "should be a crime" is plainly opinion.

> Micah parsons fan club won with a quarterback who took one snap. One. Case Keenum pitched to D’Andre Swift for 2 yards on Chicago’s first play, per ESPN, and Tyson Bagent played the rest of the game. Micah won by 29.58 anyway. So the Superflex spot is optional now. Good to know. Bum strategy, great result.

> Rams of Steel had the answer on the bench and picked the wrong guy. Same game, Monday night. Kendre Miller ran 6 times for 9 yards and lost a fumble for New Orleans (1.9). Brian Robinson ran for three touchdowns in Atlanta’s 45-24 win, from the bench (25.7). That swap is 23.8 points in a 16.2-point loss. Start the guy scoring touchdowns. That’s the whole job.

> Tetairoa McMillan caught 14 of 16 targets for 192 yards and two touchdowns. Fine. It was Carolina. Nobody in New England felt a thing. His 45.2 covered the whole 39.84-point margin for ThePeopleBeaters by himself, so the rest of the lineup was along for the ride. One real player and a bunch of passengers.

> Kingslayers left 78.22 points on the bench, the most in the league, and won. How? Rams of Steel scored 105.32, that’s how. Two disasters played each other and one of them had to win. Pathetic. Both of them.

### Before and after

| Instead of this | Write this |
| --- | --- |
| Dak Side of the Sun had an impressive week, putting up a league-high 199.52 points. | Dak Side scored 199.52, most in the league. Seven starters cleared 18 points and the worst of them was Dak Prescott, who threw for 335 yards. Nice week. Wake me up when one of them is a Patriot. |
| Kyren Williams had a huge game with 36.7 points as Dak Side cruised. | Kyren Williams ran for two touchdowns in the last four minutes of the Rams’ comeback in Philadelphia and caught 10 passes. Split Safety scored 160.36, fifth-best in the league, and lost by 39. Fifth-best and a loss. Explain that. You can’t. |
| FRAUD. TOTAL FRAUD. HOCKENSON CAUGHT 13 OF 13 AND IT MEANT NOTHING. UNBELIEVABLE. | T.J. Hockenson caught all 13 passes thrown his way for 119 yards. Thirteen for thirteen. Gronk would’ve caught fourteen. (Caps are for one outburst, not a whole paragraph; this one fails the ALL-CAPS cap.) |
| Gronk never caught 13 of 13 in a game, so Hockenson already has him beat. | Gronk would’ve caught fourteen. (The first is a factual claim the brief can’t support, dressed up as a take. The second is obviously commentary.) |
| Unbelievable. Unbelievable. Kingslayers won. Unbelievable. | Pick the one spot where the outburst lands and say it once. The catchphrase check fails a short sentence used twice in the issue. |

## Banned phrases

`python3 newsletter/build.py --lint` (and the `issue.lint` gate) fails the issue if any of these appear. Matching is case-insensitive and whole-word, and team names are ignored. Fix the copy; never edit this list to get a draft through.

The list blocks three kinds of phrase: **filler** ("in the books," "without further ado"), **sportscaster and AI-sounding clichés** ("statement win," "testament to," "delve"), and **vague praise** ("impressive," "huge," "elite"), plus the running accounting metaphors that sank past issues. It does **not** block the words the guide asks for: *fraud, bum, disaster, embarrassing, unbelievable, pathetic*, occasional profanity, and sports slang. "went off," "smash," and "cooked" came off the list for that reason; use them like a fan would, not as praise.

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
- `stellar`
- `masterclass`
- `clinic`
- `game-changer`
- `league winner`
- `exploded for`
- `feast`
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
- `nail-biter`
- `edge of their seats`
- `delve`
- `testament to`
- `it's worth noting`
- `needless to say`
- `all in all`
- `in conclusion`
- `a reminder that`
- `tapestry`
- `showcase`
- `showcased`
- `receipts`
- `the receipt`
- `audit`
- `solvency`
- `insolvent`
- `filing`
- `process failure`
- `autopsy`
- `house brand`
<!-- banned:end -->

## The voice checks

`issue.lint` measures the parts of the guide a script can count. The thresholds live in `VOICE` in `newsletter/build.py`; change them there and here together. They were tuned on the 2026 Week 4 end-to-end issue (measured values below), which passes with room for a little more heat. The issue-wide caps limit (6) and the average-sentence limit (11 words) sit between that issue and the Week 4 issue from PR #6, written before Boston Connor, which averaged 12.18 words a sentence, so drifting back to the old explanatory voice fails the lint.

| Check | Limit | Supports this line of the guide | Week 4 issue measured |
| --- | --- | --- | --- |
| ALL-CAPS words per section | 3 | "Use occasional ALL CAPS for emotional outbursts." | 2 (lead 1, recaps 2: "PRINT IT", "THROWN OUT") |
| ALL-CAPS words in the issue | 6 | "Avoid excessive yelling." | 3 |
| Average sentence length | 11 words | "Favor short, blunt, declarative statements." | 8.78 words over 276 sentences (the PR #6 Week 4 issue: 12.18) |
| Longest sentence | 32 words | "Avoid long explanations when a dismissive one-liner will do." | 29 |
| Same short sentence (6 words or fewer) twice | 0 | "Avoid ... repeating signature catchphrases." | 0 |
| Same four-word phrase (3+ content words, no names or numbers) in two items | 0 | "Avoid ... repeating signature catchphrases." | 0 |
| Exclamation marks outside team names | 4 | "Avoid excessive yelling." | 0 |
| Swear words | 4 | "occasional profanity" | 1 ("hell") |
| Em dashes | 3, none in headlines | house style; an AI tell | 0 |

How they count:

- **Sections** are lead, rankings, recaps, awards (with standouts, bench note, and injuries), transactions, and preview, each with its callout.
- **ALL-CAPS words** are three or more capital letters that aren't a label: NFL team codes, positions, and terms like TD, FAAB, ESPN, and MVP don't count. Two-letter capitals don't count either; they're nearly always initials or nicknames (AJ, PB).
- **Sentences** are measured in prose only: the dek, lead body, ranking takes, recap headlines and bodies, award bodies, the bench note, injury notes, transaction notes, preview lines, and callouts. Stat lines, names, and scores aren't prose. Decimals (23.8), initials (T.J.), and "vs." don't end a sentence.
- **Catchphrases**: injury status lines like "Questionable." or "Sleeper: questionable (hamstring)." are data, so they may repeat across players. Everything else counts, including transaction notes: "Wednesday run." on six waiver claims is a catchphrase.

Also still checked: no emoji, at most one "It's not X. It's Y." (an AI tell), no internal labels like "W2" or "PF" in prose, and no two ranking takes opening with the same word. Rhetorical questions are allowed now; the guide wants them.

What only the editor can judge, item by item against the guide, is in the editor's voice-fidelity checklist: [voice-fidelity.md](voice-fidelity.md).
