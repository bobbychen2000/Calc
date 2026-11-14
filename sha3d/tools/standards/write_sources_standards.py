"""Write refs/cache/standards/SOURCES.json (B3): URL, date, sha256, licence quote, redistributable.
usage: python3 -I sha3d/tools/standards/write_sources_standards.py sha3d"""
import json, sys, os, hashlib
root = sys.argv[1]; D = os.path.join(root, 'refs', 'cache', 'standards')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def files(sub, urls):
    out = {}
    for f in sorted(os.listdir(os.path.join(D, sub))):
        p = os.path.join(D, sub, f)
        if os.path.isdir(p): continue
        out[f] = dict(bytes=os.path.getsize(p), sha256=sha(p), url=urls.get(f, ''))
    return out
CAAC = 'https://www.caac.gov.cn/XXGK/XXGK/'
CAAC_TERMS = ('No licence or terms of use found on the pages; page footer: "版权所有：中国民用航空局" (copyright: CAAC). '
              'The standard was published commercially by 中国民航出版社 (cover: 成本价 98.00 元). PRC Copyright Law Art. 5(1) '
              'excludes "法律、法规，国家机关的决议、决定、命令和其他具有立法、行政、司法性质的文件"; whether a CAAC industry '
              'standard falls under it is not settled (not legal advice).')
S = {
 'caac_mh5001_2021': dict(
   what='MH 5001-2021 民用机场飞行区技术标准 (Aerodrome technical standards), CAAC announcement 2021 No. 8, issued 2021-09-18, '
        'in force 2021-12-01, replaces MH 5001-2013; PDF = 3rd printing (Nov 2023, errata of 2024-01-16 applied in the text); '
        'plus amendments 1 (2024-01-03, in force 2024-11-28; ACR/PCR), 2 (2024-01-23; SMGCS), 3 (2024-08-09, in force '
        '2024-11-28; ACR/PCR), 4 (2025-06-21; holding positions, enhanced centreline, mandatory instruction markings, '
        'runway vacated sign), the four CAAC pages, and page renders of the figures read (local).',
   retrieved='2026-11-14', status='verified (official CAAC download)', licence=CAAC_TERMS,
   redistributable='no (treat as all rights reserved): keep local; publish short cited parameters with clause numbers only; '
                   'no figure crops in committed files',
   files=files('caac_mh5001_2021', {
     't20211201_210343.html': CAAC + 'BZGF/HYBZ/202112/t20211201_210343.html',
     'MH5001-2021.pdf': CAAC + 'BZGF/HYBZ/202112/P020240124587371852795.pdf',
     't20240108_222597.html': CAAC + 'BZGF/HYBZ/202401/t20240108_222597.html',
     'MH5001-2021_amd1.pdf': CAAC + 'BZGF/HYBZ/202401/P020240108510340905586.pdf',
     't20240129_222809.html': CAAC + 'BZGF/HYBZ/202401/t20240129_222809.html',
     'MH5001-2021_amd2.pdf': CAAC + 'BZGF/HYBZ/202401/P020240129578936812258.pdf',
     't20240816_225067.html': CAAC + 'TZTG/202408/t20240816_225067.html',
     'MH5001-2021_amd3.pdf': CAAC + 'TZTG/202408/P020240816358433769553.pdf',
     't20250623_227783.html': CAAC + 'TZTG/202506/t20250623_227783.html',
     'MH5001-2021_amd4.pdf': CAAC + 'TZTG/202506/P020250701401698137311.pdf'})),
 'caac_other': dict(
   what='MH/T 5083-2024 民用机场助航灯光系统维护规程 (in force 2025-02-01; replaces AP-140-CA-2009-1) and 民航综机发〔2025〕1号 '
        '机场目视助航设施规划设计和审查管理工作要点 (2025-03-11), with their CAAC pages',
   retrieved='2026-11-14', status='verified (official CAAC download)', licence=CAAC_TERMS,
   redistributable='no: local only; short cited facts',
   files=files('caac_other', {
     't20241223_226214.html': CAAC + 'TZTG/202412/t20241223_226214.html',
     'MH-T5083-2024.pdf': CAAC + 'TZTG/202412/P020241224355399816301.pdf',
     't20250311_226915.html': CAAC + 'ZFGW/202503/t20250311_226915.html',
     'caac_2025_visual_aids_design_points.pdf': CAAC + 'ZFGW/202503/P020250311603080724621.pdf'})),
 'caac_hybz_index': dict(
   what='CAAC information-disclosure pages: 行业标准 index and site searches (was5) used to find the standards',
   retrieved='2026-11-14', status='verified', licence=CAAC_TERMS, redistributable='no (search pages; local)',
   files=files('caac_hybz_index', {'hybz_index.html': CAAC + 'BZGF/HYBZ/'})),
 'faa_ac150_5340_1m': dict(
   what='FAA AC 150/5340-1M Standards for Airport Markings, consolidated Change 1 (12/23/2020), for the FAA column of the comparison',
   retrieved='2026-11-14', status='verified (official FAA download)',
   licence='US Government work (17 U.S.C. 105): not subject to copyright in the US',
   redistributable='yes (public domain in the US); kept local because it is large and not needed by the build',
   files=files('faa_ac150_5340_1m', {'ac_150_5340-1m.pdf': 'https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-1M-Chg-1-Airport-Markings.pdf'})),
 'not_obtained': dict(
   what='ICAO Annex 14 Vol I (9th ed.) and ICAO Aerodrome Design Manual Part 4: sold by ICAO, not obtained and not needed '
        '(MH 5001-2021 states it implements Annex 14 Vol I 8th ed.). Also not obtained: 降低运输机场飞行区运行风险设计指南, '
        '民用机场地面活动引导与控制系统(SMGCS)建设和运行指南 (named in the 2025 notice), MH 5012-2010 (construction and acceptance).',
   status='unverified'),
}
json.dump(S, open(os.path.join(D, 'SOURCES.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', sum(len(v.get('files', {})) for v in S.values()), 'files')
