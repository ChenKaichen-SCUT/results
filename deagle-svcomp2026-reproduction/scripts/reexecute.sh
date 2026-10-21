#!/bin/bash
# Reexecute all 667 instances, or a single existing task ID, in a fresh directory.
set -euo pipefail
BASE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
test "$(id -u)" -eq 0 || { echo 'Run as root for cgroups and isolated chroot.' >&2; exit 1; }
test "$(getconf _NPROCESSORS_ONLN)" -ge 32 || { echo 'This recorded CPU allocation needs 32 logical CPUs.' >&2; exit 1; }
test -e /sys/fs/cgroup/cgroup.controllers || { echo 'cgroup v2 required.' >&2; exit 1; }
if systemctl is-active --quiet deagle-repro-batch2.service; then
 echo 'Original reproduction is still active. Preserve its dedicated CPU allocation and wait for completion.' >&2; exit 1
fi
ID=${1:-all}
case "$ID" in all) ;; *[!0-9a-f]*|'') echo 'Argument must be all or a 16-character task ID.' >&2; exit 1;; *) test "${#ID}" -eq 16;; esac
NEEDED=23000000000
if test "$ID" = all; then NEEDED=113000000000; fi
AVAILABLE=$(awk '/^MemAvailable:/ {print $2 * 1024}' /proc/meminfo)
python3 - "$AVAILABLE" "$NEEDED" <<'PY'
import sys
assert float(sys.argv[1]) >= int(sys.argv[2]), 'Insufficient available memory for isolated replay; wait until other workloads finish.'
PY
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
python3 - "$BASE" <<'PY'
import pathlib,shutil,subprocess,sys
b=pathlib.Path(sys.argv[1]);needed=sum(int(line.split()[0]) for line in subprocess.check_output(['du','-sb',str(b/'runtime/rootfs'),str(b/'sources/python-deps'),str(b/'sources/sv-benchmarks')],text=True).splitlines())
assert shutil.disk_usage(b).free >= needed+5000000000, 'Insufficient disk headroom for a fresh replay; no existing evidence will be removed.'
PY
DEST="$BASE/replays/$STAMP-$ID"
test ! -e "$DEST" || { echo 'Replay directory already exists; refusing to overwrite.' >&2; exit 1; }
mkdir -p "$DEST"/{scripts,sources,runtime,reports,runs,diagnostics,tmp,evidence}
cp -a "$BASE/runtime/rootfs" "$DEST/runtime/"
cp -a "$BASE/sources/python-deps" "$BASE/sources/sv-benchmarks" "$DEST/sources/"
cp -a "$BASE/scripts/run_batch.py" "$BASE/scripts/reexecute-private.sh" "$DEST/scripts/"
cp -a "$BASE/reports/input-hash-audit.json" "$DEST/reports/"
python3 - "$BASE/reports/run-plan.json" "$DEST/reports/run-plan.json" "$ID" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1]));selected=rows if sys.argv[3]=='all' else [r for r in rows if r['id']==sys.argv[3]]
assert selected, 'Unknown task ID'
with open(sys.argv[2],'w') as f:json.dump(selected,f,indent=2)
PY
UNIT="deagle-replay-${STAMP,,}-$ID"
systemd-run --unit="$UNIT" --property=Delegate=yes --property="StandardOutput=append:$DEST/evidence/batch.log" --property="StandardError=append:$DEST/evidence/batch.log" /usr/bin/unshare --mount --propagation private /bin/bash "$DEST/scripts/reexecute-private.sh"
printf 'Replay directory: %s\nUnit: %s\n' "$DEST" "$UNIT"
