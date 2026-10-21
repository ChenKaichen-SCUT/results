import pathlib,sys,os,json,time,hashlib
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R);sys.path.insert(0,str(R/'sources/python-deps'));os.environ['TMPDIR']=str(R/'tmp')
from benchexec.runexecutor import RunExecutor
rows=json.load(open('reports/run-plan.json'));mapping={m['id']:m for m in json.load(open('archives/validation-evidence/official-witness-mapping.json'))};exe=RunExecutor(use_namespaces=False)
for row in rows:
 candidates=[]
 if row['id'] in mapping:candidates.append(('original',R/'archives/validation-evidence/official-witnesses'/(mapping[row['id']]['hash']+'.graphml')))
 p=R/'runs'/row['id']/'work/error-witness.graphml'
 if (R/'runs'/row['id']/'result.json').exists() and p.exists():candidates.append(('reproduction',p))
 for kind,witness in candidates:
  d=R/'diagnostics'/('witnesslint-'+kind)/row['id'];d.mkdir(parents=True,exist_ok=True)
  if (d/'result.json').exists():continue
  direction='--expectViolationWitness' if row['raw_status'].startswith('false') else '--expectCorrectnessWitness'
  cmd=['/usr/bin/python3',str(R/'sources/sv-witnesses/linter/witnesslinter.py'),direction,'--ignoreSelfLoops','--expectedWitnessVersion','1','--witness',str(witness),str(R/'sources/sv-benchmarks'/row['files'][0])]
  (d/'command.json').write_text(json.dumps({'kind':kind,'task_id':row['id'],'command':cmd,'sha256':hashlib.sha256(witness.read_bytes()).hexdigest(),'scope':'Independent syntax validation only; not a proof of program correctness or feasibility.','limits':{'soft_cpu':900,'hard_cpu':960,'memory':15000000000,'cores':[0,1,2,3]}},indent=2))
  res=exe.execute_run(cmd,str(d/'stdout.log'),error_filename=str(d/'stderr.log'),softtimelimit=900,hardtimelimit=960,cores=[0,1,2,3],memlimit=15000000000,environments={'newEnv':{'PYTHONPATH':str(R/'sources/linter-deps')}},maxLogfileSize=None,write_header=False)
  ec=res['exitcode'];res['exitcode']={'raw':ec.raw,'value':ec.value,'signal':ec.signal};(d/'result.json').write_text(json.dumps(res,indent=2,default=str));print(kind,row['id'],ec.value,flush=True)
