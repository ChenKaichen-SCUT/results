import pathlib,json,collections,time,gzip,sys
R=pathlib.Path(__file__).resolve().parents[1]
rows={r['id']:r for r in json.load(open(R/'reports/run-plan.json'))};res={}
for p in (R/'runs').glob('*/result.json'):res[p.parent.name]=json.load(open(p))
print('UTC',time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'DONE',len(res),'OF',len(rows))
print('BY ORIGINAL ANOMALY',dict(collections.Counter(rows[i]['anomaly'] or 'control' for i in res)))
print('FINAL STATUS',dict(collections.Counter(r['final_status'] for r in res.values())))
print('DIFFERENT',[(i,rows[i]['anomaly'],rows[i]['task'],rows[i]['property'],r['official_status'],r['final_status']) for i,r in res.items() if not r['same_as_official_raw']][:30])
if '--brief' in sys.argv:sys.exit(0)
for p in (R/'runs').glob('*/command.json'):
 if p.parent.name in res:continue
 obs=p.parent/'observations.jsonl'
 if obs.exists():
  lines=obs.read_text().splitlines()
  if lines:
   x=json.loads(lines[-1]);print('ACTIVE',p.parent.name,rows[p.parent.name]['task'],round(x['elapsed'],1),x.get('memory.current'),repr(x.get('deagle_tmp_output_tail','')[-700:]))
for p in (R/'diagnostics').glob('*/stdout.log'):
 t=p.read_text(errors='replace');print('DIAG',p.parent.name,repr(t[-1000:]))
