#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 run_reviews_r3.py dev-p29-vs-v0 /root/.config/scene-round2.env >> logs/r3_review.log 2>&1
python3 run_reviews_r3.py dev-p29-vs-p28 /root/.config/scene-round2.env >> logs/r3_review.log 2>&1
echo DONE_ALL >> logs/r3_review.log
