> 2026-11-04 当前用户目标已收窄为 **F01.1 基础流程图**。本轮执行以 [F01_1_EXECUTION_PLAN.md](docs/F01_1_EXECUTION_PLAN.md) 为准：先完成本切片源码，再做本切片来源测试、修复和最终验收；全部图种迁移保留为后续规划。

# py-mermaid：AI 工作入口

## 日志与报告统一入口

执行命令和生成报告优先使用 `python tools/workflow.py`，规范见 [RUNS_AND_REPORTS](tools/RUNS_AND_REPORTS.md)。命令用record/batch保存独立run、原始stdout/stderr、真实退出码和指纹；已有证据用report，明确需要新A/B时才用render。不得把日志完整性、报告生成成功或像素diagnostic退出0当功能通过。历史证据不覆盖；安装验证按用户最新要求保持暂缓。当前报告服务的8765 URL保持可用，新服务用 `tools/serve_reports.py` 获取标准访问日志。

目标：将固定 Mermaid JS 的完整 spec 语法、配置、布局和渲染行为移植到 Python，以 py-skia-canvas 为唯一生产渲染引擎。

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
