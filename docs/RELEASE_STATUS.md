> 2026-11-04 F01.1基础流程图已实现并完成本地功能验证：85项测试通过，官方12正例/3非法输入在CPU、auto、GPU profile通过。见 [当前验收记录](F01_1_ACCEPTANCE.md)、[计划](F01_1_EXECUTION_PLAN.md)。仅此切片，不提升完整detector兼容状态；未发布。用户最新要求暂缓安装验证，后续不继续或复跑，先前结果保留。以下为此前历史记录。

# 当前状态

2026-11-04 像素工具：已实现独立 [PNG 对比工具](../tools/PIXEL_COMPARE.md)，含 RGBA/alpha composite 指标、差异区域/tile、热图/掩码、离线 HTML、SHA 报告及 diagnostic/exact 两模式。仅为用户本轮要求的测试基础设施，P2 完整业务比较器与 Mermaid 功能仍未实现。实际验证见 [工具记录](changes/20261104-pixel-compare-tool.json)，不提升任何图种兼容状态。

2026-11-04 渲染验收规则更新：用户已明确功能一致、跨 DOM/Canvas 不要求完全像素一致。[分层规则](RENDER_CONSISTENCY.md)和[机器策略](../references/render-validation-policy.json)以语义、实际绘制内容、几何关系/可读性及安全导出为门禁，图像差异仅诊断；正常引擎差异可通过。见 [任务记录](changes/20261104-functional-render-parity.json)。比较器仍待 P2 实现，没有新增产品渲染通过结论。

2026-11-04 完整执行交接：新增 [主方案](FULL_MIGRATION_PLAN.md)、[直接接管指令](EXECUTION_HANDOFF.md)、公共模块/并行/来源测试专项资料及 [61 项机器任务图](../references/migration-execution.json)。执行顺序改为 P1 全部源码 → P2 原实现用例/单测 → P3 统一排查修复 → P4 最终全量；旧顺序只保留范围参考。计划/任务归属的校验见 [交接记录](changes/20261104-full-migration-handoff.json)，没有新增产品实现或 Mermaid spec 通过。

2026-11-04 用户明确去 DOM：已同步 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)、功能契约和依赖策略，淘汰 DOM/虚拟 DOM/D3 selection/浏览器调度等运行机制，保留图形语义与算法，所有测量/绘制/编码走 Canvas。上游来源树不变，目标策略与生成索引更新。见 [任务记录](changes/20261104-canvas-native.json)；仍未实现 Mermaid 渲染。

2026-11-04 功能拆分：全部 detector 分为 12 组功能、跨图职责分为 8 个共享模块；首个切片选为 [F01.1 基础流程图](FEATURE_MIGRATION.md)，从文本经真实默认 py-elk 到 PNG。第一编码任务是用例/契约与最小 parser-model，后续按该切片补齐测量/适配/绘制。仍为计划，不增加兼容状态。记录见 [feature-split](changes/20261104-feature-split.json)。

2026-11-04 完整依赖树补充：生成全部锁定工作区/工具链及产品额外源码值导入的依赖树、SCC 底层顺序和逐节点 Python 处理策略，调查 14 个 Python 候选。见 [迁移方案](DEPENDENCY_MIGRATION.md)及 [任务证据](changes/20261104-dependency-tree.json)。这些是审计工具与实施方案；没有新增 Mermaid 产品功能或采纳未经验证的 Python 运行依赖。

2026-11-04 依赖盘点：已新增 [第三方依赖文档](THIRD_PARTY_DEPENDENCIES.md)、机器清单和静态复核脚本，覆盖核心 23 项声明及四个同仓库解析/扩展包。验证范围与证据见 [任务记录](changes/20261104-dependency-audit.json)。这是 M1-06 的部分资料与工具，不增加 Mermaid 解析/布局/渲染能力；py-elk 适配、实际 bundle 和传递许可审计尚未完成。

2026-11-02：**项目启动阶段，未实现 Mermaid 解析/布局/渲染，未发布渲染包。** `0.0.1a0` 是本地骨架源码版本，不表示 PyPI 可用。

已建立：src 模块边界、固定 Canvas 依赖、上游源码锁/只读 checkout、spec 文件索引、完整图种与跨图能力清单、启动/实施/兼容/测试资料、bootstrap CI 和负控制、可运行 Canvas 依赖示例。

基线 Mermaid 12.2.0，commit `1fb7869866dd619168d840291c9c54b4f129758b`。源清单有 37 个 core detector + ZenUML 插件、368 个测试源文件、2,366 个渲染 fixture、38 个 grammar、34 篇 syntax 文档。**这些不是测试通过数**；[逐项状态](compatibility.json)中的 parser/layout/canvas 均 planned。

本批实际检查（Windows / CPython 3.13.15），由任务记录 [20261102-bootstrap.json](changes/20261102-bootstrap.json)登记命令、文件 SHA 和证据路径：

| 检查 | 实际范围 |
| --- | --- |
| bootstrap 与负控制 | 12 项测试，含图种遗漏、依赖 pin、伪通过/缺失证据、fixture 越界、坏链接、图片 provenance、来源 commit/dirty/hash 漂移 |
| upstream check | 精确提交、关键 canonical blob SHA、干净源码、2,806 个索引文件及全部 detector 与已保存索引一致 |
| Canvas GPU 依赖示例 | NVIDIA GeForce RTX 5080 / Vulkan；360×140 PNG、内部 RGBA/文字宽度/尺寸检查通过，图像已审阅 |
| Canvas CPU 依赖示例 | 公开 setter 显式 CPU；相同尺寸/内部像素/文字测量检查通过，图像已审阅 |
| 本地骨架 wheel | 已构建并装入独立新环境；仓库外 `-I`、PATH 未设置时 import、模块来源与包内文件核对通过，无产品 render 接口 |
| Canvas README 文档 | 双语生态入口、链接/代码/图片来源结构检查通过；保存起点并确认既有非 README 修改原样保留 |

候选骨架 `py_mermaid-0.0.1a0-py3-none-any.whl` SHA256 为 `8b48962da2adbf709715157bf288cbae7a38b07bd2e2d27c341b9678049cb507`，仅用于本地骨架打包检查，未上传。实际示例图见 [examples](../examples/README.md) 和 [provenance](assets/manifest.json)。

这些检查**没有通过任何 Mermaid spec**，也不构成 Canvas 全 API/native trace 验收。CPU 示例不证明无 Vulkan loader 部署。Linux 本批未执行，沿用的 Canvas 平台范围不等于本项目已通过双平台验收。

当前官方 JS oracle、逐断言 spec ledger、Python Mermaid 渲染和双平台发行验收均未完成。CI 配置已准备，远端 CI、commit/push、Release/PyPI 未在本任务执行。首次隔离 import 的测试探针因 PowerShell 删除空 PATH 而失败，已用新 run 修正探针并通过；原失败文件保留。

下一步：[TASKS](TASKS.md) 的 M1 用例/宿主审计、M2 官方对照工具和 M3 flowchart 垂直切片。Canvas 示例输出仅验证基础依赖，不能提升 Mermaid 兼容状态。

2026-11-02 迁移计划梳理：已补全 [实施方案](IMPLEMENTATION_PLAN.md)和 [逐项任务](TASKS.md)，明确默认 ELK、实际 detector 顺序、内联测试及更多布局/主题来源。当前源码和兼容状态未改变。本轮重新运行的 bootstrap/12 项负控制、上游校验与 Windows Canvas auto/CPU/GPU 冒烟证据见 [20261102-migration-plan.json](changes/20261102-migration-plan.json)；仍无 Mermaid spec、Linux/no-loader 或发行验收通过结论。

2026-11-02 组织迁移收尾：用户已将仓库迁入 [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)。本轮核实仓库 ID `1442682877`、默认分支 `main` 和提交与迁移前一致，当前账号仍有管理员权限；本地 `origin`、包元数据 URL、双语 README 和新会话入口已同步。证据见 [20261102-org-transfer.json](changes/20261102-org-transfer.json)。本地已有修改已备份保留，未执行 commit/push、组织权限变更或发布；Mermaid 兼容状态不变。
