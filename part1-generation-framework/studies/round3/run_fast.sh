#!/bin/bash
cd "$(dirname "$0")"
export JUDGE_CONCURRENCY=12
python3 run_judges_fast.py holdout-p31-vs-v0 qwen,dsv4 /root/.config/scene-round2.env >> logs/r3_fast.log 2>&1
echo HOLDOUT_FAST_DONE >> logs/r3_fast.log
python3 run_judges_fast.py dev-p31-vs-v0 qwen,dsv4 /root/.config/scene-round2.env >> logs/r3_fast.log 2>&1
echo DEV_FAST_DONE >> logs/r3_fast.log
