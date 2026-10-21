set -eu
cd /root/deagle-svcomp26-repro-20261021-01a15ee7
python3 - <<'PY'
import pathlib,json,shutil,subprocess,time
R=pathlib.Path('.');src=R/'replays/20261021T164314Z-c6c1cfc251ef22d3/runs/c6c1cfc251ef22d3';res=json.load(open(src/'result.json'));assert res['final_status']=='true' and res['same_as_official_raw']
dest=R/'evidence/replay-smoke'
if not dest.exists():shutil.copytree(src,dest,symlinks=True)
out={'purpose':'Verify portable reexecute.sh in a fresh directory, preserving every original baseline file. Not counted as an additional benchmark instance.','command':'bash scripts/reexecute.sh c6c1cfc251ef22d3','replay_directory':str(src.parents[1].resolve()),'result':res}
(R/'reports/replay-script-check.json').write_text(json.dumps(out,indent=2))
units=['deagle-repro-batch2.service','deagle-repro-hard960.service','deagle-repro-diagnostics7.service','deagle-repro-resource-stacks.service','deagle-repro-resource-stacks2.service','deagle-repro-final-linter.service','deagle-replay-20261021t164314z-c6c1cfc251ef22d3.service']
records={u:subprocess.run(['systemctl','show',u,'--property=Result,ExecMainStatus,ActiveState,ExecMainStartTimestamp,ExecMainExitTimestamp'],capture_output=True,text=True).stdout for u in units}
(R/'evidence/completed-unit-status.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'units':records},indent=2))
print('REPLAY VERIFIED',res['cputime'],res['final_status'])
PY
