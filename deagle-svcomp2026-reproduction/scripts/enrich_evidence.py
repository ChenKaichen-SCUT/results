import pathlib,json,csv,re,collections,gzip,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
rows=json.load(open(R/'reports/reproduction-analysis.json'));summaries=[]
def stage(text,prior):
 events=[(m.start(),'数据竞争候选对枚举／性质编码') for m in re.finditer(r'\d+\(\d+\) - \d+\(\d+\)',text)]
 for marker in ['Runtime Convert SSA:',"Set Deagle closure solver's graph"]:
  i=text.rfind(marker)
  if i>=0:events.append((i,'排序一致性求解图构造入口之后'))
 for marker,label in [('Handling datarace','数据竞争候选对枚举／性质编码'),('number of races','数据竞争候选对枚举／性质编码'),('number of race categories','数据竞争候选对枚举／性质编码'),('removing dummy accesses','并发访问化简'),('steps after removal','并发访问化简'),('Runtime Solver:','求解结束'),('Runtime Post-process:','SAT／排序一致性求解入口之后'),('Solving with','SAT／排序一致性求解'),('Post-processing','命题公式后处理'),('converting SSA','SSA／命题公式构造'),('Adding SC constraints','SC 并发约束构造'),('size of program expression:','公式构造'),('Runtime Symex:','符号执行完成后／公式构造'),('Unwinding loop','循环展开／符号执行')]:
  i=text.rfind(marker)
  if i>=0:events.append((i,label))
 return max(events)[1] if events else prior
for row in rows:
 if not row['completed']:continue
 d=R/'runs'/row['id'];out=[];last='尚无阶段证据';previous_cmd=None;new_phase=None;commands=[]
 if row.get('last_stage')=='SSA 到命题公式转换' and row.get('final_phase_metrics',{}).get('runtimes',{}).get('Convert SSA'):
  old=row['last_stage'];row['last_stage']='排序一致性求解图构造入口之后（按控制流推断）';row['reason']=row['reason'].replace(old,row['last_stage'])
 row['root_cause_confirmation_scope']='直接失败／退出机制；不等于已证明所有内部算法因果。'
 row['memory_measurement_caveat']='sampled_cgroup_peak_bytes is a ~20ms sampled lower bound. The raw result field peak_process_tree_member_rss_bytes contains wait4 ru_maxrss from the waited process; descendants killed/reparented during cleanup may be omitted, so it is not a reliable whole-tree maximum.'
 source_map={'unsupported_inline_asm':('sources/Deagle/src/goto-programs/goto_asm.cpp','21–22'),'unsupported_tls_destructor':('sources/Deagle/src/goto-programs/builtin_functions.cpp','1617–1623'),'ssa_rename_type_invariant':('sources/Deagle/src/goto-symex/goto_symex_state.cpp','294'),'value_set_assign_type_invariant':('sources/Deagle/src/pointer-analysis/value_set.cpp','1359'),'false_true_from_incomplete_unwinding':('sources/official-tool/deagle/deagle','130–164')}
 if row['cause_code'] in source_map:
  f,lines=source_map[row['cause_code']];row.setdefault('source_evidence',[]).append({'file':f,'lines':lines})
 if row['anomaly'] in ['TIMEOUT','OUT OF MEMORY']:row['root_cause_confirmation_scope']='资源终止机制已确认；阶段为日志／采样推断，深层算法瓶颈及更大预算可终止性未被普遍证明。'
 resource_stack_notes={'5762debd1f9e9bfe':('resource-final-stack390','独立最终参数诊断在 390 秒的栈为 merge_irept::merged → symex_target_equationt::merge_ireps → register_read_from_choice_symbol → memory_model_baset::read_from → memory_model_sct::operator()。与基线最后可见 SC 构造阶段一致；该栈并非基线 OOM 瞬间采样。'),'160c74f546f52fb0':('resource-final-stack60','独立诊断在 60 秒处为 Minisat::closure::get_node → ClosureSolver::set_graph。基线之后打印 Runtime Post-process 并进入求解，约 219.80 CPU 秒因内存终止；不能把 60 秒的图构造栈误称为 OOM 瞬间栈。')}
 if row['id'] in resource_stack_notes:
  label,note=resource_stack_notes[row['id']];p=R/'diagnostics'/(row['id']+'-'+label)/'stdout.log';row['diagnostic_observations']=[note]
  if p.exists():row['diagnostic_stack_evidence']=[{'file':str(p.relative_to(R)),'line':i,'text':s} for i,s in enumerate(p.read_text(errors='replace').splitlines(),1) if s.startswith('#')]
 obs=d/'observations.jsonl'
 if row['anomaly'] in ['TIMEOUT','OUT OF MEMORY'] and obs.exists():
  for lineno,line in enumerate(obs.open(),1):
   x=json.loads(line);cmds=[p['command'] for p in x['processes'] if p['command'].startswith('./deagle_exe ')]
   cmd=cmds[-1] if cmds else None
   if cmd and cmd!=previous_cmd:
    commands.append({'elapsed':x['elapsed'],'command':cmd,'observation_line':lineno});previous_cmd=cmd;last='前端处理／当前日志尚无进一步阶段证据'
   if cmd and '--unwind-suggest' in cmd:last='循环界建议分析'
   else:last=stage(x.get('deagle_tmp_output_tail',''),last)
   cpu=dict(l.split() for l in x.get('cpu.stat','').splitlines())
   mem=int(x['memory.current']) if 'memory.current' in x else None
   out.append({'elapsed_wall_seconds':x['elapsed'],'cgroup_cpu_seconds':int(cpu.get('usage_usec','0'))/1e6,'cgroup_memory_bytes':mem,'phase_observed_or_inferred':last,'observation_line':lineno,'binary_command':cmd or ''})
  (d/'resource-timeline.csv').write_text('',encoding='utf-8')
  with (d/'resource-timeline.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(out[0]) if out else ['elapsed_wall_seconds']);w.writeheader();w.writerows(out)
  durations=collections.Counter();phase_entries={}
  for a,b in zip(out,out[1:]):
   durations[a['phase_observed_or_inferred']]+=max(0,b['elapsed_wall_seconds']-a['elapsed_wall_seconds']);phase_entries.setdefault(a['phase_observed_or_inferred'],a['elapsed_wall_seconds'])
  values=[v for v in out if v['cgroup_memory_bytes'] is not None];growth=[]
  for gb in [1,2,4,8,12,14]:
   hit=next((v for v in values if v['cgroup_memory_bytes']>=gb*10**9),None)
   if hit:growth.append({'threshold_decimal_GB':gb,**hit})
  summary={'id':row['id'],'task':row['task'],'property':row['property'],'official_anomaly':row['anomaly'],'reproduction_status':row['reproduction']['final_status'],'terminationreason':row['reproduction'].get('terminationreason'),'timeline':str((d/'resource-timeline.csv').relative_to(R)),'phase_wall_seconds_observation_estimate':dict(durations),'first_phase_observation_seconds':phase_entries,'memory_threshold_crossings':growth,'last_observation':out[-1] if out else None,'binary_invocations_observed':commands,'limits':'Original 900 CPU soft / 960 CPU hard, 15 GB, four fixed CPUs. Phase timing is sampled and subject to log buffering; it is not a profiler attribution.'}
  summaries.append(summary);row['resource_evidence']=summary
 if row['id'] in ['643ec04b71829a38','4a1c3d1fa852554c']:
  row['diagnostic_observations']=[]
  if row['id']=='643ec04b71829a38':
   row['diagnostic_observations']=['verbosity 10 显示 pthread_create/join 被替换为 build 和 delete 的直接调用；build 作为 thread 0 执行。', '在 pthread_exit 的 assume(false) 处路径被截断，此模型没有执行到 main 的剩余部分。', 'show-vcc 报告 68 个验证条件，简化后剩余 0；该 TRUE 没有经过实际 SAT 搜索。', '源码 config.cpp 根据 --malloc-may-fail 设置 malloc_may_fail，正式脚本没有该选项；cprover_library.cpp 将该值写为宏。其与比赛预期 valid-deref 违反之间的关系仍未独立确认。', '以上模型／覆盖范围现象已得到证实；精确漏报根因仍未确认。本阶段没有改变 malloc 语义。']
   row.setdefault('source_evidence',[]).extend([{'file':'sources/Deagle/src/goto-programs/goto_convert_functions.cpp','lines':'286–351'},{'file':'sources/Deagle/src/ansi-c/library/pthread_lib.c','lines':'301–319'},{'file':'sources/Deagle/src/util/config.cpp','lines':'1123–1133'},{'file':'sources/Deagle/src/ansi-c/cprover_library.cpp','lines':'36–38'}])
  else:row['diagnostic_observations']=['打印的轨迹把 thread 2 的 Operation 放在该线程的启动／初始化之前，说明输出顺序需要独立核验；不能视为实际程序可执行顺序的证明。', '原展开界下的完整性断言在 SyncPush 失败；仅凭展开不完整还不能确定该错误 FALSE 的根因。', 'SyncPush 两个循环由 3 提高至 17 的隔离诊断仍在约 15.43 CPU 秒报告原 reach_error.assertion.1 失败；完整性断言显示 UNKNOWN，不能声称已证明完整展开。直接证据见 diagnostics/4a1c3d1fa852554c-syncpush17/stdout.log:470–474。该实验没有支持“简单调大这两个界即可纠正结果”的结论。']
 # Per-validator fixed results must take precedence over the raw result, while preserving both.
 if row['anomaly']=='correct-unconfirmed':
  statuses=[]
  for v in row['validator_evidence']['validators']:
   xs=v['xml_results'];chosen=[x for x in xs if '.fixed.xml' in x['file']] or xs
   direct=[x for x in v['evidence'] if any(t in x['text'] for t in ['Unsupported feature','unsupported thread assignment','Cannot parse witness','ParseError:','AttributeError:','ineffective witness','Incompatible witness'])]
   for x in chosen:statuses.append({'validator':v['name'],'status':x['columns'].get('status'),'category':x['columns'].get('category'),'voting':x['columns'].get('voting'),'log':v['log'],'xml':x['file'],'direct_rejection_evidence':direct})
  row['semantic_validator_summary']=statuses
  row['reason']+=' 本例修正后验证器记录：'+'；'.join(s['validator'].split('-validate')[0]+'='+str(s['status'])+'/'+str(s['category'])+(('/投票'+s['voting']) if s['voting'] else '') for s in statuses)+'。'
  row['reason']+=' 具体拒绝证据：'+'；'.join(s['validator'].split('-validate')[0]+': '+x['text'] for s in statuses for x in s['direct_rejection_evidence']) if any(s['direct_rejection_evidence'] for s in statuses) else ''
for name,data in [('reproduction-analysis',rows),('anomaly-analysis',[x for x in rows if x['anomaly']]),('control-analysis',[x for x in rows if not x['anomaly']]),('resource-analysis',summaries)]:
 (R/'reports'/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 keys=list(dict.fromkeys(k for x in data for k in x))
 with (R/'reports'/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in x.items()} for x in data)
annotations=[]
annotations.append({'log':'evidence/resource-stacks.log','clarification':'The first resource-stack helper required --unwindset and failed to select the loop-free elimination_backoff_stack command. No second diagnostic binary was started in that attempt. The selector was corrected to use the last non-suggestion invocation from baseline observations; the unchanged binary argv was then run. This was an analysis-helper correction, not a Deagle or baseline modification.'})
for p in (R/'diagnostics').glob('*-solver-stack60/command.json'):
 annotations.append({'command_file':str(p.relative_to(R)),'clarification':'This diagnostic extended the launcher first unbounded attempt from 5 to 60 wall seconds under gdb. It is not the final bounded invocation and cannot be used as a baseline solver-stage sample. See bounded-final-stack60 for that separate diagnostic.'})
for p in (R/'diagnostics').glob('*-goto-model/command.json'):
 annotations.append({'command_file':str(p.relative_to(R)),'clarification':'The initial change description mentions allocation settings, but this output did not establish their initialized values. No conclusion about malloc failure semantics is based on it.'})
(R/'reports/diagnostic-annotations.json').write_text(json.dumps(annotations,indent=2));print('ENRICHED',len(rows),'resources',len(summaries))
