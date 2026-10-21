import pathlib,json,gzip,hashlib,bz2,xml.etree.ElementTree as E,zipfile,shlex
R=pathlib.Path(__file__).resolve().parents[1];a=R/'archives/official-results/results-verified';rows=json.load(open(R/'reports/run-plan.json'))
hashes=json.loads(gzip.decompress(next(a.glob('*.fileHashes.json.gz')).read_bytes()));out=[]
for r in rows:
 for f in [r['task'],r['property_file']]+r['files']:
  p=R/'sources/sv-benchmarks'/f;actual=hashlib.sha256(p.read_bytes()).hexdigest();expected=hashes.get('sv-benchmarks/'+f)
  out.append({'task_id':r['id'],'file':f,'actual':actual,'official':expected,'match':actual==expected})
(R/'reports/input-hash-audit.json').write_text(json.dumps(out,indent=2))
bad=[x for x in out if not x['match']];print('HASH ENTRIES',len(out),'MISMATCH',len(bad));print(json.dumps(bad[:30],indent=2))
def sem(root):return {'root':root.attrib,'runs':{(r.get('name'),r.get('properties')):{'attributes':r.attrib,'columns':{c.get('title'):c.get('value') for c in r.findall('column')}} for r in root.findall('run')}}
for p in (R/'sources/results/results-verified').glob('*.Concurrency.xml*'):
 z=a/(p.name.replace('.xml.bz2.fixed.xml','.xml.bz2.fixed.xml.bz2') if '.fixed.' in p.name else p.name+'.bz2')
 same=sem(E.fromstring(bz2.decompress(z.read_bytes())))==sem(E.parse(p).getroot());print('XML SEMANTIC MATCH',p.name,same);assert same
logdir=R/'evidence/official-logs';logdir.mkdir(exist_ok=True)
with zipfile.ZipFile(next(a.glob('*.logfiles.zip'))) as z:
 lookup={}
 for n in z.namelist():
  if not n.endswith('.log'):continue
  data=z.read(n);line=data.decode(errors='replace').splitlines()[0]
  try:args=shlex.split(line)
  except ValueError:continue
  if len(args)>3 and 'sv-benchmarks/' in args[1] and 'sv-benchmarks/' in args[2]:
   lookup[(args[2].split('sv-benchmarks/',1)[1],args[1].split('sv-benchmarks/',1)[1])]=(n,data,args)
 for r in rows:
  n,data,args=lookup[(r['files'][0],r['property_file'])];(logdir/(r['id']+'.log')).write_bytes(data)
  r['official_command']=args;r['original_log_member']=n
(R/'reports/run-plan.json').write_text(json.dumps(rows,indent=2));print('ORIGINAL LOGS MATCHED',len(rows))
if bad:raise SystemExit(2)
