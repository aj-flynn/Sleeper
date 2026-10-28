# Weekly data and continuity

`config.json` binds season, league ID and rules. Stable identity is `(league_id, season, roster_id)`, never a changing team name. `data/2026/history.json` contains per-week scores, opponents/results, cumulative W/L/T/PF/PA, Elo, transactions/FAAB and observed team labels through Week 7. New observations retain earlier labels rather than renaming past records. Unknown historical effective dates stay null.

`elo/2026.json` uses the existing implementation in `elo.apply_week` and `fetch_week.elo_ratings`: start 1000, K=32, no margin-of-victory factor, two-decimal equal/opposite changes. Ties use 0.5; twelve-team total stays 12000. Existing weeks 0–5 are preserved; audited source weeks 6–7 are appended. The original Week 7 source had damaged earlier name encodings, so existing repo labels remain. Its original Elo file is retained with the Halloween reference.

`data/2026/week7-capture/` holds compact public API fields and ordinary source URLs/retrieval times. Full player catalogs, avatars and unrelated user metadata are excluded. Capture reporting boundaries and retrieval time are separate: this is a later retrieval reconstructing the historical window, and later stat corrections may exist. Current injury lists are excluded. Articles need dated pre-cutoff publication; a late final-status read alone is insufficient for historical completion. Empty MCP news/injury caches mean missing coverage, not healthy players.

A draft directory contains raw-data-derived `brief.json`/`brief.md`, `candidate-history.json`, `elo.json`, `period-transactions.json`, `draft.json` (week/cutoff/theme only), the written `issue.json` and rendered `issue.html`. These are working data, not approval paperwork. Legacy `run.py` and direct `fetch_week.py` remain for older issues; use `weekly.py` for new work because the legacy runner has model assumptions and an older reporting window.

## Results, moves and budgets

All 12 distinct roster IDs must appear once in six two-team games. Every score matches starter totals and player points; zero is valid. Standings use completed games only. Ties are recorded as T, with no Elo winner; the team jump list says Tied. NFL byes affect players, not fantasy pairings. Missing partners, postponed/incomplete games, league-median scoring or playoffs stop the regular-season path until the appropriate rules are implemented. Current league has no median game and playoffs begin week 15.

Transactions deduplicate by transaction ID. Conflicting versions require investigation. Reporting-period moves use `status_updated` in `[start,end)`, retaining drop-only moves. Failed bids remain separate and never count as completed moves/spending. FAAB uses all captured legs through cutoff, zero bids, transfers and completed claims, reconciled to the roster counters after reversing later spending. Known commissioner grants may be recorded in `config.faab_adjustments` as `{roster_id, amount, effective_at, reason, evidence}`; unexplained counter changes require investigation. No made-up balancing adjustments.

## Reruns and recovery

A small exclusive lock prevents two runs writing the same output. Check its PID before removing a stale lock. Capture uses a fresh folder; if interrupted, keep it for diagnosis and start another folder. Preparation writes a complete directory atomically. Identical reruns preserve the existing draft; changed data uses a new revision folder. This prevents double-counting or accidentally replacing written copy. `prepare --record` saves the weekly data to the season ledger under a separate lock; it never publishes the newsletter. Without `--record`, fixture/trial runs leave saved season data alone.

For a score correction/backfill, keep the original source data, obtain the corrected records, and recompute from the last trustworthy week before the change through every later completed week. Rebuild W/L/PF/PA and every affected Elo week together. Never patch one Elo row while retaining later ratings based on the wrong result. Normal recording refuses conflicting earlier results. Record the correction reason in the data and deliberately replace the corrected history/Elo; no extra approval ceremony is required for data maintenance.

For season rollover, create a new season config with the verified Sleeper league ID, check format and playoff/median rules, start its 12 IDs at 1000 in week 0, and create a separate `data/<season>/` namespace. Pass `--config` and `--baseline`; defaults intentionally remain 2026. Retain prior seasons and document team/owner mapping where known.

The bundled Windows Eastern timezone file comes from IANA via tzdata 2026.6, with its license files included. The host timezone database is preferred. Update the fallback deliberately if Eastern rules change.

The 07:00 capture is explicitly provisional and records actual capture coverage plus the scheduled 08:00 cutoff. It does not promote season history. Finalization refreshes all relevant data at or after 08:00. `publication-state.json` separately records published week/link and chat send state/receipt so retries and silent corrections do not re-announce a newsletter. A sending/unknown outcome must be reconciled in the real chat before another send. Week 7 2026 is already recorded as announced.
