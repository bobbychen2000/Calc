"""Print the paragraph text of a .docx (stdlib only; reads word/document.xml, executes nothing).
usage: python3 -I tools/law/docx_text.py FILE.docx"""
import re, sys, zipfile, html
with zipfile.ZipFile(sys.argv[1]) as z:
    x = z.read("word/document.xml").decode("utf-8", "replace")
for p in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S):
    t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    if t.strip():
        print(html.unescape(t))
