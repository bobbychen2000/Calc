# long video assembly: shots in shots.json order (missing ones skipped), 0.6-s dissolves (fadeblack into night), title + chapter cards
# + credit line overlays, end card; narration at chapter starts; generative bed ducked under the voice; loudnorm
import json, os, subprocess, sys
L = sys.argv[1]; OUT = sys.argv[2]; SH = f'{L}/shots'; TR = os.path.dirname(L) + '/trailer/cards'
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).strip())
spec = [s for s in json.load(open(f'{L}/shots.json')) if os.path.exists(f"{SH}/shot_{s['id']}.mp4")]
X = 0.6; END = 7.0
ds = [dur(f"{SH}/shot_{s['id']}.mp4") for s in spec]; st = []; t = 0.0
for i, d in enumerate(ds):
    if i: t -= X
    st.append(t); t += d
end_start = t - 1.0; total = end_start + END
chs = {}; [chs.setdefault(s['ch'], st[i]) for i, s in enumerate(spec)]
vo = {k: dur(f'{L}/vo/vo_{k}.wav') for k in json.load(open(f'{L}/vo/lines.json'))}
want = [('c0', 0, 2.5), ('c1', 1, 1.5), ('c2', 2, 1.0), ('c2b', 2, 14.0), ('c3', 3, 1.0), ('c3b', 3, 15.0), ('c4', 4, 1.0), ('c5', 5, 1.5), ('c6', 6, 1.5), ('c7', 7, 1.5), ('c8', 8, 1.0)]
place = {}; last = -9
for k, c, d in want:
    if c not in chs: continue
    p = max(chs[c] + d, last + 0.8); place[k] = p; last = p + vo[k]
inp, fc = [], []
for s in spec: inp += ['-i', f"{SH}/shot_{s['id']}.mp4"]
n = len(spec)
inp += ['-loop', '1', '-t', f'{END}', '-framerate', '24', '-i', f'{TR}/end.png', '-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{TR}/title.png',
        '-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{TR}/credit.png']
iE, iT, iC = n, n + 1, n + 2; cards = [c for c in range(1, 8) if c in chs]
for c in cards: inp += ['-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{L}/cards/ch{c}.png']
for i in range(n): fc.append(f'[{i}:v]settb=AVTB,fps=24,format=yuv420p,setsar=1,eq=contrast=1.05:saturation=1.08[v{i}]')
fc.append(f'[{iE}:v]scale=1920:1080,format=yuv420p,setsar=1,settb=AVTB,fps=24[vE]')
cur, acc = 'v0', ds[0]
for i in range(1, n):
    tr = 'fadeblack' if spec[i]['ch'] != spec[i - 1]['ch'] and spec[i]['ch'] in (6, 7) else 'fade'
    fc.append(f'[{cur}][v{i}]xfade=transition={tr}:duration={X}:offset={acc - X:.3f}[x{i}]'); cur = f'x{i}'; acc += ds[i] - X
fc.append(f'[{cur}][vE]xfade=transition=fadeblack:duration=1.0:offset={acc - 1.0:.3f}[xe]')
fc.append(f'[{iT}:v]format=rgba,fade=t=in:st=0.8:d=0.8:alpha=1,fade=t=out:st=5.0:d=0.9:alpha=1[ti]')
fc.append(f'[{iC}:v]format=rgba,fade=t=out:st={end_start - 0.3:.3f}:d=0.6:alpha=1[cr]')
lab = 'xe'; fc.append(f'[xe][ti]overlay=0:0:shortest=1[o0]'); lab = 'o0'
for j, c in enumerate(cards):
    a = chs[c] + 0.7; fc.append(f'[{iC + 1 + j}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.6:alpha=1,fade=t=out:st={a + 3.4:.2f}:d=0.7:alpha=1[k{j}]')
    fc.append(f'[{lab}][k{j}]overlay=0:0:shortest=1[o{j + 1}]'); lab = f'o{j + 1}'
fc.append(f'[{lab}][cr]overlay=0:0:shortest=1,fade=t=in:st=0:d=1.0,fade=t=out:st={total - 1.2:.3f}:d=1.2,format=yuv420p[vout]')
ai = len(inp) // 2 if False else None
k0 = iC + 1 + len(cards); keys = list(place)
for k in keys: inp += ['-i', f'{L}/vo/vo_{k}.wav']
inp += ['-i', f'{L}/music.wav']; im = k0 + len(keys)
for j, k in enumerate(keys):
    ms = int(place[k] * 1000); fc.append(f'[{k0 + j}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}|{ms},apad=whole_dur={total:.3f}[a{j}]')
fc.append(''.join(f'[a{j}]' for j in range(len(keys))) + f'amix=inputs={len(keys)}:normalize=0,atrim=0:{total:.3f},asplit=2[vo][vok]')
fc.append(f'[{im}:a]aresample=48000,aformat=channel_layouts=mono,atrim=0:{total:.3f},afade=t=out:st={total - 4:.3f}:d=4,volume=0.30[mus]')
fc.append('[mus][vok]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=600[bed]')
fc.append('[vo][bed]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=stereo,aresample=48000[aout]')
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + inp + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', '-t', f'{total:.3f}', OUT]
print(json.dumps({'shots': n, 'total': round(total, 1), 'chapters': {k: round(v, 1) for k, v in chs.items()}, 'vo': {k: round(v, 1) for k, v in place.items()}}))
subprocess.check_call(cmd); print('wrote', OUT, round(os.path.getsize(OUT) / 1e6, 1), 'MB')
