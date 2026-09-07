#!/bin/bash
# One orchestrator for the remaining round-two steps. Runs one paid process per provider at a time.
set -u
cd /root/work/work/cockpit-scene-orchestration-latest/part1-generation-framework/studies/round2
ENVF=/root/.config/scene-round2.env
log(){ echo "[$(date -u +%H:%M:%S)] $*"; }

log "等待 15 完整回归"
while pgrep -f "study.py plans/15_full_regression" >/dev/null; do sleep 20; done
log "15 完成"
python3 split_analysis.py 15_full_regression --pair p26 v3_inline
python3 split_analysis.py 15_full_regression --pair p26 v0_contract | tail -3

log "启动 16 留出（DeepSeek 账本）"
setsid nohup python3 -u study.py plans/16_holdout.json --env-file "$ENVF" > logs/16_holdout.log 2>&1 < /dev/null &

log "开发盲评 1：p26 对 v3_inline（OpenRouter 账本）"
python3 quality.py prepare final-p26-vs-v3 --source-run 15_full_regression --candidate p26 --baseline v3_inline
python3 -u quality.py run final-p26-vs-v3 --env-file "$ENVF" > logs/judge-final-v3.log 2>&1
log "盲评 1 完成"

log "开发盲评 2：p26 对 v0_contract"
python3 quality.py prepare final-p26-vs-v0 --source-run 15_full_regression --candidate p26 --baseline v0_contract
python3 -u quality.py run final-p26-vs-v0 --env-file "$ENVF" > logs/judge-final-v0.log 2>&1
log "盲评 2 完成"

log "等待 16 留出"
while pgrep -f "study.py plans/16_holdout" >/dev/null; do sleep 20; done
log "16 完成"
python3 split_analysis.py 16_holdout --pair p26 v3_inline
python3 split_analysis.py 16_holdout --pair p26 v0_contract | tail -3

log "留出体验盲评"
python3 prepare_holdout_review.py
python3 -u quality.py run holdout-p26-vs-v3 --env-file "$ENVF" > logs/judge-holdout.log 2>&1
log "全部完成"
python3 - <<'PY'
import json
g=json.load(open('private-ledger.json')); j=json.load(open('judge-private-ledger.json'))
ch=sum(a.get('charged',a['upper']) for a in j['attempts'])
print(f"DS {len(g['attempts'])}/7000 | 评审 {len(j['attempts'])}/1400 ${ch:.3f}/$2.5")
PY
