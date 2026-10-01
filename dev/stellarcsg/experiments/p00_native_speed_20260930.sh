#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-native-speed-20260930","run":"two-100k-matched-pairs","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-native-speed-20260930"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

ulimit -v 2097152
ulimit -c 0
export PYTHONDONTWRITEBYTECODE=1
timeout --signal=TERM --kill-after=10s 2500s /usr/bin/python3 \
  dev/stellarcsg/experiments/p00_native_speed_20260930.py
