---
name: newsletter
description: Produce a Rebuilders Anonymous fantasy football issue, or explain how the newsletter is made. Drafting, writing, editing, fact-checking, rendering, power rankings, recaps, and awards go to the runner subagent, which uses scripts plus the writer (Opus) and editor (Sonnet) subagents. Explaining the process or adapting it to another league stays in this skill's reference files.
---

# Rebuilders Anonymous newsletter

Dispatch the week. Do not write the issue, and do not review it.

## Produce a week

Spawn the `runner` subagent with the Task tool. Set `subagent_type` to `runner`. Do not set `model`. The pin is in `.cursor/agents/runner.md`.

Tell the runner the week number, the season when it is not 2026, and the user's request. Then stop.

Do not read the voice guide, the brief, or `issue.json`. Do not run `newsletter/run.py` in this chat.

If `runner` is not a registered subagent type, launch a general-purpose subagent on `composer-2.5[fast=false]` and give it the body of `.cursor/agents/runner.md` as its instructions. Then stop.

A request that names a week to produce uses the runner, even when it also asks a question.

## Explain or adapt

Read [reference/process.md](reference/process.md) to explain how an issue is made. Read [reference/adapting.md](reference/adapting.md) to adapt the pipeline to another league. Do not start a run for either of those requests.
