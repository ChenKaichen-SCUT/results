import pathlib,xml.etree.ElementTree as E,json,csv,collections,hashlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]
def cols(t):return {x.get('title'):x.get('value') for x in t.findall('column')}
def key(t):return (t.get('name'),t.get('properties'),t.get('propertyFile'))
rows=[];meta=[]
for p in sorted((R/'sources/results/results-verified').glob('*.Concurrency.xml')):
 a=E.parse(p).getroot();fp=p.with_name(p.name+'.bz2.fixed.xml');b=E.parse(fp).getroot()
 aa={key(t):t for t in a.findall('run')};bb={key(t):t for t in b.findall('run')};assert len(aa)==len(a.findall('run'));assert aa.keys()==bb.keys()
 meta.append({'raw':p.name,'fixed':fp.name,'attributes':a.attrib,'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fixed_sha256':hashlib.sha256(fp.read_bytes()).hexdigest()})
 for k,t in aa.items():
  raw=cols(t);fixed=cols(bb[k]);status=fixed['status'];cat=fixed['category'];excluded=status.startswith('invalid task')
  label=''
  if not excluded:
   if status in ['ERROR','unknown','TIMEOUT','OUT OF MEMORY']:label=status.upper()
   elif status.startswith('witness missing'):label='witness missing'
   elif status.startswith('witness invalid'):label='witness invalid'
   elif cat=='wrong':label='wrong'
   elif cat=='correct-unconfirmed':label=cat
   elif cat!='correct':label='other:'+cat
  rel=t.get('name').split('sv-benchmarks/',1)[1];prop=t.get('properties')
  rows.append({'id':hashlib.sha256((rel+'|'+prop).encode()).hexdigest()[:16],'task':rel,'property':prop,'property_file':t.get('propertyFile').split('sv-benchmarks/',1)[1],'files':[s.strip().split('sv-benchmarks/',1)[1] for s in t.get('files').strip('[]').split(',')],'family':rel.split('/')[1],'expected_verdict':t.get('expectedVerdict'),'raw_status':raw['status'],'raw_category':raw['category'],'fixed_status':status,'fixed_category':cat,'excluded_invalid':excluded,'anomaly':label,'official_cpu_seconds':float(raw['cputime'].rstrip('s')),'official_wall_seconds':float(raw['walltime'].rstrip('s')),'official_memory_bytes':int(raw['memory'].rstrip('B')),'official_raw_columns':raw,'official_fixed_columns':fixed,'xml_file':p.name,'selected_control':False})
groups=collections.defaultdict(list)
for r in rows:
 if not r['excluded_invalid'] and r['fixed_category']=='correct':groups[(r['family'],r['property'])].append(r)
for k,v in groups.items():
 # Deterministic representative near the median of the successful family/property tasks.
 v.sort(key=lambda x:(x['official_cpu_seconds'],x['task']));v[len(v)//2]['selected_control']=True
reports=R/'reports';reports.mkdir(exist_ok=True)
def write(name,data):
 (reports/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 flat=[{k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in r.items()} for r in data]
 with (reports/(name+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=flat[0].keys());w.writeheader();w.writerows(flat)
write('all-official-tasks',rows);write('anomalies',[r for r in rows if r['anomaly']]);write('invalid-excluded',[r for r in rows if r['excluded_invalid']]);write('run-plan',[r for r in rows if r['anomaly'] or r['selected_control']])
summary={'all':len(rows),'invalid':sum(r['excluded_invalid'] for r in rows),'anomalies':dict(collections.Counter(r['anomaly'] for r in rows if r['anomaly'])),'controls':sum(r['selected_control'] for r in rows),'families':dict(collections.Counter(r['family'] for r in rows if r['anomaly'])),'xml_metadata':meta}
(reports/'inventory-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='xml_metadata'},indent=2))
print('WRONG',[(r['task'],r['property'],r['raw_status'],r['expected_verdict']) for r in rows if r['anomaly']=='wrong'])
