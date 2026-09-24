You're taking over "SFO Live 3D". It's a real-time, interactive 3D simulation of San Francisco International Airport driven by live ADS-B traffic. It was built in an earlier Claude session, and this repository is that work.

1. First read `CLAUDE.md` (the final-state objective, working rules, run and test commands, architecture), then `docs/HANDOFF.md` (history, what was verified, known issues, prioritised task list), then `docs/qa/review_pass1.md`.
2. Look at `docs/qa/current/*.jpg` (the current renders) and `docs/qa/ref/*` (the real airport, from my satellite screenshots).
3. Set up:
   - `git init` and commit a baseline;
   - `npm i -D playwright && npx playwright install chromium`;
   - run `python3 -m http.server 8000` and open `live.html?mode=snapshot`;
   - run `PREFIX=qa VIEWS="view:overview;gate:B26,60,1,14" node livetest.mjs jobs/qa3.mjs` to confirm rendering works on this machine.
   - If I've put my satellite screenshots in `tools/sat/screens/`, run `python3 tools/sat/export_stands.py && python3 tools/sat/check.py`. The output should reproduce `data/sfo_stands.json`.
4. Then work through the task list in `docs/HANDOFF.md` §7 in priority order.
   - Start with adversarial visual QA pass 2: render every component, have an independent reviewer subagent critique the renders against the reference images, fix, and repeat for several passes.
   - Next is the physical-plausibility testing under moving traffic.
   - Then cross-check the inferred stands against OSM / X-Plane gateway data. You have internet access that the previous sandbox lacked.

Rules:
- Never make unverified key assumptions. Check coordinates, dimensions, frequencies, API terms and licences against the original source, or ask me.
- Use the Google imagery only as reference, never as textures.
- Show me renders as you go.
- The goal is quality that surpasses anything on the market, with nothing physically implausible anywhere.
