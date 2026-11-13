"""Compare the AIP China ZSSS ARP with OurAirports and with the OSM runway geometry (WGS-84, Vincenty).

Usage: python3 -I tools/aip/arp_check.py
Inputs are the published values quoted in docs/phase0/aip.md (AIP AD 2.2/2.10/2.12) and the OSM runway-end
nodes quoted in docs/phase0/geo.md section 5. Prints distances; writes nothing.
"""
import math

A = 6378137.0
F = 1 / 298.257223563

def inverse(lat1, lon1, lat2, lon2):
    """Vincenty inverse on the WGS-84 ellipsoid -> (distance m, initial true bearing deg)."""
    b = A * (1 - F)
    L = math.radians(lon2 - lon1)
    U1 = math.atan((1 - F) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - F) * math.tan(math.radians(lat2)))
    sU1, cU1, sU2, cU2 = math.sin(U1), math.cos(U1), math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.hypot(cU2 * sl, cU1 * sU2 - sU1 * cU2 * cl)
        if ss == 0:
            return 0.0, 0.0
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sig = math.atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2m = cs - 2 * sU1 * sU2 / c2a if c2a else 0.0
        C = F / 16 * c2a * (4 + F * (4 - 3 * c2a))
        prev = lam
        lam = L + (1 - C) * F * sa * (sig + C * ss * (c2m + C * cs * (-1 + 2 * c2m ** 2)))
        if abs(lam - prev) < 1e-12:
            break
    u2 = c2a * (A * A - b * b) / (b * b)
    AA = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    BB = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = BB * ss * (c2m + BB / 4 * (cs * (-1 + 2 * c2m ** 2) - BB / 6 * c2m * (-3 + 4 * ss ** 2) * (-3 + 4 * c2m ** 2)))
    brg = math.degrees(math.atan2(cU2 * math.sin(lam), cU1 * sU2 - sU1 * cU2 * math.cos(lam))) % 360
    return b * AA * (sig - ds), brg

def offset(lat, lon, brg_true, dist):
    """Local-tangent-plane forward step (adequate for a few km)."""
    e2 = F * (2 - F)
    phi = math.radians(lat)
    rn = A / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    rm = A * (1 - e2) / (1 - e2 * math.sin(phi) ** 2) ** 1.5
    dn, de = dist * math.cos(math.radians(brg_true)), dist * math.sin(math.radians(brg_true))
    return lat + math.degrees(dn / rm), lon + math.degrees(de / (rn * math.cos(phi)))

AIP_ARP = (31 + 11.8 / 60, 121 + 20.1 / 60)          # AD 2.2 item 1: N31°11.8' E121°20.1', "Center of RWY18L/36R"
VAR_W = 5 + 46 / 60                                   # AD 2.2 item 5: 5°46'W (2017), -42"/yr
OURAIRPORTS = (31.198104, 121.33426)
OSM = {'18L': (31.2131135, 121.3354641), '36R': (31.1825842, 121.3371157),   # geo.md section 5
       '18R': (31.2129628, 121.3316265), '36L': (31.1833933, 121.3332449)}
OSM_TWR = (31.1966742, 121.3415341)                   # OSM node 3342630333 tower:type=aircraft_control

def dm(x):
    d = int(x)
    return f'{d}°{(x - d) * 60:.3f}\''

def main():
    d, b = inverse(*AIP_ARP, *OURAIRPORTS)
    print(f'AIP ARP = {AIP_ARP[0]:.6f}, {AIP_ARP[1]:.6f}; OurAirports minus AIP: {d:.1f} m at {b:.1f}° true')
    print(f'  half a 0.1\' step: {inverse(*AIP_ARP, AIP_ARP[0] + 0.05 / 60, AIP_ARP[1])[0]:.1f} m N-S, '
          f'{inverse(*AIP_ARP, AIP_ARP[0], AIP_ARP[1] + 0.05 / 60)[0]:.1f} m E-W')
    l1, b1 = inverse(*OSM['18L'], *OSM['36R'])
    l2, b2 = inverse(*OSM['18R'], *OSM['36L'])
    print(f'OSM RWY18L/36R {l1:.1f} m, {b1:.3f}° true (AIP 177.34° GEO); RWY18R/36L {l2:.1f} m, {b2:.3f}° true (AIP 177.33° GEO)')
    c1 = ((OSM['18L'][0] + OSM['36R'][0]) / 2, (OSM['18L'][1] + OSM['36R'][1]) / 2)
    c2 = ((OSM['18R'][0] + OSM['36L'][0]) / 2, (OSM['18R'][1] + OSM['36L'][1]) / 2)
    print(f'OSM centre of RWY18L/36R = {c1[0]:.6f}, {c1[1]:.6f} = N{dm(c1[0])} E{dm(c1[1])}')
    for name, p in (('AIP ARP', AIP_ARP), ('OurAirports ARP', OURAIRPORTS)):
        d, b = inverse(*c1, *p)
        print(f'  {name} is {d:.1f} m from it at {b:.1f}° true')
    d, b = inverse(*c1, *c2)
    print(f'RCL spacing from OSM midpoints: {d * math.sin(math.radians(b - b1)):.1f} m (AIP: 365 m)')
    twr = offset(*c1, 145 - VAR_W, 1022)              # AD 2.10 obstacle "TOWER 145/1022, 48 m"
    print(f'AD 2.10 TOWER (145° MAG / 1022 m) -> {twr[0]:.6f}, {twr[1]:.6f}; '
          f'{inverse(*twr, *OSM_TWR)[0]:.0f} m from the OSM aircraft_control node')
    d, b = inverse(*c1, *OSM_TWR)
    print(f'OSM aircraft_control node from the RWY18L/36R centre: {b + VAR_W:.1f}° MAG / {d:.0f} m')

if __name__ == '__main__':
    main()
