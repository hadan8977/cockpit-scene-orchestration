#!/bin/bash
cd "$(dirname "$0")"
export SCENE_CAPS=r3 SCENE_CONTRACT=v4 SCENE_CONCURRENCY=16
until [ -f results/r3_05_equal/archive.json ]; do sleep 10; done
python3 study.py plans/r3_06_holdout.json --env /root/.config/scene-round2.env >> logs/r3_06_holdout.log 2>&1
echo HOLDOUT_DONE >> logs/r3_06_holdout.log
