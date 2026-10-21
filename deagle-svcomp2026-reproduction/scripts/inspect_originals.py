import pathlib,json,collections,re
R=pathlib.Path(__file__).resolve().parents[1];rows=json.load(open(R/'reports/run-plan.json'))
for cat in ['ERROR','UNKNOWN','TIMEOUT','OUT OF MEMORY','witness missing','witness invalid']:
 a=[r for r in rows if r['anomaly']==cat];groups=collections.defaultdict(list)
 for r in a:
  s=(R/'evidence/official-logs'/(r['id']+'.log')).read_text(errors='replace')
  pattern='over300' if 'Too large unwind limit:' in s else 'traceback' if 'Traceback' in s else 'explicit ERROR' if re.search(r'^ERROR$',s,re.M) else 'other'
  groups[(r['family'],pattern)].append(r)
 print('CATEGORY',cat,'GROUPS',{str(k):len(v) for k,v in groups.items()})
 for key,rs in list(groups.items())[:5]:
  r=rs[0];s=(R/'evidence/official-logs'/(r['id']+'.log')).read_text(errors='replace');print('EXAMPLE',r['id'],r['task'],r['property'],repr(s[-1500:]))
