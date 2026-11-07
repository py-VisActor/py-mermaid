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

> 2026-11-06 第三轮 HTML 静态控件已完成本地验收：22 种 input 与 button/select/textarea/meter/progress/fieldset 等初始状态、排版和 Canvas 绘制；2046 测试、865 输入三后端、915 导出（含独立同候选导出修复补证）。[验收](HTML_HOST_ACCEPTANCE.md) · [分轮报告](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/index.html)，第三轮 131 例 / 11 页。video/audio、交互和 Dagre 排除；7 图表后续 py-vchart，任意浏览器 HTML/CSS 不宣称完整；安装暂缓，本轮未提交推送发布。下方旧“控件未迁移”及旧候选状态仅作历史。

> 2026-11-06 本批31入口（29新增+2流程图回归）已完成本地静态验收与HTML交付：1702测试、670输入×CPU/auto/GPU、465导出、297历史正例×3通过；原源7异常独立确认。当前入口 [BULK_STATIC_ACCEPTANCE](BULK_STATIC_ACCEPTANCE.md)。7暂缓入口不计完成；安装验证暂缓，不提交推送发布。下方旧阶段/未实现/执行中状态按历史保留。

> 2026-11-06 **固定 KaTeX 0.18.11 核心静态迁移已完成本地验收**：973 方法、684 上下文、1909 功能输入/217 等价关系、275 案例三后端与 297 历史流程图三后端通过。当前入口为 [完整验收](MATH_FULL_ACCEPTANCE.md)。安装验证暂缓，未提交推送发布；下方旧 alpha/未实现状态仅作历史。

> 2026-11-05 **独立 py-katex 原生静态 alpha 与 Mermaid 数学标签接入已完成本地验收**：712 个方法、69 个数学/集成案例 × 3 后端、297 个历史案例 × 3 后端通过。当前入口为 [数学验收](MATH_ACCEPTANCE.md)；完整 KaTeX 兼容仍有明确未支持项。Dagre/交互排除，安装验证暂缓，当前修改未提交推送发布；下文旧“数学延后”及旧候选说明保留为历史。

> 2026-11-05 **F01.4 保留静态流程图已完成本地验收**：486 项测试、200 正例三后端矩阵及 F01.1～F01.3 回归通过，含五种导出与 HTML/人工 QA。[验收记录](F01_4_ACCEPTANCE.md)。数学模块独立后续；Dagre 与交互已排除；安装验证继续暂缓。本轮未提交推送或发布。以下旧状态保留为历史。

> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

> 2026-11-04 当前执行范围仅F01.1基础流程图，已实现接口见 [使用说明](F01_1_USAGE.md)，本地结果见 [验收记录](F01_1_ACCEPTANCE.md)。安装验证按用户最新要求暂缓，后续不继续或复跑。下方完整迁移范围和旧时序仅作后续规划/历史来源，当前以 [F01.1计划](F01_1_EXECUTION_PLAN.md) 为准。

# 执行任务清单：全部源码完成后再测试

执行顺序以 [完整方案](FULL_MIGRATION_PLAN.md)为准。任务定义来自 [机器任务图](../references/migration-execution.json)；当前全部 planned，产品源码尚未实现。旧 M0…M8 编号只作范围追踪。

`dependsOn` 是开工前置；`integrationNeeds` 是最终集成前置。4 槽采用主协调+3 worker，详见 [并行规范](PARALLEL_EXECUTION.md)。文件写入路径是执行期拟定范围，领取时必须落实唯一 owner。

P1 仅做源码/编译/import/接口接线机械检查；完整测试设计和单测在 P2，产品分组首次运行在 P3，最终全量在 P4。

## P0

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P0-01 | 接管脏树、来源身份与恢复点 | COORD | 无 | 无 |
| P0-02 | 功能/模块/路径和最小接口边界 | COORD | P0-01 | 无 |
| P0-03 | 目标依赖、Canvas/py-elk 接口与资源约束 | DEPENDENCIES | P0-01 | 无 |
| P0-GATE | 接管与边界门禁 | COORD | P0-02, P0-03 | 无 |

## P1

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P1-01 | 核心纯数据、单位、错误和协议 | CORE | P0-GATE | 无 |
| P1-02 | 完整配置/defaults/merge 与 JS 值适配 | CONFIG | P1-01 | 无 |
| P1-03 | 预处理/位置映射/检测与 parser 基础 | PARSER | P1-01 | P1-02, P1-05 |
| P1-04 | 完整纯几何、路径、相交、marker 和图基础 | GEOMETRY | P1-01 | 无 |
| P1-05 | 离线资源、安全、链接与 a11y 元数据 | RESOURCES | P1-01 | P1-02, P1-04 |
| P1-06 | 全部主题/look 和解析后样式 | STYLES | P1-01 | P1-02, P1-11 |
| P1-07 | 普通/多行标签与测量协议编排 | LABELS | P1-01 | P1-05, P1-06, P1-08 |
| P1-08 | 唯一 Canvas 后端/测量/所有导出/owner | CANVAS | P1-01 | P1-04, P1-05 |
| P1-09 | 完整 py-elk 适配、选项/端口/层级/路由 | ELK | P1-01 | P1-04, P1-07 |
| P1-11 | D3 所用数值/日期/颜色/尺度/树/空间算法 | NUMERICS | P1-01 | P1-04 |
| P1-12 | 两套 COSE、fCoSE、tidy 算法 | TREE-FORCE | P1-01 | P1-04, P1-11 |
| P1-13 | Sankey/Venn/swimlane 与专用布局 | SPECIAL-LAYOUT | P1-01 | P1-04, P1-11 |
| P1-14 | Markdown/富文本/HTML 含义的 Python 标签 | RICH-LABELS | P1-01 | P1-05, P1-06, P1-07, P1-08 |
| P1-15 | 数学语法/宏与数学 box 排版 | MATH | P1-01 | P1-04, P1-05, P1-07, P1-08 |
| P1-16 | Rough/手绘填充和随机流 | ROUGH | P1-04 | P1-06, P1-11 |
| P1-17 | runtime、API/CLI、注册/包和例子源码 | COORD | P1-01 | P1-02, P1-03, P1-05, P1-08 |
| P1-F01-SEED | 首写基础流程图源码接线 | FEATURE-F01 | P1-01, P1-03 | P1-02, P1-04, P1-06, P1-07, P1-08, P1-09 |
| P1-F01 | 流程图全部专用源码 | FEATURE-F01 | P1-01, P1-03, P1-F01-SEED | P1-02, P1-05, P1-06, P1-07, P1-08, P1-09, P1-14, P1-15, P1-16, P1-17 |
| P1-F02 | 关系与建模图全部专用源码 | FEATURE-F02 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-09, P1-14, P1-15, P1-17 |
| P1-F03 | 时序图全部专用源码 | FEATURE-F03 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-14, P1-15, P1-17 |
| P1-F04 | 时间与过程图全部专用源码 | FEATURE-F04 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-11, P1-14, P1-15, P1-17 |
| P1-F05 | 数值图表全部专用源码 | FEATURE-F05 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-11, P1-14, P1-15, P1-17 |
| P1-F06 | 树与层次图全部专用源码 | FEATURE-F06 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-11, P1-12, P1-14, P1-15, P1-17 |
| P1-F07 | 流量与集合图全部专用源码 | FEATURE-F07 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-13, P1-14, P1-15, P1-17 |
| P1-F08 | 结构与架构图全部专用源码 | FEATURE-F08 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-12, P1-14, P1-15, P1-17 |
| P1-F09 | 专用业务图全部专用源码 | FEATURE-F09 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-09, P1-13, P1-14, P1-15, P1-16, P1-17 |
| P1-F10 | 语法轨道图全部专用源码 | FEATURE-F10 | P1-01, P1-03 | P1-02, P1-04, P1-05, P1-06, P1-07, P1-08, P1-14, P1-15, P1-17 |
| P1-F11 | ZenUML 插件全部专用源码 | FEATURE-F11 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-14, P1-15, P1-17 |
| P1-F12 | 信息与诊断输出全部专用源码 | FEATURE-F12 | P1-01, P1-03 | P1-02, P1-05, P1-06, P1-07, P1-08, P1-14, P1-15, P1-17 |
| P1-INTEGRATE | 全部公共能力与 38 入口源码收口 | COORD | P1-01, P1-02, P1-03, P1-04, P1-05, P1-06, P1-07, P1-08, P1-09, P1-11, P1-12, P1-13, P1-14, P1-15, P1-16, P1-17, P1-F01-SEED, P1-F01, P1-F02, P1-F03, P1-F04, P1-F05, P1-F06, P1-F07, P1-F08, P1-F09, P1-F10, P1-F11, P1-F12 | 无 |
| P1-GATE | 全部源码齐备且未验证门禁 | COORD | P1-INTEGRATE | 无 |

## P2

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P2-V01 | 全部来源与断言清单 | QA-SOURCE | P1-GATE | 无 |
| P2-V02 | 官方/候选环境和共享输入协议 | QA-ENV | P1-GATE | 无 |
| P2-V03 | 官方 A 采集工具 | QA-ORACLE | P1-GATE, P2-V02 | 无 |
| P2-V04 | 隔离 Python B runner | QA-RUNNER | P1-GATE, P2-V02 | 无 |
| P2-V05 | 分层比较器和原始差异报告 | QA-COMPARE | P1-GATE, P2-V02 | 无 |
| P2-V06 | 比较器/清单负控制 | QA-CONTROL | P1-GATE, P2-V01, P2-V05 | 无 |
| P2-U01 | 配置/语法/模型/全部图种单元用例 | QA-LANGUAGE | P1-GATE, P2-V01 | 无 |
| P2-U02 | 数值/几何/布局单元用例 | QA-ALGORITHMS | P1-GATE, P2-V01 | 无 |
| P2-U03 | 标签/样式/资源/安全单元用例 | QA-PRESENTATION | P1-GATE, P2-V01 | 无 |
| P2-U04 | 绘制/图种组合/导出/生命周期/部署用例 | QA-RUNTIME | P1-GATE, P2-V01, P2-V02 | 无 |
| P2-V07 | 分组/影响集运行器与完整测试归属收口 | COORD | P2-V01, P2-V02, P2-V03, P2-V04, P2-V05, P2-V06, P2-U01, P2-U02, P2-U03, P2-U04 | 无 |
| P2-GATE | 测试设计/单测/工具齐备门禁 | COORD | P2-V07 | 无 |

## P3

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P3-01 | 模块/图种分组首轮运行并冻结失败 | QA-GROUPS | P2-GATE | 无 |
| P3-02 | 统一根因归类和修复优先级 | COORD | P3-01 | 无 |
| P3-03 | 公共根因批修与相关复测 | SHARED-OWNERS | P3-02 | 无 |
| P3-04 | 图种/资源/平台原因批修 | FEATURE-OWNERS | P3-02 | P3-03 |
| P3-05 | 整合修复、准备候选和相关回归收口 | COORD | P3-03, P3-04 | 无 |
| P3-GATE | 功能排查修复闭环门禁 | COORD | P3-05 | 无 |

## P4

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P4-01 | 冻结最终源码/依赖/资源和同一 wheel | COORD | P3-GATE | 无 |
| P4-02 | 全断言/配置/算法完整矩阵 | QA-FULL-LOGIC | P4-01 | 无 |
| P4-03 | 视觉/字体/设备/格式完整矩阵 | QA-FULL-VISUAL | P4-01 | 无 |
| P4-04 | 双平台/部署/安全/生命周期完整矩阵 | QA-FULL-DEPLOY | P4-01 | 无 |
| P4-GATE | 同候选最终全量门禁 | COORD | P4-02, P4-03, P4-04 | 无 |

## P5

| 任务 | 源码/工具/验收工作 | 角色 | 开工前置 | 最终集成前置 |
| --- | --- | --- | --- | --- |
| P5-01 | 核对交接文档/真实例子/候选发行条件 | COORD | P4-GATE | 无 |
| P5-02 | 按实际授权 commit/push/CI/发布/回读 | COORD | P5-01 | 无 |

## 源码与验证状态

图种作者交付完整源码只能标 code_complete_unverified；provider 未齐时保留 awaiting_provider。P1 总门禁要求全部真实 provider 和接线完成；不允许 stub/白图/硬编码坐标/吞异常冒称完成。P2 测试写好不要求产品全绿，P3 接收和归类实际失败后统一修改，P4 对同一最终候选完整验证。

细节见 [模块边界](MODULE_BOUNDARIES.md)、[来源测试方案](SOURCE_BASED_VERIFICATION.md)和 [直接接管指令](EXECUTION_HANDOFF.md)。历史 M1/M2 的来源阅读与接口契约仍服务 P1，实现以外的正式 case/assertion/单测/oracle 工作后置到 P2。
