#!/bin/bash
cd "$(dirname "$0")"
export JUDGE_CONCURRENCY=8
until grep -q MAIN_GATE_DONE logs/r3_review3.log 2>/dev/null; do sleep 15; done
python3 run_reviews_r3.py holdout-p31-vs-v0 /root/.config/scene-round2.env >> logs/r3_review4.log 2>&1
echo HOLDOUT_REVIEW_DONE >> logs/r3_review4.log
