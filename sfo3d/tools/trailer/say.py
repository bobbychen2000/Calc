# narration lines -> wav files (Kokoro-82M, Apache-2.0, via kokoro-onnx, MIT)
import sys, json, soundfile as sf
from kokoro_onnx import Kokoro
D = sys.argv[1]; voice = sys.argv[2] if len(sys.argv) > 2 else 'af_heart'; speed = float(sys.argv[3]) if len(sys.argv) > 3 else 0.95
k = Kokoro(D + '/dl/kokoro-v1.0.onnx', D + '/dl/voices-v1.0.bin')
lines = json.load(open(D + '/lines.json'))
out = {}
for key, text in lines.items():
    a, sr = k.create(text, voice=voice, speed=speed, lang='en-us')
    sf.write(f'{D}/vo_{key}.wav', a, sr); out[key] = round(len(a) / sr, 2)
print(json.dumps(out))
