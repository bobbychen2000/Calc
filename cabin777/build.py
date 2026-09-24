import glob, os, re, sys
root = os.path.dirname(os.path.abspath(__file__))
dist = os.environ.get('CABIN_DIST') or os.path.join(root, 'dist')   # per-agent output dir for parallel work
os.makedirs(dist, exist_ok=True)
js = []
for f in sorted(glob.glob(os.path.join(root, 'src', '*.js'))):
    js.append('// ==== ' + os.path.basename(f) + ' ====\n' + open(f).read())
script = '\n'.join(js) + '\nboot();\n'
page = open(os.path.join(root, 'src', 'page.html')).read()
out = page.replace('/*__SCRIPT__*/', script)
open(os.path.join(dist, 'cabin.html'), 'w').write(out)
skeleton = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#f7f7f5}img{max-width:100%}[hidden]{display:none!important}</style>'
            '</head><body>\n')
open(os.path.join(dist, 'test.html'), 'w').write(skeleton + out + '\n</body></html>')
print('built', len(out), 'bytes')
