import pathlib,json,zipfile,bz2,xml.etree.ElementTree as E,re,collections,hashlib
R=pathlib.Path(__file__).resolve().parents[1];base=R/'archives/validation-evidence';rows=json.load(open(R/'reports/run-plan.json'));out=[];ns={'g':'http://graphml.graphdrawing.org/xmlns'}
mapping={m['id']:m for m in json.load(open(base/'official-witness-mapping.json'))}
logs={}
for p in (base/'validation-logs').glob('*.zip'):
 direction='violation' if '-violation-' in p.name else 'correctness';validator=p.name.split('-validate-')[0]
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if n.endswith('.log'):logs[(p.name,n.split('/')[-1])]=z.read(n)
xml=[]
for p in (base/'validation-xml').glob('*.bz2'):
 root=E.fromstring(bz2.decompress(p.read_bytes()))
 for run in root.findall('run'):
  path=run.get('name','');path=path.split('sv-benchmarks/',1)[-1]
  prop=run.get('properties');xml.append((p.name,path,prop,dict(run.attrib),{c.get('title'):c.get('value') for c in run.findall('column')}))
for row in rows:
 direction='violation' if row['raw_status'].startswith('false') else 'correctness'
 item={'id':row['id'],'task':row['task'],'property':row['property'],'direction':direction,'official_witness':mapping.get(row['id']),'validators':[]}
 target=f'SV-COMP26_{row["property"]}.{pathlib.PurePosixPath(row["task"]).name}.log'
 d=R/'evidence/validation-per-task'/row['id'];d.mkdir(parents=True,exist_ok=True)
 for (archive,n),data in logs.items():
  if n!=target or '-'+direction+'-' not in archive:continue
  label=archive.split('-deagle.')[0];p=d/(label+'.log');p.write_bytes(data)
  lines=data.decode(errors='replace').splitlines();evidence=[{'line':i+1,'text':l} for i,l in enumerate(lines) if re.search(r'ERROR|Error|error:|Exception|Invalid|invalid|not found|does not exist|violation|exit code|TRUE|FALSE|UNKNOWN|Traceback',l)]
  matching=[{'file':name,'attributes':attr,'columns':col} for name,path,prop,attr,col in xml if name.startswith(label+'-deagle.') and path==row['task'] and prop==row['property']]
  item['validators'].append({'name':label,'log':str(p.relative_to(R)),'evidence':evidence,'xml_results':matching})
 if item['official_witness']:
  h=item['official_witness']['hash'];p=base/'official-witnesses'/(h+'.graphml');b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==h;root=E.fromstring(b);keys={k.get('id'):k.get('attr.name') for k in root.findall('g:key',ns)}
  invalid=[];edata=[]
  for dta in root.findall('.//g:data',ns):
   name=keys.get(dta.get('key'),dta.get('key'));value=dta.text or ''
   if name in ['startline','endline','startoffset','endoffset','threadId','createThread'] and not re.fullmatch(r'\d+',value):invalid.append({'key':name,'value':value})
  item['witness_structure']={'nodes':len(root.findall('.//g:node',ns)),'edges':len(root.findall('.//g:edge',ns)),'invalid_numeric_data':invalid,'graph_metadata':{keys.get(x.get('key'),x.get('key')):x.text for x in root.findall('g:graph/g:data',ns)}}
 out.append(item)
(R/'reports/validator-evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for item in out:
 row=next(r for r in rows if r['id']==item['id'])
 if row['anomaly'] in ['witness invalid','correct-unconfirmed','wrong']:
  print(item['id'],row['anomaly'],item['task'],item.get('witness_structure',{}).get('invalid_numeric_data',[]));print([(v['name'],[(x['columns'].get('status'),x['columns'].get('category')) for x in v['xml_results']]) for v in item['validators']])
