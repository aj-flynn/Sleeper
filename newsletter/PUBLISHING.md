# Automatic Wednesday publication and one chat link

AJ authorizes this recurring process for Rebuilders Anonymous, league `1319718857249665024`. It hosts each new newsletter on GitHub Pages and announces it once as JeffyWaterton in that league's Sleeper chat. No fresh weekly approval is required. ESPN/wife-league work is outside this authorization and stays draft-only. Do not post a link during tests, replays, historical backfills or silent corrections.

1. Use final data through Wednesday 08:00 America/New_York. `draft.json` must not be provisional. Read `data/publication-state.json` and the chat's existing link history before any send. Week 7 2026 is already published/announced and seeded accordingly.
2. Preserve existing root pages, homepage links and unrelated edits. From current main, commit only this issue's root `<season>-week<week>.html`, its homepage link, weekly source/continuity data and required process changes. Use a scoped branch/PR and merge through normal repository controls. AJ's recurring authorization covers these newsletter commits, pushes and merges; never impersonate his review approval or bypass required protection. Stop/report if repository permissions or required checks prevent publication.
3. GitHub Pages deploys main's repository root through its generated workflow. Wait for its normal successful deployment, open the live page and confirm the intended issue is readable. A push alone is not publication. Keep working-state files on Office between runs; never reset them to discard delivery state.
4. Record the successful live issue (substitute actual season/week/directory):

   ```powershell
   python newsletter/delivery.py published --season 2026 --week 8 --draft newsletter/work/2026-11-04-final-draft --url https://aj-flynn.github.io/Sleeper/2026-week8.html --scheduled
   python newsletter/delivery.py begin-chat --season 2026 --week 8
   ```

   Use `--scheduled` only for a new scheduled issue. A correction omits it and retains the prior chat status. `begin-chat` returns skip for an already announced/historical issue and blocks an uncertain prior send. Its `sending` state is written before the browser action. If another run is active, keep the publication run serialized.
5. In the authenticated Sleeper browser, verify Rebuilders Anonymous and JeffyWaterton. Look for this issue's live URL from JeffyWaterton first. If it is already there, record that actual receipt and send nothing. Otherwise send one short league-appropriate message containing the live link. This is the only chat send for the issue. Use available supported browser controls; there is no stored API credential or unofficial chat-send API here.
6. When the message is visibly present, record the actual receipt, such as its text and visible timestamp or message ID. Do not invent an identifier:

   ```powershell
   python newsletter/delivery.py sent --season 2026 --week 8 --receipt "Actual visible message text/time or message ID"
   ```

   If sending may have happened but confirmation is unavailable, use `delivery.py unknown --season ... --week ... --receipt "What happened"`, stop and report. A later run must inspect the chat and reconcile the actual outcome before any retry. No blind duplicate send. If confirmed present, `sent` records the receipt; if still unknown, remain blocked. A verified not-executed action can be resumed after deliberately clearing that pending state.
7. Save the plain publication/chat state with the ordinary repository workflow. It contains the published week, live URL and real chat receipt, not approval paperwork. Include pending local state when resuming and commit its final update; a state-only deployment never gets another league post.

The current 2026 Week 7 root page includes the revised Halloween design and removal of bench prose from PR 19. Preserve it during process commits. Archived originals are historical references; do not copy them over the current page.
