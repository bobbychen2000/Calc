"""Strip an HTML file to text (stdlib only). usage: python3 -I tools/field/html_text.py FILE [encoding]"""
import html, re, sys
raw = open(sys.argv[1], "rb").read()
enc = sys.argv[2] if len(sys.argv) > 2 else None
if not enc:
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', raw[:4000])
    enc = m.group(1).decode() if m else "utf-8"
t = raw.decode(enc, errors="replace")
t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", t)
t = html.unescape(re.sub(r"<[^>]+>", " ", t))
t = re.sub(r"[ \t　\xa0]+", " ", t)
t = re.sub(r"\n\s*\n+", "\n", t)
print(t.strip())
