# 第三方来源与许可

本项目沿用根 [MIT LICENSE](LICENSE)。

- Mermaid：固定 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`，MIT；版权原文保留于 [references/licenses/mermaid-LICENSE](references/licenses/mermaid-LICENSE)，随本包分发。F01.1 基础流程图语法、配置、样式和几何职责的来源映射位于 `references/f011-*-sources.json`；F01.2 的经典形状、组/边标签、子图与复合布局来源位于 `references/f012-*-sources.json`；F01.3 的前处理、主题/样式、富标签和标题来源位于 `references/f013-*-sources.json`。完整参考 checkout 不进入发行包。
- py-skia-canvas：依赖 0.1.0a18，使用其公开 Python API。其 wheel 内含自身及 Rust/Skia 等第三方许可；本项目不复制其核心或原生库。
- Khroma：固定本地官方构建依赖 `khroma@2.1.0`，MIT；颜色通道、调整、反色、HSL 意图、透明度、序列化与颜色名规则移植为纯 Python，支持完整主题的连续派生计算。来源见 `references/f013-parser-sources.json` 与 `docs/changes/bulk-shared-khroma-P3.json`，许可证保留于 [khroma-LICENSE](references/licenses/khroma-LICENSE)。生产不导入或解释 JavaScript，不依赖 npm 包。
- py-visactor-elk：依赖 0.1.0，使用公开 `pyelk.ELK` 接口，不复制其算法源码。该独立分发包自行携带 `MIT AND (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0` 许可及来源通知。
- Mermaid 的 Dagre/ELK/D3/RoughJS/KaTeX/Iconify/ZenUML 等依赖：锁定源码中的包/lock 只提供来源起点，实际移植/打包前逐项审计版本、传递依赖和许可。不能从 Mermaid 主仓库 MIT 推断所有依赖或资源均为 MIT。
- 系统/用户字体、图标及图片：不随本骨架复制，后续共享 fixture 资源须附独立许可、来源与 SHA。

任何后续源码移植需要同步来源映射和本说明。发布前检查最终 wheel 实际携带的代码、资源、NOTICE 和许可证。

## 2026-11-07 非图表收口来源

- `langium@4.4.0`，MIT，字符串单字符转义和 CommonValueConverter 的纯值规则按固定 Mermaid parser bundle 的 sourcesContent 移植；不包含或执行 Langium/JavaScript 运行时。原许可见 [langium-4.4.0-LICENSE](references/licenses/langium-4.4.0-LICENSE)。
- `dayjs@1.11.21`，MIT，固定 Gantt 日期解析、星期/ISO week/advancedFormat 语义作为 Python 日历实现的来源；生产不加载 Dayjs。原许可见 [dayjs-1.11.21-LICENSE](references/licenses/dayjs-1.11.21-LICENSE)。
- 两份许可来自对应 npm 精确版本 tarball，SHA512 integrity 已核验；原始元数据、tarball与许可指纹保存在 `CLOSURE-P1-SOURCES-record-20261107T075917Z-c684fc9f`。D3时间/格式规则继续使用已列原许可，不以源码参考引入npm运行依赖。

## 2026-11-06 静态批次新增来源

下列通知记录实际移植来源与已纳入的资产；功能、设备和导出验收状态由执行账本单独记录。
统计图表、矩形树图、桑基图和韦恩图已由用户暂缓，其专用依赖不因保留源码而计入本批完成项。

- Mermaid 的全部 11 个主题构造与派生颜色规则：固定同一 12.2.0 commit，MIT；
  Python 静态规则与原文件 SHA 见 `references/bulk-themes-sources.json`。
  `tools/port_bulk_themes.mjs` 只在开发阶段读取固定源并生成 Python，不进入生产执行链。
- D3 的数值/时间/路径职责：时间与过程图使用的比例尺刻度、日期区间、格式和路径规则来自
  固定开发依赖中的 `d3-array`、`d3-time`、`d3-time-format`、`d3-path`、`d3-shape`。
  各包 ISC 许可原文分别保留于 `references/licenses/d3-*-LICENSE`；实际文件与算法来源由图种 source map 细化。
  Python 生产不导入 D3，也不保留 selection、DOM 或调度器。
- `non-layered-tidy-tree-layout@2.0.2`：MIT，供原源可选 tidy-tree 布局的数值算法迁移；
  固定 npm tarball 已按 pnpm lock 的 SHA512 校验，只下载源码，没有安装或执行该包。
  来源回执位于 `.local/bulk-sources/non-layered-tidy-tree-layout-2.0.2/source-receipt.json`，
  许可随包保留于 `references/licenses/non-layered-tidy-tree-layout-LICENSE`。
- COSE-Bilkent 与 fCoSE 的专用数值职责：MIT。固定源分别为
  `cytoscape-cose-bilkent@4.1.0` / `cose-base@1.0.3` / `layout-base@1.0.2`，以及
  `cytoscape-fcose@2.2.0` / 其嵌套的 `cose-base@2.2.0` / `layout-base@2.0.1`。
  原许可按包名与版本分别保留于 `references/licenses/*-LICENSE`，未混合两套依赖版本。
  Python 移植保留专用力学、谱初始化和约束职责；不复制 Cytoscape/浏览器宿主。
  fCoSE 的原生数值适配与来源差异明确列于 `references/bulk-A-F08-sources.json`。
- `@zenuml/core@3.49.2`：MIT，Copyright (c) 2022 Peng Xiao；
  固定源 commit 为 `213c239587ffa1f3dbb54d8b64468c3038ced55d`。
  迁移其专用语法、模型、布局数值职责与自有静态 SVG；
  许可保留于 `references/licenses/zenuml-core-LICENSE` 及内置 assets 的 `LICENSE-core`。
  该 MIT 许可不覆盖下列厂商云服务图标。

### ZenUML 云服务图标

内置图标从上述固定 ZenUML 来源原字节保留，只用于图示对应的云服务，保留原色和比例；
不将这些图标声明为本项目的 MIT 资产，也不将其用作项目标志。

- AWS：EC2、Lambda、IAM、SNS、SQS 图标来自源附带的 `AWS-Asset-Package_02062024`。
  [AWS 官方图标说明](https://aws.amazon.com/architecture/icons/)允许客户和合作伙伴用这些资产制作架构图，
  并说明图标可出现在文档和演示材料中。本项目按该图示用途集成，厂商保留相关权利。
- Microsoft：Azure Function 图标来自源附带的 `Azure_Public_Service_Icons`。
  [Azure 官方图标条款](https://learn.microsoft.com/en-us/azure/architecture/icons/)允许架构图、培训材料和文档用途的复制、分发和显示，
  并限制裁剪、翻转、旋转及改变图标形状等使用。
  原附带条款 `Microsoft_Terms_of_Use.pdf` 随内置资产一同保留；其他权利归 Microsoft。

上述厂商资源集成依据其图示用途说明，资源文件名、来源 SHA 与具体用途在 ZenUML source map 中单独记录。

- RoughJS：固定 roughjs@4.6.6，MIT（Copyright (c) 2019 Preet Shihn）。F01.4 将必要的 seeded Random、线段/Bezier 扰动及手绘填充职责实现为纯 Python，生产不依赖 JavaScript；许可证随包保留于 [roughjs-LICENSE](references/licenses/roughjs-LICENSE)，来源见 `references/f014-canvas-sources.json`。

- py-visactor-katex：固定正式版本 0.1.0，MIT，Python 导入名 `py_katex`，源码仓库 `py-VisActor/py-katex`。该独立发行包携带 KaTeX 0.18.11 数学字体、度量及来源许可；本项目只调用其 API，不复制其字体或数学实现。

- py-visactor-vchart：图表依赖版本 0.1.1，MIT，导入名 `py_vchart`，仓库 `py-VisActor/py-vchart`。发行包保留 VChart、venn.js、fmin 与统计色板的来源许可；本项目通过其公开静态 spec/布局/Canvas API 调用，不内嵌该包源码。NumPy 为该独立包声明的运行依赖；skia-python 仅属于其可选 reference 开发校验模式，不是本项目运行依赖。发行与安装实测状态见 [VChart 接入](docs/VCHART_INTEGRATION.md)。

- W3C CSS Color 4：控件初始色值的纯 Python 转换参考官方 `conversions.js` 示例中的矩阵与传递函数，未引入 JavaScript 运行依赖。来源、固定下载 SHA 与 `csswg-drafts` 根许可适用记录见 `references/html-host-semantics.json`。保留 [W3C notice](references/licenses/w3c-css-color-NOTICE.txt)、[完整 Software and Document License 2023](references/licenses/w3c-software-document-license-2023.html)、[官方 short notice](references/licenses/w3c-software-document-short-notice-2023.html) 及 [原仓库许可声明](references/licenses/csswg-drafts-LICENSE.md)；这些来源权利与免责声明不被本项目 MIT 声明替换。

- Chromium / Skia 色彩状态数值：控件色值归一化还参考固定 Chrome 156.0.8078.76 的 Chromium `skcms_ext` / color-input 调用路径及其精确 DEPS 对应的 Skia `SkColorSpace.h` 传递函数与 D50/ICC 系数，独立改写为 Python 标量计算以保持静态初始色值；不调用或复制其栅格器、字体、设备或浏览器运行实现。Copyright 2025 The Chromium Authors；Copyright 2016 Google Inc.。适用 BSD 许可随包保留于 [chromium-LICENSE](references/licenses/chromium-LICENSE) 与 [skia-LICENSE](references/licenses/skia-LICENSE)，固定 revision、原头部及 primary URL/SHA 见 `references/html-host-semantics.json`。
