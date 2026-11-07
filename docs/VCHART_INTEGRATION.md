# py-vchart 正式发行与 Mermaid 接入

2026-11-07，用户明确要求发布 py-vchart，并接入 py-mermaid，支持 py-vchart 全部图表类型。本条开启此前暂缓的图表集成；Dagre、交互、动画、video/audio、任意 HTML/CSS 扩展仍排除。上一轮分支核实的 22 条已知缺口保留，不能由本轮图表接入视为修复。

## 目标与边界

- 发布发行名 `py-visactor-vchart`，导入名 `py_vchart`。既有 GitHub `v0.1.0` 原文件不改；本轮正式版本为 `0.1.1`。
- 显式 `vchart` JSON 及 Python spec API 支持实际注册的全部 68 个二维静态类型，包括核心、二维扩展、统计规格。类型由正式依赖公开清单获得，不能手写少量白名单冒充全部。
- 恢复 pie、quadrantChart、xychart、radar、treemap、sankey、venn 的 Mermaid 语法入口，转换或复用 VChart 的真实图元/布局；保留标题、文字和图例。此项与 68 类型 spec 桥分别验收，未支持的高级字段明确诊断。
- Canvas a18/a19 兼容解决数学依赖约束；默认 Canvas 路径无 skia-python 运行依赖。旧严格像素基准由显式 reference 模式保留，阈值不改，不将其验收冒用到新模式。
- 原生 CPU/auto/GPU、PNG/JPEG/WebP/SVG/PDF；最终绘制在同一 owner 线程和 Canvas，SVG/PDF 不通过整图 PNG 嵌入伪装矢量。离线 maps/SVG 资源按请求隔离，不隐式下载或污染全局注册表。
- 所谓“全部类型”指当前 py-vchart 的 68 个二维入口，不等于 VChart JS 全部高级选项、3D 或交互兼容。

## 执行顺序与文件责任

依 [并行规范](PARALLEL_EXECUTION.md)，root 负责发行、依赖、文档及最终验证；A 负责七个 Mermaid 语法与对应 VChart 纯布局/消费者；B 负责全类型 spec 桥、公开 API、registry 和 Painter 合成；C 负责 VChart Canvas/text/mask/pictogram/core/public API。精确单文件 owner 在会话消息中登记，同一文件不并写。

1. P0：固定现有干净 VChart 起点 `f1ae8a7` 及 Mermaid 脏树；读取固定上游与实际能力边界。
2. P1：集中完成供应方原生接口和消费者接线，仅编译/import/签名等机械检查，不把源码完成标为功能通过。
3. P2：根据固定来源与已有独立案例，编写全部类型、七语法、资源、安全、错误、导出、后端、安装验证。
4. P3：分组首次运行，保留失败；归类后批修并相关复跑。旧 reference 严格门禁保持，新 Canvas 字形差异独立展示并核对语义、几何、文字与可读性。
5. P4：冻结候选；本机三后端、全部 68 类型与累计 225 供应方案例、受影响 Mermaid 回归；发行 wheel/sdist 仓库外安装，Windows/Linux CI 与 Canvas a18/a19。
6. P5：发布已审阅的同组发行字节，再以正式发行依赖验证 Mermaid。PyPI Trusted Publishing 需账户 Publisher 配置；本次实际被 `invalid-publisher` 阻止，已使用 GitHub stable Release 和带 SHA-256 的正式 wheel 依赖完成可安装交付。账户配置完成后复用同组字节上传并核实际 PyPI 下载哈希。报告按轮次、每页最多 12 例。发布 py-mermaid 包不在本次授权范围。

新证据写独立 `test-runs/`，保留历史报告；所有实际结果以新运行记录为准。下列实际状态覆盖本页初始计划。


## 实际发布状态

[GitHub 正式发行 0.1.1](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.1) 已发布，源码提交 `ff16c91d38ab61e57d03b58579d5bf1beb2a1840`。wheel SHA-256 为 `45b66f82d0c74a8d15306b117d93ad2d88c26d2997719306336bcc92b7ce49e2`，sdist 为 `fee51a35d75b7f8572e76b0028d63c833f6e01c670c7ea41dc412386b3bcef7f`。精确安装依赖、文件地址与来源见 [发行锁](../references/vchart-release-lock.json)。发布后的文档提交不移动 tag、不覆盖资产。

[CI 42337813981](https://github.com/py-VisActor/py-vchart/actions/runs/42337813981) 的 Windows/Linux × Canvas a18/a19 四组验证均通过；wheel/sdist 共八次独立安装，每次完成 225 个输入、68 个类型与 36 项原生/负控方法。原始 CI 资产已按 GitHub SHA 回读归档于 `../py-vchart/test-runs/vchart-ci-final-42337813981/summary.json`。PyPI publish 步骤返回 `invalid-publisher`，整次 workflow 不能称为全绿。PyPI 项目 `py-visactor-vchart` 尚未发布；待账户添加 owner `py-VisActor`、repo `py-vchart`、workflow `publish-pypi.yml`、environment `pypi` 的 Publisher。

## 候选审查与保留失败

首轮完整分组运行和历次修复均保留于标准 `test-runs/`；`VCHART-P4-batch-20261107T041705Z-6c07df8d` 功能检查全部通过，但随后实际审阅 30 对 Mermaid 原图发现标题基线、无效颜色继承、柱宽、Treemap 样式和共享粗描边边界问题，不能把此运行冒作最终视觉验收。完整审查收据为 `test-runs/vchart-visual-review-20261107T043500Z.json`。

目前回到 P3 集中修复：四类语法样式已修正，共享描边边界正在修复。首次修后 145 方法仍有两个失败，保留于 `VCHART-VISUAL-REPAIR-record-20261107T043919Z-8882b2ed`；Treemap 绿字已据根因修复并用原断言及实际绿色像素复核，XY 总宽等待共享边界修复。最终将以重新冻结的同候选运行、实际看图和独立安装作为交付依据。

## 当前明确限制

- “全部类型”为供应方实际注册的 68 个二维静态类型，完整清单由 `supported_vchart_types()` 返回。
- Mermaid Venn 最多三个单集合；超出时明确报错。Treemap 使用 VChart binary 布局，部分数值格式操作符明确拒绝，与原 D3 squarify 不要求像素一致。
- 资源仅接受显式离线输入；地图和 SVG 按请求隔离。自定义字体注册使用内容哈希私有别名，绑定单个 `fontFamily`；自定义字体 fallback 列表明确拒绝，避免跨请求污染。
- 两例原生词云装饰重复数允许因 Canvas 字形占用出现来源可解释差异；原始比较结果保留，并单独核实主词、权重字号、真实字形墨迹和蒙版边界。旧 reference 225 例严格阈值不改。
- 既有 22 条 Mermaid 分支缺口原样保留；本轮不声称全部高级选项完成，也不发布 py-mermaid 包。


第二次完整运行 `VCHART-P4-batch-20261107T044508Z-506fd409` 如实 FAILED：共享边界修复后，67 供应方方法、155 接入方法、225 原生输入×三后端、旧 reference 225 与全部旧回归通过；七语法三后端仅三例 Treemap 的白字无墨迹门禁失败。原版实际 PNG/computed styles 证实同样存在无填色白字缺陷，完整30对审查收据为 `test-runs/vchart-visual-review-20261107T045200Z.json`。本端已仅在缺失父填色时使用主题普通文字颜色，透明填色、父色/叶透明度与合法 class/inline 样式优先级保留；没有放宽文字墨迹门禁。新增3例真实标签/值像素回归，统一156方法通过（`VCHART-VISUAL-REPAIR-record-20261107T045049Z-74816ee1`）。当前重新冻结 P4，旧失败与源码保持不变。


## 最终结论

以上 P1/P3/P4 进行中状态和失败均为保留历史；当前以 [最终验收](VCHART_ACCEPTANCE.md) 和 [机器汇总](../references/vchart-verification-summary.json) 为准。最终同候选运行 `VCHART-P4-batch-20261107T045154Z-dd03474c`、156接入/共2283方法、三后端、30张实际看图及两次真实安装通过；分页报告29页/335条和2537原字节附件已交付。PyPI 仍被 invalid-publisher 阻止，GitHub 正式发布和可安装接入已完成。


## PyPI 发布更新

账户配置完成，已复用同组已验收文件正式发布 PyPI；工作流第2次尝试全部成功，py-mermaid 已切换 `py-visactor-vchart==0.1.1` 并通过两个全新环境安装。上文 invalid-publisher 和 GitHub渠道描述保留为历史，当前状态见 [发布补证](VCHART_PYPI_PUBLICATION.md)。渲染源码未改变，原报告与失败证据不重写。
