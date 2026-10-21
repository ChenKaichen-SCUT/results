import os,sys,pathlib,json,time,threading,queue,shlex,hashlib,gzip,traceback,argparse,logging
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R)
os.environ['TMPDIR']=str(R/'tmp');sys.path.insert(0,str(R/'sources/python-deps'))
from benchexec.runexecutor import RunExecutor
from benchexec.tools.deagle import Tool
from benchexec.tools.template import BaseTool2
import yaml
class MeasuredExecutor(RunExecutor):
 def _setup_cgroups(self,*a,**kw):
  cg=super()._setup_cgroups(*a,**kw);self.active_cgroup=cg.path;self.actual_cgroup_settings={}
  for n in ['memory.max','memory.swap.max','memory.oom.group','cpuset.cpus.effective','cpuset.mems.effective']:
   try:self.actual_cgroup_settings[n]=(cg.path/n).read_text().strip()
   except OSError:pass
  return cg
 def _wait_for_process(self,*a,**kw):
  rc,usage=super()._wait_for_process(*a,**kw);self.last_maxrss=usage.ru_maxrss*1024;return rc,usage
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
P=argparse.ArgumentParser();P.add_argument('--smoke',action='store_true');P.add_argument('--workers',type=int,default=7);args=P.parse_args()
rows=json.load(open('reports/run-plan.json'))
if args.smoke:rows=[next(r for r in rows if r['selected_control'] and r['official_cpu_seconds']<2),next(r for r in rows if r['anomaly']=='witness missing' and r['family']=='pthread' and r['official_cpu_seconds']<1)]
else:rows.sort(key=lambda r:(r['official_cpu_seconds'],r['id']),reverse=True)
assert all(x['match'] for x in json.load(open('reports/input-hash-audit.json')))
rootfs=R/'runtime/rootfs'
def jsonsave(p,x):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str));tmp.replace(p)
def observer(d,stop,executor,measurements):
 held={};seq=0;t0=time.monotonic();lastres=0
 out=(d/'observations.jsonl').open('w');raw=d/'captured';raw.mkdir(exist_ok=True)
 def drain(k,entry):
  f,g,last=entry;st=os.fstat(f.fileno())
  if st.st_size<f.tell():g.write(b'\n[OBSERVER: same file truncated for next invocation]\n');f.seek(0)
  while b:=f.read(1024*1024):g.write(b)
  return st
 try:
  while not stop.is_set():
   for name in ['deagle_tmp_output','deagle_tmp_unwind_suggest']:
    p=d/'work'/name
    try:
     st=p.stat();k=(name,st.st_ino)
     if k not in held:
      seq+=1;held[k]=[p.open('rb'),gzip.open(raw/f'{seq:03d}-{name}.log.gz','wb'),None]
     drain(k,held[k])
    except (FileNotFoundError,ProcessLookupError):pass
   now=time.monotonic()
   cg=getattr(executor,'active_cgroup',None)
   if cg:
    try:measurements['sampled_cgroup_peak_bytes']=max(measurements.get('sampled_cgroup_peak_bytes',0),int((cg/'memory.current').read_text()))
    except (OSError,ValueError):pass
   if now-lastres>=.5:
    lastres=now;processes=[];cgroup=None
    for p in pathlib.Path('/proc').iterdir():
     if not p.name.isdigit():continue
     try:
      cwd=os.readlink(p/'cwd')
      if '/runs/'+d.name+'/work' not in cwd:continue
      cmd=(p/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace');stat=(p/'stat').read_text().rsplit(')',1)[1].split()
      status=(p/'status').read_text();rss=next((int(s.split()[1])*1024 for s in status.splitlines() if s.startswith('VmRSS:')),0)
      processes.append({'pid':int(p.name),'command':cmd,'cpu_ticks':int(stat[11])+int(stat[12]),'rss_bytes':rss})
      cg=(p/'cgroup').read_text().strip().split('::',1)[1];cgroup=pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/')
     except (OSError,ValueError,IndexError):pass
    entry={'elapsed':now-t0,'processes':processes}
    if cgroup:
     entry['cgroup']=str(cgroup)
     for f in ['memory.current','memory.peak','memory.events','cpu.stat','memory.stat','cpuset.cpus.effective']:
      try:entry[f]=(cgroup/f).read_text().strip()
      except OSError:pass
    for name in ['deagle_tmp_output','deagle_tmp_unwind_suggest']:
     try:
      p=d/'work'/name
      with p.open('rb') as f:f.seek(max(0,p.stat().st_size-1200));entry[name+'_tail']=f.read().decode(errors='replace')
     except OSError:pass
    out.write(json.dumps(entry)+'\n');out.flush()
   time.sleep(.02)
 finally:
  for k,e in held.items():
   try:drain(k,e)
   except OSError:pass
   e[0].close();e[1].close()
  out.close()
def execute(row,slot,executor):
 d=R/'runs'/row['id'];d.mkdir(exist_ok=True)
 if (d/'result.json').exists():return json.load(open(d/'result.json'))
 w=d/'work';w.mkdir(exist_ok=True);(d/'tmp').mkdir(exist_ok=True);(d/'home').mkdir(exist_ok=True)
 for name in ['deagle','deagle_exe']:
  p=w/name
  if not p.is_symlink():p.symlink_to('/tool/'+name)
 y=yaml.safe_load((R/'sources/sv-benchmarks'/row['task']).read_text());dm=y['options']['data_model'];flag={'ILP32':'--32','LP64':'--64'}[dm]
 assert flag==row['official_command'][-1],(dm,row['official_command'])
 toolcmd=['./deagle','/benchmarks/'+row['property_file'],'/benchmarks/'+row['files'][0],flag]
 cores=list(range(4+slot*4,8+slot*4));env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':f'/runs/{row["id"]}/home','TMPDIR':f'/runs/{row["id"]}/tmp','TMP':f'/runs/{row["id"]}/tmp','TEMP':f'/runs/{row["id"]}/tmp','LC_ALL':'C'}
 command=['/usr/sbin/chroot',str(rootfs),'/usr/bin/env']+[k+'='+v for k,v in env.items()]+['/bin/sh','-c',f'cd /runs/{row["id"]}/work && exec '+shlex.join(toolcmd)]
 meta={'row':row,'kind':'official-binary-original-configuration','argv':command,'tool_argv':toolcmd,'shell_command':shlex.join(command),'environment':env,'cwd':str(w),'data_model':dm,'limits':{'soft_cpu_seconds':900,'hard_cpu_seconds':960,'memory_bytes':15000000000,'cpus':cores},'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':[]}
 for f in [row['task'],row['property_file']]+row['files']:
  p=R/'sources/sv-benchmarks'/f;meta['files'].append({'path':f,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 jsonsave(d/'command.json',meta);(d/'reproduce-command.sh').write_text('#!/bin/sh\n'+shlex.join(command)+'\n')
 measurements={'memory_peak_method':'cgroup memory.current sampled every ~20ms; kernel 5.15 has no memory.peak','memory_sample_interval_seconds':.02};executor.active_cgroup=None
 stop=threading.Event();t=threading.Thread(target=observer,args=(d,stop,executor,measurements),daemon=True);t.start()
 try:
  result=executor.execute_run(command,str(d/'stdout.log'),error_filename=str(d/'stderr.log'),hardtimelimit=960,softtimelimit=900,cores=cores,memlimit=15000000000,environments={'newEnv':env},workingDir=str(w),write_header=False,maxLogfileSize=None)
 finally:stop.set();t.join()
 exitcode=result['exitcode'];output=BaseTool2.RunOutput((d/'stdout.log').read_text(errors='replace').splitlines(True)+(d/'stderr.log').read_text(errors='replace').splitlines(True));run=BaseTool2.Run(tuple(toolcmd),exitcode,output,result.get('terminationreason'))
 toolstatus=Tool().determine_result(run);term=result.get('terminationreason');status='TIMEOUT' if term in ('cputime','cputime-soft','walltime') else 'OUT OF MEMORY' if term=='memory' else toolstatus
 result['exitcode']={'raw':exitcode.raw,'value':exitcode.value,'signal':exitcode.signal}
 result.update(measurements);result['peak_process_tree_member_rss_bytes']=getattr(executor,'last_maxrss',None)
 result['actual_cgroup_settings']=getattr(executor,'actual_cgroup_settings',{})
 result.update({'id':row['id'],'tool_status':toolstatus,'final_status':status,'official_status':row['raw_status'],'same_as_official_raw':status==row['raw_status'],'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'witness_files':[{'name':str(p.relative_to(d)),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in w.rglob('*') if p.is_file() and p.suffix in ['.graphml','.yml','.yaml']]})
 jsonsave(d/'result.json',result);return result
q=queue.Queue();quick=queue.Queue()
for row in rows:(quick if row['official_cpu_seconds']<20 else q).put(row)
executors=[MeasuredExecutor(use_namespaces=False) for _ in range(min(args.workers,len(rows)))]
def worker(slot,executor):
 while True:
  first,second=(quick,q) if slot==len(executors)-1 else (q,quick)
  try:row=first.get_nowait();activeq=first
  except queue.Empty:
   try:row=second.get_nowait();activeq=second
   except queue.Empty:return
  try:
   res=execute(row,slot,executor);print(json.dumps({'id':row['id'],'task':row['task'],'property':row['property'],'status':res['final_status'],'cpu':res.get('cputime'),'memory':res.get('memory'),'remaining':q.qsize()+quick.qsize()}),flush=True)
  except BaseException as e:
   d=R/'runs'/row['id'];d.mkdir(exist_ok=True);(d/'execution-error.txt').write_text(traceback.format_exc());print('EXECUTION ERROR',row['id'],repr(e),flush=True)
  finally:activeq.task_done()
threads=[threading.Thread(target=worker,args=(i,e)) for i,e in enumerate(executors)]
for t in threads:t.start()
for t in threads:t.join()
print('BATCH FINISHED',len(rows),flush=True)
