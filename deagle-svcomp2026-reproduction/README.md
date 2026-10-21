# Deagle / SV-COMP 2026 Concurrency 复现与根因分析

**667 / 667 个实例已完成，剩余 0 个。** 包含 611 个异常和 56 个正常对照，667 个原始工具状态全部与官方记录一致。官方标记的 53 个 invalid task 已从异常分析中排除。

## 阅读与下载

- [完整中文分析报告（HTML，内嵌图表和 611 个可筛选案例）](https://github.com/ChenKaichen-SCUT/results/releases/download/deagle-svcomp2026-repro-20261021/Deagle-SVCOMP2026-report-zh.html)
- [全部 CSV / JSON 结果表](data/)
- [611 个异常 CSV](data/异常任务611.csv) · [667 次运行 CSV](data/全部实际运行667.csv) · [官方 3177 个实例 CSV](data/官方全部实例3177.csv)
- [原因与家族耗时分布](data/原因与家族耗时分布.csv)
- [运行、诊断与分析脚本](scripts/) · [使用说明](README.txt)
- [逐实例完整日志、witness、验证器证据和运行记录](https://github.com/ChenKaichen-SCUT/results/releases/download/deagle-svcomp2026-repro-20261021/evidence-and-results.tar.gz)
- [正式工具、固定源码／基准与隔离运行环境](https://github.com/ChenKaichen-SCUT/results/releases/download/deagle-svcomp2026-repro-20261021/runtime-and-sources.tar.gz)
- [Release 与全部附件](https://github.com/ChenKaichen-SCUT/results/releases/tag/deagle-svcomp2026-repro-20261021)

HTML 文件需打开或保存后用浏览器查看；GitHub 文件页只显示源文件。两份 tar.gz 解压到同一个新的 Linux 目录，可合并为完整复现目录。

## 官方异常清单

| 官方分类 | 数量 | 已运行 |
| --- | ---: | ---: |
| ERROR | 248 | 248 |
| UNKNOWN | 85 | 85 |
| TIMEOUT | 35 | 35 |
| OUT OF MEMORY | 25 | 25 |
| witness missing | 193 | 193 |
| witness invalid | 2 | 2 |
| 错误 TRUE / FALSE | 4 | 4 |
| correct-unconfirmed | 19 | 19 |
| 合计 | 611 | 611 |

## 已核实的主要结论

248 个 ERROR 来自正式启动脚本在建议展开界超过 300 时打印 UNKNOWN 并以 0 退出，适配器将该组合归为 ERROR。85 个 UNKNOWN 中，76 个为不支持 asm，4 个为不支持 TLS 析构函数，5 个为内部不变式失败。这些结论来自实际日志和源码位置，未按耗时猜测。

193 个 witness missing 对应数据竞争分支明确跳过 GraphML 输出；2 个 invalid 的原始和重新生成文件均有空源位置字段。19 个 correct-unconfirmed 保留每个独立验证器的原始／修正记录，不能视为错误结果。

两个 theta 错误 TRUE 在完整记录的展开诊断中得到原性质反例。另外两个错误结果的精确根因仍标为“原因未确认”。60 个资源失败逐实例记录终止阶段、资源曲线、展开规模和结构证据，有限的栈快照不冒充终止瞬间或全程性能剖析。

## 复现边界

- 使用正式竞赛 Deagle 4.1.0 二进制，未源码重建。固定基准提交为 `7efe28dd29576b46927b7a34e8f742bd90966a75`；2,001 项运行输入哈希匹配。
- 每任务 4 个逻辑 CPU、15 GB、900 秒 CPU soft / 960 秒 hard，7 组并行。官方超时记录约 961 秒 / SIGKILL，本地软限制约 900 秒终止；另有两例独立 hard960 诊断，两者仍超时。
- 用户服务器硬件、内核及兼容用户态与比赛环境不同。Linux 5.15 的 cgroup 内存采样峰值是下界，wait4 ru_maxrss 也不等于整个进程树的精确峰值。
- 原始标准输出／错误完整保存；对工具删除的短暂内部日志只能尽力捕获。GraphML 语法检查已重跑，独立语义验证证据采用比赛归档，未声称全部重新执行语义验证器。
- 本阶段未修复 Deagle、优化算法、修改待验证程序或验证属性。诊断调整均独立标注，不计入原配置成功数。

## 重新运行

在满足资源要求的 Linux 主机解压两个证据包后：

```bash
bash scripts/reexecute.sh                 # 全部 667 个实例
bash scripts/reexecute.sh 15fbf61018a5dd49 # 单例
```

脚本为新运行创建独立目录，不覆盖原始证据。详情见 [README.txt](README.txt)。

## 完整性

| 附件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| evidence-and-results.tar.gz | 134161569 | `2a59e07e3435e3bcb12d929ba6e8b91f34fe017e38c9a7e1fd5d3c4680f837c0` |
| runtime-and-sources.tar.gz | 292260077 | `efe806b9adc222ef5704e0452833899c8d26f1b33e59e597bd66323c6bc528da` |

发布文件由 Linux 服务器直接推送。GitHub 发布凭据和服务器登录密码未写入交付内容。
