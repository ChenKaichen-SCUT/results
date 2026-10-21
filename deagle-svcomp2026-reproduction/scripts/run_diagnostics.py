import os,sys,pathlib,json,shlex,time,re,hashlib
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R);sys.path.insert(0,str(R/'sources/python-deps'));os.environ['TMPDIR']=str(R/'tmp')
from benchexec.runexecutor import RunExecutor
rows=json.load(open('reports/run-plan.json'));byid={r['id']:r for r in rows}
specs=[]
def command(r,first=False):
 lines=(R/'evidence/official-logs'/(r['id']+'.log')).read_text().splitlines();ls=[l for l in lines if l.startswith('./deagle_exe ')]
 cmd=shlex.split((ls[0] if first else ls[-1]).split(' > ',1)[0]);cmd=['/tool/deagle_exe']+[('/benchmarks/'+a.split('sv-benchmarks/',1)[1] if 'sv-benchmarks/' in a else a) for a in cmd[1:]];return cmd
for family in ['libvsync','ldv-linux-3.14-races','pthread-divine','weaver','pthread-complex']:
 r=next(r for r in rows if r['family']==family and r['anomaly']=='UNKNOWN')
 specs.append((r,'unknown-full-log',command(r),['Direct final binary invocation from official launcher log; output is retained instead of redirected/deleted; parameters unchanged.']))
for r in rows:
 if r['anomaly'] in ['wrong','witness invalid']:
  specs.append((r,'trace',command(r)+['--trace'],['Added --trace for counterexample diagnostics; original parameters retained.']))
for ident in ['15fbf61018a5dd49','3166c6eacc7f22c8']:
 r=byid[ident];cmd=command(r);i=cmd.index('--unwindset');cmd[i+1]=cmd[i+1].replace(':3,',':101,');specs.append((r,'unwind101',cmd+['--trace','--unwinding-assertions'],['Changed undetermined-loop limit from 3 to 101. Added unwinding assertions to check completeness, and --trace. Diagnostic result is not an official-condition result.']))
r=byid['643ec04b71829a38'];cmd=command(r);specs.append((r,'unwinding-check',cmd+['--unwinding-assertions','--trace'],['Added unwinding assertions to assess completeness at unchanged loop bounds; diagnostic assertions are additional checks, not a replacement for the task property.']))
for ident in ['15fbf61018a5dd49','3166c6eacc7f22c8']:
 r=byid[ident];cmd=command(r);i=cmd.index('--unwindset');cmd[i+1]=re.sub(r':\d+,',':102,',cmd[i+1]);specs.append((r,'all-loops102',cmd+['--trace','--unwinding-assertions'],['Raised all loop limits to 102, accounting for the loop-exit test. Added completeness assertions and trace. Additional-check failures are distinguished from reach_error.']))
r=byid['4a1c3d1fa852554c'];cmd=command(r);specs.append((r,'unwinding-check',cmd+['--unwinding-assertions','--trace'],['Added completeness checks at unchanged bounds.']))
r=byid['643ec04b71829a38'];cmd=command(r);specs.append((r,'goto-model',cmd+['--show-goto-functions'],['Display GOTO model and initialized allocation settings; no solving and no target modification.']))
for ident in ['3f0a3910c4fa6eaa','afb4ad0607f691f7','3bbcf5f598f873f4']:
 r=byid[ident];cmd=['/tool/deagle_exe','/benchmarks/'+r['files'][0],'--refined-pointer-analysis','--graphml-witness','error-witness.graphml']
 if r['property']=='no-overflow':cmd+=['--no-assertions','--signed-overflow-check','--unsigned-overflow-check']
 if r['property']=='no-data-race':cmd+=['--no-assertions','--datarace']
 gdb=['/usr/bin/timeout','--preserve-status','-s','INT','-k','8','60','/usr/bin/gdb','-nx','-nh','-batch','-ex','set pagination off','-ex','run','-ex','thread apply all bt 24','--args']+cmd
 specs.append((r,'solver-stack60',gdb,['Independent diagnostic binary run under gdb, interrupted at 60 wall seconds to capture stack. No baseline process is attached or interrupted. Resource ceilings remain 900/960 CPU seconds and 15 GB.']))
for ident in ['3f0a3910c4fa6eaa','afb4ad0607f691f7','3bbcf5f598f873f4']:
 r=byid[ident];observations=(R/'runs'/ident/'observations.jsonl').read_text().splitlines();candidates=[]
 for line in reversed(observations):
  data=json.loads(line)
  candidates=[p['command'] for p in data['processes'] if p['command'].startswith('./deagle_exe ') and '--unwindset' in p['command']]
  if candidates:break
 if not candidates:continue
 cmd=shlex.split(candidates[0]);cmd[0]='/tool/deagle_exe'
 gdb=['/usr/bin/timeout','--preserve-status','-s','INT','-k','8','60','/usr/bin/gdb','-nx','-nh','-batch','-ex','set pagination off','-ex','run','-ex','thread apply all bt 24','--args']+cmd
 specs.append((r,'bounded-final-stack60',gdb,['Exact final-phase binary argv recovered from baseline /proc command observations, including --unwindset. Independent gdb diagnostic interrupted at 60 wall seconds; baseline runs are not attached.']))
executor=RunExecutor(use_namespaces=False)
for ident in ['643ec04b71829a38','4a1c3d1fa852554c']:
 r=byid[ident];specs.append((r,'verbose10',command(r)+['--verbosity','10'],['Added diagnostic verbosity 10 only; final-phase loop bounds and property flags unchanged.']))
r=byid['643ec04b71829a38'];specs.append((r,'show-vcc',command(r)+['--show-vcc'],['Display verification conditions at unchanged final-phase bounds. No target or property modification; this mode may stop before solving.']))
r=byid['4a1c3d1fa852554c'];cmd=command(r);i=cmd.index('--unwindset');cmd[i+1]=cmd[i+1].replace('SyncPush.0:3,','SyncPush.0:17,').replace('SyncPush.1:3,','SyncPush.1:17,');specs.append((r,'syncpush17',cmd+['--unwinding-assertions','--trace'],['Only SyncPush loop bounds raised from 3 to 17; all other original bounds and property flags retained. Added completeness checks and trace. This is a strategy diagnostic, not an original-configuration result.']))
for r in rows:
 if r['anomaly']=='wrong':specs.append((r,'datatype-symbols',command(r)+['--show-symbol-table'],['Inspect actual configured C type widths at the original property/final-phase parameters. No --32 override is added: the competition launcher does not forward its extra --32 argument. Symbol-table display is a diagnostic, not an additional verification verdict.']))
for r,label,cmd,changes in specs:
 name=r['id']+'-'+label;d=R/'diagnostics'/name;d.mkdir(parents=True,exist_ok=True)
 if (d/'result.json').exists():continue
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/diagnostics/'+name,'TMPDIR':'/diagnostics/'+name,'TMP':'/diagnostics/'+name,'TEMP':'/diagnostics/'+name,'LC_ALL':'C'}
 full=['/usr/sbin/chroot',str(R/'runtime/rootfs'),'/usr/bin/env']+[k+'='+v for k,v in env.items()]+['/bin/sh','-c','cd /diagnostics/'+name+' && exec '+shlex.join(cmd)]
 meta={'task_id':r['id'],'task':r['task'],'property':r['property'],'label':label,'changes':changes,'binary_command':cmd,'resource_command':full,'limits':{'soft_cpu':900,'hard_cpu':960,'memory_bytes':15000000000,'cores':[0,1,2,3]},'start_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (d/'command.json').write_text(json.dumps(meta,indent=2));print('START',name,flush=True)
 result=executor.execute_run(full,str(d/'stdout.log'),error_filename=str(d/'stderr.log'),softtimelimit=900,hardtimelimit=960,memlimit=15000000000,cores=[0,1,2,3],maxLogfileSize=None,write_header=False)
 ec=result['exitcode'];result['exitcode']={'raw':ec.raw,'value':ec.value,'signal':ec.signal};(d/'result.json').write_text(json.dumps(result,indent=2,default=str));print('DONE',name,result,flush=True)
