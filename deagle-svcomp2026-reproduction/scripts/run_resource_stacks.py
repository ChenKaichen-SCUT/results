import pathlib,os,sys,json,shlex,time
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R);sys.path.insert(0,str(R/'sources/python-deps'));os.environ['TMPDIR']=str(R/'tmp')
from benchexec.runexecutor import RunExecutor
rows={r['id']:r for r in json.load(open('reports/run-plan.json'))};ex=RunExecutor(use_namespaces=False)
for ident,seconds in [('5762debd1f9e9bfe',390),('160c74f546f52fb0',60)]:
 r=rows[ident];candidates=[]
 for line in reversed((R/'runs'/ident/'observations.jsonl').read_text().splitlines()):
  x=json.loads(line);candidates=[p['command'] for p in x['processes'] if p['command'].startswith('./deagle_exe ') and '--unwind-suggest' not in p['command']]
  if candidates:break
 assert candidates,(ident,'no final-phase invocation recovered')
 cmd=shlex.split(candidates[0]);cmd[0]='/tool/deagle_exe'
 label='resource-final-stack'+str(seconds);d=R/'diagnostics'/(ident+'-'+label);d.mkdir(parents=True,exist_ok=True)
 if (d/'result.json').exists():continue
 gdb=['/usr/bin/timeout','--preserve-status','-s','INT','-k','8',str(seconds),'/usr/bin/gdb','-nx','-nh','-batch','-ex','set pagination off','-ex','run','-ex','thread apply all bt 30','--args']+cmd
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/diagnostics/'+d.name,'TMPDIR':'/diagnostics/'+d.name,'TMP':'/diagnostics/'+d.name,'TEMP':'/diagnostics/'+d.name,'LC_ALL':'C'}
 full=['/usr/sbin/chroot',str(R/'runtime/rootfs'),'/usr/bin/env']+[k+'='+v for k,v in env.items()]+['/bin/sh','-c','cd /diagnostics/'+d.name+' && exec '+shlex.join(gdb)]
 meta={'task_id':ident,'task':r['task'],'property':r['property'],'label':label,'changes':['Independent GDB run using the exact final binary argv recovered from baseline process observations; original baseline never attached or interrupted.',f'Diagnostic wall-time interrupt at {seconds} seconds to obtain a stack; original CPU and memory ceilings preserved. This timing sample does not prove the entire baseline spent its time in the sampled function.'],'binary_command':cmd,'gdb_command':gdb,'full_command':full,'limits':{'soft_cpu_seconds':900,'hard_cpu_seconds':960,'memory_bytes':15000000000,'cores':[0,1,2,3]},'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (d/'command.json').write_text(json.dumps(meta,indent=2));print('START',d.name,flush=True)
 res=ex.execute_run(full,str(d/'stdout.log'),error_filename=str(d/'stderr.log'),softtimelimit=900,hardtimelimit=960,cores=[0,1,2,3],memlimit=15000000000,maxLogfileSize=None,write_header=False)
 ec=res['exitcode'];res['exitcode']={'raw':ec.raw,'value':ec.value,'signal':ec.signal};(d/'result.json').write_text(json.dumps(res,indent=2,default=str));print('DONE',d.name,res,flush=True)
