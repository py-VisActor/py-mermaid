# py-mermaid：AI 工作入口

目标：将固定 Mermaid JS 的完整 spec 语法、配置、布局和渲染行为移植到 Python，以 py-skia-canvas 为唯一生产渲染引擎。

## 开始前

1. 完整读取 [NEW_SESSION](docs/NEW_SESSION.md)、[实施方案](docs/IMPLEMENTATION_PLAN.md)、[兼容规则](docs/API_COMPATIBILITY.md)、[任务清单](docs/TASKS.md)。
2. 读取 [测试与发布](docs/TEST_AND_RELEASE.md)、[当前状态](docs/RELEASE_STATUS.md)、[来源规则](references/README.md)。
3. 检查 `git status --short`，保存用户已有修改；读取 [upstream.lock.json](references/upstream.lock.json) 和 [compatibility.json](docs/compatibility.json)。
4. 执行 bootstrap 与上游校验；资料检查成功不代表渲染通过。

## 不可改变的约束

- 基线固定 mermaid@12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`。不跟随在线最新版，不修改来源哈希掩盖漂移；升级另开任务。
- 全部 detector、外部 ZenUML、配置/主题/资源/安全/错误/布局插件保留在分母。先细化 spec 用例/断言清单，不能把文件数当成覆盖率。
- 运行时不依赖 Node/npm、Playwright、浏览器、JS 解释器、skia-python 或 `.local`。开发 oracle 可以使用官方 Mermaid 和浏览器，不能作为 fallback。
- 只用公开 py-skia-canvas API，不复制其 Rust/Skia、字体 shaping、编码、Vulkan 或设备选择实现。布局移植属于本项目；Canvas 缺口在其仓库单独处理。
- 保留默认 GPU/CPU 策略；CPU 检查不替代 GPU。所有 Canvas/Context/字体对象留在创建线程，跨线程传 bytes 或不可变语义数据。
- 不实现成功 stub、不返回白图、不用少数例子宣称整个图种完成。未支持项明确失败并在清单保留；不吞异常。
- 每个移植入口记录上游路径、默认值、参数/单位、返回/异常、UTF-16 边界和线程/所有权；source map 与独立回归同步更新。
- 先保存修改前证据，再实现及比较。新证据写入新 `test-runs/<run-id>/`；保留失败，禁止覆盖、隐去像素差异、放宽标准或截图后处理。
- 同批更新 README 双语、相关中文契约/开发资料、可运行例子和真实图像来源。无影响的文档主题说明具体理由。
- 代码/测试/工具/打包任务写 `docs/changes/<task-id>.json`，记录基线、起点脏树、验收、源文件 SHA、实际命令/退出码/证据 SHA、限制及下一步。更新后的源码不能冒用旧报告。
- 计划、实现、限定验证、发行验收和发布分开记录。当前没有渲染实现，不发布占位包。
- 保留用户修改；按当前用户授权执行 commit/push/发布，准备资料不自动授权这些外部操作。

普通实施选择可自主推进；改变兼容基线、默认行为、渲染引擎或降低验收要求时需用户决策。缺硬件/字体时记录未验收项并继续独立工作。
