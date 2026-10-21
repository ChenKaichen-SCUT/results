import pathlib,os,json,collections,argparse
os.environ['MPLCONFIGDIR']=str(pathlib.Path('work/matplotlib-config').resolve())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=argparse.ArgumentParser();P.add_argument('--data',default='work/report-data');P.add_argument('--out',default='outputs');a=P.parse_args()
R=pathlib.Path(a.data);O=pathlib.Path(a.out)/'figures';O.mkdir(parents=True,exist_ok=True)
rows=json.loads((R/'reports/reproduction-analysis.json').read_text(encoding='utf-8'));an=[r for r in rows if r['anomaly']]
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
cats=['ERROR','UNKNOWN','TIMEOUT','OUT OF MEMORY','witness missing','witness invalid','wrong','correct-unconfirmed']
fig,ax=plt.subplots(figsize=(13,5.7),layout='constrained')
for j,(color,label,key) in enumerate([('#8192a7','官方 CPU 时间','official_cpu_seconds'),('#12695f','复现 CPU 时间','reproduction')]):
 data=[[r['official_cpu_seconds'] if key=='official_cpu_seconds' else r['reproduction']['cputime'] for r in an if r['anomaly']==c and (key=='official_cpu_seconds' or r['completed'])] for c in cats]
 positions=[i*2+.35*j for i in range(len(cats))]
 b=ax.boxplot(data,positions=positions,widths=.28,patch_artist=True,showfliers=False,whis=(5,95))
 for box in b['boxes']:box.set(facecolor=color,alpha=.8)
 for med in b['medians']:med.set(color='#111827',linewidth=1.4)
 ax.plot([],[],color=color,linewidth=7,label=label)
ax.set(yscale='log',ylabel='CPU 时间 / 秒（对数坐标）',title='异常类别的耗时分布：箱体 P25–P75，须线 P5–P95')
ax.set_xticks([i*2+.175 for i in range(len(cats))],cats,rotation=18,ha='right');ax.grid(axis='y',alpha=.18);ax.legend(frameon=False,loc='upper left')
for ext in ['png','svg']:fig.savefig(O/('cpu-distributions.'+ext),dpi=180)
plt.close(fig)
groups=['固定启发式导致提前放弃','当前验证算法能力限制','实现错误或环境问题','计算资源不足','witness 生成或验证问题','尚未确定原因']
colors=['#d9902c','#477eaa','#a95b6e','#6f64a5','#248d80','#8b929b'];families=sorted({x['family'] for x in an},key=lambda f:-sum(x['family']==f for x in an))
fig,ax=plt.subplots(figsize=(13,8),layout='constrained');left=[0]*len(families)
for g,c in zip(groups,colors):
 vals=[sum(x['family']==f and x['reason_group']==g for x in an) for f in families];ax.barh(families,vals,left=left,color=c,label=g);left=[x+y for x,y in zip(left,vals)]
for i,n in enumerate(left):ax.text(n+1,i,str(n),va='center',fontsize=9)
ax.invert_yaxis();ax.set(xlabel='任务 × 属性实例数',title='程序家族与失败原因（互斥主分类）');ax.legend(frameon=False,loc='lower right',fontsize=9);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
for ext in ['png','svg']:fig.savefig(O/('family-causes.'+ext),dpi=180)
plt.close(fig);print('FIGURES',O)
