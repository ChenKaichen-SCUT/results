import os,sys,json,subprocess,pathlib,concurrent.futures,urllib.request,hashlib,zipfile,io,time
R=pathlib.Path('/root/deagle-svcomp26-repro-20261021-01a15ee7');os.chdir(R)
def fetch(url,out):
 p=pathlib.Path(out);p.parent.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen(url,timeout=90) as r,p.open('wb') as f:
  while b:=r.read(1024*1024): f.write(b)
 return str(p)
def clone(url,dest,ref=None):
 cmd=['git','clone']+(['--depth','1','--branch',ref] if ref else [])+[url,'sources/'+dest]
 cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 pathlib.Path('evidence/clone-'+dest+'.log').write_text(cp.stdout)
 if cp.returncode: raise RuntimeError(cp.stdout)
 sha=subprocess.check_output(['git','-C','sources/'+dest,'rev-parse','HEAD'],text=True).strip()
 pathlib.Path('evidence/'+dest+'-commit.txt').write_text(sha+'\n');return dest+': '+sha
def tool():
 d=json.load(open('evidence/deagle-record.json'));f=d['files'][0]
 fetch(f['links']['self'],'archives/deagle.zip');b=pathlib.Path('archives/deagle.zip').read_bytes()
 assert 'md5:'+hashlib.md5(b).hexdigest()==f['checksum']
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  for i in z.infolist():
   if pathlib.PurePosixPath(i.filename).is_absolute() or '..' in pathlib.PurePosixPath(i.filename).parts:raise ValueError('unsafe zip')
   p=pathlib.Path(z.extract(i,'sources/official-tool'))
   if i.external_attr>>16:p.chmod(i.external_attr>>16)
 return 'official tool downloaded and MD5 verified; sha256='+hashlib.sha256(b).hexdigest()
def records():
 for id in [19736446,18650775,18650756,18651735,18653053]:
  fetch(f'https://zenodo.org/api/records/{id}',f'evidence/zenodo-{id}.json')
 return 'Zenodo metadata saved'
jobs=[lambda:clone('https://github.com/thufv/Deagle.git','Deagle'),lambda:clone('https://github.com/ChenKaichen-SCUT/results.git','results'),lambda:clone('https://gitlab.com/sosy-lab/sv-comp/bench-defs.git','bench-defs','svcomp26'),lambda:clone('https://github.com/sosy-lab/benchexec.git','benchexec','3.34'),tool,records]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for fut in concurrent.futures.as_completed([ex.submit(j) for j in jobs]):
  try:print(fut.result(),flush=True)
  except Exception as e:print('FAILED',repr(e),flush=True)
