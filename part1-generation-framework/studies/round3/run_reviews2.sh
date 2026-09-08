#!/bin/bash
cd "$(dirname "$0")"
export JUDGE_CONCURRENCY=8
python3 run_reviews_r3.py dev-p31-vs-v0 /root/.config/scene-round2.env >> logs/r3_review2.log 2>&1
python3 run_reviews_r3.py dev-p31-vs-v3 /root/.config/scene-round2.env >> logs/r3_review2.log 2>&1
echo DEV_REVIEWS_DONE >> logs/r3_review2.log
