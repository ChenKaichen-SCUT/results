#!/bin/bash
set -euo pipefail
R=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$R"
python3 - <<'PY'
import json,pathlib
r=pathlib.Path('.');a=json.load(open(r/'reports/final-audit.json'))
assert a['completed']==667 and not a['failures']
assert all((r/'runs'/x['id']/'result.json').exists() for x in json.load(open(r/'reports/run-plan.json')))
PY
mkdir -p deliverables
tar --exclude='*/.git' --exclude='*/__pycache__' -czf deliverables/evidence-and-results.tar.gz README.txt runs diagnostics reports scripts evidence archives/official-results archives/validation-evidence archives/competition-inputs archives/competition-input-archive-audit.json
sha256sum deliverables/evidence-and-results.tar.gz deliverables/runtime-and-sources.tar.gz > deliverables/archive-SHA256SUMS
cat deliverables/archive-SHA256SUMS
