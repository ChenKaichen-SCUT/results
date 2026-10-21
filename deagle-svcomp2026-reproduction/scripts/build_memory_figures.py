import pathlib,os,tarfile,json,io,csv,argparse
os.environ['MPLCONFIGDIR']=str(pathlib.Path('work/matplotlib-config').resolve())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=argparse.ArgumentParser();P.add_argument('--data',default='work/report-data');P.add_argument('--archive',default='outputs/evidence-and-results.tar.gz');P.add_argument('--out',default='outputs');a=P.parse_args()
R=pathlib.Path(a.data);O=pathlib.Path(a.out)/'figures';O.mkdir(parents=True,exist_ok=True)
rows=json.loads((R/'reports/reproduction-analysis.json').read_text(encoding='utf-8'));oom=[r for r in rows if r['anomaly']=='OUT OF MEMORY' and r['completed']]
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig,axes=plt.subplots(5,5,figsize=(15,11),layout='constrained',sharey=True)
with tarfile.open(a.archive,'r:gz') as z:
 for ax,r in zip(axes.flat,oom):
  member=z.getmember('runs/'+r['id']+'/resource-timeline.csv');f=io.TextIOWrapper(z.extractfile(member),encoding='utf-8-sig');points=list(csv.DictReader(f));xs=[float(p['elapsed_wall_seconds']) for p in points if p['cgroup_memory_bytes']];ys=[int(p['cgroup_memory_bytes'])/1e9 for p in points if p['cgroup_memory_bytes']]
  ax.plot(xs,ys,color='#6f64a5',lw=1.4);ax.axhline(15,color='#b55f3b',ls='--',lw=.7);ax.set_title(r['id']+'\n'+r['property'],fontsize=8);ax.set_ylim(0,15.8);ax.grid(alpha=.15)
fig.supxlabel('Wall time / 秒');fig.supylabel('cgroup memory.current / GB（约 0.5 秒记录）');fig.suptitle('25 个官方 OOM 实例的复现内存轨迹；虚线为 15 GB 限制',fontsize=15)
for ext in ['png','svg']:fig.savefig(O/('oom-memory-trajectories.'+ext),dpi=180)
print('MEMORY FIGURE',len(oom))
