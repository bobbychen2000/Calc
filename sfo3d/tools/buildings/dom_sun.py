"""Sun position (NOAA simplified algorithm, ~0.01 deg) for the NAIP epochs over the domestic terminals.

Used to cross-check the sun vectors that are measured on the imagery (tower shadow, pole shadows): the shadow vector
per metre of height is s = cot(elevation) * (sin az_s, -cos az_s) in world (x east, z south), az_s = sun az + 180.
"""
import math
from datetime import datetime, timezone, timedelta

LAT, LON = 37.6155, -122.384      # centre of the domestic terminals (world ~(-880, 330))


def sunpos(dt, lat=LAT, lon=LON):
    jd = dt.timestamp() / 86400 + 2440587.5
    T = (jd - 2451545.0) / 36525
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = math.radians(M)
    C = math.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * Mr) * (0.019993 - 0.000101 * T) + math.sin(3 * Mr) * 0.000289
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * T))
    eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * T))
    dec = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    y = math.tan(math.radians(eps / 2)) ** 2
    L0r = math.radians(L0)
    eqt = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(Mr) + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    minutes = dt.hour * 60 + dt.minute + dt.second / 60
    tst = (minutes + eqt + 4 * lon) % 1440
    ha = tst / 4 - 180
    latr, decr, har = map(math.radians, (lat, dec, ha))
    cz = math.sin(latr) * math.sin(decr) + math.cos(latr) * math.cos(decr) * math.cos(har)
    el = 90 - math.degrees(math.acos(cz))
    az = (math.degrees(math.atan2(math.sin(har), math.cos(har) * math.sin(latr) - math.tan(decr) * math.cos(latr))) + 180) % 360
    return az, el


def path(day, t0=(12, 0), t1=(18, 0), step_s=30):
    """list of (UTC datetime, az, el) for a day (UTC hours)."""
    out = []; dt = datetime(*day, *t0, tzinfo=timezone.utc)
    end = datetime(*day, *t1, tzinfo=timezone.utc) if t1[0] < 24 else datetime(*day, tzinfo=timezone.utc) + timedelta(hours=t1[0])
    while dt <= end:
        out.append((dt,) + sunpos(dt)); dt += timedelta(seconds=step_s)
    return out


def el_at_az(day, az_target, utc_hours=(15, 26)):
    """elevation of the sun when it is at azimuth az_target on `day` (PDT afternoon when needed)."""
    best = None
    for dt, az, el in path(day, (utc_hours[0], 0), (min(utc_hours[1], 23), 59)):
        d = abs(az - az_target)
        if best is None or d < best[0]: best = (d, dt, az, el)
    # continue past midnight UTC (PDT afternoon of the same local day)
    nxt = datetime(*day, tzinfo=timezone.utc) + timedelta(days=1)
    for dt, az, el in path((nxt.year, nxt.month, nxt.day), (0, 0), (3, 0)):
        d = abs(az - az_target)
        if el > 0 and d < best[0]: best = (d, dt, az, el)
    return best


if __name__ == '__main__':
    for day, azs in (((2020, 5, 24), (266.0, 267.4, 269.0)), ((2024, 5, 20), (180.0, 186.6, 195.0))):
        for a in azs:
            d, dt, az, el = el_at_az(day, a)
            print(day, 'sun az %.1f -> el %.2f at %s UTC (%s PDT), shadow length/height %.3f' % (
                az, el, dt.strftime('%H:%M'), (dt - timedelta(hours=7)).strftime('%H:%M'), 1 / math.tan(math.radians(el))))
