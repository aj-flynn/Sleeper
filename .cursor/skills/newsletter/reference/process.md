# How a Rebuilders Anonymous issue is made

This file explains the pipeline. The procedure for producing a week is `.cursor/agents/runner.md`. `.cursor/skills/newsletter/SKILL.md` only dispatches to that runner.

Rebuilders Anonymous is a 12-team dynasty fantasy football league on Sleeper. League facts are in [league.md](league.md). Each issue is one HTML page. It has a lead, power rankings, an Elo chart, six matchup recaps, awards, transactions, and the next week's games. The fantasy result is explained through the real box score. The voice is Boston Connor. [The guide](../voice/boston-connor.md) is the only source for tone. Takes can be absurd. Scores, stats, and transactions cannot.

Scripts do every job that has one right answer. Two subagents do the jobs that need judgment. A person approves the draft before anything publishes.

| Step | Who | Model | Gate command |
| --- | --- | --- | --- |
| Fetch, brief, check the brief | runner, via `newsletter/run.py` | `composer-2.5[fast=false]` | `fetch`, `brief`, `check-brief` |
| Write `issue.json` | `writer` | `claude-opus-5-5[effort=high]` | `check-issue` |
| Review the draft | `editor` | `claude-sonnet-5-5[effort=high]` | `record-review`, then `check-review` |
| Fix blocking notes | `writer` | same pin | `check-review` |
| Render, verify, checklist | runner, via `newsletter/run.py` | `composer-2.5[fast=false]` | `render`, `verify`, `checklist` |
| Approve and publish | the owner | none | `approval` |

The model strings are the `model` field in `.cursor/agents/`. `newsletter/run.py` reads them with `agent_model()` and stamps `writer.json` and `review.json`. A review whose model does not match the editor file fails `check-review`.

Opus writes because finding the story and landing it in that voice, without bending a fact, is the reason the newsletter exists. Sonnet reviews because the job is a checklist, and a second model does not share the writer's blind spots. The editor is `readonly`. Composer runs the rest because those steps are script gates and file handoffs. The chart is not copy. Render draws it from `newsletter/elo/<season>.json`. Details are in [design.md](design.md#the-elo-progression-chart) and [league.md](league.md#elo).

An issue is done when all of these are true.

- Every number traces to the brief, or to arithmetic on the brief that the fact check recomputed.
- The lead, every recap, and every award explain the fantasy result with real box-score numbers.
- The writing matches the voice guide. The editor grades every item in [voice-fidelity.md](voice-fidelity.md).
- The page is fine on a phone. No sideways scroll, the team jump list works, fonts are embedded, nothing loads from the network, and the Elo chart is readable at 390px.
- The editor has no open blocking notes, and the owner has approved the pull request.

`verification.json` in the issue folder records each gate. `result` is `pass`, `fail`, or `waiting`. `stopped_at` is the stage that stopped the run. `next_action` says what to do next. `gates` lists every gate with `status`, the command that reproduces it, and `details`.

Run the week after Monday night's game is final and Wednesday waivers have processed, about 07:00 UTC Wednesday. The fetch gate stops early and names what it is waiting for. Fetch, the brief, the checks, and rendering use the Python standard library. Playwright is only for `verify`. Tests are `python3 -m pytest newsletter/tests -q`.

Words used in the other reference files. Brief means `brief.md` and `brief.json`, the only source of facts. Derived number means arithmetic on brief numbers, stored on `issue.json` and recomputed by the fact check. Schema 3 is the current shape of `issue.json`, documented in [issue-schema.md](issue-schema.md). FAAB is the $200 waiver budget. Superflex is a lineup slot that can hold a quarterback. PPR is a point per reception.
