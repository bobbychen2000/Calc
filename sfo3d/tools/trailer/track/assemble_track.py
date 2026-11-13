# Assemble one tracking film: its shots in shots3.json order (missing ones skipped), hard cuts, per-shot phase label +
# time-lapse badge (cards_track.mjs), film title over the opening, end card with credits, generative music bed (long/music.wav).
# usage: assemble_track.py <track dir> <arr|dep> <out.mp4>
import json, os, subprocess, sys
T, FILM, OUT = sys.argv[1:4]; SH = f'{T}/shots'; CD = f'{T}/cards'
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).strip())
spec = [s for s in json.load(open(f'{T}/shots3.json')) if s['film'] == FILM and os.path.exists(f"{SH}/shot_{s['id']}.mp4")]
X, END = 0.0, 6.0
ds = [dur(f"{SH}/shot_{s['id']}.mp4") for s in spec]; st = []; t = 0.0
for i, d in enumerate(ds):
    if i: t -= X
    st.append(t); t += d
end_start = t - 1.0; total = end_start + END
inp, fc = [], []
for s in spec: inp += ['-i', f"{SH}/shot_{s['id']}.mp4"]
n = len(spec); iE = n; iT = n + 1
inp += ['-loop', '1', '-framerate', '24', '-t', f'{END}', '-i', f'{CD}/end.png', '-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{CD}/title_{FILM}.png']
for s in spec: inp += ['-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f"{CD}/lab_{s['id']}.png"]
for i in range(n): fc.append(f'[{i}:v]settb=AVTB,fps=24,format=yuv420p,setsar=1,eq=contrast=1.04:saturation=1.06[v{i}]')
fc.append(f'[{iE}:v]scale=1920:1080,format=yuv420p,setsar=1,settb=AVTB,fps=24[vE]')
# hard cuts between shots (a dissolve between two shots of the same aircraft reads as a ghosted double aircraft --
# review 13 Nov); fade through black into the end card only
fc.append(''.join(f'[v{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0,fps=24[cat]'); acc = sum(ds)
fc.append(f'[cat][vE]xfade=transition=fadeblack:duration=1.0:offset={acc - 1.0:.3f}[xe]')
fc.append(f'[{iT}:v]format=rgba,fade=t=in:st=0.8:d=0.8:alpha=1,fade=t=out:st=6.2:d=0.9:alpha=1[ti]')
fc.append('[xe][ti]overlay=0:0:shortest=1[o0]'); lab = 'o0'
for j in range(n):
    a = st[j] + (7.4 if j == 0 else 0.6); b = st[j] + ds[j] - 0.9
    if b - a < 1.5: continue
    fc.append(f'[{iT + 1 + j}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.5:alpha=1,fade=t=out:st={b:.2f}:d=0.5:alpha=1[k{j}]')
    fc.append(f'[{lab}][k{j}]overlay=0:0:shortest=1[o{j + 1}]'); lab = f'o{j + 1}'
fc.append(f'[{lab}]fade=t=in:st=0:d=1.0,fade=t=out:st={total - 1.2:.3f}:d=1.2,format=yuv420p[vout]')
im = iT + 1 + n; inp += ['-i', f'{os.path.dirname(T)}/long/music.wav']
fc.append(f'[{im}:a]aresample=48000,atrim=0:{total:.3f},afade=t=in:st=0:d=2,afade=t=out:st={total - 4:.3f}:d=4,volume=0.55,loudnorm=I=-18:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[aout]')
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + inp + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', '-t', f'{total:.3f}', OUT]
print(json.dumps({'film': FILM, 'shots': n, 'missing': [s['id'] for s in json.load(open(f'{T}/shots3.json')) if s['film'] == FILM and s not in spec], 'total': round(total, 1)}))
subprocess.check_call(cmd); print('wrote', OUT, round(os.path.getsize(OUT) / 1e6, 1), 'MB')
