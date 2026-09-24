"""Brands shown on aircraft at SFO: brand code -> display name, the callsign (ICAO airline designator) that flies it,
and how regional operators map to their partners' brands.

Brand code = ICAO designator of the marketing airline whose livery is painted on the aircraft; regional brands add a
suffix (United Express UAL-X, Delta Connection DAL-C, American Eagle AAL-E, Air Canada Express ACA-X). Alaska's
regional flights (Horizon, SkyWest) wear the Alaska livery: brand ASA. Sources for the operator -> brand relations:
docs/research/liveries.md §2 (US DOT BTS marketing-carrier data, DataSF SFO landings).
"""

BRANDS = {
    # code: (name, [callsigns that are this brand's own mainline flights])
    'UAL': ('United Airlines', ['UAL']),
    'UAL-X': ('United Express', []),
    'UAL-G': ('United Airlines (2010 Globe livery)', []),
    'DAL': ('Delta Air Lines', ['DAL']),
    'DAL-C': ('Delta Connection', []),
    'AAL': ('American Airlines', ['AAL']),
    'AAL-E': ('American Eagle', []),
    'ASA': ('Alaska Airlines', ['ASA', 'QXE']),       # Horizon (QXE) flies only Alaska-branded E175s
    'SWA': ('Southwest Airlines', ['SWA']),
    'JBU': ('JetBlue', ['JBU']),
    'FFT': ('Frontier Airlines', ['FFT']),
    'ACA': ('Air Canada', ['ACA']),
    'ACA-X': ('Air Canada Express', ['JZA']),         # Jazz: Air Canada Express (SFO pair Air Canada / Jazz, CRJ9)
    'WJA': ('WestJet', ['WJA']),
    'AMX': ('Aeroméxico', ['AMX']),
    'HAL': ('Hawaiian Airlines', ['HAL']),
    'SCX': ('Sun Country Airlines', ['SCX']),
    'MXY': ('Breeze Airways', ['MXY']),
    'CPA': ('Cathay Pacific', ['CPA']),
    'EVA': ('EVA Air', ['EVA']),
    'CAL': ('China Airlines', ['CAL']),
    'SIA': ('Singapore Airlines', ['SIA']),
    'KAL': ('Korean Air', ['KAL']),
    'ANA': ('ANA', ['ANA']),
    'JAL': ('Japan Airlines', ['JAL']),
    'QFA': ('Qantas', ['QFA']),
    'PAL': ('Philippine Airlines', ['PAL']),
    'AFR': ('Air France', ['AFR']),
    'BAW': ('British Airways', ['BAW']),
    'DLH': ('Lufthansa', ['DLH']),
    'UAE': ('Emirates', ['UAE']),
    'THY': ('Turkish Airlines', ['THY']),
    'VIR': ('Virgin Atlantic', ['VIR']),
    'AIC': ('Air India', ['AIC']),
    'ANZ': ('Air New Zealand', ['ANZ']),
    'AVA': ('Avianca', ['AVA', 'TAI', 'LRC']),         # TACA International (TAI) flies Avianca colours (liveries.md §3.2)
    'VOI': ('Volaris', ['VOI']),
    'CMP': ('Copa Airlines', ['CMP']),
    'KLM': ('KLM', ['KLM']),
    'SWR': ('Swiss', ['SWR']),
    'AAR': ('Asiana Airlines', ['AAR']),
    'SJX': ('Starlux Airlines', ['SJX']),
    'TZP': ('ZIPAIR', ['TZP']),
    'EIN': ('Aer Lingus', ['EIN']),
    'QTR': ('Qatar Airways', ['QTR']),
    'FBU': ('French bee', ['FBU']),
    'POE': ('Porter Airlines', ['POE']),
    'SAS': ('SAS', ['SAS']),
    'TAP': ('TAP Air Portugal', ['TAP']),
    'APZ': ('Air Premia', ['APZ']),
    'FLE': ('Flair Airlines', ['FLE']),
    'ITY': ('ITA Airways', ['ITY']),
    'CSN': ('China Southern', ['CSN']),
    'CES': ('China Eastern', ['CES']),
    'CCA': ('Air China', ['CCA']),
    'HVN': ('Vietnam Airlines', ['HVN']),
    'FJI': ('Fiji Airways', ['FJI']),
    'CFG': ('Condor', ['CFG']),
    'IBE': ('Iberia', ['IBE']),
    'LOT': ('LOT Polish Airlines', ['LOT']),
    'FDX': ('FedEx', ['FDX']),
    'UPS': ('UPS', ['UPS']),
}

# US regional operators (ICAO callsign -> BTS operating-carrier code) and the BTS marketing network -> brand code
REGIONAL_OPS = {'SKW': 'OO', 'QXE': 'QX', 'RPA': 'YX', 'ENY': 'MQ', 'JIA': 'OH', 'EDV': '9E', 'ASH': 'YV', 'GJS': 'G7', 'UCA': 'C5',
                'PDT': 'PT', 'AWI': 'ZW'}
NETWORK_BRAND = {'UA': 'UAL-X', 'AA': 'AAL-E', 'DL': 'DAL-C', 'AS': 'ASA'}
# ADS-B type designator -> BTS/FAA short type used in the tail table (tools/models/build_brands.py)
ADSB_TO_BTS = {'E75L': 'E175', 'E75S': 'E175', 'E170': 'E170', 'CRJ2': 'CRJ2', 'CRJ7': 'CRJ7', 'CRJ9': 'CRJ9', 'E145': 'E145', 'E135': 'E145'}
# SkyWest at SFO: majority brand per type from DataSF (SFO landings Aug 2025 - Jul 2026, docs/research/liveries.md §1.1):
# E175 United 16,959 / 26,336 (64 %), CRJ200 and CRJ700 United only
SFO_MAJORITY = {'OO': {'E175': 'UAL-X', 'CRJ2': 'UAL-X', 'CRJ7': 'UAL-X', 'E170': 'UAL-X', '*': 'UAL-X'}, 'QX': {'*': 'ASA'}}

# per-registration special liveries (observed in the named sources); rendered in the brand's standard livery until a
# special livery is painted (the entry says so)
REG_OVERRIDE = {
    'N645SY': dict(brand='UAL-X', special='"Mountain Ascent" special livery (E175)', src='https://worldairlinenews.com/2026/09/04/united-airlines-unveils-a-new-mountain-ascent-livery-on-n645sy/', rendered='standard United Express'),
    'N735AT': dict(brand='AAL', special='centennial retro "Flagship" livery (777-300)', src='https://news.aa.com/news/news-details/2025/American-Airlines-unveils-special-Flagship-livery-ahead-of-centennial-year-CENT-10/default.aspx', rendered='standard American'),
}
