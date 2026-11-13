"""Dump rows of an .xlsx (stdlib only; downloads are untrusted, run with python3 -I).

usage: python3 -I tools/field/xlsx_rows.py FILE.xlsx [grep-regex]
Prints the header rows (first 6) of every sheet and then any row matching the regex.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read(path):
    z = zipfile.ZipFile(path)
    for info in z.infolist():
        if info.file_size > 50_000_000:
            raise SystemExit("member too large: %s" % info.filename)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
    sheets = []
    for s in wb.find("m:sheets", NS):
        target = relmap[s.get(RNS)]
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.iter("{%s}row" % NS["m"]):
            cells = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                t = c.get("t")
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                else:
                    val = v.text if v is not None else ""
                cells[col_index(c.get("r"))] = val
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        sheets.append((s.get("name"), rows))
    return sheets


def main():
    path = sys.argv[1]
    pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
    for name, rows in read(path):
        print("### sheet", name, "rows", len(rows))
        for r in rows[:6]:
            print(" | ".join(r))
        if pat:
            print("... matches:")
            for r in rows:
                if any(pat.search(x) for x in r):
                    print(" | ".join(r))


if __name__ == "__main__":
    main()
