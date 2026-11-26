#!/usr/bin/env bash
# Build a task image and run its verifier twice without Harbor: unchanged (nop, expect 0) and after the
# reference solution (oracle, expect 1). Prints the verifier details for both. Usage: check_task.sh TASK_DIR
set -euo pipefail
task=$(cd "$1" && pwd); name=$(basename "$task")
docker build -q -t "ahl-devbench-check/$name" "$task/environment" >/dev/null
for mode in nop oracle; do
  cmd="bash /tests/test.sh >/dev/null 2>&1; cat /logs/verifier/details.json"
  [ $mode = oracle ] && cmd="bash /solution/solve.sh && $cmd"
  echo "$name $mode $(docker run --rm --network none -v "$task/tests:/tests:ro" -v "$task/solution:/solution:ro" \
    "ahl-devbench-check/$name" bash -c "$cmd" | tr -d '\n ')"
done
