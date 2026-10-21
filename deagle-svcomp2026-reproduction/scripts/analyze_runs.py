import pathlib,json,csv,gzip,re,collections,statistics,hashlib,sys,time
R=pathlib.Path(__file__).resolve().parents[1];rows=json.load(open(R/'reports/run-plan.json'));validators={x['id']:x for x in json.load(open(R/'reports/validator-evidence.json'))}
pattern=re.compile(r'Too large unwind limit|UNKNOWN|^ERROR$|does not support asm|Destroyer functions|Invariant check failed|File: .*function:|Reason:|GCC preprocessing failed|Failed to open temporary|Unwinding successfully|Runtime |size of program expression|Generated \d+ VCC|VERIFICATION |SAT checker|ClosureSolver finishes|Unwindset:|The bound of loops|SUCCESSFUL|^FAILED$|Not solved within|Solved within|removing dummy accesses|steps after removal|Handling datarace|number of races|number of race categories')
def scan(path):
 evidence=[];metrics={'max_unwind_iteration':0,'max_thread_id':0,'max_expression_steps':0,'max_vccs':0,'runtimes':{},'suggested_bounds':[],'shared_accesses':[]};tail=collections.deque(maxlen=14);markers=set();laststage='原因未确认';lastloop=None;count=0
 op=gzip.open if path.name.endswith('.gz') else open
 try:
  with op(path,'rt',encoding='utf-8',errors='replace') as f:
   for number,line in enumerate(f,1):
    count=number;line=line.rstrip();tail.append(line[:1500])
    if pattern.search(line):
     if len(evidence)<500:evidence.append({'file':str(path.relative_to(R)),'line':number,'text':line[:1200]})
    for marker in ['does not support asm','Destroyer functions','goto_symex_state.cpp:294','value_set.cpp:1359','GCC preprocessing failed','Failed to open temporary file','Too large unwind limit','VERIFICATION FAILED','VERIFICATION SUCCESSFUL','Unwinding successfully','The bound of loops is not determined']:
     if marker in line:markers.add(marker)
    m=re.search(r'Unwinding loop (.+?) iteration (\d+)',line)
    if m:metrics['max_unwind_iteration']=max(metrics['max_unwind_iteration'],int(m[2]));laststage='符号执行与循环展开'
    m=re.search(r'\bthread (\d+)\b',line)
    if m:metrics['max_thread_id']=max(metrics['max_thread_id'],int(m[1]))
    m=re.search(r'size of program expression: (\d+) steps',line)
    if m:metrics['max_expression_steps']=max(metrics['max_expression_steps'],int(m[1]));laststage='并发事件编码与公式构造'
    m=re.search(r'(\d+) steps (?:before|after) removal',line)
    if m:metrics['max_expression_steps']=max(metrics['max_expression_steps'],int(m[1]));laststage='并发访问化简'
    m=re.search(r'The number of (races|race categories) (before|after) filter: (\d+)',line)
    if m:metrics[m[1].replace(' ','_')+'_'+m[2]+'_filter']=int(m[3]);laststage='数据竞争候选对枚举／性质编码'
    if 'Handling datarace' in line:laststage='数据竞争候选对枚举／性质编码'
    m=re.search(r'Generated (\d+) VCC',line)
    if m:metrics['max_vccs']=max(metrics['max_vccs'],int(m[1]))
    m=re.search(r'Runtime ([\w -]+): ([\d.eE+-]+)s',line)
    if m:metrics['runtimes'].setdefault(m[1],[]).append(float(m[2]))
    if 'Adding SC constraints' in line:laststage='SC 并发事件约束构造'
    if 'converting SSA' in line:laststage='SSA 到命题公式转换'
    if 'Runtime Convert SSA:' in line or "Set Deagle closure solver's graph" in line:laststage='排序一致性求解图构造入口之后（按控制流推断）'
    if 'Post-processing' in line:laststage='命题公式后处理'
    if 'Runtime Post-process:' in line or 'Solving with' in line:laststage='SAT／排序一致性求解入口之后（按日志与控制流推断）'
    if 'Runtime Solver:' in line:laststage='求解结束后'
    if line.startswith('Loop '):lastloop=line[5:].rstrip(':')
    m=re.search(r'Suggested unwind limit: (\d+)',line)
    if m:metrics['suggested_bounds'].append({'loop':lastloop,'bound':int(m[1])})
    m=re.search(r'Shared (.*): (\d+)R/(\d+)W',line)
    if m:metrics['shared_accesses'].append({'variable':m[1],'reads':int(m[2]),'writes':int(m[3])})
 except (EOFError,OSError) as e:markers.add('log_read_incomplete')
 return {'evidence':evidence,'metrics':metrics,'markers':sorted(markers),'last_stage':laststage,'tail':list(tail),'line_count':count}
def flatten(v):return json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v
def save(name,data):
 (R/'reports'/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 if data:
  keys=list(dict.fromkeys(k for x in data for k in x))
  with (R/'reports'/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:flatten(v) for k,v in x.items()} for x in data)
analyses=[]
for row in rows:
 ident=row['id'];d=R/'runs'/ident;res=json.load(open(d/'result.json')) if (d/'result.json').exists() else None
 a={k:v for k,v in row.items() if k not in ['official_raw_columns','official_fixed_columns']};a['completed']=res is not None;a['reproduction']=res;a['evidence']=[];a['root_cause_confirmed']=False
 if res is None:
  a.update(reason_group='尚未确定原因',cause_code='pending',reason='原配置运行尚未完成；不提前给出失败结论。',confidence='未判定');analyses.append(a);continue
 logs=[]
 for p in [d/'stdout.log',d/'stderr.log',d/'work/deagle_tmp_output',d/'work/deagle_tmp_unwind_suggest']+sorted((d/'captured').glob('*.gz')):
  if p.exists():logs.append(scan(p))
 markers={m for l in logs for m in l['markers']};a['log_markers']=sorted(markers)
 # Prefer a surviving final inner log; otherwise the latest captured inner stdout.
 final_candidates=[p for p in [d/'work/deagle_tmp_output'] if p.exists()] or sorted((d/'captured').glob('*deagle_tmp_output*.gz'))[-1:]
 final_log=scan(final_candidates[-1]) if final_candidates else (logs[0] if logs else None)
 a['last_stage']=final_log['last_stage'] if final_log else '原因未确认';a['final_phase_metrics']=final_log['metrics'] if final_log else {}
 evidence=[e for l in logs for e in l['evidence']];seen=set();a['evidence']=[]
 for e in evidence:
  k=(e['file'],e['line']);
  if k not in seen:a['evidence'].append(e);seen.add(k)
 a['source_evidence']=[];a['strategy_assessment']='无足够证据证明增加时间可解决。';a['confidence']='高';a['root_cause_confirmed']=True
 cat=row['anomaly']
 if cat=='ERROR' and 'Too large unwind limit' in markers:
  a.update(reason_group='固定启发式导致提前放弃',cause_code='bound_gt_300_adapter_error',reason='启动脚本检测到建议展开界大于 300，打印 UNKNOWN 并以 0 退出；适配器仅将退出码 1 映射为 unknown，因此对该输出组合返回 ERROR。未进入正式求解，非解析崩溃。',last_stage='循环界推断完成后的脚本阈值检查',strategy_assessment='单纯增加 CPU 时间无效：相同脚本仍立即退出。提高阈值或改变展开策略可使其继续尝试，但本报告不据此宣称可以完成验证。')
  a['source_evidence']=[{'file':'sources/official-tool/deagle/deagle','lines':'8, 57–67'},{'file':'sources/python-deps/benchexec/tools/deagle.py','lines':'58–77'}]
 elif cat=='UNKNOWN' and 'does not support asm' in markers:
  a.update(reason_group='当前验证算法能力限制',cause_code='unsupported_inline_asm',reason='内部日志明确报告 Error: Deagle does not support asm code，发生于 Generating GOTO Program 阶段；外层脚本吞掉内部错误细节，以 1 退出，被适配器报告为 unknown。',last_stage='前端 GOTO 程序生成',strategy_assessment='延长时间或调大展开界不能实现当前前端缺失的 asm 支持。')
 elif cat=='UNKNOWN' and 'Destroyer functions' in markers:
  a.update(reason_group='当前验证算法能力限制',cause_code='unsupported_tls_destructor',reason='pthread_key_create 的析构函数参数触发 Destroyer functions are yet unsupported；不是无法推断循环界。',last_stage='前端 GOTO 程序生成',strategy_assessment='单纯增加时间无效，需要工具支持该程序结构；本阶段未修改工具。')
 elif cat=='UNKNOWN' and ('goto_symex_state.cpp:294' in markers or 'value_set.cpp:1359' in markers):
  rename='goto_symex_state.cpp:294' in markers
  a.update(reason_group='实现错误或环境问题',cause_code='ssa_rename_type_invariant' if rename else 'value_set_assign_type_invariant',reason=('符号执行重命名触发 goto_symex_state.cpp:294 的类型一致性不变式失败。' if rename else '符号执行中的 value_sett::assign 在 value_set.cpp:1359 检测到 RHS 数组类型与目标类型不一致。')+'日志含实际不变式条件及调用栈；外层退出 1 被映射为 unknown。',last_stage='符号执行／指针值集合与 SSA 类型处理',strategy_assessment='原参数下稳定触发内部不变式；增加时间缺乏解决依据。')
 elif cat in ['TIMEOUT','OUT OF MEMORY']:
  a.update(reason_group='计算资源不足',cause_code='cpu_limit' if cat=='TIMEOUT' else 'memory_limit',reason=('官方 CPU 时间耗尽；本次终止原因为 '+str(res.get('terminationreason'))+'.' if cat=='TIMEOUT' else '官方内存耗尽；本次终止原因为 '+str(res.get('terminationreason'))+'.')+' 最后可见阶段：'+a['last_stage']+'。该阶段定位不等于证明算法在无限资源下会终止。',confidence='资源终止：高；具体热点：中（有独立栈证据的实例另列）',strategy_assessment='资源不足已确认，但不能仅凭超时／OOM推断增加预算一定成功。原始限制下结果保留；阶段、规模、资源曲线见逐实例记录。')
  if res['final_status']!=row['raw_status']:a['reason']+=' 本机状态与官方不同，差异须结合硬件和 5 秒 wall-time 分支解释，不能当作同机确定性改进。'
 elif cat=='witness missing':
  files=res.get('witness_files',[])
  a.update(reason_group='witness 生成或验证问题',cause_code='datarace_witness_deliberately_omitted',reason='Deagle 报告数据竞争反例；原版 output_graphml 在 datarace 开启时直接返回。本次 GraphML 文件数：'+str(len(files))+'。这是反例证据未输出，不是未找到反例。',last_stage='反例 witness 输出',strategy_assessment='增加验证时间不会改变该显式返回分支；需要 witness 输出能力变更，超出本阶段范围。')
  a['source_evidence']=[{'file':'sources/Deagle/src/goto-checker/bmc_util.cpp','lines':'113–127'}]
 elif cat=='witness invalid':
  a.update(reason_group='witness 生成或验证问题',cause_code='empty_graphml_source_location',reason='竞赛原始 GraphML 已由 SHA-256 验证，包含空 startline（并存在空源位置 data 标签）。官方 witnesslint 返回 invalid witness syntax；独立验证器还报告空字符串整数解析异常。本次生成文件及独立语法检查另存。',last_stage='GraphML witness 序列化／独立解析',strategy_assessment='更多求解时间不能修复已输出文件的空源位置字段。格式检查通过也不自动证明反例可行。')
 elif cat=='wrong' and ident in ['15fbf61018a5dd49','3166c6eacc7f22c8']:
  a.update(reason_group='固定启发式导致提前放弃',cause_code='false_true_from_incomplete_unwinding',reason='原版 5 秒无界尝试之后，对无法推断的循环使用展开界 3，未要求展开完整，随后将有界 UNSAT 报告为 TRUE。独立诊断将循环界提高到 102 并检查完整性，得到原 reach_error 性质的反例。',last_stage='有界求解结果解释',strategy_assessment='本例有直接证据支持通过展开策略改变获得正确反例；该诊断不计作官方原参数下成功。')
 elif cat=='wrong':
  a.update(reason_group='尚未确定原因',cause_code='wrong_verdict_root_unconfirmed',reason='已复现与期望性质冲突的工具报告，并保存原属性、SC 设置、展开参数、求解日志和可得证据。展开不完整的诊断不能单独证明其是此错误结果的根因；精确因果仍未确认。',confidence='错误报告复现：高；根因：未确认',root_cause_confirmed=False,strategy_assessment='没有证据证明单纯增加时间可纠正该错误。不得把工具报告或未通过验证的反例当作真值。')
 elif cat=='correct-unconfirmed':
  a.update(reason_group='witness 生成或验证问题',cause_code='semantic_validation_unconfirmed',reason='工具报告与任务期望相符，但独立验证未确认反例。原始 GraphML、每个验证器的结果及日志已保存；语法通过不代表执行语义可行，无法进一步确认的语义根因标为未确认。',confidence='未确认状态与验证器退出原因：高；反例语义根因：未确认',root_cause_confirmed=False,last_stage='独立 witness 语义验证',strategy_assessment='应按验证器的具体超时、异常或拒绝证据判断；不能笼统断言提高验证器预算会确认，也不能将 unconfirmed 等同于 wrong。')
 elif not cat:
  a.update(reason_group='正常对照',cause_code='control',reason='按程序家族与属性选取的官方正常对照。',confidence='工具报告比较：高',strategy_assessment='对照用途。')
 else:a.update(reason_group='尚未确定原因',cause_code='unclassified',reason='证据不满足已确认分类规则，原因未确认。',confidence='未确认',root_cause_confirmed=False)
 a['validator_evidence']=validators.get(ident,{})
 a['diagnostics']=[str(p.relative_to(R)) for p in sorted((R/'diagnostics').glob(ident+'-*')) if p.is_dir()]
 a['independent_linter']={}
 for kind in ['original','reproduction']:
  p=R/'diagnostics'/('witnesslint-'+kind)/ident/'result.json'
  if p.exists():a['independent_linter'][kind]={'result':json.load(open(p)),'directory':str(p.parent.relative_to(R))}
 analyses.append(a)
save('reproduction-analysis',analyses);save('anomaly-analysis',[a for a in analyses if a['anomaly']]);save('control-analysis',[a for a in analyses if not a['anomaly']])
def quantiles(v):
 if not v:return {}
 s=sorted(v)
 def q(p):k=(len(s)-1)*p;i=int(k);return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(k-i)
 return {'n':len(v),'sum':sum(v),'min':min(v),'p25':q(.25),'median':q(.5),'p75':q(.75),'p90':q(.9),'p95':q(.95),'max':max(v)}
stats=[]
for dimension in ['anomaly','reason_group','cause_code','family']:
 groups=collections.defaultdict(list)
 for a in analyses:
  if a['anomaly']:groups[a[dimension]].append(a)
 for name,g in sorted(groups.items()):
  completed=[a for a in g if a['completed']];stats.append({'dimension':dimension,'name':name,'count':len(g),'completed':len(completed),'official_cpu':quantiles([a['official_cpu_seconds'] for a in g]),'reproduction_cpu':quantiles([a['reproduction']['cputime'] for a in completed]),'reproduction_wall':quantiles([a['reproduction']['walltime'] for a in completed]),'sampled_memory':quantiles([a['reproduction'].get('sampled_cgroup_peak_bytes',0) for a in completed])})
save('group-statistics',stats)
cross=[]
for task in sorted({a['task'] for a in analyses if a['anomaly']}):
 g=[a for a in analyses if a['task']==task];cross.append({'task':task,'family':g[0]['family'],'properties':{a['property']:{'id':a['id'],'official_anomaly':a['anomaly'],'cause_code':a['cause_code'],'completed':a['completed'],'status':a['reproduction']['final_status'] if a['completed'] else None} for a in g}})
save('program-cross-property',cross)
allrows=json.load(open(R/'reports/all-official-tasks.json'));byid={a['id']:a for a in analyses}
for r in allrows:
 a=byid.get(r['id']);r['selected_for_reproduction']=a is not None;r['reproduced']=bool(a and a['completed']);r['reproduction_status']=a['reproduction']['final_status'] if a and a['completed'] else None;r['cause_code']=a['cause_code'] if a else 'invalid_excluded' if r['excluded_invalid'] else 'not_selected_normal';r['reason']=a['reason'] if a else '官方 invalid task，排除。' if r['excluded_invalid'] else '官方正常实例，未被选为对照。'
save('all-tasks-with-analysis',allrows)
summary={'generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'planned':len(rows),'completed':sum(a['completed'] for a in analyses),'anomalies_planned':sum(bool(a['anomaly']) for a in analyses),'anomalies_completed':sum(bool(a['anomaly']) and a['completed'] for a in analyses),'same_status':sum(a['completed'] and a['reproduction']['same_as_official_raw'] for a in analyses),'reason_groups':dict(collections.Counter(a['reason_group'] for a in analyses if a['anomaly'])),'cause_codes':dict(collections.Counter(a['cause_code'] for a in analyses if a['anomaly']))}
(R/'reports/analysis-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
