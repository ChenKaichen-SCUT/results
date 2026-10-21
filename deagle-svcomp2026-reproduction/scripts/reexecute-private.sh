#!/bin/bash
set -euo pipefail
R=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$R"
mount --bind "$R/runs" "$R/runtime/rootfs/runs"
mount -t proc proc "$R/runtime/rootfs/proc"
export PYTHONPATH="$R/sources/python-deps"
export TMPDIR="$R/tmp"
exec taskset -c 0-3 python3 scripts/run_batch.py --workers 7
