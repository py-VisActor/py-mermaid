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
