> 2026-11-07 ?????????????????????132 ??????119 ??????255 ???866 ??? VChart 301?3/816 ?????105 ????????12???????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`????????????Linux real-TZ ? PyPI ??????????????????[????](docs/CLOSURE_BATCH_ACCEPTANCE.md)???? pending/??????????

> 2026-11-07 ??????? Event ???????132 ? portable ???5 ?????????????/??/??/???????? HTML/F01.3/??/B ????????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`?????????????132 ???119 ???13 parserOnly??255 ???866 ????? VChart??????????????????? Windows/Linux ????? Linux TZ?OIDC ? PyPI ??????????????????????????????

> 2026-11-07 当前：第二轮完整 P4 `CLOSURE-P4-batch-20261107T103937Z-ea2939c1` 已关闭，机器 SUCCESS、source/testTools unchanged，历史866与VChart DSL均通过；但补充原版/原生多行 JSON 原图证明 Event 数据框标题越框、严重误测，故该候选人工拒收，不发布。源独立实证进一步确认 SVG ASCII 空白折叠/trim、normal HTML 行盒与末尾br、code块左对齐/满宽、NBSP保留、字面\n/$$及全图entity transport先编码再substring/最终解码的顺序。相应Event源码、直接HTML provider和独立测试已统一应用；`CLOSURE-EVENT-HTML-P3-related-20261107T110330Z-53265a55` 正在执行，尚待相关及最终行为验收。当前待验收132新增方法（120+Event12）、132输入（119绘制/13 parserOnly）、255导出（17×3×5）。新源冻结后不额外扩审，所有既定门禁闭合才发布；最终P4不重复开发安装。正式clean一次构建的exact wheel/sdist须在同一workflow通过Windows/Linux双工件安装及Linux real-TZ验证，OIDC上传job须needs validate，随后核实际PyPI两工件SHA与安装回读。Publisher已配置，条件发布授权持续有效，无需再问。下方旧状态、原先错误前提及全部旧失败/拒收收据按历史保留。见[统一收口计划](docs/CLOSURE_BATCH_PLAN.md)。

> 2026-11-07 当前：旧最终 P4 `CLOSURE-P4-batch-20261107T101239Z-1852a0e5` 已关闭，机器 SUCCESS、source/testTools 均未变；但人工发现 Event Modeling 的 Place 被同 lane 的 Orders 遮挡，故该候选 **NEEDS_REPAIR，不用于最终验收或发布**。根因是原版按字面 SVG 文本测量包含 HTML 标签的内容，原生误按 HTML 测量；已应用来源独立提案中的专用字面测量、双字体选择和本地 wrap，以及独立原版夹具/验证。相关 Run `CLOSURE-EVENT-P3-related-20261107T103759Z-d4488fc8` 已启动，尚未完成行为验收。当前分母为127新增方法、130输入（117绘制/13 parserOnly），收口五格式225项（15×3×5）；这些是待验收分母，不是预先通过声明。后续最终 P4 全回归不重复开发安装；正式 clean wheel/sdist 一次构建后交 Windows/Linux CI，两个工件分别在仓库外独立安装，并通过 Linux real-TZ 门禁。门禁未通过不正式发布；Windows 看图与 aware-offset 控制不替代 Linux 实际时区验证。Publisher 已添加，既有条件发布授权有效，不再询问账户配置。全部旧 Run/旧状态和计数保持历史。见[统一收口计划](docs/CLOSURE_BATCH_PLAN.md)。

> 2026-11-07 当前：非 VChart 单批收口的相关修复已通过，最终同候选全量即将冻结。原22条分支、4项元数据/严格性、原未证边界及新增四项公开绘制接线均纳入；120新增合同方法、114绘制输入/13纯值输入、历史866输入和全部VChart DSL将统一验收。所有产品/测试/工具/资料在最终Run期间只读；旧失败证据保留。PyPI Pending Publisher已由用户确认添加，正式发行名py-visactor-mermaid，导入py_mermaid/CLI py-mermaid。最终P4、实际原图复核、分页报告、Windows/Linux同工件门禁通过后直接正式发布，无需再次请求发布授权。见[统一收口计划](docs/CLOSURE_BATCH_PLAN.md)。下方旧阶段状态仅作历史。

> 2026-11-07 用户已决定：四集合Venn、Treemap格式及VChart专属能力由py-vchart管理，py-mermaid本批不再处理。其余22分支/9簇及语义/未证项合并为[一个收口批次](docs/CLOSURE_BATCH_PLAN.md)，当前P1集中实现；随后统一来源测试/首跑批修/同候选全量/双平台发行验证。旧24条复查报告保留为历史，不因范围转交修改原证据。

> 2026-11-07 最后一次能力复查已完成：**仍有22条旧分支缺口及2项图表有效输入缺失，不发布正式包**。39入口/68类型接线存在，缺失集中于语法、日期、关系/绘制及Venn多集合/Treemap格式。另有4项发行门禁、7项未证记录；Windows当前候选已安装验证，Linux消费者与正式发布CI待补。见[复查与修复顺序](docs/FINAL_CAPABILITY_REVIEW.md)、[分页报告](http://127.0.0.1:8765/FINAL-CAPABILITY-P5-delivery-20261107T074816Z-a497e757/index.html)。本轮产品/测试只读，未提交推送或上传包；用户“无缺失再发布”的授权条件保留。下方有限范围验收不得解释为无缺口。

> 2026-11-07 最新交付：原生 VChart DSL v1 已实现并完成本地静态范围验收：68类型、2364测试、301案例×三后端、816额外导出、wheel/sdist正式PyPI依赖新环境通过。新增运行依赖为零。见[验收](docs/VCHART_DSL_ACCEPTANCE.md)与[第六轮分页报告](http://127.0.0.1:8765/VCHART-DSL-P5-delivery-20261107T072726Z-cd08a488/index.html)。供应方选项限制、有限字段审计及22旧分支缺口保留；未发布/提交/推送 py-mermaid。下方旧“设计未实现/执行中”均为历史。

> 2026-11-07 当前执行：用户已要求规划并实现VChart DSL完整功能，正在按[执行计划](docs/VCHART_DSL_EXECUTION_PLAN.md)开展P1集中源码接线；[模块合同](docs/VCHART_DSL_INTERFACES.md)。源码/设计不等于验证通过，随后统一P2/P3/P4及第六轮分页报告。68类型/225规格、正式PyPI依赖、既有静态排除与22旧分支缺口保留。

> 2026-11-07 当前设计：原生 `vchart <type>` DSL v1 已形成[完整规范](docs/VCHART_DSL_DESIGN.md)、[执行计划](docs/VCHART_DSL_EXECUTION_PLAN.md)与68类型/225原规格清单。状态仅为设计，解析器未实现；8组独立预期JSON已通过现有API预览，不冒称DSL运行。PyPI正式依赖和此前验收保持，未修改产品渲染源码。

> 2026-11-07 最新状态：py-visactor-vchart 0.1.1 已正式发布 PyPI 与 GitHub，py-mermaid 已使用 PyPI 固定版本依赖并通过两个全新环境的68类型/数学/ELK/SVG/PDF验证。[发布补证](docs/VCHART_PYPI_PUBLICATION.md)。渲染源码与此前2283方法/三后端/30实际看图候选一致；旧22条分支缺口、静态排除及Mermaid未整体提交/发布状态保留。下文PyPI blocked均为历史。




> 2026-11-06 第四轮分支核实已完成归类，**发现保留功能仍有缺口，产品尚未修复**：122 条有限记录、124 图例三后端、90 纯值、5 ABNF 探针、79 新方法；22 条确认功能缺口另列修复队列。当前入口：[核实结果](docs/BRANCH_VERIFICATION_RESULTS.md) · [分页结论](http://127.0.0.1:8765/BRANCH-VERIFY-P5-delivery-20261106T150821Z-81018151/index.html) · [原始A/B](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T150823Z-94db3ad3/index.html)。静态 HTML/CSS 扩展明确排除，旧“全部迁移完成”仅指当时限定用例；安装仍暂缓，未提交推送发布。

> 2026-11-06 最新用户决策：静态 HTML/CSS 扩展明确不支持、不列为待迁移；既有基础静态标签/控件保留。当前执行[第四轮分支覆盖核实](docs/BRANCH_COVERAGE_VERIFICATION.md)，生产源码只读，先核实并记录真实缺口；安装继续暂缓。下方 HTML/CSS“尚待扩展”仅作历史。

> 2026-11-06 第三轮 HTML 静态控件已完成本地验收：22 种 input 与 button/select/textarea/meter/progress/fieldset 等初始状态、排版和 Canvas 绘制；2046 测试、865 输入三后端、915 导出（含独立同候选导出修复补证）。[验收](docs/HTML_HOST_ACCEPTANCE.md) · [分轮报告](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/index.html)，第三轮 131 例 / 11 页。video/audio、交互和 Dagre 排除；7 图表后续 py-vchart，任意浏览器 HTML/CSS 不宣称完整；安装暂缓，本轮未提交推送发布。下方旧“控件未迁移”及旧候选状态仅作历史。

> 2026-11-06 报告展示已按轮次拆页：[分页总入口](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T110340Z-823e8bf0/index.html)。第二轮 64 例/6 页，第一轮 670 例/56 页，每页最多 12 例；更早 F01.1～F01.4/数学报告从首页进入。734 案例与 2746 PNG/685 SVG 原字节核对通过，原验收状态和历史报告不改写。此项仅重组报告，不是新渲染或新功能验收。

> 2026-11-06 最新用户范围：**video/audio 整体删除并排除**，包括播放、解码、封面/占位、控制条及初始静态外观，不再列为待迁移功能或验收项。保留现有明确拒绝与输入安全；普通图片/图标不受影响。下一轮仅保留已确认的 7 类 HTML 控件样例，见[docs/STATIC_HTML_HOST_PLAN](docs/STATIC_HTML_HOST_PLAN.md)。下方历史“音视频待迁移/9类”由本条覆盖，原报告不改写。

> 2026-11-06 功能分支补齐已完成本轮本地验收：1780方法、734输入×三后端、465导出、297历史正例×3；严格Zen扩大到186。当前入口 [GAP_AUDIT_ACCEPTANCE](docs/GAP_AUDIT_ACCEPTANCE.md)。**HTML控件/音视频初始静态外观仍未迁移**，9类已实际确认，见[下一模块](docs/STATIC_HTML_HOST_PLAN.md)。7类图表继续留给后续py-vchart；安装暂缓。本轮未提交推送发布，下方旧“全部完成”按其限定用例/历史范围理解。

> 2026-11-06 最新范围：7 个排除入口后续统一接入 py-vchart，本轮继续排除；31 个保留入口已完成本地静态验收并推送。下一轮先做[静态功能完整性复核](docs/NEXT_ITERATION.md)，不能用入口验收直接宣称全部功能分支覆盖，也不自动转为安装/发布任务。安装验证继续暂缓。

> 2026-11-06 用户现已明确授权提交并推送 py-mermaid 本批代码、测试、文档与来源记录。生成报告/日志留本地；保留精确文件字节以维持验收指纹。安装验证仍暂缓，不发布发行包。下方“未提交推送”是验收时历史状态，不阻止此次已授权操作。

> 2026-11-06 本批31入口（29新增+2流程图回归）已完成本地静态验收与HTML交付：1702测试、670输入×CPU/auto/GPU、465导出、297历史正例×3通过；原源7异常独立确认。当前入口 [BULK_STATIC_ACCEPTANCE](docs/BULK_STATIC_ACCEPTANCE.md)。7暂缓入口不计完成；安装验证暂缓，不提交推送发布。下方旧阶段/未实现/执行中状态按历史保留。

后续不自动恢复旧38全范围任务；只有用户明确纳入的暂缓图种才开启下一批。

> 2026-11-06 新联合P4候选冻结 `a6d05b852e156aac3227d839f1521f3e9a71a808ba8b701ad33b1443e993f2a0`，所有owner已停写；1166新增/共享方法、670fixture、148严格Zen结构与1597负控/后端。固定原版独立新采已完成且完整性PASS，P4显式核验输入/固定源身份后复用；Python单测/原生三后端/465导出/297历史图全部新跑。产品、测试、工具在本轮关闭前只读；31保留/7暂缓，安装验证继续暂缓。

> 2026-11-06 初次P4全量已关闭 FAILED/sourceUnchanged=true（`BULK-P4-final-20261106T053339Z-476daa06`），当前回到P3集中修复人工看图与旧验收资料问题。root+A/B/C写租约已开放，见execution-state；原候选及完整失败证据保留，绝不冒充最终通过。31保留/7暂缓，安装验证继续暂缓，不提交推送发布。

> 2026-11-06 当前 P4 联合候选全量验证，源码 SHA `51c9c8f75ec4518680450e985ac24e1e576850ae4522fe697d8725b1e23cf248`。P3 全部 owner 已停写，670 fixture（621 正常渲染、41 负例/诊断、7 已证上游缺陷、1 静态排除），执行期间产品/测试/工具只读。安装验证继续暂缓，不自动提交推送发布。

> 2026-11-06 P2 已冻结：1092 方法、656 fixture（617 render），当前 P3 全分组首跑。产品源码及测试/工具在 sweep 关闭前只读；保留全部失败后统一批修。入口 [P3](docs/P3_BULK_FIRST_SWEEP.md)，P1 候选仍为 `97b353ebf7e176a750a736a714c85638e0a497b722e451dc77570579a2d36cbb`。

> 2026-11-06 P1 已冻结 `97b353ebf7e176a750a736a714c85638e0a497b722e451dc77570579a2d36cbb`；当前 P2，root + 既有 A/B/C 三 worker 按 [测试设计合同](docs/P2_BULK_VERIFICATION.md)并行编写来源独立测试和对比工具。P2 不改产品、不执行产品行为。31 保留 / 7 暂缓，覆盖下方旧 P1 状态。

> 2026-11-06 用户已明确“继续推进”：恢复 P1 源码收口，执行本批 31 个入口（29 新增 + 2 流程图回归）；7 个暂缓入口保持不动。当前入口 [BULK_STATIC_EXECUTION](docs/BULK_STATIC_EXECUTION.md)，机器范围 [bulk-scope.json](references/bulk-scope.json)。以本条覆盖下面暂停说明；保留全部脏树与历史证据，不自动提交推送发布。

> 2026-11-06 最新范围：本批暂缓统计图表（pie/quadrantChart/xychart/radar）、矩形树图（treemap）、桑基图（sankey）、韦恩图（venn）共 7 个入口；保留 29 个新增入口 + 2 个流程图回归，共 31 个。现有成果保留，暂缓项不计完成、不纳入本批验收。用户暂停仍有效，目标 paused，所有 worker 停止；仅调整范围不代表恢复。见 [当前批次](docs/BULK_STATIC_EXECUTION.md)。下方旧 38 全范围/执行中说明以本条覆盖。

> 2026-11-06 当前用户要求一次批量完成全部静态迁移并继续执行：38 detector / 13 跨图能力，固定 Mermaid 12.2.0。当前 P1/in_progress，先收齐全部真实源码，再集中 P2 测试设计、P3 分组首跑与批修、P4 同候选全量、P5 HTML/日志交付。执行入口 [BULK_STATIC_EXECUTION](docs/BULK_STATIC_EXECUTION.md)，接口 [BULK_STATIC_INTERFACES](docs/BULK_STATIC_INTERFACES.md)。保留脏树，Dagre 与交互排除，不自动提交推送发布。下文旧数学专项/单图范围仅作历史。

> 2026-11-06 正式数学依赖接入已完成：`py-visactor-katex==0.1.0`，导入 `py_katex`。wheel/sdist 外部安装、当前开发解释器、22 项回归各两环境、8 图三后端及五格式通过。当前入口 [正式数学接入验收](docs/MATH_RELEASE_INTEGRATION.md)。本轮未提交/推送/发布 py-mermaid，下文旧状态为历史。

> 2026-11-06 当前任务：接入正式 `py-visactor-katex==0.1.0`（导入 `py_katex`）。本轮执行受影响的包构建、PyPI 依赖解析、仓库外安装和数学/静态导出验证；覆盖下方这部分安装暂缓说明，不扩展其它图种或触发 py-mermaid 发布。保留所有既有脏树和历史证据。

> 2026-11-06 **固定 KaTeX 0.18.11 核心静态迁移已完成本地验收**：973 方法、684 上下文、1909 功能输入/217 等价关系、275 案例三后端与 297 历史流程图三后端通过。当前入口为 [完整验收](docs/MATH_FULL_ACCEPTANCE.md)。安装验证暂缓，未提交推送发布；下方旧 alpha/未实现状态仅作历史。

> 2026-11-05 当前任务：一次完成剩余 KaTeX 核心静态迁移，见 [完整收口计划](https://github.com/py-VisActor/py-katex/blob/main/docs/FULL_STATIC_MIGRATION.md)。旧数学 alpha 报告是历史起点，安装验证仍暂缓。

> 2026-11-05 **独立 py-katex 原生静态 alpha 与 Mermaid 数学标签接入已完成本地验收**：712 个方法、69 个数学/集成案例 × 3 后端、297 个历史案例 × 3 后端通过。当前入口为 [数学验收](docs/MATH_ACCEPTANCE.md)；完整 KaTeX 兼容仍有明确未支持项。Dagre/交互排除，安装验证暂缓，当前修改未提交推送发布；下文旧“数学延后”及旧候选说明保留为历史。

> 2026-11-05 **F01.4 保留静态流程图已完成本地验收**：486 项测试、200 正例三后端矩阵及 F01.1～F01.3 回归通过，含五种导出与 HTML/人工 QA。[验收记录](docs/F01_4_ACCEPTANCE.md)。数学模块独立后续；Dagre 与交互已排除；安装验证继续暂缓。本轮未提交推送或发布。以下旧状态保留为历史。

> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](docs/LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](docs/STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

> 2026-11-05 **F01.3 已完成本地验收**：产品 279 项 + 工具 25 项通过；50 正例/8 语法负例/6 范围外诊断/1 上游缺陷在 CPU、auto、GPU 全通过。[验收记录](docs/F01_3_ACCEPTANCE.md)。F01.4/Dagre 暂停，安装验证继续暂缓，本轮未提交推送。下方旧状态保留为历史。

> 2026-11-05 当前仅执行 **F01.3**，按用户最新要求暂停 F01.4/Dagre，见 [本轮计划](docs/F01_3_EXECUTION_PLAN.md)。安装验证暂缓。下方旧目标仅作历史。

> 2026-11-04 **F01.2 已完成本地验收**：产品 150 项 + 工具 17 项通过；35 正例/8 语法负例/1 上游渲染缺陷在 CPU、auto、GPU 全通过。[验收记录](docs/F01_2_ACCEPTANCE.md)。安装验证暂缓，本轮未提交推送；后续 F01.3 尚未开始。下方执行中说明保留为历史。

> 2026-11-04 当前用户要求完成 **F01.2 流程图增强**。执行以 [F01_2_EXECUTION_PLAN.md](docs/F01_2_EXECUTION_PLAN.md) 和当前账本为准；F01.1已完成并提交，安装验证继续暂缓。以下旧范围/时序说明以本条覆盖。

> 2026-11-04 当前用户目标已收窄为 **F01.1 基础流程图**。本轮执行以 [F01_1_EXECUTION_PLAN.md](docs/F01_1_EXECUTION_PLAN.md) 为准：先完成本切片源码，再做本切片来源测试、修复和最终验收；全部图种迁移保留为后续规划。

# py-mermaid：AI 工作入口

## 日志与报告统一入口

执行命令和生成报告优先使用 `python tools/workflow.py`，规范见 [RUNS_AND_REPORTS](tools/RUNS_AND_REPORTS.md)。命令用record/batch保存独立run、原始stdout/stderr、真实退出码和指纹；已有证据用report，明确需要新A/B时才用render。不得把日志完整性、报告生成成功或像素diagnostic退出0当功能通过。历史证据不覆盖；安装验证按用户最新要求保持暂缓。当前报告服务的8765 URL保持可用，新服务用 `tools/serve_reports.py` 获取标准访问日志。

目标：将固定 Mermaid JS 保留范围内的语法、配置、布局和静态渲染行为移植到 Python，以 py-skia-canvas 为唯一生产渲染引擎。所有模块排除交互逻辑与交互元数据交付要求；完整来源索引保留，纯交互项标记 excluded_by_static_scope。

## 开始前

1. 完整读取 [NEW_SESSION](docs/NEW_SESSION.md)、[主执行方案](docs/FULL_MIGRATION_PLAN.md)、[接管指令](docs/EXECUTION_HANDOFF.md)与[任务清单](docs/TASKS.md)。旧 [M0…M8 资料](docs/IMPLEMENTATION_PLAN.md)仅作范围/来源参考，执行顺序不再使用。
2. 主协调读取 [模块边界](docs/MODULE_BOUNDARIES.md)、[并行规范](docs/PARALLEL_EXECUTION.md)、[来源验证](docs/SOURCE_BASED_VERIFICATION.md)、[兼容规则](docs/API_COMPATIBILITY.md)、[当前状态](docs/RELEASE_STATUS.md)；worker 按负责模块阅读对应资料。测试/发行与来源细节按 [TEST_AND_RELEASE](docs/TEST_AND_RELEASE.md)、[references](references/README.md)查阅，不在每次领取任务时重做全仓审计。
3. 检查 `git status --short`，保存用户已有修改；读取 [upstream.lock.json](references/upstream.lock.json) 和 [compatibility.json](docs/compatibility.json)。
4. 执行 bootstrap 与上游校验；资料检查成功不代表渲染通过。

## 当前用户确定的执行时序

P0 接管/来源阅读/接口边界 → **P1 一次集中完成全部图种与公共功能源码** → **P2 根据原实现设计测试与单元测试/oracle** → **P3 分组首次运行、统一归类根因与批修、相关复跑** → **P4 同候选最终全量** → P5 交付/发行。任务图见 [migration-execution.json](references/migration-execution.json)。

P1 不提前编写完整功能测试、不设置每图先测试通过的门禁；允许必要的编译/import/引用/签名/注册等机械集成检查，仅标 `code_complete_unverified`。基础流程图是第一条源码接线，不是停止点；其后继续全部 38 detector 和 13 跨图能力。公共模块随功能扩建，尽量并行，单文件唯一写 owner。P2/P3/P4 的实际验证不得由源码完成状态推定。

## 不可改变的约束

- 基线固定 mermaid@12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`。不跟随在线最新版，不修改来源哈希掩盖漂移；升级另开任务。
- 全部 detector、外部 ZenUML、配置/主题/资源/安全/错误/布局插件保留在分母。P0/P1 维护完整源码责任，P2 再正式细化 spec 用例/断言清单，不能把文件数当成覆盖率。
- 运行时不依赖 Node/npm、Playwright、浏览器、JS 解释器、skia-python 或 `.local`。开发 oracle 可以使用官方 Mermaid 和浏览器，不能作为 fallback。
- 只用公开 py-skia-canvas API，不复制其 Rust/Skia、字体 shaping、编码、Vulkan 或设备选择实现。布局移植属于本项目；Canvas 缺口在其仓库单独处理。
- 用户已明确采用 [Canvas 原生架构](docs/CANVAS_NATIVE_ARCHITECTURE.md)：抛弃 DOM/虚拟 DOM、D3 selection、浏览器排版/调度/截图等机制与依赖，以 Python 语义模型、样式、布局几何和绘制指令承接功能。上游依赖树仅用于溯源，不是逐库复刻清单；淘汰宿主机制不等于删去图种、计算、标签、安全或资源功能。
- 用户已明确 [功能一致、渲染不要求完全像素一致](docs/RENDER_CONSISTENCY.md)：跨 DOM/Canvas 以语义、实际绘制内容、几何关系/可读性和安全/导出为门禁；像素差/SSIM 仅作诊断。已解释的正常引擎差异可以通过，不因它们反复请示或追求零差异；漏内容、错关系、裁切/不可读不能据此放行。
- 保留默认 GPU/CPU 策略；CPU 检查不替代 GPU。所有 Canvas/Context/字体对象留在创建线程，跨线程传 bytes 或不可变语义数据。
- 不实现成功 stub、不返回白图、不用少数例子宣称整个图种完成。未支持项明确失败并在清单保留；不吞异常。
- 每个移植入口在 P1 记录上游路径、默认值、参数/单位、返回/异常、UTF-16 边界和线程/所有权，同步 source map；正式独立回归在 P2 设计/编写、P3 执行与修复，不用旧“同步回归”表述改变用户已定时序。
- 先保存修改前证据，再实现及比较。新证据写入新 `test-runs/<run-id>/`；保留失败，禁止覆盖、隐去像素差异、放宽标准或截图后处理。
- 同批更新相关资料与状态；P1 可写例子源码但不伪造运行图片，真实输出/图片在 P3/P4 生成和核查，候选内 README/许可/资源在 P3 收口，P5 核对交付。无影响主题说明具体理由。
- 代码/测试/工具/打包任务写 `docs/changes/<task-id>.json`，记录基线、起点脏树、验收、源文件 SHA、实际命令/退出码/证据 SHA、限制及下一步。更新后的源码不能冒用旧报告。
- 计划、实现、限定验证、发行验收和发布分开记录。当前没有渲染实现，不发布占位包。
- 保留用户修改；按当前用户授权执行 commit/push/发布，准备资料不自动授权这些外部操作。

普通实施选择可自主推进；改变兼容基线、默认行为、渲染引擎或降低验收要求时需用户决策。缺硬件/字体时记录未验收项并继续独立工作。
