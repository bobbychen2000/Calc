# trailer assembly: shots + xfades + title/credit overlays + end card; VO lines on their shots + quiet synthesized pad
import json, os, subprocess, sys
D = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else D + '/sfo_live_3d_trailer.mp4'
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).strip())
ORDER = ['aerial', 'arrival', 'gates', 'taxi', 'tower', 'night', 'takeoff']
shots = [s for s in ORDER if os.path.exists(f'{D}/shot_{s}.mp4') and os.path.getsize(f'{D}/shot_{s}.mp4') > 0]
X = {'night': 1.0}            # transition INTO this shot (fadeblack), others 0.6 s dissolve
END_D, END_X = 6.0, 1.0
ds = [dur(f'{D}/shot_{s}.mp4') for s in shots]
starts, t = [], 0.0
for i, s in enumerate(shots):
    if i: t -= X.get(s, 0.6)
    starts.append(t); t += ds[i]
end_start = t - END_X; total = end_start + END_D
st = dict(zip(shots, starts)); dd = dict(zip(shots, ds))
vo = {k: dur(f'{D}/../tts/vo_{k}.wav') for k in ['l1', 'l2', 'l3', 'l4', 'l5', 'l6']}
place = {}
place['l1'] = st.get('aerial', 0) + 1.2
if 'arrival' in st: place['l2'] = st['arrival'] + 0.5
if 'gates' in st: place['l3'] = st['gates'] + 0.4
if 'taxi' in st: place['l4'] = max(st['taxi'] + 1.2, place.get('l3', 0) + vo['l3'] + 0.4)
if 'tower' in st: place['l5'] = max(st['tower'] + 1.0, place.get('l4', 0) + vo['l4'] + 0.5)
place['l6'] = (st['takeoff'] + 3.0) if 'takeoff' in st else end_start + 0.5
# video graph
inp = []; fc = []
for s in shots: inp += ['-i', f'{D}/shot_{s}.mp4']
inp += ['-loop', '1', '-t', f'{END_D}', '-framerate', '24', '-i', f'{D}/cards/end.png']
inp += ['-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{D}/cards/title.png']
inp += ['-loop', '1', '-framerate', '24', '-t', f'{total:.3f}', '-i', f'{D}/cards/credit.png']
n = len(shots); iE, iT, iC = n, n + 1, n + 2
for i in range(n): fc.append(f'[{i}:v]settb=AVTB,fps=24,format=yuv420p,setsar=1[v{i}]')
fc.append(f'[{iE}:v]scale=1920:1080,format=yuv420p,setsar=1,settb=AVTB,fps=24[vE]')
cur = 'v0'; acc = ds[0]
for i in range(1, n):
    x = X.get(shots[i], 0.6); tr = 'fadeblack' if shots[i] == 'night' else 'fade'
    fc.append(f'[{cur}][v{i}]xfade=transition={tr}:duration={x}:offset={acc - x:.3f}[x{i}]'); cur = f'x{i}'; acc += ds[i] - x
fc.append(f'[{cur}][vE]xfade=transition=fadeblack:duration={END_X}:offset={acc - END_X:.3f}[xe]')
t0, t1 = st.get('aerial', 0) + 0.6, st.get('aerial', 0) + 4.4
fc.append(f'[{iT}:v]format=rgba,fade=t=in:st={t0}:d=0.8:alpha=1,fade=t=out:st={t1}:d=0.9:alpha=1[ti]')
fc.append(f'[{iC}:v]format=rgba,fade=t=out:st={end_start - 0.2:.3f}:d=0.6:alpha=1[cr]')
fc.append('[xe][ti]overlay=0:0:shortest=1[o1]'); fc.append('[o1][cr]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.8,' + f'fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p[vout]')
# audio: VO + pad (A major-ish drone, slow swell), ducked under the voice
ai = n + 3
for k in ['l1', 'l2', 'l3', 'l4', 'l5', 'l6']: inp += ['-i', f'{D}/../tts/vo_{k}.wav']
pad = ("aevalsrc='0.10*sin(2*PI*110*t)+0.07*sin(2*PI*164.81*t)+0.06*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.07*t))"
       "+0.045*sin(2*PI*277.18*t)*(0.5+0.5*sin(2*PI*0.05*t+1))+0.035*sin(2*PI*329.63*t)*(0.5+0.5*sin(2*PI*0.09*t+2))"
       f"+0.02*sin(2*PI*440*t)*(0.5+0.5*sin(2*PI*0.031*t))':s=48000:d={total:.3f}")
inp += ['-f', 'lavfi', '-i', pad]; ip = ai + 6
vol = []
for j, k in enumerate(['l1', 'l2', 'l3', 'l4', 'l5', 'l6']):
    ms = int(place[k] * 1000); fc.append(f'[{ai + j}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}|{ms},apad=whole_dur={total:.3f}[a{j}]'); vol.append(f'[a{j}]')
fc.append(''.join(vol) + f'amix=inputs=6:normalize=0,atrim=0:{total:.3f},asplit=2[vo][vok]')
fc.append(f'[{ip}:a]lowpass=f=1800,aecho=0.8:0.7:120|260:0.25|0.18,afade=t=in:st=0:d=2.5,afade=t=out:st={total - 3.0:.3f}:d=3.0,volume=0.22,aformat=channel_layouts=mono[pad0]')
fc.append('[pad0][vok]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[pad]')
fc.append('[vo][pad]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9,aformat=channel_layouts=stereo,aresample=48000[aout]')
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + inp + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.3f}', OUT]
print(json.dumps({'shots': dict(zip(shots, [round(x, 2) for x in ds])), 'starts': {k: round(v, 2) for k, v in st.items()}, 'vo': {k: [round(place[k], 2), vo[k]] for k in place}, 'total': round(total, 2)}))
subprocess.check_call(cmd); print('wrote', OUT, round(os.path.getsize(OUT) / 1e6, 1), 'MB')
