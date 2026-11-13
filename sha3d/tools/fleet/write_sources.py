"""Write SOURCES.json beside every Phase-0 'fleet' download (sha3d/refs/cache/fleet/* and sha3d/refs/cache/models/*).

Usage: python3 -I write_sources.py <sha3d/refs/cache>
Every entry: url, retrieved (2026-11-13), licence (quoted where a licence text exists), redistributable, sha256 per file.
Git clones are listed by commit (their checked-out files are hashed; blobs that were never checked out are listed by git blob id).
"""
import sys, os, json, hashlib, subprocess

ROOT = sys.argv[1]
DAY = "2026-11-13"
WP_LIC = ("Wikipedia text: 'Text is available under the Creative Commons Attribution-ShareAlike 4.0 License; additional terms may apply' "
          "(CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/)")
COMAC_TERMS = ("COMAC website terms (https://www.comac.cc/bottom/201401/13/t20140113_1340598.shtml): '本网站提供的任何内容（包括但不限于设计、数据、文字、图表、图象、声音或录像等）"
               "的版权均属于中国商飞公司或相关权利人。未经中国商飞公司或相关权利人事先的书面许可，您不得以任何方式擅自复制、传播、出版、转帖、改编或陈列本网站的内容。' "
               "The limited licence excludes '（3）衍生性的使用本网站及其内容' and '（4）使用任何数据收集方法自动或手动收集本网站信息'.")
COMAC_ACAP_STMT = ("ACAP front matter: 'COMMERCIAL AIRCRAFT CORPORATION OF CHINA, LTD. PROPRIETARY, CONFIDENTIAL, AND/OR TRADE SECRET ... "
                   "The information contained herein shall not be reproduced, quoted, disclosed or used directly or indirectly, in whole or in part "
                   "for any purposes, except with prior written authorization by COMAC.' and 'The COMAC company name and logo containing \"COMAC\", "
                   "the ARJ21 name and logo containing \"ARJ21\" and the C909 name and logo containing \"C909\" and the C919 name and logo containing "
                   "\"C919\" are all trademarks owned by the Commercial Aircraft Corporation of China, Ltd.'")
HKEX_LIC = ("HKEX Terms of Use (https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en), section 5 'Copyright and Permitted Use': "
            "'All intellectual property rights in all the Information on this Website ... shall be and remain vested in HKEX or relevan[t third parties]' "
            "and you may 'store such pages in electronic form on disk (but not on any server or other storage device connected to a network) for your "
            "personal use. Unless HKEX or relevant third-parties has/have given you express written permission, you are not permitted to ... "
            "distribute, display, copy, modify, download, publish, post, transmit or otherwise make available ...'. The filings are the issuers' own "
            "documents; used here as a primary source for numbers (facts) only.")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files(d, skip_git=True):
    out = {}
    for dp, dns, fs in os.walk(d):
        if skip_git and ".git" in dns:
            dns.remove(".git")
        for f in sorted(fs):
            if f == "SOURCES.json":
                continue
            p = os.path.join(dp, f)
            out[os.path.relpath(p, d)] = dict(bytes=os.path.getsize(p), sha256=sha(p))
    return out


def git_info(d, interesting):
    def g(*a):
        return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True).stdout.strip()
    tree = g("ls-tree", "-r", "HEAD").splitlines()
    blobs = {}
    for line in tree:
        meta, path = line.split("\t", 1)
        if any(k in path.lower() for k in interesting):
            blobs[path] = meta.split()[2]
    return dict(remote=g("config", "--get", "remote.origin.url"), commit=g("rev-parse", "HEAD"),
                commit_date=g("log", "-1", "--format=%ci"), n_files_in_tree=len(tree), blob_ids=blobs)


def write(d, entries):
    with open(os.path.join(d, "SOURCES.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.join(d, "SOURCES.json"))


def wp(title, d):
    rev = {}
    try:
        j = json.load(open(os.path.join(d, title + ".revinfo.json"), encoding="utf-8"))
        p = list(j["query"]["pages"].values())[0]
        rev = dict(pageid=p.get("pageid"), revid=p["revisions"][0]["revid"], rev_timestamp=p["revisions"][0]["timestamp"])
    except Exception as e:  # noqa
        rev = dict(note="revinfo not parsed: %s" % e)
    return dict(what="English Wikipedia article wikitext (action=raw) + revision id (secondary source)",
                url="https://en.wikipedia.org/w/index.php?title=%s&action=raw" % title, retrieved=DAY, **rev,
                licence=WP_LIC, redistributable="yes, CC BY-SA 4.0 with attribution (article title, URL, revision); ShareAlike for adaptations",
                status="secondary", files=files(d))


def main():
    F = os.path.join(ROOT, "fleet")
    for name in sorted(os.listdir(F)):
        d = os.path.join(F, name)
        if name.startswith("wikipedia_"):
            if name == "wikipedia_sha":
                e = wp("Shanghai_Hongqiao_International_Airport", d)
                e["files"] = files(d)
                e["url"] = "https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&action=raw"
                e["note"] = "renamed files SHA_wikitext.txt / SHA_revinfo.json"
                try:
                    j = json.load(open(os.path.join(d, "SHA_revinfo.json"), encoding="utf-8"))
                    p = list(j["query"]["pages"].values())[0]
                    e.update(pageid=p["pageid"], revid=p["revisions"][0]["revid"], rev_timestamp=p["revisions"][0]["timestamp"])
                    e.pop("note", None)
                except Exception:
                    pass
                write(d, {"wikipedia_sha": e})
            else:
                t = [f[:-len(".wikitext")] for f in os.listdir(d) if f.endswith(".wikitext")][0]
                write(d, {name: wp(t, d)})
    write(os.path.join(F, "comac_en"), {"comac_en": dict(
        what="COMAC English site: home, C919 (/products/ca/), C909 (/products/c909/), C929 (/products/WideBody/), Operation Support (/products/jszl/, gzip) and its document list (/products/jszl/jszl/)",
        url="https://english.comac.cc/products/c909/ ; https://english.comac.cc/products/ca/ ; https://english.comac.cc/products/jszl/jszl/",
        retrieved=DAY, status="primary (manufacturer)", licence=COMAC_TERMS, redistributable="no (local reference only)",
        files=files(os.path.join(F, "comac_en")))})
    write(os.path.join(F, "comac_cn"), {"comac_cn": dict(
        what="COMAC Chinese site: C919 / C909 product pages, operation-support page and its document list (links to the ACAP PDFs and the C919 three-view DWG)",
        url="https://www.comac.cc/cpyzr/c919/ ; https://www.comac.cc/cpyzr/c909/ ; https://www.comac.cc/cpyzr/jszl/jszl/",
        retrieved=DAY, status="primary (manufacturer)", licence=COMAC_TERMS, redistributable="no (local reference only)",
        files=files(os.path.join(F, "comac_cn")))})
    write(os.path.join(F, "comac_terms"), {"comac_terms": dict(
        what="COMAC website terms of use and privacy statement (网站使用条款和隐私声明)",
        url="https://www.comac.cc/bottom/201401/13/t20140113_1340598.shtml", retrieved=DAY, status="primary",
        licence=COMAC_TERMS, redistributable="no (link only)", files=files(os.path.join(F, "comac_terms")))})
    for key, url, what in [
        ("comac_c919_acap", "https://www.comac.cc/fujian/c919acap_en.pdf",
         "COMAC C919 Aircraft Characteristics for Airport Planning (ACAP), C919-SVV19-50009-00, R9 2025-10-17, 260 pp."),
        ("comac_c909_acap", "https://www.comac.cc/fujian/c909acap_en.pdf",
         "COMAC C909 (ARJ21-700) Aircraft Characteristics for Airport Planning (ACAP), TP-E700051 (PMC ARJ21-SVV19-50009-00), R13 2025-12-24, 246 pp."),
        ("comac_c919_3view", "https://www.comac.cc/fujian/c919sanmiantu.dwg",
         "COMAC C919 three-view drawing (C919飞机三面图), AutoCAD 2013-2017 DWG (not converted)"),
        ("comac_ccc", "https://www.comac.cc/fujian/ccc_en.pdf", "COMAC Crash Crew Chart (English)")]:
        write(os.path.join(F, key), {key: dict(what=what, url=url, linked_from="https://english.comac.cc/products/jszl/jszl/ (and the Chinese list)",
                                               retrieved=DAY, status="primary (manufacturer)",
                                               licence=COMAC_TERMS + (" " + COMAC_ACAP_STMT if "acap" in key else ""),
                                               redistributable="no: measurement reference only, keep in the gitignored cache; only measured numbers may be used (owner to confirm)",
                                               files=files(os.path.join(F, key)))})
    for key, url, what in [
        ("hkex_ces_opdata_202609", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/1015/2026101501062.pdf",
         "China Eastern Airlines (00670) 'Announcement on operating data for September 2026' (15 Oct 2026): fleet structure at 30 Sep 2026"),
        ("hkex_ces_interim_2026", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0923/2026092300276.pdf",
         "China Eastern Airlines (00670) Interim Report 2026 (23 Sep 2026): fleet structure at 30 Jun 2026, hub strategy"),
        ("hkex_cca_opdata_202609", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/1015/2026101501144.pdf",
         "Air China (00753) 'Announcement on key operating data of September 2026' (15 Oct 2026): fleet total 974"),
        ("hkex_cca_interim_2026", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0923/2026092300452.pdf",
         "Air China (00753) Interim Report 2026 (23 Sep 2026): group fleet by type at 30 Jun 2026"),
        ("hkex_csn_opdata_202609", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/1015/2026101500876.pdf",
         "China Southern Airlines (01055) 'Announcement on key operating data' for September 2026 (15 Oct 2026): fleet by type at 30 Sep 2026")]:
        write(os.path.join(F, key), {key: dict(what=what, url=url, found_via="https://www1.hkexnews.hk/search/titlesearch.xhtml (titleSearchServlet.do)",
                                               retrieved=DAY, status="primary (issuer filing)", licence=HKEX_LIC,
                                               redistributable="no (link only; numbers may be cited)", files=files(os.path.join(F, key)))})
    write(os.path.join(F, "icao_doc8643"), {"icao_doc8643": dict(
        what="ICAO Doc 8643 Aircraft Type Designators, full list as JSON (7,261 rows) from the ICAO DOC8643 web service",
        url="https://doc8643.icao.int/external/aircrafttypes (POST, empty body; redirected from https://www4.icao.int/doc8643/External/AircraftTypes)",
        retrieved=DAY, status="primary (ICAO)",
        licence="ICAO website content (c) ICAO; no open licence stated with the service. Designators are facts used for mapping only.",
        redistributable="no (link only; individual designators may be cited)", files=files(os.path.join(F, "icao_doc8643")))})
    cl = os.path.join(F, "commons_livref")
    if os.path.isdir(cl):
        write(cl, {"commons_livref": dict(
            what="Wikimedia Commons API search / category listings (JSON metadata only, no images) for livery reference photos and the "
                 "'on final approach towards SHA' photo sets",
            url="https://commons.wikimedia.org/w/api.php (generator=search / list=search / list=categorymembers)", retrieved=DAY,
            status="secondary (photo metadata)",
            licence="API metadata: Wikimedia Commons structured data CC0, file description pages CC BY-SA 4.0; each photo carries its own licence "
                    "(LicenseShortName in the JSON, mostly CC BY / CC BY-SA)",
            redistributable="metadata yes; the photos themselves are reference only and are not downloaded or shipped",
            files=files(cl))})
    th = os.path.join(F, "commons_livref_thumbs")
    if os.path.isdir(th):
        C = "https://commons.wikimedia.org/wiki/File:"
        meta = {  # file: (Commons file name, licence as shown in the Commons API extmetadata, author)
            "r1.jpg": ("China Eastern Airbus A320neo B-32AA on final approach to Shanghai Hongqiao May 2026.jpg", "CC BY 4.0", "4300streetcar"),
            "r2.jpg": ("20240107 Boeing 737-8 MAX of Shanghai Airlines (B-1381) at SHA 01.jpg", "CC BY-SA 4.0", "Windmemories"),
            "r3.jpg": ("Spring Airlines Airbus A321neo B-326Q on final approach to Shanghao Hongqiao May 2026.jpg", "CC BY 4.0", "4300streetcar"),
            "r4.jpg": ("Juneyao Air Airbus A321neo (B-30EQ) on final approach towards SHA.jpg", "CC BY-SA 4.0", "Benlisquare"),
            "r5.jpg": ("China Eastern Comac C919 B-919G on final approach to Shanghai Hongqiao May 2026 1.jpg", "not read (API rate-limited); same uploader's set is CC BY 4.0", "4300streetcar (by file-name series; unverified)"),
            "r6.jpg": ("Spring Airlines Airbus A320neo B-32MX on final approach to Shanghao Hongqiao May 2026.jpg", "CC BY 4.0", "4300streetcar"),
            "r7.jpg": ("Juneyao Air Airbus A321 B-1647 on final approach to Shanghai Hongqiao May 2026.jpg", "not read (API rate-limited)", "4300streetcar (by file-name series; unverified)"),
            "r8.jpg": ("(CHN-Shanghai) Juneyao Air Airbus A320-271N B-32EY @ ZSPD 2025-12-23.jpg", "CC BY 4.0", "S5A-0043"),
            "ref_4.jpg": ("(CHN-Shanghai) Shanghai Airlines Boeing 787-9 B-208X @ ZSPD 2025-12-23.jpg", "CC BY 4.0", "S5A-0043"),
            "ref_5.jpg": ("Juneyao Air Boeing 787-9 B-1115 on final approach to Shanghai Hongqiao June 2025.jpg", "CC BY 4.0", "4300streetcar"),
        }
        fl = files(th)
        per = {}
        for k, v in fl.items():
            if k in meta:
                n, lic, au = meta[k]
                per[k] = dict(commons_file=n, page=C + n.replace(" ", "_"), licence=lic, author=au, **v)
            else:
                per[k] = v
        write(th, {"commons_livref_thumbs": dict(
            what="1280-px thumbnails of Wikimedia Commons photos of the Shanghai carriers' current liveries (livery reference only: "
                 "measuring layout / colours by eye; nothing is traced or shipped)",
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/<a>/<ab>/<file>/1280px-<file> (per file below)", retrieved=DAY,
            status="observed reference (secondary)",
            licence="per photo (CC BY 4.0 / CC BY-SA 4.0 as listed per file); attribution: author + licence + Commons page",
            redistributable="licence would allow it with attribution, but by owner rule these are reference only: keep in the gitignored cache",
            files=per)})
    # ---------------- models ----------------
    M = os.path.join(ROOT, "models")
    for name in sorted(os.listdir(M)):
        d = os.path.join(M, name)
        if name.startswith("sketchfab_"):
            uid = name.split("_", 1)[1]
            j = json.load(open(os.path.join(d, "model_api.json"), encoding="utf-8"))
            lic = j.get("license") or {}
            write(d, {name: dict(
                what="Sketchfab model metadata (API v3) + its thumbnail (for a visual identity check). The model itself was NOT downloaded "
                     "(Sketchfab downloads need an account) and nothing was converted.",
                url="https://api.sketchfab.com/v3/models/%s" % uid, viewer=j.get("viewerUrl"), name=j.get("name"),
                author=(j.get("user") or {}).get("username"), published=j.get("publishedAt"), retrieved=DAY,
                downloadable=j.get("isDownloadable"), face_count=j.get("faceCount"), vertex_count=j.get("vertexCount"),
                licence=("%s (%s): '%s'" % (lic.get("label"), lic.get("url"), lic.get("requirements"))) if lic else
                        "no licence on the model page (not downloadable; all rights reserved by default)",
                redistributable=("model: yes under CC BY 4.0 with the credit line; metadata JSON / thumbnail: reference only" if lic.get("slug") == "by"
                                 else "no"),
                files=files(d))})
        elif name.startswith("gh_"):
            interesting = ["licen", "copying", "readme", ".glb", ".gltf", ".obj", ".fbx", ".blend"]
            gi = git_info(d, interesting)
            write(d, {name: dict(
                what="Shallow, blob-less git clone (git clone --depth 1 --filter=blob:none --no-checkout), only licence / README files checked out "
                     "to read them; models not converted",
                url=gi["remote"], commit=gi["commit"], commit_date=gi["commit_date"], retrieved=DAY,
                n_files_in_tree=gi["n_files_in_tree"], blob_ids_of_interest=gi["blob_ids"],
                checked_out_files=files(d)),
                "_note": "licence findings are summarised in sha3d/docs/phase0/fleet.md section 3"})


if __name__ == "__main__":
    main()
