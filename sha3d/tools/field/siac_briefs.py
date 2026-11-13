"""Parse the Hongqiao block of SIAC monthly traffic briefs (运输生产情况简报).

usage: python3 -I tools/field/siac_briefs.py refs/cache/field/siac_monthly_briefs/brief_*.pdf
Needs poppler's pdftotext on PATH. Downloads are untrusted: run with python3 -I.
Prints one JSON object per month with movements (架次), passengers (万人次), cargo (万吨),
per route class, plus the implied "other" (non-commercial GA) movements = total - domestic - outside.
"""
import calendar
import json
import re
import subprocess
import sys

ROWS = {"总计": "total", "境内航线": "domestic", "境外航线": "outside_mainland",
        "-国际航线": "international", "-港澳台航线": "hk_macau_taiwan"}


def parse(path):
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True,
                         text=True, check=True).stdout
    m = re.search(r"(\d{4})年(\d{1,2})月运输生产情况简报", txt)
    year, month = int(m.group(1)), int(m.group(2))
    block = txt[txt.index("虹桥国际机场"):]
    out = {"file": path.rsplit("/", 1)[-1], "year": year, "month": month}
    for line in block.splitlines():
        s = line.strip()
        for key, name in ROWS.items():
            if s.startswith(key):
                nums = re.findall(r"-?[\d,]+\.?\d*", s[len(key):])
                vals = [float(n.replace(",", "")) for n in nums]
                out[name] = {"movements": int(vals[0]), "movements_yoy_pct": vals[1],
                             "pax_10k": vals[2], "pax_yoy_pct": vals[3],
                             "cargo_10kt": vals[4], "cargo_yoy_pct": vals[5]}
        if s.startswith("重要说明"):
            break
    days = calendar.monthrange(year, month)[1]
    t = out["total"]["movements"]
    out["days"] = days
    out["movements_per_day"] = round(t / days, 1)
    out["other_movements"] = t - out["domestic"]["movements"] - out["outside_mainland"]["movements"]
    out["outside_share_pct"] = round(100 * out["outside_mainland"]["movements"] / t, 2)
    return out


if __name__ == "__main__":
    rows = [parse(p) for p in sorted(sys.argv[1:])]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    tot = sum(r["total"]["movements"] for r in rows)
    days = sum(r["days"] for r in rows)
    print("# months", len(rows), "movements", tot, "days", days, "mean/day", round(tot / days, 1))
