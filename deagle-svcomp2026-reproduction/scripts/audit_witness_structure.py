import pathlib,json,xml.etree.ElementTree as E,hashlib,collections
R=pathlib.Path(__file__).resolve().parents[1];rows=json.load(open(R/'reports/run-plan.json'));mapping={x['id']:x for x in json.load(open(R/'archives/validation-evidence/official-witness-mapping.json'))};ns={'g':'http://graphml.graphdrawing.org/xmlns'};out=[]
def audit(row,kind,path):
 root=E.parse(path).getroot();keys={x.get('id'):x.get('attr.name') for x in root.findall('g:key',ns)}
 def data(x):return {keys.get(d.get('key'),d.get('key')):d.text or '' for d in x.findall('g:data',ns)}
 graph=root.find('g:graph',ns);meta=data(graph);nodes={n.get('id'):data(n) for n in graph.findall('g:node',ns)};edges=[{'source':n.get('source'),'target':n.get('target'),'data':data(n)} for n in graph.findall('g:edge',ns)]
 entry=[n for n,d in nodes.items() if d.get('entry')=='true'];violation=[n for n,d in nodes.items() if d.get('violation')=='true'];reachable=set(entry);pending=list(entry);adj=collections.defaultdict(list)
 for ed in edges:adj[ed['source']].append(ed['target'])
 while pending:
  n=pending.pop()
  for m in adj[n]:
   if m not in reachable:reachable.add(m);pending.append(m)
 inputhash=hashlib.sha256((R/'sources/sv-benchmarks'/row['files'][0]).read_bytes()).hexdigest();spec=(R/'sources/sv-benchmarks'/row['property_file']).read_text().strip()
 return {'id':row['id'],'task':row['task'],'property':row['property'],'kind':kind,'file':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'metadata':meta,'program_hash_matches_input':meta.get('programHash','').lower()==inputhash,'specification_matches_property_whitespace_normalized':''.join(meta.get('specification','').split())==''.join(spec.split()),'architecture_matches_ILP32':meta.get('architecture')=='32bit','node_count':len(nodes),'edge_count':len(edges),'entry_nodes':entry,'violation_nodes':violation,'violation_reachable_in_graph':any(x in reachable for x in violation),'edges_with_threadId':sum('threadId' in ed['data'] for ed in edges),'edges_with_createThread':sum('createThread' in ed['data'] for ed in edges),'edges_with_empty_startline':sum('startline' in ed['data'] and not ed['data']['startline'].strip() for ed in edges),'edges_with_assumptions':sum('assumption' in ed['data'] for ed in edges),'caveat':'Graph reachability and metadata checks do not establish that the represented execution is semantically feasible. Optional missing edge attributes are counted, not automatically called invalid.'}
for r in rows:
 if r['id'] in mapping:out.append(audit(r,'original',R/'archives/validation-evidence/official-witnesses'/(mapping[r['id']]['hash']+'.graphml')))
 p=R/'runs'/r['id']/'work/error-witness.graphml'
 if (p.parent.parent/'result.json').exists() and p.exists():out.append(audit(r,'reproduction',p))
byid={r['id']:r for r in rows}
for x in out:
 r=byid[x['id']];x['tool_verdict']=r['raw_status'];x['expected_witness_type']='correctness_witness' if r['raw_status']=='true' else 'violation_witness'
 x['declared_type_matches_tool_verdict']=x['metadata'].get('witness-type')==x['expected_witness_type']
 if not x['declared_type_matches_tool_verdict']:
  x['type_mismatch_explanation']='工具报告 TRUE，但 GraphML 声明 violation_witness。Deagle src/xmllang/graphml.cpp:497–501 无条件写入该类型；witnesslint 的 Type-Match 为信息字段，False 不使其语法检查退出码必然非零。此附加发现不改变官方异常清单。'
(R/'reports/witness-structure-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('WITNESSES',len(out),'HASH MATCH',sum(x['program_hash_matches_input'] for x in out),'SPEC MATCH',sum(x['specification_matches_property_whitespace_normalized'] for x in out),'EMPTY LINE',[(x['id'],x['kind']) for x in out if x['edges_with_empty_startline']])
