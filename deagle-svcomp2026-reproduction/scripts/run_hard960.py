import pathlib,os,sys,json,time,shlex
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R);sys.path.insert(0,str(R/'sources/python-deps'));os.environ['TMPDIR']=str(R/'tmp')
from benchexec.runexecutor import RunExecutor
from benchexec.tools.deagle import Tool
from benchexec.tools.template import BaseTool2
rows={r['id']:r for r in json.load(open('reports/run-plan.json'))};ex=RunExecutor(use_namespaces=False)
for ident in ['3f0a3910c4fa6eaa','afb4ad0607f691f7']:
 row=rows[ident];d=R/'diagnostics'/(ident+'-hard960-policy');d.mkdir(parents=True,exist_ok=True)
 if (d/'result.json').exists():continue
 for n in ['deagle','deagle_exe']:
  if not (d/n).is_symlink():(d/n).symlink_to('/tool/'+n)
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/diagnostics/'+d.name,'TMPDIR':'/diagnostics/'+d.name,'TMP':'/diagnostics/'+d.name,'TEMP':'/diagnostics/'+d.name,'LC_ALL':'C'}
 tc=['./deagle','/benchmarks/'+row['property_file'],'/benchmarks/'+row['files'][0],'--32']
 full=['/usr/sbin/chroot',str(R/'runtime/rootfs'),'/usr/bin/env']+[k+'='+v for k,v in env.items()]+['/bin/sh','-c','cd /diagnostics/'+d.name+' && exec '+shlex.join(tc)]
 meta={'task_id':ident,'task':row['task'],'property':row['property'],'tool_command':tc,'full_command':full,'limits':{'soft_cpu_seconds':None,'hard_cpu_seconds':960,'memory_bytes':15000000000,'cores':[0,1,2,3]},'diagnostic_adjustment':'Do not send SIGTERM at 900 s; retain 960 s hard limit to examine the observed official ~961 s timeout policy. This is not a 900-second baseline success, nor proof of an exact reconstruction of the VCloud implementation. Tool, input, property and launcher parameters unchanged.','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (d/'command.json').write_text(json.dumps(meta,indent=2));print('START',d.name,flush=True)
 res=ex.execute_run(full,str(d/'stdout.log'),error_filename=str(d/'stderr.log'),hardtimelimit=960,cores=[0,1,2,3],memlimit=15000000000,maxLogfileSize=None,write_header=False)
 ec=res['exitcode'];out=BaseTool2.RunOutput((d/'stdout.log').read_text(errors='replace').splitlines(True)+(d/'stderr.log').read_text(errors='replace').splitlines(True));res['tool_status']=Tool().determine_result(BaseTool2.Run(tuple(tc),ec,out,res.get('terminationreason')));res['exitcode']={'raw':ec.raw,'value':ec.value,'signal':ec.signal}
 (d/'result.json').write_text(json.dumps(res,indent=2,default=str));print('DONE',d.name,res,flush=True)
