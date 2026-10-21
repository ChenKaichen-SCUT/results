#!/bin/bash
set -euo pipefail
R=/root/deagle-svcomp26-repro-20261021-01a15ee7
while systemctl is-active --quiet deagle-repro-batch2.service || systemctl is-active --quiet deagle-repro-resource-stacks.service; do sleep 5; done
cd "$R"
export TMPDIR="$R/tmp"
exec taskset -c 0-3 python3 scripts/run_linter.py
