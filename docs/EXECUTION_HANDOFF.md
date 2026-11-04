> 2026-11-04 当前用户目标已收窄为 **F01.1 基础流程图**。本轮执行以 [F01_1_EXECUTION_PLAN.md](F01_1_EXECUTION_PLAN.md) 为准：先完成本切片源码，再做本切片来源测试、修复和最终验收；全部图种迁移保留为后续规划。

# 给新执行会话的完整交接指令

2026-11-04。当前仓库实际位置为 `C:/code/py-visactor/py-mermaid`，远端 [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)。旧的 `C:/code/py-mermaid` 不存在；迁移到其他机器时以实际仓库根目录为准。**以下是待执行任务，不是已经实现的能力。**

## 1. 当前事实

- Python 源码版本为 `0.0.1a0`，只有版本接口与职责目录，没有 Mermaid parser/layout/render/CLI 产品实现，尚无可用 Mermaid 渲染包。
- 已有固定上游锁、2,806 文件索引、全部 38 detector/13 跨图能力清单、完整上游依赖图、Canvas 原生架构、公共模块/并行/验证计划。
- `py-skia-canvas==0.1.0a18` 已是声明依赖；独立 py-elk 已发布 `py-visactor-elk 0.1.0`，本仓库尚未添加或完成集成。使用既有 py-elk，不回退版本、不重新移植 ELK。
- 当前有多轮本地未提交文档/工具/清单修改。先保存工作树及文件指纹，不执行 reset/clean，不把本地方案当远端已经存在。历史记录在 `docs/changes/`，原始本地证据在 `test-runs/`。
- 最新执行要求是 **全部功能源码先完成，再按原实现设计测试/单测，再统一排查修复，最后全量验证**。旧 M1/M2 或旧 F01.1 文档中的先测门禁已经被新方案替代。

## 2. 必须执行的顺序

渲染标准已确定为 [功能一致、不要求跨 DOM/Canvas 像素一致](RENDER_CONSISTENCY.md)：核对语义、实际内容、几何关系/可读性和安全导出，图片指标仅诊断。正常字体/抗锯齿/自然尺寸/合法路由差异可通过，漏内容、错箭头/关系、裁切不可通过。

独立 [PNG 像素对比工具](../tools/PIXEL_COMPARE.md)已按用户本轮要求提前提供，可复用作 P2-V05 的 L4 基础；P2 正式 Mermaid 用例/语义比较和 P3 产品运行仍后置。默认 diagnostic 的退出码 0 只表示完成分析，不表示功能通过。

1. P0：接管脏树、核来源、固定模块接口和文件 owner；不提前拆完整单测/断言。
2. P1：持续并行完成全部公共模块和 F01…F12 全功能源码；先写基础流程图接线，再继续所有图种，公共模块随新功能扩建。只做编译/import/签名/注册等机械检查，状态仅 `code_complete_unverified`。
3. P2：全源码收口后，按固定原实现设计完整 case/assertion、单元和功能测试；编写官方 oracle、Python runner、比较器与负控制。
4. P3：分组首次运行，记录并去重失败；优先修公共根因，再修图种；只回跑变更和受影响范围。
5. P4：冻结同一最终候选，统一完整功能/平台/设备/字体/资源/安全/导出/生命周期/部署矩阵；失败回 P3，保留旧报告后对新候选再全量。
6. P5：核对真实文档/例子/包与证据，按实际授权交付或发布。候选内 README/许可/资源/示例必须在 P3 收口，P5 改变候选字节就需回 P4；不以仅完成代码就发布。

## 3. 接管后现在就做什么

在仓库根目录使用独立 CPython 3.13 环境。以下命令已经存在，只检查资料和计划，不运行 Mermaid 产品功能：

```shell
git status --short
python scripts/validate_bootstrap.py
python scripts/upstream.py check
python scripts/audit_dependencies.py --check
python scripts/build_dependency_tree.py --check
python scripts/validate_migration_plan.py --check
```

上游 checkout 不存在时才按现有 `python scripts/upstream.py fetch` 创建并校验；已有 checkout 不重置、不覆盖。不要为准备阶段重编 Skia/Node 或反复采集图片。执行所需 Canvas/py-elk 与候选依赖在独立环境按来源和实际 pin 安装，不能隐式引入 JS wrapper 或另一 native renderer。

创建执行账本 `docs/execution-state.json`（拟建），引用 [机器任务图](../references/migration-execution.json)的固定 ID；记录阶段、任务状态、接口版本、agent/角色、路径租约、来源/变更 SHA、机械检查/验证证据、未完成能力、下一个 ready task。不要把源码阶段的新状态塞进未扩展 schema 的 `compatibility.json`。

可复制 [执行账本模板](../references/execution-state.template.json)，创建后填写实际起点、owner 与状态。模板包含全部任务、38 个 detector、13 跨图项和 8 公共责任；它本身不是已执行记录。一个族内可拆 detector 子任务，只有全部子项真实写完并接线后才关闭父任务。

第一轮默认 4 个并发槽：

| 槽位 | 初始任务 | 第一批产物 |
| --- | --- | --- |
| 主协调 | P0-01/02，维护状态和文件租约，准备 P1-01 核心协议 | 起点、完整分母、接口 v1、ready 队列 |
| worker A | 阅读 parser/config 源码契约，接 P1-02/03 | 共享前处理/配置/位置与 parser 基础的源码分片 |
| worker B | 读取几何/布局接口与既有 py-elk，接 P1-04/09 | 纯几何和真实 ELK 适配源码分片 |
| worker C | 读取 Canvas 公开接口与绘制/测量合同，接 P1-08/07 | 唯一 Canvas adapter 与标签测量源码分片 |

P1 任务开工严格遵守机器图 `dependsOn`；P0 读取/边界工作可并行，协议冻结前不抢写尚未分配的公共文件。接口可用后，立即从 ready 队列分发独立图种源码，不让所有 worker 等待完整 flowchart 或测试。ZenUML grammar/model 风险较高，可按合同尽早安排独立分片；其他槽持续推进公共模块和图种。

角色是逻辑责任，不要求同时启动几十个 agent。4 槽时反复复用 3 个 worker，更多槽仅扩大独立目录分片。同一公共文件只有一个写 owner；公共接口扩展用请求单交给 owner，消费者继续写自身不冲突部分。主协调统一总注册器、API/CLI、包元数据和最终集成。

## 4. 继续工作而不误停

P1 的源码任务可以依据上游实现/spec 理解规则，但不提前写完整测试套件或以先跑图种单测作为继续编码的前提。未知行为写入待 P2 验证记录；实际缺失实现仍须在 P1 门禁前补齐，不使用 stub/白图/固定坐标/无条件 fallback。

布局、标签、公共算法未齐时，只暂停真正依赖它们的集成，继续可独立编写的 grammar/model/数值或其他图种。记录 `awaiting_provider` 并释放 worker 槽，禁止反复安装、反复全仓阅读或重复全量检查来等待。

会话上下文不足或结束前，写清：最后完成任务、仍有缺口的源码/接口、全部活跃 owner、未集成 provider、当前源树与产物指纹、下一 ready task、未完成环境项。下个会话从该账本恢复，不从头重复准备或把同一个功能重新拆一遍。

普通内部实现和可逆本地工作自主推进。兼容基线/默认行为/Canvas 边界和最终验收标准不能擅改；遇到真实不可等价项先提供具体材料，同时继续独立工作。commit/push/发布依实际授权，规划交接本身不构成已发布事实。

## 5. 可直接复制的新会话提示

```text
进入 C:/code/py-visactor/py-mermaid，执行完整 Mermaid-to-Python 迁移，不只做首个 flowchart。
先读 AGENTS.md、docs/NEW_SESSION.md、docs/FULL_MIGRATION_PLAN.md、docs/EXECUTION_HANDOFF.md，
然后按角色读 MODULE_BOUNDARIES、PARALLEL_EXECUTION、SOURCE_BASED_VERIFICATION。
机器任务来源为 references/migration-execution.json；已有所有本地修改必须保留并保存起点。
基线固定 Mermaid12.2.0/1fb7869866dd619168d840291c9c54b4f129758b；Canvas0.1.0a18。
默认 ELK 复用独立 py-visactor-elk，不回退、不重写既有ELK。
完全使用 py-skia-canvas 公开API做测量/绘制/编码；丢弃DOM/虚拟DOM/D3 selection/fastdom/React浏览器层。
生产不用Node/browser/JS/skia-python/.local；保留所用语义、配置、数值布局算法、标签内容和安全资源功能。
顺序严格为：P0接管/边界 → P1全部功能源码 → P2根据原实现设计测试与单元测试/oracle →
P3分组首次运行、统一归类根因、集中修复并相关复跑 → P4同候选最终全量 → P5交付发行。
P1只做编译/import/签名/引用/注册等机械检查，不提前写功能测试或用逐图测试通过阻塞其他源码。
P1源码完成仅标code_complete_unverified；provider未齐标awaiting_provider，不造stub/白图/固定坐标。
4槽采用主协调+3worker，按ready队列尽量并行；单文件唯一owner，公共模块随图种需求增量扩建。
先完成基础流程图源码接线，之后继续全部F01…F12、38detector及13跨图能力；不要在首图结束任务。
建立docs/execution-state.json，固定任务ID，记录owner/路径/接口/source-map/未实现点/证据/下一任务。
每批复盘等待与公共需求并改进调度；不要反复全量测试或重做已经完成的资料审计。
P2测试期望依据原实现而非新代码自证；P3修公共根因，P4完整矩阵保留全部原始差异和未验项。
渲染要求功能/内容/关系/可读性一致，跨DOM/Canvas不要求完全像素或绝对坐标一致；图片指标只诊断，正常引擎差异可通过。
实际授权、commit/push/远端CI/发布/下载核验分别记录，不把源码齐备或计划完成当兼容/发行成功。
现在从P0-01/P0-02/P0-03开始，完成必要接管后马上分派P1源码任务，持续推进到完整目标。
```
