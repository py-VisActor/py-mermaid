> 2026-11-05 **独立 py-katex 原生静态 alpha 与 Mermaid 数学标签接入已完成本地验收**：712 个方法、69 个数学/集成案例 × 3 后端、297 个历史案例 × 3 后端通过。当前入口为 [数学验收](../docs/MATH_ACCEPTANCE.md)；完整 KaTeX 兼容仍有明确未支持项。Dagre/交互排除，安装验证暂缓，当前修改未提交推送发布；下文旧“数学延后”及旧候选说明保留为历史。

> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](../docs/LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 **F01.3 已完成本地验收**：产品 279 项 + 工具 25 项通过；50 正例/8 语法负例/6 范围外诊断/1 上游缺陷在 CPU、auto、GPU 全通过。[验收记录](../docs/F01_3_ACCEPTANCE.md)。F01.4/Dagre 暂停，安装验证继续暂缓，本轮未提交推送。下方旧状态保留为历史。

> 2026-11-04 当前执行范围为 F01.2 流程图增强，已完成 F01.1 基线；以 [F01.2 执行计划](../docs/F01_2_EXECUTION_PLAN.md) 与当前账本为准。安装验证继续暂缓。以下旧范围和时序保留为历史资料。

# 上游资料与 spec 索引

当前执行按 [完整主方案](../docs/FULL_MIGRATION_PLAN.md)与 [机器任务图](migration-execution.json)进行。P0/P1 读取来源以编写全部功能源码；正式逐 case/assertion 拆解与单测/oracle 后置 P2，排查批修 P3、最终全量 P4。本文旧 M1/M2 名称只表示来源工作范围。

固定官方 [Mermaid 12.2.0 源码](https://github.com/mermaid-js/mermaid/tree/1fb7869866dd619168d840291c9c54b4f129758b)，详细版本和关键 canonical Git blob 的 SHA256 见 [upstream.lock.json](upstream.lock.json)。[spec-inventory.json](spec-inventory.json)记录每个源文件的路径、Git blob ID 与类别；checkout 位于被忽略的 `.local/upstream-mermaid`。

[dependencies.json](dependencies.json)补充五个产品包的声明、锁定版本、传递 snapshot 图、registry integrity、源码 import 和补丁指纹。运行 `python scripts/audit_dependencies.py --check` 复核；说明及限制见 [第三方依赖盘点](../docs/THIRD_PARTY_DEPENDENCIES.md)。这是静态依赖盘点，不是 bundle 可达性或传递许可证审计结论。

完整视图见 [产品树](dependency-tree.txt)、[全工具链树](dependency-toolchain-tree.txt)、[完整机器图](dependency-tree.json)和 [底层工作索引](dependency-bottom-up.md)，统一由 `python scripts/build_dependency_tree.py --check` 核对。处理规则来自 [策略文件](dependency-porting-policy.json)，候选研究见 [python-candidates.json](python-candidates.json)，方案与范围见 [依赖迁移](../docs/DEPENDENCY_MIGRATION.md)。候选元数据中的版本不自动成为产品 pin。

[Canvas 原生架构](../docs/CANVAS_NATIVE_ARCHITECTURE.md)明确淘汰目标产品中的 DOM/浏览器实现层。原始来源节点/边保留，`plan` 描述功能保留、计算迁移与宿主淘汰；不能把完整 npm 来源树当成目标 Python 依赖列表。

```shell
python scripts/upstream.py fetch
python scripts/upstream.py check
```

命令在仓库根执行。`fetch` 只在 checkout 不存在时 clone 精确 tag，然后核 commit/版本/关键 SHA/干净状态；已有 checkout 不做 reset、pull 或覆盖。`check` 从锁定 Git tree 重建内存索引并比较已提交清单，发现漂移立即失败。

首次建立新基线时，`python scripts/upstream.py inventory` 可写入**不存在**的索引文件；日常不能删除旧索引再生成以掩盖变化。升级需新任务、保留旧基线、审阅范围并更新全部状态/对照证据。

索引覆盖全仓 `.spec/.test` JS/TS 文件、`e2e/**/*.mmd`、Jison/Langium grammar、syntax docs。包含示例/基础设施测试；不是全部独立 test case 的数量。M1 仍需拆开动态/参数化测试、多断言、fixture 配置和 snapshot。

37 个 core detector 文件由 `diagram-orchestration.ts` 的 import 清单提取；这不是运行时检测优先级，后者须审计 `addDiagrams` 中的实际注册调用顺序、构建开关和配置副作用。ZenUML 为独立外部插件，其包版本在 lock 单独记录。`error`/`---` 单独登记诊断。检测器是源码范围清单，Python 实现均未开始。

文件名索引也不是全部测试入口：锁定源码的 `diagrams/git/gitGraphParser.ts` 含内联测试。M1 应补查 `import.meta.vitest`、动态/参数化用例、snapshot 和其他公开行为，保留原索引并建立补充 assertion/source map。完整任务见 [实施方案](../docs/IMPLEMENTATION_PLAN.md)和 [M1 工作分解](../docs/TASKS.md)。

checkout 只读、不随 wheel 发布、不作 runtime fallback。复制或移植第三方代码时保留 upstream path/commit、MIT 版权和其他依赖许可；仅锁某个 package.json 不等于已审计其全部传递依赖。当前许可证原文见 [mermaid-LICENSE](licenses/mermaid-LICENSE)。
> 2026-11-05：F01.4 保留静态流程图已完成本地验收，当前汇总见 [f014-verification-summary.json](f014-verification-summary.json) 和 [验收记录](../docs/F01_4_ACCEPTANCE.md)。486 项测试、200 正例三后端矩阵、旧模块回归、五种导出及 HTML/人工 QA 通过。数学独立后续，Dagre/交互排除，安装验证暂缓。各 f014 source map/断言中的早期阶段字段为历史，`finalVerification` 指向当前同候选结果；其他图种没有因此验收通过。
