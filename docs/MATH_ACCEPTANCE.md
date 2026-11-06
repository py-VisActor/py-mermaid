> 2026-11-06 已接入正式 `py-visactor-katex==0.1.0`，导入 `py_katex`；wheel/sdist 仓库外安装、22 项既有回归各两环境、8 集成图三后端和五格式均通过。当前入口为 [正式数学接入验收](MATH_RELEASE_INTEGRATION.md)。本轮受影响安装验证已完成，下文旧“相邻源码/数学未发布/安装暂缓”按历史保留；未发布 py-mermaid。

> 2026-11-06 **固定 KaTeX 0.18.11 核心静态迁移已完成本地验收**：973 方法、684 上下文、1909 功能输入/217 等价关系、275 案例三后端与 297 历史流程图三后端通过。当前入口为 [完整验收](MATH_FULL_ACCEPTANCE.md)。安装验证暂缓，未提交推送发布；下方旧 alpha/未实现状态仅作历史。

# 原生数学模块接入验收（2026-11-05）

独立仓库 [py-katex](https://github.com/py-VisActor/py-katex) 已克隆到相邻 `../py-katex` 并完成本地 `0.1.0a0` 原生静态 alpha；[完整验收与边界](../../py-katex/docs/ACCEPTANCE.md)、[可复用日志与报告流程](../../py-katex/docs/RUNS_AND_REPORTS.md)。不是完整 KaTeX 命令/宏/环境兼容验收，也不扩大到其它图种。

## 接入行为

Mermaid 声明 `py-katex==0.1.0a0` 依赖；运行时用公开 API 获得不可变数学盒，在标签测量和 Canvas 绘制时共享缓存。节点、边、分组中的 `$$...$$` 与文本可混排；字形、横线、路径均由公开 Canvas API 实际绘制。

移除原 plain/Markdown/metadata 的延后数学拒绝，公式在 HTML/Markdown/实体/换行处理前受保护，防止 `\nu`、比较符、矩阵 `&`/分行损坏。HTML 数学分支将源实际双反斜杠折叠一次；不要在每个处理阶段重复 unescape。`htmlLabels=false` 沿固定 Mermaid 源保留字面公式；`true` 使用原生测量/绘制，生产不创建 DOM。

F01.3 `math` 和 F01.4 `math-separate` 保留历史 ID，现由派生夹具明确标注 promotedMath 并检查成功解析、公式、实际字形/堆叠基线/像素；不删除旧分母。相关旧方法也改为真实正断言。未知公式不回退成成功字符串或空图。

数学实现及 20 份字体归独立依赖仓库维护并附许可；Mermaid 没有复制第三方数学实现/字体，因此其第三方声明不重复搬入依赖内部资产。

## 同候选验收

712 个方法通过（676 产品、36 工具），含历史 486；61 个公式 + 8 个流程图 × CPU/auto/GPU = 207 视图通过。历史 297 个正例 × 3 后端及原有其它分类通过。真实生成 PNG/JPG/WebP/SVG/PDF；完整报告与五种下载、移动/桌面布局 QA 通过。

[查看 HTML 对比报告](http://127.0.0.1:8765/MATH-batch-20261105T122804Z-878bf5d4/index.html)。HTML SHA256 `9f7ef845b1a8f495d66824f48208da6206f6b3235d3b9e3f5b7a20bf493e88ee`。

Mermaid 源 SHA256 `6e37306deb59a5eb21a2bcceedd66c128a2367f392b094854e2e9bdb3e0e4088`；数学源 SHA256 `6e11f0a8f9f88c78fb387faf4429cfea72781a4e961328bf53299625bea2cb80`。详见 [机器验收摘要](../references/math-verification-summary.json)。旧 F01.4 报告仅对应其历史源码，不能用于证明当前数学候选。

## 已记录差异及未完成项

- `math-flow-metadata`：官方 Mermaid 元数据预处理将反斜杠 n 破坏为换行，A 图显示残缺的字面公式；本实现保留 TeX 并绘制 ν<y，属于明确修正源异常，不能声称与该异常图相同。

- `math-flow-group`：官方 MathML 宿主显示斜体 Unicode Group；原生 TeX 使用 Main-Bold 正体粗体。

- `math-flow-mixed`：官方 flex/MathML 合并公式边界空格；原生保留 Area πr² units 的边界空格。

- 不是完整 KaTeX 兼容实现；注册项与功能族映射不等于逐分支覆盖率。
- 自动公式编号/tag、CD、部分宏展开边界尚未实现；明确拒绝未支持语法。
- Parser 不暴露 displayMode/strict/leqno/fleqn 全部源选项；Options.display_mode 用于视觉样式。
- HTML class/id/style/data、includegraphics 拒绝；href/url 仅保留静态文本，无交互。
- 部分 Unicode 缺少源字体度量时明确报错，不用系统字体伪造数学度量。
- pmb 保留偏移副本，未复刻原实现 0.04px 模糊。
- 本轮验证 Windows 本地环境；安装、构建、Linux/no-loader 验证未执行。
- 版本 0.1.0a0 未发布；Mermaid 声明依赖版本，开发验证使用两个源码目录 PYTHONPATH，安装解析需后续发布或本地安装阶段验证。

Dagre 和交互继续完全排除。当前修改尚未提交、推送、发布；其它图种与完整宏/环境兼容需后续独立任务。安装验证按用户要求暂缓。
