import pathlib,json,hashlib,collections,re,gzip,time,subprocess
R=pathlib.Path(__file__).resolve().parents[1];rows=json.load(open(R/'reports/run-plan.json'));analysis=json.load(open(R/'reports/reproduction-analysis.json'));byid={a['id']:a for a in analysis};fail=[];checks=[];diff=[]
assert len(rows)==667 and len({r['id'] for r in rows})==667
official_tool_hashes={'deagle':'dde429fe0347ae2ed77d03bc3cf34b50e5f21f8ace6933d1eac554ed95b5ec73','deagle_exe':'63eaf07f9ee1d0f3f7f1c7a4bb9507455343f5ad2d4bb37b40c584904a94e932'}
for n,h in official_tool_hashes.items():
 if hashlib.sha256((R/'runtime/rootfs/tool'/n).read_bytes()).hexdigest()!=h:fail.append(['official tool changed',n])
for r in rows:
 d=R/'runs'/r['id']
 for name in ['command.json','stdout.log','stderr.log','result.json','observations.jsonl','reproduce-command.sh']:
  if not (d/name).is_file():fail.append([r['id'],'missing',name])
 if not (d/'result.json').is_file():continue
 res=json.load(open(d/'result.json'));meta=json.load(open(d/'command.json'))
 if meta['limits']['soft_cpu_seconds']!=900 or meta['limits']['hard_cpu_seconds']!=960 or meta['limits']['memory_bytes']!=15000000000 or len(meta['limits']['cpus'])!=4:fail.append([r['id'],'wrong resource limits'])
 if res.get('actual_cgroup_settings',{}).get('memory.max')!='14999998464':fail.append([r['id'],'memory.max not confirmed'])
 actual=res.get('actual_cgroup_settings',{});cpus=meta['limits']['cpus']
 if actual.get('cpuset.cpus.effective')!=str(cpus[0])+'-'+str(cpus[-1]):fail.append([r['id'],'CPU affinity mismatch'])
 if actual.get('memory.swap.max')!='0':fail.append([r['id'],'swap not disabled'])
 for f in meta['files']:
  p=R/'runtime/rootfs/benchmarks'/f['path'];h=hashlib.sha256(p.read_bytes()).hexdigest();checks.append({'id':r['id'],'runtime_input':f['path'],'recorded_sha256':f['sha256'],'actual_runtime_sha256':h,'match':h==f['sha256']})
  if h!=f['sha256']:fail.append([r['id'],'runtime input changed',f['path']])
 if not res['same_as_official_raw']:diff.append({'id':r['id'],'task':r['task'],'property':r['property'],'official_status':r['raw_status'],'reproduction_status':res['final_status'],'cpu':res['cputime'],'termination':res.get('terminationreason')})
 if byid[r['id']]['cause_code'] in ['pending','unclassified']:fail.append([r['id'],'incomplete analysis'])
 if r['anomaly']=='witness missing' and res['witness_files']:fail.append([r['id'],'unexpected witness; revisit cause'])
 # Ensure environment-related failed preprocessing has not leaked into the valid baseline.
 for p in [d/'stdout.log',d/'stderr.log',d/'work/deagle_tmp_output']+list((d/'captured').glob('*.gz')):
  if not p.exists():continue
  op=gzip.open if p.suffix=='.gz' else open
  with op(p,'rt',encoding='utf-8',errors='replace') as f:
   for n,line in enumerate(f,1):
    if any(t in line for t in ['GCC preprocessing failed','Failed to open temporary file','gnu/stubs-x32.h: No such file']):fail.append([r['id'],'environment failure',str(p.relative_to(R)),n,line.strip()])
out={'generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'planned':len(rows),'completed':sum((R/'runs'/r['id']/'result.json').exists() for r in rows),'anomaly_counts':dict(collections.Counter(r['anomaly'] for r in rows if r['anomaly'])),'failures':fail,'different_statuses':diff,'runtime_input_hash_checks':len(checks),'all_runtime_inputs_match':all(x['match'] for x in checks)}
(R/'reports/final-audit.json').write_text(json.dumps(out,indent=2));(R/'reports/runtime-input-hash-audit.json').write_text(json.dumps(checks,indent=2));print(json.dumps(out,indent=2));assert not fail
