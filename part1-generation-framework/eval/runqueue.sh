#!/bin/bash
# 串行跑一批评测：每行 "<tag> <prompt> [额外参数...]"，已有 summary.json 的 tag 直接跳过。
# 用法：bash runqueue.sh jobs.txt
cd /root/work/work/cockpit-scene-orchestration-r2-20260902/eval
source .env.local
mkdir -p logs
while read -r tag prompt rest; do
  [ -z "$tag" ] && continue
  case "$tag" in \#*) continue;; esac
  if [ -f "results/$tag/summary.json" ]; then echo "[skip] $tag"; continue; fi
  log="logs/$(echo $tag | tr '/' '_').log"
  echo "[start] $(date +%H:%M:%S) $tag $prompt $rest"
  python3 run_eval.py --model-key ds-v4-flash --prompt "$prompt" --style p3 --lang both --repeat 1 --concurrency 4 --tag "$tag" $rest > "$log" 2>&1
  echo "[done] $(date +%H:%M:%S) $tag rc=$?"
done < "$1"
echo QUEUE_DONE
