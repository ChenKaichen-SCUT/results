#!/bin/bash
set -euo pipefail
R=/root/deagle-svcomp26-repro-20261021-01a15ee7
cd "$R"
# Invoked inside a private mount namespace. All filesystem changes stay in R.
mount --bind "$R/runs" "$R/runtime/rootfs/runs"
mount -t proc proc "$R/runtime/rootfs/proc"
export PYTHONPATH="$R/sources/python-deps"
export TMPDIR="$R/tmp"
exec taskset -c 0-3 python3 scripts/run_batch.py "$@"
