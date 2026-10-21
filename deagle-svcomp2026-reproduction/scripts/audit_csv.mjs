import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';
const out=process.argv[2]||'outputs';
const data=path.join(out,'data');
const source=JSON.parse(await fs.readFile(path.join(data,'reproduction-analysis.json'),'utf8'));
const byId=new Map(source.map(r=>[r.id,r]));
const files=[['全部实际运行667.csv',667],['异常任务611.csv',611],['正常对照56.csv',56],['官方全部实例3177.csv',3177],['原因与家族耗时分布.csv',null]];
const results=[];
for(const [name,expected] of files){
 const text=await fs.readFile(path.join(data,name),'utf8');
 assert(text.charCodeAt(0)===0xfeff,'UTF-8 BOM missing');
 const wb=await Workbook.fromCSV(text.replace(/^\uFEFF/,''),{sheetName:'Data'});
 const values=wb.worksheets.getItem('Data').getUsedRange().values;
 const [headers,...rows]=values;
 if(expected!==null)assert.equal(rows.length,expected,name);
 assert.equal(new Set(headers).size,headers.length,'duplicate column name');
 assert(rows.every(r=>r.length===headers.length),'column alignment');
 const idIndex=headers.indexOf('id');
 if(idIndex>=0)assert.equal(new Set(rows.map(r=>r[idIndex])).size,rows.length,'duplicate task ID');
 if(['全部实际运行667.csv','异常任务611.csv','正常对照56.csv'].includes(name)){
  const ix=Object.fromEntries(headers.map((h,i)=>[h,i]));
  for(const row of rows){
   const original=byId.get(row[ix.id]);assert(original,'unknown ID');
   assert.equal(row[ix.task],original.task);assert.equal(row[ix.property],original.property);
   assert.equal(row[ix.reproduction_status],original.reproduction.final_status);
   assert(Math.abs(Number(row[ix.cpu_seconds])-original.reproduction.cputime)<1e-9);
   assert.equal(row[ix.cause_code],original.cause_code);
  }
 }
 results.push({file:name,rows:rows.length,columns:headers.length,unique_headers:true,matching_json:expected!==3177&&expected!==null,encoding:'UTF-8 with BOM'});
 console.log(name,rows.length,'rows',headers.length,'columns');
}
const groups=JSON.parse(await fs.readFile(path.join(data,'group-statistics.json'),'utf8'));
for(const dim of new Set(groups.map(x=>x.dimension)))assert.equal(groups.filter(x=>x.dimension===dim).reduce((a,x)=>a+x.count,0),611);
await fs.writeFile(path.join(data,'deliverable-table-audit.json'),JSON.stringify({method:'Read-only CSV import with @oai/artifact-tool; comparison against complete JSON and independent group counts.',files:results,all_group_dimensions_total_611:true},null,2));
