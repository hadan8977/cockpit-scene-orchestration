#!/bin/bash
set -u
cd /root/work/work/cockpit-scene-orchestration-latest/part1-generation-framework/studies/round2
E=/root/.config/scene-round2.env
echo "[$(date -u +%H:%M:%S)] 盲评1 p26 vs v3_inline"
python3 -u quality.py run final-p26-vs-v3 --env-file "$E" > logs/judge-final-v3.log 2>&1
echo "[$(date -u +%H:%M:%S)] 盲评2 p26 vs v0_contract"
python3 -u quality.py run final-p26-vs-v0 --env-file "$E" > logs/judge-final-v0.log 2>&1
echo "[$(date -u +%H:%M:%S)] 两轮开发盲评完成"
