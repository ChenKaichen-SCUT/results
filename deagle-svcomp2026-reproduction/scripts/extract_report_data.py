import pathlib,tarfile,argparse,shutil
p=argparse.ArgumentParser();p.add_argument('--archive',default='outputs/evidence-and-results.tar.gz');p.add_argument('--out',default='work/final-data');a=p.parse_args()
root=pathlib.Path(a.out).resolve();root.mkdir(parents=True,exist_ok=True);count=0
with tarfile.open(a.archive,'r:gz') as z:
 for m in z:
  if not m.isfile() or not m.name.startswith(('reports/','diagnostics/')):continue
  dest=root.joinpath(*pathlib.PurePosixPath(m.name).parts).resolve()
  if not dest.is_relative_to(root):raise ValueError('Unsafe archive member '+m.name)
  dest.parent.mkdir(parents=True,exist_ok=True)
  with z.extractfile(m) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)
  count+=1
print('EXTRACTED',count,'regular report/diagnostic files')
