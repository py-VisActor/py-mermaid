> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

# Canvas 原生架构与 DOM 实现淘汰原则

2026-11-04，用户明确：**所有绘制完全使用 py-skia-canvas；尽可能抛弃上游基于 DOM 操作的实现思路与依赖。** 本文将该要求落实为移植边界，替代早期计划中容易被理解为“为 DOM 库寻找一套 Python 替身”的表述。

目标是保留 Mermaid 的图语言、模型、配置含义、布局计算和图形表达，使用 Python 数据与 Canvas 重新组织渲染。上游 DOM 是参考实现的机制，不是 Python 产品必须重现的接口。该架构决定已经取得用户授权；具体功能缺口、资源与视觉差异仍要记录和验证。

## 1. 产品数据管线

```text
Mermaid 文本 + 配置 + 显式资源
  → Python 解析/语义模型
  → 解析后的样式 + TextRun / LabelBox
  → py-skia-canvas 测量字体与文字
  → py-elk / Python 图布局、路由
  → Python 绘制指令：形状 / 路径 / 文本 / 图像 / 裁剪 / 变换
  → py-skia-canvas 绘制与编码
  → bytes + 尺寸 + diagnostics + 必要静态格式信息
```

TextRun、LabelBox、绘制指令均是拟定的内部数据职责，不是已经发布的 API。语义模型与几何数据不持有 DOM、SVG element、Canvas 或设备对象。Canvas 测量、绘制和编码留在其 owner 线程，字体 shaping 和设备管理继续由公开 Canvas API 负责。

这里不需要先生成 SVG/HTML 文档再交给另一渲染器，也不构建 Element/Document/querySelector/getBBox 的兼容层。SVG 图标可以作为离线输入数据解析为路径/变换；这与运行 SVG DOM 不同。SVG/PDF 等目标导出仍走 Canvas 的公开能力及独立验收。

## 2. 上游实现如何处理

| 上游机制或依赖 | Python 架构处理 | 仍需保留的功能 |
| --- | --- | --- |
| D3 selection、DOM append/attr/style、节点树修改 | 淘汰，直接构造样式值与绘制指令 | 形状、颜色、层叠、变换、文本表达 |
| D3 transition、DOM 事件、拖拽/缩放/brush 控件 | 淘汰浏览器控件与动画运行层 | 完全排除事件、导航、命中测试、动画播放与交互元数据；仅保留初始静态可见样式 |
| fastdom、requestAnimationFrame、DOM measure/mutate | 淘汰浏览器调度库，用明确的测量→布局→绘制阶段 | 真实测量、正确阶段依赖、异常传播和线程所有权 |
| getBBox、getBoundingClientRect、getComputedStyle | 生产中淘汰 | Canvas 文字测量、Python 几何包围盒、显式样式解析 |
| React/ReactDOM、UI 组件树、DOM 虚拟列表/浮层 | 不移植框架，以语义模型和 Canvas 指令重写图形功能 | ZenUML 等实际需要的模型、标签、几何、样式与元数据 |
| html-to-image、浏览器截图 | 产品中淘汰 | Canvas 直接编码；官方浏览器输出仅作开发对照 |
| Stylis、浏览器 CSS 注入/前缀及级联管线 | 淘汰运行机制，主题/配置解析为 Python 样式 | 所需颜色、字体、边框、背景、spacing、样式优先级及用户样式含义 |
| DOMPurify 的 DOM 遍历/重写机制 | 不移植 DOM sanitizer，构建面向 Python 输入与资源的安全策略 | 脚本拒绝、链接/资源策略、标签转义、恶意输入诊断 |
| HTML foreignObject | 不创建 foreignObject 或 HTML 文档 | 支持的富文本含义转换为 TextRun/LabelBox，用 Python 排版和 Canvas 绘制 |
| dagre-d3-es 的 D3/SVG 渲染与 graphlib 接线 | 淘汰渲染接线，不复刻 graphlib API | 目标完全排除 Dagre 算法/包；图结构和几何需求分别由自有模型与纯几何承担 |
| D3 scales/shape/path/hierarchy/force 等计算 | 保留所用算法或寻找真正等价的 Python 实现 | 数值、刻度、曲线、层级、排序、seed 与停止条件 |
| ELK、COSE/fCoSE、tidy、Sankey、Venn、Rough 几何 | 保留布局/几何，全部输出给 Canvas | 端口/路由/约束/采样/填充等算法行为 |
| 其他 native Canvas 后端 | 不接入 | 所有测量/绘制/编码统一由 py-skia-canvas 承担 |

淘汰 DOM/React 等库的实现不需要先证明这些库在上游不可达：这是用户已确定的架构替换。**要证明的是它们承担的 Mermaid 功能如何由新模型、算法、样式和绘制指令承接。** 对于计划删除的数值算法、标签内容或可见配置，仍须有不可达证据或明确的功能处理记录，不能借“去 DOM”缩减图种与功能分母。

## 3. 标签、样式与安全边界

普通文字直接解析为文本 run 与样式，使用 Canvas 测量和绘制。多行、粗体、字体、颜色、换行等富文本需要 Python 标签模型与排版；数学公式需要公式模型和数学 box，不能只删掉标记。

`htmlLabels` 等输入配置可以继续识别，并映射到相应的标签解释/排版语义；它不再意味着 Python 必须生成 DOM 或执行浏览器布局。保留配置含义与默认值，记录两种标签模式的差异，不以强制改为 false 代替实现，也不以模拟默认 DOM 路径作为首图前置。

CSS 候选仅在保留的用户样式功能需要时提供 tokenizer/选择器计算等工具；html5lib 仅可能用于复杂富文本的输入解析。它们都不是首批的必选运行依赖，更不构成浏览器 DOM/CSS 排版层。普通标签的解析、转义、安全限制、主题样式和字体度量应优先由小型 Python 模块与 Canvas 完成。

DOMPurify 的执行机制被移除后，输入安全、离线资源约束与链接策略仍需要独立实现。解析标签不会自动保证安全；Canvas 不执行脚本也不意味着可以任意读取文件、下载资源或执行导航；交互链接元数据不属于交付范围。

## 4. 完整来源树与 Python 目标依赖

[完整上游树](../references/dependency-tree.json)保留所有真实来源边，供定位计算和功能来源；不因为 Python 去 DOM 就篡改上游锁或删掉来源节点。其 `plan` 字段和[策略文件](../references/dependency-porting-policy.json)标记哪些机制淘汰、哪些算法保留。

因此 npm 图的叶节点和层号只用于来源分析，不能直接成为 Python 的包列表或每个包都要重写的任务列表。新 Python 包需由保留的功能主动论证引入。目标运行依赖仍以已有 Canvas 与计划接入的 py-elk 为核心；解析器、Markdown/数学等候选按对应功能另行评估。

## 5. 对 F01.1 的具体修正

首个切片仍是基础流程图，落地为：

1. Python 解析矩形节点/普通标签/有向边，得到有序语义图。
2. 将默认主题与相关配置解析成明确的颜色、线宽、字体、spacing 和 padding。
3. 用 Canvas 得到文字度量，由 Python 计算矩形尺寸和标签位置。
4. 将节点尺寸和图关系交给真实 py-elk，拿到节点坐标及边路由。
5. 生成矩形、路径、箭头、文本等绘制指令，直接调用 Canvas 输出 PNG。

本切片不引入 DOM、虚拟 DOM、D3 selection、fastdom、DOMPurify、Stylis 的 Python 兼容实现。所需图结构和边界/曲线运算按功能重写，不复刻上游 graphlib 的全部 API。该选择不阻碍后续扩展复杂标签、主题、子图和其他图种。

## 6. 验证对应关系

移植映射记录“上游行为/算法 → Python 职责”，允许多个 DOM helper 合并为一项 Canvas 操作，也允许一个复杂 DOM 排版过程拆成多项 Python 排版计算。不要求同名类、方法或 DOM 操作次数一致。

开发 oracle 可以在上游浏览器中采集语义、最终样式、边界、路由和图像；生产只用自身输入、真实字体与 Canvas 测量，不读取 oracle 尺寸/坐标。按用户已确定的 [功能一致规则](RENDER_CONSISTENCY.md)，功能/内容/几何关系与可读性是门禁，正常字体/抗锯齿/合理排版差异可通过，不要求跨引擎像素、绝对坐标或自然尺寸相等。DOM/React 树和浏览器调度不作为 Python 复制目标。

按用户最新 [执行方案](FULL_MIGRATION_PLAN.md)，P1 先完成全部功能源码，仅做机械集成检查；P2 再依据原实现设计测试/单测，P3 分组运行与统一修复、只复跑变更及影响面，P4 最后全量。本次架构资料本身不代表绘制器已经实现或通过 Mermaid 功能验证。
