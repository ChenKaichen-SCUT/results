#!/bin/bash
set -euo pipefail
R=/root/deagle-svcomp26-repro-20261021-01a15ee7
cd "$R"
mkdir -p diagnostics runtime/rootfs/diagnostics
mount --bind "$R/diagnostics" "$R/runtime/rootfs/diagnostics"
mount -t proc proc "$R/runtime/rootfs/proc"
export TMPDIR="$R/tmp"
exec taskset -c 0-3 python3 scripts/run_diagnostics.py
