import subprocess,json,pathlib,os
R=pathlib.Path(__file__).resolve().parents[1];os.chdir(R)
def run(a,**kw):
 print('COMMAND',a,flush=True);subprocess.run(a,check=True,**kw)
run(['git','clone','--filter=blob:none','--no-checkout','--depth','1','--branch','svcomp26','https://gitlab.com/sosy-lab/benchmarking/sv-benchmarks.git','sources/sv-benchmarks'])
sha=subprocess.check_output(['git','-C','sources/sv-benchmarks','rev-parse','HEAD'],text=True).strip()
assert sha=='7efe28dd29576b46927b7a34e8f742bd90966a75',sha
(R/'evidence/sv-benchmarks-commit.txt').write_text(sha+'\n')
rows=json.load(open('reports/run-plan.json'));paths={'c/Concurrency.set','c/properties/','README.md','LICENSE'}
for row in rows:
 paths.add(row['task']);paths.add(row['property_file'])
 for f in row['files']:
  paths.add(f)
  if f.endswith('.i'):paths.add(f[:-2]+'.c')
# Include headers and task-family metadata for unpreprocessed inputs without checking out unrelated benchmarks.
families={r['family'] for r in rows}
for f in families:
 paths.update({f'c/{f}/*.h',f'c/{f}/README*',f'c/{f}/Makefile'})
patterns='\n'.join('/'+x for x in sorted(paths))+'\n'
(R/'evidence/benchmark-sparse-patterns.txt').write_text(patterns)
run(['git','-C','sources/sv-benchmarks','sparse-checkout','set','--no-cone','--stdin'],input=patterns,text=True)
run(['git','-C','sources/sv-benchmarks','checkout','--detach',sha])
for row in rows:
 for f in [row['task'],row['property_file']]+row['files']:assert (R/'sources/sv-benchmarks'/f).is_file(),f
print('ALL SELECTED INPUTS AVAILABLE',len(rows),flush=True)
