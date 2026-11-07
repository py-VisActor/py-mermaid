> 2026-11-07 ?????????????????????132 ??????119 ??????255 ???866 ??? VChart 301?3/816 ?????105 ????????12???????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`????????????Linux real-TZ ? PyPI ??????????????????[????](CLOSURE_BATCH_ACCEPTANCE.md)???? pending/??????????

> 2026-11-07 ??????? Event ???????132 ? portable ???5 ?????????????/??/??/???????? HTML/F01.3/??/B ????????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`?????????????132 ???119 ???13 parserOnly??255 ???866 ????? VChart??????????????????? Windows/Linux ????? Linux TZ?OIDC ? PyPI ??????????????????????????????

> 2026-11-07 当前：第二轮完整 P4 `CLOSURE-P4-batch-20261107T103937Z-ea2939c1` 已关闭，机器 SUCCESS、source/testTools unchanged，历史866与VChart DSL均通过；但补充原版/原生多行 JSON 原图证明 Event 数据框标题越框、严重误测，故该候选人工拒收，不发布。源独立实证进一步确认 SVG ASCII 空白折叠/trim、normal HTML 行盒与末尾br、code块左对齐/满宽、NBSP保留、字面\n/$$及全图entity transport先编码再substring/最终解码的顺序。相应Event源码、直接HTML provider和独立测试已统一应用；`CLOSURE-EVENT-HTML-P3-related-20261107T110330Z-53265a55` 正在执行，尚待相关及最终行为验收。当前待验收132新增方法（120+Event12）、132输入（119绘制/13 parserOnly）、255导出（17×3×5）。新源冻结后不额外扩审，所有既定门禁闭合才发布；最终P4不重复开发安装。正式clean一次构建的exact wheel/sdist须在同一workflow通过Windows/Linux双工件安装及Linux real-TZ验证，OIDC上传job须needs validate，随后核实际PyPI两工件SHA与安装回读。Publisher已配置，条件发布授权持续有效，无需再问。下方旧状态、原先错误前提及全部旧失败/拒收收据按历史保留。见[统一收口计划](CLOSURE_BATCH_PLAN.md)。

> 2026-11-07 当前：旧最终 P4 `CLOSURE-P4-batch-20261107T101239Z-1852a0e5` 已关闭，机器 SUCCESS、source/testTools 均未变；但人工发现 Event Modeling 的 Place 被同 lane 的 Orders 遮挡，故该候选 **NEEDS_REPAIR，不用于最终验收或发布**。根因是原版按字面 SVG 文本测量包含 HTML 标签的内容，原生误按 HTML 测量；已应用来源独立提案中的专用字面测量、双字体选择和本地 wrap，以及独立原版夹具/验证。相关 Run `CLOSURE-EVENT-P3-related-20261107T103759Z-d4488fc8` 已启动，尚未完成行为验收。当前分母为127新增方法、130输入（117绘制/13 parserOnly），收口五格式225项（15×3×5）；这些是待验收分母，不是预先通过声明。后续最终 P4 全回归不重复开发安装；正式 clean wheel/sdist 一次构建后交 Windows/Linux CI，两个工件分别在仓库外独立安装，并通过 Linux real-TZ 门禁。门禁未通过不正式发布；Windows 看图与 aware-offset 控制不替代 Linux 实际时区验证。Publisher 已添加，既有条件发布授权有效，不再询问账户配置。全部旧 Run/旧状态和计数保持历史。见[统一收口计划](CLOSURE_BATCH_PLAN.md)。

> 2026-11-07 当前：非 VChart 单批收口的相关修复已通过，最终同候选全量即将冻结。原22条分支、4项元数据/严格性、原未证边界及新增四项公开绘制接线均纳入；120新增合同方法、114绘制输入/13纯值输入、历史866输入和全部VChart DSL将统一验收。所有产品/测试/工具/资料在最终Run期间只读；旧失败证据保留。PyPI Pending Publisher已由用户确认添加，正式发行名py-visactor-mermaid，导入py_mermaid/CLI py-mermaid。最终P4、实际原图复核、分页报告、Windows/Linux同工件门禁通过后直接正式发布，无需再次请求发布授权。见[统一收口计划](CLOSURE_BATCH_PLAN.md)。下方旧阶段状态仅作历史。

> 2026-11-07 用户已决定：四集合Venn、Treemap格式及VChart专属能力由py-vchart管理，py-mermaid本批不再处理。其余22分支/9簇及语义/未证项合并为[一个收口批次](CLOSURE_BATCH_PLAN.md)，当前P1集中实现；随后统一来源测试/首跑批修/同候选全量/双平台发行验证。旧24条复查报告保留为历史，不因范围转交修改原证据。

> 2026-11-07 最后一次能力复查已完成：**仍有22条旧分支缺口及2项图表有效输入缺失，不发布正式包**。39入口/68类型接线存在，缺失集中于语法、日期、关系/绘制及Venn多集合/Treemap格式。另有4项发行门禁、7项未证记录；Windows当前候选已安装验证，Linux消费者与正式发布CI待补。见[复查与修复顺序](FINAL_CAPABILITY_REVIEW.md)、[分页报告](http://127.0.0.1:8765/FINAL-CAPABILITY-P5-delivery-20261107T074816Z-a497e757/index.html)。本轮产品/测试只读，未提交推送或上传包；用户“无缺失再发布”的授权条件保留。下方有限范围验收不得解释为无缺口。

> 2026-11-07 最新交付：原生 VChart DSL v1 已实现并完成本地静态范围验收：68类型、2364测试、301案例×三后端、816额外导出、wheel/sdist正式PyPI依赖新环境通过。新增运行依赖为零。见[验收](VCHART_DSL_ACCEPTANCE.md)与[第六轮分页报告](http://127.0.0.1:8765/VCHART-DSL-P5-delivery-20261107T072726Z-cd08a488/index.html)。供应方选项限制、有限字段审计及22旧分支缺口保留；未发布/提交/推送 py-mermaid。下方旧“设计未实现/执行中”均为历史。

> 2026-11-07 当前执行：用户已要求规划并实现VChart DSL完整功能，正在按[执行计划](VCHART_DSL_EXECUTION_PLAN.md)开展P1集中源码接线；[模块合同](VCHART_DSL_INTERFACES.md)。源码/设计不等于验证通过，随后统一P2/P3/P4及第六轮分页报告。68类型/225规格、正式PyPI依赖、既有静态排除与22旧分支缺口保留。

> 2026-11-07 当前设计：原生 `vchart <type>` DSL v1 已形成[完整规范](VCHART_DSL_DESIGN.md)、[执行计划](VCHART_DSL_EXECUTION_PLAN.md)与68类型/225原规格清单。状态仅为设计，解析器未实现；8组独立预期JSON已通过现有API预览，不冒称DSL运行。PyPI正式依赖和此前验收保持，未修改产品渲染源码。

> 2026-11-07 最新状态：py-visactor-vchart 0.1.1 已正式发布 PyPI 与 GitHub，py-mermaid 已使用 PyPI 固定版本依赖并通过两个全新环境的68类型/数学/ELK/SVG/PDF验证。[发布补证](VCHART_PYPI_PUBLICATION.md)。渲染源码与此前2283方法/三后端/30实际看图候选一致；旧22条分支缺口、静态排除及Mermaid未整体提交/发布状态保留。下文PyPI blocked均为历史。




> 2026-11-06 第四轮分支核实已完成归类，**发现保留功能仍有缺口，产品尚未修复**：122 条有限记录、124 图例三后端、90 纯值、5 ABNF 探针、79 新方法；22 条确认功能缺口另列修复队列。当前入口：[核实结果](BRANCH_VERIFICATION_RESULTS.md) · [分页结论](http://127.0.0.1:8765/BRANCH-VERIFY-P5-delivery-20261106T150821Z-81018151/index.html) · [原始A/B](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T150823Z-94db3ad3/index.html)。静态 HTML/CSS 扩展明确排除，旧“全部迁移完成”仅指当时限定用例；安装仍暂缓，未提交推送发布。

> 2026-11-06 最新用户决策：静态 HTML/CSS 扩展明确不支持、不列为待迁移；既有基础静态标签/控件保留。当前执行[第四轮分支覆盖核实](BRANCH_COVERAGE_VERIFICATION.md)，生产源码只读，先核实并记录真实缺口；安装继续暂缓。下方 HTML/CSS“尚待扩展”仅作历史。

> 2026-11-06 第三轮 HTML 静态控件已完成本地验收：22 种 input 与 button/select/textarea/meter/progress/fieldset 等初始状态、排版和 Canvas 绘制；2046 测试、865 输入三后端、915 导出（含独立同候选导出修复补证）。[验收](HTML_HOST_ACCEPTANCE.md) · [分轮报告](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/index.html)，第三轮 131 例 / 11 页。video/audio、交互和 Dagre 排除；7 图表后续 py-vchart，任意浏览器 HTML/CSS 不宣称完整；安装暂缓，本轮未提交推送发布。下方旧“控件未迁移”及旧候选状态仅作历史。

> 2026-11-06 报告展示已按轮次拆页：[分页总入口](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T110340Z-823e8bf0/index.html)。第二轮 64 例/6 页，第一轮 670 例/56 页，每页最多 12 例；更早 F01.1～F01.4/数学报告从首页进入。734 案例与 2746 PNG/685 SVG 原字节核对通过，原验收状态和历史报告不改写。此项仅重组报告，不是新渲染或新功能验收。

> 2026-11-06 最新用户范围：**video/audio 整体删除并排除**，包括播放、解码、封面/占位、控制条及初始静态外观，不再列为待迁移功能或验收项。保留现有明确拒绝与输入安全；普通图片/图标不受影响。下一轮仅保留已确认的 7 类 HTML 控件样例，见[STATIC_HTML_HOST_PLAN](STATIC_HTML_HOST_PLAN.md)。下方历史“音视频待迁移/9类”由本条覆盖，原报告不改写。

> 2026-11-06 功能分支补齐已完成本轮本地验收：1780方法、734输入×三后端、465导出、297历史正例×3；严格Zen扩大到186。当前入口 [GAP_AUDIT_ACCEPTANCE](GAP_AUDIT_ACCEPTANCE.md)。**HTML控件/音视频初始静态外观仍未迁移**，9类已实际确认，见[下一模块](STATIC_HTML_HOST_PLAN.md)。7类图表继续留给后续py-vchart；安装暂缓。本轮未提交推送发布，下方旧“全部完成”按其限定用例/历史范围理解。

> 2026-11-06 本批31入口（29新增+2流程图回归）已完成本地静态验收与HTML交付：1702测试、670输入×CPU/auto/GPU、465导出、297历史正例×3通过；原源7异常独立确认。当前入口 [BULK_STATIC_ACCEPTANCE](BULK_STATIC_ACCEPTANCE.md)。7暂缓入口不计完成；安装验证暂缓，不提交推送发布。下方旧阶段/未实现/执行中状态按历史保留。

> 2026-11-06 已接入正式 `py-visactor-katex==0.1.0`，导入 `py_katex`；wheel/sdist 仓库外安装、22 项既有回归各两环境、8 集成图三后端和五格式均通过。当前入口为 [正式数学接入验收](MATH_RELEASE_INTEGRATION.md)。本轮受影响安装验证已完成，下文旧“相邻源码/数学未发布/安装暂缓”按历史保留；未发布 py-mermaid。

> 2026-11-06 **固定 KaTeX 0.18.11 核心静态迁移已完成本地验收**：973 方法、684 上下文、1909 功能输入/217 等价关系、275 案例三后端与 297 历史流程图三后端通过。当前入口为 [完整验收](MATH_FULL_ACCEPTANCE.md)。安装验证暂缓，未提交推送发布；下方旧 alpha/未实现状态仅作历史。

> 2026-11-05 当前任务：一次完成剩余 KaTeX 核心静态迁移，见 [完整收口计划](../../py-katex/docs/FULL_STATIC_MIGRATION.md)。旧数学 alpha 报告是历史起点，安装验证仍暂缓。

> 2026-11-05 **独立 py-katex 原生静态 alpha 与 Mermaid 数学标签接入已完成本地验收**：712 个方法、69 个数学/集成案例 × 3 后端、297 个历史案例 × 3 后端通过。当前入口为 [数学验收](MATH_ACCEPTANCE.md)；完整 KaTeX 兼容仍有明确未支持项。Dagre/交互排除，安装验证暂缓，当前修改未提交推送发布；下文旧“数学延后”及旧候选说明保留为历史。

> 2026-11-05 **F01.4 保留静态流程图已完成本地验收**：486 项测试、200 正例三后端矩阵及 F01.1～F01.3 回归通过，含五种导出与 HTML/人工 QA。[验收记录](F01_4_ACCEPTANCE.md)。数学模块独立后续；Dagre 与交互已排除；安装验证继续暂缓。本轮未提交推送或发布。以下旧状态保留为历史。

> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

> 2026-11-05 **F01.3 已完成本地验收**：产品 279 项 + 工具 25 项通过；50 正例/8 语法负例/6 范围外诊断/1 上游缺陷在 CPU、auto、GPU 全通过。[验收记录](F01_3_ACCEPTANCE.md)。F01.4/Dagre 暂停，安装验证继续暂缓，本轮未提交推送。下方旧状态保留为历史。

> 2026-11-05 当前仅执行 **F01.3**，按用户最新要求暂停 F01.4/Dagre，见 [本轮计划](F01_3_EXECUTION_PLAN.md)。安装验证暂缓。下方旧目标仅作历史。

> 2026-11-04 **F01.2 已完成本地验收**：产品 150 项 + 工具 17 项通过；35 正例/8 语法负例/1 上游渲染缺陷在 CPU、auto、GPU 全通过。[验收记录](F01_2_ACCEPTANCE.md)。安装验证暂缓，本轮未提交推送；后续 F01.3 尚未开始。下方执行中说明保留为历史。

> 2026-11-04 当前用户要求完成 **F01.2 流程图增强**。执行以 [F01_2_EXECUTION_PLAN.md](F01_2_EXECUTION_PLAN.md) 和当前账本为准；F01.1已完成并提交，安装验证继续暂缓。以下旧范围/时序说明以本条覆盖。

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
