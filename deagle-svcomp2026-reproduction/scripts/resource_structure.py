"""Attach reviewable source structures to resource failures; never infer causality from syntax alone."""
import pathlib,json,csv,re,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
rows=json.load(open(R/'reports/reproduction-analysis.json'))
notes=[
 ('/indexer.yml','共享 table[128] 与按索引访问的锁数组；13 个线程运行哈希探测，内层 CAS 失败会继续探测。数组下标与线程交错增加访问组合；具体内存热点仍以阶段记录为准。'),
 ('/26_stack_cas_longest-','用 1,921 个 int 的共享 memory 数组模拟堆，存在 CAS 重试、push 循环，以及 main 中循环创建线程。有限展开仍会复制线程／访问事件，符号下标访问可能增加数组约束。此结构不单独证明具体分配热点。'),
 ('/bounded_buffer.yml','两个生产者、两个消费者，各循环执行 4 次操作；容量为 3 的共享环形缓冲区含符号索引、指针数组、条件等待循环和锁操作。程序结构与实际展开／公式规模并列保存，未把它们当作独立因果证明。'),
 ('/elimination_backoff_stack','三个 push 与四个 pop 线程共享指针链式栈、location 数组及可复用的 4 个 ThreadInfo 对象；多处分支和 CAS 操作产生别名与并发读写组合。虽然源程序操作次数有限，公式仍可能很大；具体瓶颈看运行阶段。'),
 ('/divinefifo','一个生产线程与主线程消费动态链式 FIFO，INSERTS=7、NODE_SIZE=2；预处理输入含等待非空的循环与动态节点分配。潜在的展开和指针组合规模需结合实际日志判断。'),
 ('/09-regions_21-arrayloop2_nr.yml','初始化 10 个槽位、每槽 30 个堆节点；两个线程按槽位锁遍历链表，包含嵌套循环和 container-of 风格指针算术。堆对象、符号下标及共享访问形成较大的展开／性质编码规模。'),
 ('/09-regions_22-nocollapse.yml','初始化 10×30 个堆节点，两个线程使用非确定起始槽位、嵌套遍历和 container-of 指针算术。源中返回的指针别名也被保留；规模影响以实际日志为证，不推定无限预算可终止。'),
 ('/09-regions_24-evilcollapse_nr.yml','10×30 个堆节点及双线程嵌套链表遍历，另有 lookup1/lookup2 的非确定槽位选择与分支合流指针。该结构提供别名和事件规模背景，不能据此单独定位内存分配热点。'),
]
patterns=[('循环',re.compile(r'\b(?:while|for)\s*\(')),('线程创建',re.compile(r'\bpthread_create\s*\(')),('动态分配',re.compile(r'\b(?:malloc|calloc|realloc)\s*\(')),('同步／原子操作',re.compile(r'\b(?:pthread_(?:mutex|cond)_\w+|__VERIFIER_atomic_\w+)\s*\(')),('规模常量',re.compile(r'^\s*#define\s+(?:SIZE|MAX|NUM_THREADS|MEMSIZE|PRODUCER_SUM|CONSUMER_SUM|INSERTS|NODE_SIZE)\b'))]
out=[]
for a in rows:
 if a['anomaly'] not in ['TIMEOUT','OUT OF MEMORY']:continue
 source=pathlib.Path(a['task']).with_suffix('.c');p=R/'sources/sv-benchmarks'/source
 if not p.exists():source=pathlib.Path(a['files'][0]);p=R/'sources/sv-benchmarks'/source
 evidence=[]
 for n,line in enumerate(p.read_text(errors='replace').splitlines(),1):
  kinds=[label for label,rx in patterns if rx.search(line)]
  if kinds:evidence.append({'file':str(p.relative_to(R)),'line':n,'kinds':kinds,'text':line.strip()[:500]})
 desc=next((v for k,v in notes if k in a['task']),None)
 if desc is None:desc='下列源代码行记录循环、线程创建、分配与同步结构；这些是程序结构证据。运行热点的归因以本实例阶段日志和资源采样为准，不能仅按源码模式确认根因。'
 x={'id':a['id'],'task':a['task'],'property':a['property'],'reviewed_source':str(source),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actual_verification_inputs':a['files'],'source_is_direct_input':str(source) in a['files'],'structure_observation':desc,'evidence':evidence,'causal_status':'结构存在已确认；其对具体内存分配／耗时的因果贡献未做完整 profiler 证明。'}
 a['program_structure']=x;out.append(x)
for name,data in [('reproduction-analysis',rows),('anomaly-analysis',[x for x in rows if x['anomaly']]),('resource-program-structure',out)]:
 (R/'reports'/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 keys=list(dict.fromkeys(k for x in data for k in x))
 with (R/'reports'/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in x.items()} for x in data)
print('RESOURCE STRUCTURE',len(out))
