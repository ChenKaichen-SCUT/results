#!/bin/bash
set -euo pipefail
R=/root/deagle-svcomp26-repro-20261021-01a15ee7
while systemctl is-active --quiet deagle-repro-hard960.service; do sleep 5; done
exec /usr/bin/unshare --mount --propagation private /bin/bash "$R/scripts/launch_diagnostics.sh"
