#!/usr/bin/env python3
"""Record live ADS-B around SFO from adsb.lol and adsb.fi, for provider comparison and replay tests.

Uses exactly the relay's polling code (sfo_live_server.Poller / RecordWriter), so recordings show what the relay sees:
  adsb.lol  https://api.adsb.lol/v2/point/37.6188/-122.3754/40            every 1.0-1.5 s (random), one request in
            flight; HTTP 429 -> wait 2 s, then 4, 8, 16, 30 s (realtime_feeds.md §5.1)
  adsb.fi   https://opendata.adsb.fi/api/v3/lat/37.6188/lon/-122.3754/dist/40   every 2.0 s at an even second + 0.3 s
            (its snapshot changes only on even seconds, §4.2; v3 replaces the deprecated v2 lat/lon/dist, §3.2);
            errors -> 4, 8, 16, 32, 60 s
Writes one gzip JSON-lines file per provider per UTC hour to refs/cache/rec/ (gitignored: the data is the providers',
see realtime_feeds.md for their terms). Each line:
  {"t": request start (s), "tr": response received (s), "p": "adsblol"|"adsbfi", "code": HTTP status, "d": response}
  failures: {"t", "tr", "p", "code" (null on network errors), "err": message, "ra": Retry-After header if any}
adsb.fi v3 lists aircraft under 'ac' with 'now' in ms (the v2 files before 24 Sep 10:1x UTC: 'aircraft', 'now' in s);
tools/live/recio.py reads both, including the hour still being written.
A summary line per provider is printed every 10 min (to recorder.log when started as below).

  python3 tools/live/record.py [hours=14]
  detached:  setsid nohup python3 tools/live/record.py 14 >> refs/cache/rec/recorder.log 2>&1 < /dev/null &
  stop:      kill $(cat refs/cache/rec/recorder.pid)        (SIGTERM closes the gzip members cleanly)
Never run it while `sfo_live_server.py --record` writes to the same directory, and remember that the relay and the
recorder poll from the same IP: stop the recorder while testing the relay live (adsb.fi allows 1 request/s).
"""
import os, signal, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
import sfo_live_server as S  # noqa: E402

OUT = os.path.join(ROOT, 'refs', 'cache', 'rec')
LAT, LON, NM = 37.6188, -122.3754, 40      # SFO ARP (FAA 37.6188056, -122.3754167) to 4 decimals, as before


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 14.0
    os.makedirs(OUT, exist_ok=True)
    pidf = os.path.join(OUT, 'recorder.pid')
    for name in ('recorder.pid', 'relay_record.pid'):       # another record.py, or sfo_live_server.py --record
        f = os.path.join(OUT, name)
        if os.path.exists(f):
            try:
                other = int(open(f).read().strip())
            except ValueError:
                other = None
            if other and other != os.getpid() and S.pid_alive(other):
                sys.exit(f'record.py: pid {other} ({name}) is already writing to {OUT}; stop it first: kill {other}')
    open(pidf, 'w').write(str(os.getpid()))
    until = time.time() + hours * 3600
    writer = S.RecordWriter(OUT)
    stop = threading.Event()
    pollers = []

    def on_result(prov, t0, t1, status, hd, js, err):
        writer.write(prov['id'], t0, t1, status, hd, js, err)

    for prov in S.PROVIDERS.values():
        p = S.Poller(prov, on_result, LAT, LON, NM, active=lambda: not stop.is_set())
        pollers.append(p)
        p.start()

    def on_signal(signum, frame):
        stop.set()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), f'record.py pid {os.getpid()} started for {hours} h;',
          'UA', S.UA, flush=True)
    for p in pollers:
        print('  ', p.p['id'], p.url, flush=True)
    last = time.time()
    try:
        while not stop.is_set() and time.time() < until:
            stop.wait(5.0)
            if time.time() - last >= 600 or stop.is_set() or time.time() >= until:
                last = time.time()
                for p in pollers:
                    s = p.status()
                    print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), p.p['id'],
                          'req', s['requests'], 'ok', s['ok'], '429', s['http429'], 'err', s['errors'], 'dup', s['duplicates'],
                          'lat_ms p50/p90', s['latency_ms_p50'], s['latency_ms_p90'],
                          'start-now p50', s['request_minus_now_s_p50'], 'phase', s['phase_s'],
                          'last_error', s['last_error'], flush=True)
    finally:
        stop.set()
        for p in pollers:
            p.stop_ev.set()
        for p in pollers:
            p.join(timeout=12)
        writer.close()
        try:
            if open(pidf).read().strip() == str(os.getpid()):
                os.remove(pidf)
        except OSError:
            pass
        print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'record.py stopped', flush=True)


if __name__ == '__main__':
    main()
