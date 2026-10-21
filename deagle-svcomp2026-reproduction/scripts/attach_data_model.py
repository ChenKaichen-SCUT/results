"""Attach symbol-table observations; never reinterpret the baseline results."""
import pathlib,json,re
R=pathlib.Path(__file__).resolve().parents[1]
audit=[]
note='在原始最终命令上仅追加 --show-symbol-table 的隔离诊断显示 int、long、pointer 均为 32 位，符合 ILP32；没有额外强制 --32，也没有修改程序／属性。不能从 64-bit 工具横幅推断 C 数据模型为 LP64。'
for d in sorted((R/'diagnostics').glob('*-datatype-symbols')):
 lines=(d/'stdout.log').read_text().splitlines(); widths={}; evidence=[]
 for i,line in enumerate(lines):
  m=re.fullmatch(r'Symbol\.*: __CPROVER_architecture_(int|long_int|pointer)_width',line)
  if not m:continue
  for j in range(i+1,min(i+10,len(lines))):
   v=re.fullmatch(r'Value\.*: \(integer\)(\d+)',lines[j])
   if v:
    widths[m[1]]=int(v[1]);evidence.extend([{'file':str((d/'stdout.log').relative_to(R)),'line':i+1,'text':line},{'file':str((d/'stdout.log').relative_to(R)),'line':j+1,'text':lines[j]}]);break
 assert widths=={'int':32,'long_int':32,'pointer':32},(d,widths)
 assert json.loads((d/'result.json').read_text())['exitcode']['value']==0
 audit.append({'id':d.name.split('-')[0],'diagnostic':str(d.relative_to(R)),'widths_bits':widths,'expected_model':'ILP32','matches_expected_model':True,'evidence':evidence,'interpretation':note})
assert len(audit)==4
for fn in ['reproduction-analysis','anomaly-analysis']:
 p=R/'reports'/(fn+'.json'); rows=json.loads(p.read_text()); byid={x['id']:x for x in rows}
 for a in audit:
  row=byid[a['id']];row['data_model_audit']=a
  if a['diagnostic'] not in row['diagnostics']:row['diagnostics'].append(a['diagnostic'])
  if note not in row.setdefault('diagnostic_observations',[]):row['diagnostic_observations'].append(note)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(R/'reports/program-data-model-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print('Verified original target data model for',len(audit),'wrong-result cases: ILP32')
