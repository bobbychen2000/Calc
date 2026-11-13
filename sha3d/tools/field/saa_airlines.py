"""Parse the Shanghai Airport Authority airline directory (www.avinex.com/airlines/index.html).

The page holds four lists, <ul id="company1..4"> = PVG T1, PVG T2, SHA T1, SHA T2.
usage: python3 -I tools/field/saa_airlines.py PAGE.html   (stdlib only; input is untrusted)
Prints JSON: {terminal: [{name, iata, counters}]}.
"""
import html
import json
import re
import sys

LABELS = {"1": "PVG_T1", "2": "PVG_T2", "3": "SHA_T1", "4": "SHA_T2"}


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def main(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'id="company(\d)"', t)]
    out = {}
    for i, (pos, num) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else t.find("<footer", pos)
        block = t[pos:end]
        rows = []
        for li in re.split(r"<li>", block)[1:]:
            name = re.search(r'<div class="title">(.*?)</div>', li, re.S)
            if not name:
                continue
            fields = dict((text(a).rstrip("："), text(b)) for a, b in
                          re.findall(r'<div class="name">(.*?)</div>\s*<div class="value">(.*?)</div>', li, re.S))
            rows.append({"name": text(name.group(1)), "iata": fields.get("二字代码", ""),
                         "counters": fields.get("值机柜台", "")})
        out[LABELS.get(num, num)] = rows
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
