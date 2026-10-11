# The league and the Elo ratings

## Rebuilders Anonymous

- Sleeper league ID `1319718857249665024` (2026 season). `fetch_week.py` uses it by default.
- 12 teams, dynasty, Superflex, full PPR. Scoring: 1 per catch, 0.1 per rushing or receiving yard, 6 per rushing or receiving TD, 0.04 per passing yard, 4 per passing TD, minus 2 per interception or lost fumble.
- Starting lineup: QB, 2 RB, 2 WR, TE, 2 FLEX, Superflex, K, DEF, plus 8 bench spots. Playoffs start in Week 15.
- $200 FAAB per season, blind bids. Waivers process once a week, early Wednesday UTC. Startup was a $1,000 auction (the draft review is `rebuilders-anonymous-draft-review.html`).
- The newsletter is "Presented by Unsportsmanlike Conduct" (UC), the house brand. UC gets roasted like everyone else, a little harder if anything.
- Team names change. Use exactly the names in the brief, with their casing and punctuation (`hammball` is lowercase, `Micah parsons fan club` has one capital, `J’Allen Waffle Stompers` and `Skat’s BruteForce Theorem` use curly apostrophes, `WELL! It's The Big Shough` keeps its exclamation mark). The brief uses the Sleeper team name and falls back to the manager's display name when a team has none.
- Week 4 teams and managers: Split Safety Syndicate (kylejones10), Micah parsons fan club (Packersfan1992), Dak Side of the Sun (SweetRavenge84), Mendozareamazingpicks (DarknessMonster), J’Allen Waffle Stompers (BigJohnDeBo008, called J’Alle in Week 2), Unsportsmanlike Conduct (JeffyWaterton), Kingslayers (maierz3948), hammball (hammball), ThePeopleBeaters (ThePeopleBeaters), WELL! It's The Big Shough (KaranLuvSport), Rams of Steel (iemerson969), Skat’s BruteForce Theorem (LittleTimmyFlynn). The draft review uses older names; never use those unless the brief does.
- Past issues: `2026-week2.html` (published, repo root) and the Week 4 issue in `newsletter/issues/2026-week4/`. Read Week 2 for data shape only; it predates the voice and the NFL-stat rules.

## Elo

The power rankings are ordered by Elo, a rating system from chess: every win takes points from the loser, and beating a higher-rated team takes more. `fetch_week.py` (`elo_ratings`) computes it from the league's real head-to-head results for weeks 1 through N and writes it into the brief's **Elo** table. Never compute it by hand and never reorder the rankings for taste. The `issue.facts` gate fails the issue if the rankings don't match the brief's Elo order and values, and `brief.valid` recomputes the ratings from `raw/` to make sure the brief is right.

Each week's ratings are also written to `newsletter/elo/<season>.json`, keyed by week and then Sleeper `roster_id`, with the team name and Elo. Week 0 is the 1000 baseline for every team. The brief step reads weeks 0 through N-1 from that file, applies this week's games to the recorded week N-1 ratings, and writes only week N. Rerunning a week overwrites that week with the same numbers. A recompute that disagrees with a past week fails the brief instead of rewriting history. The 2026 file was backfilled once from weeks 1-4.

- **Starting rating:** every team starts the season at 1000.
- **Expected score:** for team A against team B, \(E_A = 1 / (1 + 10^{(R_B - R_A)/400})\).
- **Result:** 1 for a win, 0.5 for a tie, 0 for a loss, from the two teams' fantasy scores that week.
- **Update:** \(\Delta = K \times (S_A - E_A)\) with **K = 32**, rounded to two decimals. The loser's change is exactly the negative of the winner's. All of a week's games update at once from the ratings going into that week, and each week's new rating is stored to two decimals.
- **Margin of victory doesn't count.** Winning by 0.5 or by 60 moves the rating the same. That's why a team can rank high on few points; say so in the take when it matters.
- **Ties in the order** are broken by wins, then season points for.
- This is the method behind the published Week 2 issue (`2026-week2.html`): it reproduces that issue's post-Week 2 Elo for all 12 teams. The test suite pins the post-Week 4 values.

A worked example from Week 1: everyone is at 1000, so every expected score is 0.5 and every winner gains \(32 \times (1 - 0.5) = 16\). That's why the brief shows six teams at 1016.00 and six at 984.00 after Week 1.

In the issue, `elo` is the rating with two decimals ("1029.33") and `elo_change` is this week's change with a sign ("+14.80", or "−18.91" with a real minus sign). Copy both from the brief.
