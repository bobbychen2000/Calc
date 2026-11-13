// Regression test (13 Nov 2026): js/live/lookup.js livery() cached the livery object without the registration in its key,
// so every aircraft resolved the same way (brand / source / reason / airline) wore the FIRST one's registration decal
// (UAL900 N71112, ICAO a9825a, showed UAL901's N61115 in the tracking film). Recording 8 Nov 2026, both United 787-9s.
// usage: node tools/live/test_lookup_reg.mjs   (exit 1 on failure)
import { liveryForAirline, resolveLivery } from '../../js/live/lookup.js';
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m); } else console.log('ok  ', m); };
const a = liveryForAirline('UAL', 'N61115', 'a7f50e', 'B789'), b = liveryForAirline('UAL', 'N71112', 'a9825a', 'B789');
ok(a.reg === 'N61115' && b.reg === 'N71112', `feed registrations kept per aircraft (${a.reg}, ${b.reg})`);
ok(liveryForAirline('UAL', 'N71112', 'a9825a', 'B789') === b, 'same aircraft -> same cached livery object');
// no feed registration: resolved from the ICAO address (US block decode), per aircraft
const r1 = resolveLivery(liveryForAirline('UAL'), 'a9825a', 'B789'), r2 = resolveLivery(liveryForAirline('UAL'), 'a7f50e', 'B789');
ok(r1.reg === 'N71112' && r2.reg === 'N61115', `ICAO-address registrations per aircraft (${r1.reg}, ${r2.reg})`);
process.exit(fail ? 1 : 0);
