#!/bin/bash
# sequential trial queue (one model at a time: 4 cores)
cd /home/user/rhwork/tts_zh
while kill -0 6863 2>/dev/null; do sleep 15; done
echo "== ming 灵朵儿"; THREADS=4 /home/user/rhwork/venv-ming/bin/python gen_ming.py 灵朵儿 2>&1 | grep --line-buffered -E "^T"
echo "== ming 灵楷"; THREADS=4 /home/user/rhwork/venv-ming/bin/python gen_ming.py 灵楷 2>&1 | grep --line-buffered -E "^T"
echo "== voxcpm design ref"
cat > /tmp/claude-0/sp/vox_ref.json <<'J'
{"REF": "黎曼猜想是数学中最著名的未解决问题之一，它关乎素数分布的深层规律。"}
J
python3 - <<'P'
import json; T=json.load(open('testset.json')); T.update(json.load(open('/tmp/claude-0/sp/vox_ref.json'))); json.dump(T, open('testset_ref.json','w'), ensure_ascii=False)
P
cp testset.json testset.bak.json; cp testset_ref.json testset.json
THREADS=4 /home/user/rhwork/venv-voxcpm/bin/python gen_voxcpm.py voxcpm2_design REF --design "一位知性的青年女性，音色清澈温暖，吐字清晰，语速适中偏慢，语调平稳，像科普纪录片的旁白" 2>&1 | grep --line-buffered -E "^REF|load"
cp testset.bak.json testset.json
echo "== voxcpm locked ref"; THREADS=4 /home/user/rhwork/venv-voxcpm/bin/python gen_voxcpm.py voxcpm2_f --ref out/voxcpm2_design/REF.wav --ref-text "黎曼猜想是数学中最著名的未解决问题之一，它关乎素数分布的深层规律。" 2>&1 | grep --line-buffered -E "^T|load|rror"
echo "== qwen 0.6B serena rest"; THREADS=4 /home/user/rhwork/venv-qwen/bin/python gen_qwen.py models/Qwen3-TTS-12Hz-0.6B-CustomVoice Serena T3_waves T4_stepanov T5_theta 2>&1 | grep --line-buffered -E "^T"
echo "== eval"; /home/user/rhwork/venv-eval/bin/python eval_zh.py out/*/T*.wav 2>&1 | grep --line-buffered "cer "
/home/user/rhwork/venv-eval/bin/python eval_zh.py --summary
echo QUEUE DONE
