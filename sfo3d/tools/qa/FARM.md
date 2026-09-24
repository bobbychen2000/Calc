# Render farm (cloud sessions) for high-resolution QA renders

Measured 24 Sep 2026 (test session, idle 4-core container, Mesa llvmpipe): 2 views at 2560x1440,
`?quality=ultra&fixedres=1`, rendered in 677 s including page load (about 5.6 min per view).
The main session's container is saturated while workflows run, so high-resolution renders go to worker sessions.

Constraints learned from the test:
- A worker session's permitted push target is the parent's working branch (`claude/sfo-live-3d-handoff-er667m`);
  `outcome_branch` did not take effect, and pushing to another branch was refused by the permission check.
- Workers cannot message back; the parent polls with get_session and `git fetch`.

Worker recipe (one worker per view batch, ~6 views):
1. `cd sfo3d && npm ci --no-audit --no-fund` (Chromium is preinstalled at /opt/pw-browsers).
2. `SOFTGL=1 W=2560 H=1440 QS='&quality=ultra&fixedres=1' SETTLE=6000 PREFIX=<round>_<batch> VIEWS="<views>" node livetest.mjs jobs/qa3.mjs`
3. Convert to JPEG q92 (keeps history small), put under `sfo3d/renders/<round>/`, `git add -f`, commit,
   `git pull --rebase origin claude/sfo-live-3d-handoff-er667m && git push origin HEAD:claude/sfo-live-3d-handoff-er667m`
   (retry on non-fast-forward).
