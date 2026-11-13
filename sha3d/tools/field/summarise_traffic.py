"""Reproducible traffic summary for SHA/ZSSS from the cached CAAC and SIAC downloads.

usage (from sha3d/):  python3 -I tools/field/summarise_traffic.py > refs/cache/field/derived_field/traffic_summary.json
Reads (untrusted, stdlib only):
  refs/cache/field/caac_bulletin_{2023,2024,2025}/ranking_*.xlsx   CAAC airport ranking (attachment 1)
  refs/cache/field/caac_bulletin_2025/hubs_by_route_2025.xlsx       CAAC hub airports by route (attachment 2)
  refs/cache/field/derived_field/siac_hongqiao_monthly.jsonl         output of tools/field/siac_briefs.py
"""
import calendar
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_rows import read  # noqa: E402  (our own module, not a download)

ROOT = "refs/cache/field"


def row_for(path, name="上海/虹桥"):
    for _sheet, rows in read(path):
        for r in rows:
            if r and r[0].strip() == name:
                return r
    raise SystemExit("no row %s in %s" % (name, path))


def main():
    out = {"airport": "上海/虹桥 (SHA/ZSSS)", "caac_annual": {}, "caac_2025_by_route": {}, "siac_monthly": []}
    for year in (2023, 2024, 2025):
        r = row_for(f"{ROOT}/caac_bulletin_{year}/ranking_{year}.xlsx")
        days = 366 if calendar.isleap(year) else 365
        mov = int(float(r[10]))
        out["caac_annual"][year] = {
            "passengers": int(float(r[2])), "passengers_rank": int(float(r[1])),
            "passengers_prev_year": int(float(r[3])), "passengers_yoy_pct": round(float(r[4]), 1),
            "cargo_t": round(float(r[6]), 3), "cargo_rank": int(float(r[5])),
            "movements": mov, "movements_rank": int(float(r[9])),
            "movements_prev_year": int(float(r[11])), "movements_yoy_pct": round(float(r[12]), 1),
            "days": days, "movements_per_day": round(mov / days, 1),
        }
    r = row_for(f"{ROOT}/caac_bulletin_2025/hubs_by_route_2025.xlsx")
    tot, dom, hmt, intl = (int(float(x)) for x in r[9:13])
    ptot, pdom, phmt, pintl = (int(float(x)) for x in r[1:5])
    out["caac_2025_by_route"] = {
        "movements": {"total": tot, "domestic_incl_hmt": dom, "of_which_hk_macau_taiwan": hmt, "international": intl,
                      "share_intl_pct": round(100 * intl / tot, 2), "share_hmt_pct": round(100 * hmt / tot, 2),
                      "share_intl_plus_hmt_pct": round(100 * (intl + hmt) / tot, 2)},
        "passengers": {"total": ptot, "domestic_incl_hmt": pdom, "of_which_hk_macau_taiwan": phmt, "international": pintl,
                       "share_intl_plus_hmt_pct": round(100 * (pintl + phmt) / ptot, 2)},
    }
    rows = [json.loads(line) for line in open(f"{ROOT}/derived_field/siac_hongqiao_monthly.jsonl")
            if line.startswith("{")]
    out["siac_monthly"] = [{"month": f"{x['year']}-{x['month']:02d}", "movements": x["total"]["movements"],
                            "per_day": x["movements_per_day"], "yoy_pct": x["total"]["movements_yoy_pct"],
                            "domestic": x["domestic"]["movements"], "international": x["international"]["movements"],
                            "hk_macau_taiwan": x["hk_macau_taiwan"]["movements"], "other_ga": x["other_movements"],
                            "outside_mainland_share_pct": x["outside_share_pct"]} for x in rows]
    ytd = [x for x in rows if x["year"] == 2026]
    mv = sum(x["total"]["movements"] for x in ytd)
    dd = sum(x["days"] for x in ytd)
    out["siac_2026_ytd"] = {"months": len(ytd), "movements": mv, "days": dd, "per_day": round(mv / dd, 1),
                            "min_month_per_day": min(x["movements_per_day"] for x in ytd),
                            "max_month_per_day": max(x["movements_per_day"] for x in ytd),
                            "other_ga_per_day": round(sum(x["other_movements"] for x in ytd) / dd, 1)}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
