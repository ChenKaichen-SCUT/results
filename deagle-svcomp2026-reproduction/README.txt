Deagle / SV-COMP 2026 Concurrency 复现与分析交付说明

先阅读 Deagle-SVCOMP2026-中文报告.html。报告的附录可以按任务路径、属性、异常类型和 ID 筛选 611 个异常实例。

数据
data/异常任务611.csv：611 个异常的原始/修正状态、实际运行结果、失败机制、证据、置信度。
data/全部实际运行667.csv：611 个异常与 56 个正常对照。
data/官方全部实例3177.csv：完整官方清单，包括 53 个明确排除的 invalid 实例。
data/anomaly-analysis.json、reproduction-analysis.json：完整嵌套证据、原始命令、资源信息、验证器与诊断路径。
data/原因与家族耗时分布.csv、group-statistics.json：数量、总耗时和分位数。
data/program-cross-property.json：同一 YAML 在不同属性下的异常对照。
figures/：静态 PNG 和 SVG 研究图。

完整运行资料分成两个压缩包，解压到同一个新目录即可合并。
1. runtime-and-sources.tar.gz：正式工具、固定源码和基准快照、隔离运行环境与依赖。
2. evidence-and-results.tar.gz：逐实例原始日志、运行记录、原始/修正 XML、验证器日志、witness、诊断、脚本及审计表。
这些包采用 Linux tar 格式，含符号链接及隔离 rootfs 的设备文件。应在 Linux 上以 root 解压，以保留权限和链接；不要用 Windows 的普通解压工具部署运行环境。

在用户服务器上，所有原始文件还保留在：
/root/deagle-svcomp26-repro-20261021-01a15ee7

重跑（推荐在该服务器、完成原批次后执行）
cd /root/deagle-svcomp26-repro-20261021-01a15ee7
bash scripts/reexecute.sh

只重跑一个实例：
bash scripts/reexecute.sh 15fbf61018a5dd49

脚本为新运行创建 replays/时间戳-ID，不覆盖已有证据。要求 root、cgroup v2、32 个逻辑 CPU 和足够可用内存。原配置为 7 个互斥 CPU 组、每任务 4 个逻辑 CPU、15 GB、900 秒 CPU soft 和 960 秒 hard。脚本禁止在原批次仍活动时争用其分配。
runs/ID/reproduce-command.sh 仅保存工具调用，本身不施加资源上限；请用 reexecute.sh 执行受限复跑。

分析脚本顺序（在复现根目录）：
python3 scripts/analyze_runs.py
python3 scripts/enrich_evidence.py
python3 scripts/resource_structure.py
python3 scripts/audit_witness_structure.py
python3 scripts/attach_data_model.py
python3 scripts/attach_data_model.py
python3 scripts/final_audit.py
python3 scripts/provenance.py

报告和图的生成使用 Python 3 与 matplotlib（图字体使用 Microsoft YaHei）。可在 Windows 分析机上运行：
python scripts/build_report.py --data 解压根目录 --out 新的输出目录
python scripts/build_figures.py --data 解压根目录 --out 新的输出目录
python scripts/build_memory_figures.py --data 解压根目录 --archive evidence-and-results.tar.gz --out 新的输出目录
python scripts/embed_figures.py --out 新的输出目录

最后一步将图片内嵌到 HTML，便于单独打开和分享；PNG/SVG 原图仍在 figures/ 中。

脚本目录也保存了获取资料和搭建环境的历史过程，包含失败过的下载/构建环境尝试；不要将这些历史脚本全部顺序执行。正式复跑入口是 reexecute.sh。

重要边界
使用的是正式竞赛 Deagle 4.1.0 二进制，没有源码重建。原二进制的完整构建容器/编译器记录不可得，不能将其等同于本地 GCC 运行环境。源代码、固定提交、工具及脚本哈希均有记录。
官方 TIMEOUT 原始记录约为 961 CPU 秒/SIGKILL；本地 900 秒 soft 限制会提前终止。这一 VCloud 行为差异、硬件/内核/用户态差异均写入报告。hard960-policy 是单独的诊断，任何结果都不计作 900 秒基线成功。
内核 5.15 不提供 cgroup memory.peak；memory.current 约 20 ms 采样值是峰值下界。wait4 ru_maxrss 可能遗漏清理时重新托管的子进程，不代表整个进程树峰值。内核实际执行内存上限。
语法检查并非反例可行性证明；完整语义验证证据来自正式归档的独立验证器记录。未确认根因保持“原因未确认”。
环境预检的错误结果全部保留在 evidence/environment-* 并明确排除，没有计入有效复现批次。
交付内容不包含服务器登录密码。
