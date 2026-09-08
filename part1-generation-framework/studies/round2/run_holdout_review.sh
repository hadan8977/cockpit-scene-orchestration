#!/bin/bash
# Prepare and run the holdout experience review once the second development blind review has finished.
set -u
cd /root/work/work/cockpit-scene-orchestration-latest/part1-generation-framework/studies/round2
E=/root/.config/scene-round2.env
until [ -f judge/final-p26-vs-v0/summary.json ]; do sleep 20; done
echo "[$(date -u +%H:%M:%S)] 开发盲评2 已出结果，准备留出盲评"
python3 prepare_holdout_review.py
echo "[$(date -u +%H:%M:%S)] 启动留出盲评"
python3 -u quality.py run holdout-p26-vs-v3 --env-file "$E" > logs/judge-holdout.log 2>&1
echo "[$(date -u +%H:%M:%S)] 留出盲评完成"
python3 - <<'PY'
import json
g=json.load(open('private-ledger.json')); j=json.load(open('judge-private-ledger.json'))
ch=sum(a.get('charged',a['upper']) for a in j['attempts'])
print(f"DS {len(g['attempts'])}/7000 | 评审 {len(j['attempts'])}/1400 ${ch:.3f}/$2.5")
PY
