#!/bin/bash
cd "$(dirname "$0")"
export JUDGE_CONCURRENCY=12
python3 run_judges_fast.py dev-p33-vs-v0 dsv4,qwen /root/.config/scene-round2.env >> logs/r3_fast2.log 2>&1
echo P33_DONE >> logs/r3_fast2.log
