# Requests to sfo3d (from sha3d Phase 0, 2026-11-13)

sha3d does not modify `sfo3d/`. These are findings from the sha3d research that affect sfo3d. The sfo3d owner or
session decides on each.

## R1. adsb.lol is now metered: 500 requests/day per IP without a key (high)

- **Source:** `https://api.adsb.lol/api/openapi.json`, read 2026-11-13 (sha3d `docs/phase0/adsb.md` §2.1, facts F2;
  confirmed by the adversarial verifier in `docs/phase0/verify_licences_law.md`).
  - Quote: "No key: **500 requests/day per IP**." Over quota the API returns `429` with `Retry-After`.
  - The documentation disagrees on the daily window: the OpenAPI says "a fixed 24h bucket, not midnight UTC", while
    the docs page says "resets at 00:00 UTC".
  - Feeder keys get 7,200 requests a day. Sponsor plans cost EUR 20–999 a month.
  - The data licence is unchanged: ODbL 1.0.
- **Effect on sfo3d:** `sfo_live_server.py` polls adsb.lol "every 1.0–1.5 s (random)" (docstring, line 31). The AIMD
  floor reacts to 429s but not to a daily quota, so a keyless relay exhausts the quota in about 10 minutes. It then
  runs on adsb.fi alone. The same applies to `tools/live/record.py`, which shares the Poller.
- **Observed (sha3d recorder, 2026-11-13 19:08–21:21Z):** one keyless request every 15 s, about 507 requests in
  2.2 h, which broke the published quota. It drew 6 HTTP 429s (the first at request 107) and 20 connection resets.
  Another 429 came at 21:30Z, after the recorder had slowed to one request per 180 s. A 2.2 h window cannot show how a
  24 h quota is enforced, so treat the published figure as binding.
- **Suggestion:** decide between a feeder or sponsor key, adsb.fi as the primary source, or a quota-aware schedule.
  Update `docs/research/realtime_feeds.md` and the About text.

## R2. The relay's User-Agent carries the owner's repository URL (low; owner's privacy rule)

- `sfo_live_server.py` line 56: `CONTACT = <the owner's repository URL>`, used in
  `UA = 'sfo-live-3d-relay/... (+CONTACT; ...)'`. It goes to every provider on every request.
- The project rules ask that the owner's details are not sent to outside services without explicit consent. hwd3d uses
  a generic User-Agent.
- If the owner has consented, nothing needs to change. Otherwise switch to a generic UA, as hwd3d did.

## R3. Other providers' terms changed (information)

- **airplanes.live:** returns 403 to non-contributors. A third party reports it went contributor-only in Sep 2026
  [secondary].
- **OpenSky:** the Terms require a written licence for "any operational capacity — including integration into a live
  product, service, or automated system". Terms 3(i) require aircraft identifiers to be anonymised in publications.

Details and quotes are in sha3d `docs/phase0/adsb.md` §2.
