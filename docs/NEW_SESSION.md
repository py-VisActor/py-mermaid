> 2026-11-06 本批31入口（29新增+2流程图回归）已完成本地静态验收与HTML交付：1702测试、670输入×CPU/auto/GPU、465导出、297历史正例×3通过；原源7异常独立确认。当前入口 [BULK_STATIC_ACCEPTANCE](BULK_STATIC_ACCEPTANCE.md)。7暂缓入口不计完成；安装验证暂缓，不提交推送发布。下方旧阶段/未实现/执行中状态按历史保留。

> 2026-11-06 已接入正式 `py-visactor-katex==0.1.0`，导入 `py_katex`；wheel/sdist 仓库外安装、22 项既有回归各两环境、8 集成图三后端和五格式均通过。当前入口为 [正式数学接入验收](MATH_RELEASE_INTEGRATION.md)。本轮受影响安装验证已完成，下文旧“相邻源码/数学未发布/安装暂缓”按历史保留；未发布 py-mermaid。

> 2026-11-06 **固定 KaTeX 0.18.11 核心静态迁移已完成本地验收**：973 方法、684 上下文、1909 功能输入/217 等价关系、275 案例三后端与 297 历史流程图三后端通过。当前入口为 [完整验收](MATH_FULL_ACCEPTANCE.md)。安装验证暂缓，未提交推送发布；下方旧 alpha/未实现状态仅作历史。

> 2026-11-05 **独立 py-katex 原生静态 alpha 与 Mermaid 数学标签接入已完成本地验收**：712 个方法、69 个数学/集成案例 × 3 后端、297 个历史案例 × 3 后端通过。当前入口为 [数学验收](MATH_ACCEPTANCE.md)；完整 KaTeX 兼容仍有明确未支持项。Dagre/交互排除，安装验证暂缓，当前修改未提交推送发布；下文旧“数学延后”及旧候选说明保留为历史。

> 2026-11-05 **F01.4 保留静态流程图已完成本地验收**：486 项测试、200 正例三后端矩阵及 F01.1～F01.3 回归通过，含五种导出与 HTML/人工 QA。[验收记录](F01_4_ACCEPTANCE.md)。数学模块独立后续；Dagre 与交互已排除；安装验证继续暂缓。本轮未提交推送或发布。以下旧状态保留为历史。

> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

> 2026-11-05 **F01.3 已完成本地验收**：产品 279 项 + 工具 25 项通过；50 正例/8 语法负例/6 范围外诊断/1 上游缺陷在 CPU、auto、GPU 全通过。[验收记录](F01_3_ACCEPTANCE.md)。F01.4/Dagre 暂停，安装验证继续暂缓，本轮未提交推送。下方旧状态保留为历史。

> 2026-11-05 当前仅执行 **F01.3**，按用户最新要求暂停 F01.4/Dagre，见 [本轮计划](F01_3_EXECUTION_PLAN.md)。安装验证暂缓。下方旧目标仅作历史。

> 2026-11-04 **F01.2 已完成本地验收**：产品 150 项 + 工具 17 项通过；35 正例/8 语法负例/1 上游渲染缺陷在 CPU、auto、GPU 全通过。[验收记录](F01_2_ACCEPTANCE.md)。安装验证暂缓，本轮未提交推送；后续 F01.3 尚未开始。下方执行中说明保留为历史。

> 2026-11-04 当前用户要求完成 **F01.2 流程图增强**。执行以 [F01_2_EXECUTION_PLAN.md](F01_2_EXECUTION_PLAN.md) 和当前账本为准；F01.1已完成并提交，安装验证继续暂缓。以下旧范围/时序说明以本条覆盖。

> 2026-11-04 当前用户目标已收窄为 **F01.1 基础流程图**。本轮执行以 [F01_1_EXECUTION_PLAN.md](F01_1_EXECUTION_PLAN.md) 为准：先完成本切片源码，再做本切片来源测试、修复和最终验收；全部图种迁移保留为后续规划。

# 新会话启动文档

2026-11-04 执行顺序更新：先读 [完整主方案](FULL_MIGRATION_PLAN.md)与 [直接接管指令](EXECUTION_HANDOFF.md)。按 P0→P1 全部源码→P2 原实现测试设计/单测→P3 排查批修→P4 最终全量→P5 交付执行。旧 M0…M8 仅作历史范围参考。

2026-11-02：项目已迁移至 [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)，本地启动结构已建立。当前源码版本 `0.0.1a0` 仅表示骨架，未发布 Mermaid 渲染功能。当前事实见 [RELEASE_STATUS](RELEASE_STATUS.md)，逐图种见 [compatibility.json](compatibility.json)。

## 需求与基线

用户目标是**全面移植 Mermaid JS spec 渲染到 Python，渲染引擎基于 py-skia-canvas**。不是只支持 flowchart，也不是让 Python 调用 JS 或把浏览器 SVG 截图包装成 Python 渲染。

参考 [py-skia-canvas](https://github.com/xuanhun/py-skia-canvas) 的锁定来源、宿主边界、共享输入差分、真实输出证据与启动文档方法；不要照抄其“Rust 核心机械拆分”方案。Mermaid 的语法、配置、图布局与图形表达建立 Python 实现；按照用户确认的 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)，淘汰 DOM 操作与浏览器依赖，用语义模型/样式/文字与几何/绘制指令直接连接 Canvas，不建立 Python DOM 兼容层。

- Mermaid：`12.2.0`，tag `mermaid@12.2.0`，commit `1fb7869866dd619168d840291c9c54b4f129758b`。
- Canvas：`py-skia-canvas==0.1.0a18`。首轮 CPython 3.13，Windows AMD64 / Linux glibc 2.28+ x86_64。
- 研发源码 checkout：`.local/upstream-mermaid/`，只读且不进入产品包。
- 实际源码清单：37 个 core detector + ZenUML 插件；368 个测试源文件、2,366 个渲染 fixture、38 个 grammar、34 篇语法文档。尚未拆成逐断言清单。
- 当前没有 parse/render/CLI 产品接口；包只公开版本信息，模块目录仅划分职责。

## 首次操作

Windows PowerShell 可使用短路径新环境：

```powershell
py -3.13 -m venv C:\venvs\pymmd
C:\venvs\pymmd\Scripts\Activate.ps1
```

Linux shell 可使用：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

先按 [AGENTS](../AGENTS.md) 完成必读，检查 Git 状态。使用 CPython 3.13 独立环境，安装步骤见 [README](../README.md#开始开发)。然后执行：

```shell
python scripts/validate_bootstrap.py
python scripts/upstream.py check
python scripts/audit_dependencies.py --check
python scripts/build_dependency_tree.py --check
python scripts/validate_migration_plan.py --check
```

P0/P1 不要求先运行 Canvas 图片或图种功能测试。上游 checkout 缺失时先运行 `python scripts/upstream.py fetch`；已有 checkout 不重置。真实图像、GPU/CPU/字体/格式与产品验证后置到 P3/P4，CPU 不替代 GPU、未验不算通过。

## 下一批的具体任务

验收采用用户已授权的 [渲染功能一致规则](RENDER_CONSISTENCY.md)：跨 DOM/Canvas 不要求像素、绝对坐标或自然尺寸相等；功能/实际内容/连接关系/可读性/安全导出是门禁，图像指标作诊断。正常引擎差异可以通过，不重新把像素零差当成完整迁移目标。

独立 [PNG 像素工具](../tools/PIXEL_COMPARE.md)已经可用，产生指标、热图、局部变化和离线报告。它只完成 L4 通用基础，完整 Mermaid comparator/正式用例仍在 P2；不要重写已有工具或误把 diagnostic 返回 0 当功能通过。

从 [接管指令](EXECUTION_HANDOFF.md)的 P0-01/02/03 开始，核对起点、来源与文件 owner，再进入 [机器任务图](../references/migration-execution.json)的全部 P1 源码任务。建立 `docs/execution-state.json`，记录真实阶段、任务、owner、接口、路径租约和未完成能力。

4 槽使用主协调 + 3 worker，按 ready 队列调度。先固定 model/measure/layout/display 协议，再写基础流程图源码接线；协议可用后其他 F01…F12 图种并行推进，公共模块由唯一 owner 随需求扩建。完整次序和角色分工见 [并行规范](PARALLEL_EXECUTION.md)，接口职责见 [模块边界](MODULE_BOUNDARIES.md)。

P1 覆盖所有 38 detector 和 13 跨图能力，仅做编译/import/签名/引用/注册等机械检查，源码齐备只标 `code_complete_unverified`。不要在完成 F01.1 后停止，也不要先建立逐图 oracle/单测通过门禁。

全源码收口后进入 P2：依据原实现设计测试/单测和 V01…V07 工具；P3 分组首次运行并按公共根因统一修复、只回跑变更影响面；P4 最后统一完整矩阵。详见 [来源驱动验证](SOURCE_BASED_VERIFICATION.md)。

完整依赖树和 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)已经建立，不必每次从头审计。默认 ELK 使用独立 py-elk；不移植 DOM/虚拟 DOM/D3 selection/fastdom/React 浏览器层，保留所需算法、内容、安全和配置含义。

## 可直接粘贴给开发 AI

```text
进入 C:/code/py-visactor/py-mermaid，完整执行 docs/EXECUTION_HANDOFF.md。
先读 AGENTS/NEW_SESSION/FULL_MIGRATION_PLAN，再按角色读 MODULE_BOUNDARIES/PARALLEL_EXECUTION/SOURCE_BASED_VERIFICATION。
保留全部现有脏树；任务 ID 使用 references/migration-execution.json，实际状态写 docs/execution-state.json。
固定 Mermaid12.2.0/1fb7869866dd619168d840291c9c54b4f129758b、Canvas0.1.0a18，布局复用独立py-visactor-elk。
完全使用Canvas公开API做测量/绘制/编码，淘汰DOM/虚拟DOM/D3 selection/fastdom/React浏览器层。
执行顺序：P0接管与接口 → P1一次完成全部源码 → P2按原实现设计测试/单测/oracle → P3分组运行排查、统一批修 → P4最终全量 → P5交付发行。
P1只做编译/import/符号签名/注册接线机械检查，不能先跑逐图功能测试或把代码齐备叫验证通过。
4槽主协调+3worker，协议先行、ready队列并行、单文件唯一owner；公共模块随后续图种增量扩建。
首写F01.1源码链之后继续全部F01…F12、38detector和13跨图能力，不能在首图停下。
P2测试期望独立来自原实现，P3优先修公共根因并相关复跑，P4同一候选完整矩阵保留原始差异。
渲染功能和内容/关系/可读性必须一致，跨DOM/Canvas不要求像素或绝对坐标相等；正常引擎差异可通过，图像指标仅诊断。
每批写回执与复盘，缺接口时继续无关源码并释放worker槽，不重复全仓阅读/全量检查。
没有stub/白图/固定坐标/吞异常；实际授权、commit/push/CI/发布/回读分别记录。
现在从P0-01开始，完成必要接管后持续并行推进全部源码。
```

## 恢复检查

读取最新 `docs/changes/` 记录与独立 `test-runs/`，确认源码 SHA/依赖/字体未变。若只存在本地文件，不能声称远端已有启动资料。旧会话通过只适用于其记录的源码、环境与范围。
