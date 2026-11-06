> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

# 公共模块边界、数据契约与功能扩建规则

2026-11-04。本文是完整迁移执行方案的模块设计，目录、类型与接口名称均为拟建职责，不表示已有对应产品 API。执行阶段以 [主方案](FULL_MIGRATION_PLAN.md) 为准：**P1 集中完成全部功能源码；P2 再依据固定上游设计测试用例与单元测试；随后排查、统一修复和最终全量验证。** P1 阅读 grammar/算法/defaults、记录来源与设计接口，不等于提前编写测试套件。

采用用户确定的 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)。全部图种共享 Python 语义、样式、文字、几何和绘制数据，只有 `rendering/skia/` 操作公开 py-skia-canvas API。DOM、虚拟 DOM、D3 selection、fastdom、React 浏览器层、HTML 截图及浏览器 CSS 排版器不进入目标架构。

## 1. 模块划分

以下路径均位于 `src/py_mermaid/`。现有目录占位继续使用；新增目录按所属职责创建，不为了与 JS 文件数量对应而机械拆分。

| 模块/拟建目录 | 唯一职责与主要输出 | 允许依赖 | 禁止承担的职责 |
| --- | --- | --- | --- |
| `model/` | 不可变请求/诊断/source span；各共享图元素、布局输入输出、样式、文字及绘制指令数据契约 | Python 标准库 | Canvas/设备对象、DOM、文件下载、布局执行、图种注册副作用 |
| `config/` | 固定 schema/defaults、配置层叠、主题/look 选择、资源/安全设置解析 | `model/`；必要的纯数据工具 | 创建 Canvas；为绕开未实现能力改默认 ELK 或标签配置 |
| `parsing/` | 预处理/frontmatter/directives、共享词法工具、位置映射、检测注册机制 | `model/`、`config/`、`security/` 的纯策略 | 单一正则覆盖全部 grammar；持有图种可变全局 DB；绘制 |
| `geometry/` | 点/矩形/变换、路径段、相交/裁剪/边界、marker 锚点、曲线采样、精确谓词与填充 | `model/`、标准库 | 持有 Canvas Path2D；决定图种语义；加入浏览器几何 API 兼容层 |
| `numerics/` | 需要保留的 scale/tick/interpolate/color/date/hierarchy/force/quadtree 等纯计算；稳定顺序和随机流 | `model/`、`geometry/`、标准库及已批准 Python 依赖 | 绘图库后端、D3 selection/DOM 调度、隐式取系统时区或随机状态 |
| `rendering/styles/` | 主题变量、样式优先级、颜色/字体/描边/填充等解析后的样式值 | `model/`、`config/`、`numerics/`、`security/` | 浏览器 style 注入、通用 CSS 运行环境、选择器绑定 DOM |
| `rendering/labels/` | 普通/多行/Markdown/富文本/数学标签解释与 box 排版；输出文字 run、测量请求、标签几何 | `model/`、`geometry/`、`numerics/`、`rendering/styles/`、安全/资源描述；注入测量协议 | 自己创建 Canvas；另行实现 shaping；把不支持的内容静默剥成普通文字 |
| `layout/` | 引擎目录/选项、图数据适配、节点/组/端口/标签定位、路由；统一布局结果 | `model/`、`geometry/`、`numerics/`；已测量的不可变 box | import `rendering/skia/` 或私自测量字体；修改语义节点/边；用 oracle 坐标填结果 |
| `rendering/display/` | 将解析后的图种绘图意图、布局与样式编译为有顺序的绘制指令、包围盒及适用元数据 | `model/`、`geometry/`、解析后样式/资源描述 | 重新运行布局、创建 DOM/SVG 文档、执行 Canvas、充当通用 JS 调用解释器 |
| `rendering/skia/` | Canvas/Context/Path2D/Font 的 owner 生命周期；测量协议实现、绘制指令执行、编码与各导出格式 | `model/`、纯几何、公开 `py-skia-canvas` API | 图种专用 grammar/语义/布局；复制 Rust/Skia/shaping/编码/Vulkan；其他 native 渲染器 |
| `resources/` | 显式离线字体/图标/图像资源、内容和许可指纹、缓存描述、SVG 图标到路径数据 | `model/`、`security/`、纯几何；显式文件/bytes 输入 | 运行 JS 图标包、自动联网下载、创建 SVG DOM；跨线程共享 native 字体/图像对象 |
| `security/` | 输入/资源/URL 策略、标签安全解释、上限与拒绝诊断 | `model/`、标准库及明确选定的解析工具 | DOMPurify/浏览器 DOM 兼容层；擅自扩大文件/网络访问范围 |
| `runtime/` | 每次请求的隔离、取消/时限/预算、阶段编排、worker 所有权、缓存生命周期 | 上述协议；通过注入的 renderer/layout 工厂组合 | 存放图种规则或通用业务工具；暗改 GPU/CPU/线程默认值 |
| `diagrams/<family>/` | 本图种的 grammar/lexer/AST/语义校验/专用排布；将图种数据转成共享模型与绘制意图 | 上述公共契约与计算；按需要调用布局接口 | 直接操作 Canvas/DOM；复制公共颜色/标签/路径实现；图种间相互 import 私有 helper |
| `api.py`、`cli.py`、`__main__.py` | 参数/公开返回值/异常和显式文件输出、CLI 退出码；选择图种并调用 runtime | `runtime/`、注册表与公开模型 | 再实现解析/布局/绘制；把未实现入口包装成成功结果 |

`layout/` 内可按 `elk/`、`cose/`、`tidy/`、`sankey/`、`venn/`、`swimlane/` 拆分。共享的几何/数值实现放在纯模块；专用算法留在其引擎/图种目录。若一种图按固定源码有自有排布，它不必绕经 ELK，也不能为复用接口强行改算法。

`rendering/` 的顶层 `__init__` 保持轻量，不能因为 import 中性模型或 labels/styles 就加载 native Canvas。共享数据契约位于 `model/`，避免 `layout → rendering → layout` 循环。数学公式的语法和 box 计算归 labels，字形测量/shaping/绘制仍由 Canvas 承担。

## 2. 依赖方向与运行管线

```text
纯数据：model
纯计算：geometry / numerics / security

配置 + 预处理 + 图种 grammar
    → DiagramModel
    → ResolvedStyle + LabelSpec
    → LabelMeasureRequest → 注入的 Canvas 测量协议 → MeasuredLabel
    → LayoutRequest → py-elk / Python 图布局 → LayoutResult
    → 图种绘图意图 + display 编译 → DisplayList
    → Canvas 指令执行与导出 → RenderResult

runtime 负责以上阶段的调度与错误收集；它不是语义/几何实现层。
```

标签可能因宽度约束需要二次测量，布局也可能有上游定义的测量反馈阶段。反馈通过明确的输入/输出协议回到 labels/测量，不让布局引擎直接持有 Canvas 或偷偷读浏览器 box。所有反馈次数、终止条件与预算由实际算法和 runtime 记录。

## 3. 跨模块数据契约

P0 固定最小字段、单位、不可变性与错误类别；P1 可以增量扩展接口和实现，但还不设计/运行新增的功能测试套件。下表是必须达成的契约主题，字段可由对应源码审计细化，不应把示意类型名称直接宣传为已发布 API。

| 契约 | 必须包含或明确的语义 | 生产者 → 消费者 |
| --- | --- | --- |
| `SourceDocument` / `SourceSpan` | 原始字节/文本身份、预处理位置映射；字符、行列与 JS UTF-16 code unit 的换算规则；不能丢失原文 | parsing → 全部诊断/模型 |
| `ResolvedConfig` | 不可变有效配置、来源层级、schema 版本；missing/null/false/0/空串区分；layout 默认 ELK、theme/look、标签/安全/资源选项 | config → grammar/labels/layout/display/runtime |
| `DiagramModel` | detector/family、稳定节点/边 ID 和插入顺序、图种专用语义、源位置、标题/描述；不塞入绘制对象 | 图种 parser → 标签/布局/装配 |
| `GraphModel` | 有向/无向、多重边、自环、组/父子、端口/约束和引用；算法需要的顺序；明确对象身份与相等性 | 图种语义 → graph 布局适配 |
| `ResolvedStyle` | 字体描述、颜色与 alpha、线宽/dash、填充、对齐、padding；样式优先级计算结果与来源；逻辑尺寸单位 | styles → labels/display/skia |
| `LabelSpec` / `TextRun` | 文本类型/内容、样式 run、换行/空白/转义和受支持的 rich/math 结构；标签模式保留配置含义，绝不要求 DOM | 图种/labels → 测量与标签排版 |
| `MeasureRequest` / `MeasuredLabel` | 字体/资源指纹、后端/线程上下文、宽度限制、文字/行/基线/包围盒、padding 与换行结果；测量缓存键 | labels ↔ 注入的 skia 测量器 |
| `LayoutRequest` | 与语义 ID 对应的尺寸、组/端口、边、方向、引擎/算法/参数/seed、约束与测量结果；不包含硬编码期望坐标 | 图种装配 → layout |
| `LayoutResult` | 对应 ID 的局部/绝对坐标约定、节点/组/标签 box、边分段/控制点/端点、引擎信息和诊断；不得静默丢未知元素 | layout → 图种/display |
| `PathData` / `DrawCommand` | 闭合/开路径段、弧/Bezier 表达、变换、clip、填充/描边、文字/图像与 z 顺序；使用值类型，执行前无 Canvas 对象 | geometry/display → skia |
| `ResourceDescriptor` | 显式资源 ID/类型/bytes 或受控路径、SHA、许可来源、解码/缺失策略和上限；系统字体不可冒充已捆绑资源 | resources/security → labels/skia |
| `RenderResult` | bytes、实际 MIME/宽高/页/后端信息、诊断与适用元数据、资源/配置身份；异常与取消的返回/抛出规则 | skia/runtime → API/CLI |

单位统一以逻辑图坐标表达，输出 density/scale 在导出边界显式转换。角度单位、矩阵顺序、alpha 范围、浮点/NaN/Infinity、负零、舍入、线宽与 marker 缩放不能依赖调用者猜测；各字段在契约中明确，并追踪上游来源。语义值保留上游需要的精度，不为暂时图像相似而偷偷取整。

Canvas/Context/Font/Path2D 与解码后的 native 资源在 owner 线程内创建使用。跨线程传不可变语义/几何数据或 bytes；原生对象不进入 dataclass、共享缓存或 `RenderResult`。字体度量缓存至少区分字体与资源 SHA、字号/样式、标签解释配置、宽度约束、实际后端及生命周期；错误和未完成测量不写为成功缓存。

## 4. 12 组功能如何对接与扩建公共模块

各功能包均负责完整语法/语义/默认配置接线与图种专有逻辑，公共模块由后续需求继续扩展。下表按 [功能清单](../references/feature-modules.json) 保留全部 38 个 detector；依赖列是工程分工，不表示同一组图使用同一布局算法。

| 功能组 | detector 范围 | 专有实现重点 | 公共模块扩建重点 |
| --- | --- | --- | --- |
| F01 流程图 | `flowchart-v2`, `flowchart-elk` | flow grammar/DB、shape/边/组、显式别名与默认 ELK 接线 | 首先建立有序图、普通标签、矩形/路径/箭头、py-elk 适配和 PNG；P1 内继续补全 flowchart 全功能 |
| F02 关系/建模 | `classDiagram`, `stateDiagram`, `er`, `requirement`, `usecase`, `c4` | 成员/关系/命名空间、状态、基数、约束/容器和专用节点 | 复合图/多区块标签/各端 marker、路由和样式表达；不把类成员等业务字段塞入通用 GraphNode |
| F03 时序 | `sequence` | 消息、参与者、激活、循环/分支与专用时序排布 | 标签 box、对齐、分组背景、虚实线/箭头及绘制顺序；时间序列语义留在本图种 |
| F04 时间/过程 | `gantt`, `journey`, `timeline`, `gitGraph` | 日期日历、旅程、时间事件、提交/分支及专用排布 | 日期/时区/格式、刻度/时间轴、泳道/多行标签与图形；Git 分支规则不进入通用图工具 |
| F05 数值图表 | `pie`, `quadrantChart`, `xychart`, `radar` | 各类数据语法、坐标、分区/极坐标表达 | scales/ticks/format、弧/区域/轴/图例几何，图表元素复用 display/skia |
| F06 树/层次 | `mindmap`, `treeView`, `treemap` | 树节点、层级面积或具体力导向/tidy 规则 | 树/空间索引、层级/面积、COSE/tidy 适配与标签；保留各图种实际算法 |
| F07 流量/集合 | `sankey`, `venn` | 流量/集合模型、区域与专用位置计算 | Sankey/Venn 算法、曲线/相交/填充与标签定位 |
| F08 结构/架构 | `block`, `packet`, `kanban`, `architecture` | 网格/位宽/列、服务/组/端口、约束 | 网格/端口/组几何、fCoSE 及图标/图片资源功能 |
| F09 专用业务图 | `swimlane`, `agentflow`, `eventmodeling`, `ishikawa`, `wardley`, `cynefin` | 专用语义、布局/泳道/区域与后处理 | 按真实重复需求扩展几何/约束/标签/资源；专用规则留在所属包 |
| F10 语法轨道图 | `railroad`, `railroadEbnf`, `railroadAbnf`, `railroadPeg` | 四种 grammar、组合/选择/重复和轨道排布 | 可组合路径、连接/圆角、标签测量；不复用流程图 parser 解释语法图 |
| F11 ZenUML | `zenuml` | 以固定插件入口追踪语法、模型、专用布局和样式 | 将必需能力接到既有 labels/geometry/display；移除 React/DOM/native 替代后端，不构建第二套渲染器 |
| F12 信息/诊断 | `info` | 版本/信息输出；另有 `error`、`---` 诊断入口 | 标准诊断、位置、文字/背景与元数据；不把诊断当作新增图种 detector |

F01.1 是先编写的接线顺序和源码骨架；按照最新阶段规则，它不再要求先完成全部单元/视觉测试才能继续 P1 的其他功能。首个链路提供公共模块的最小实现，P1 后续各功能持续补齐真实逻辑；任何仍依赖 stub、空白输出、硬编码 oracle 数据或缺失分支的功能都不能记为“源码完整”。

## 5. 13 项跨图功能归属

| 跨图项 | 主归属 | 需要协同的模块 |
| --- | --- | --- |
| preprocessing/frontmatter/directives | parsing/config | security、图种检测 |
| configuration/schema/defaults | config | runtime、全部图种 |
| themes/CSS cascade | rendering/styles | config、labels、图种样式意图 |
| text/HTML/Markdown/math | rendering/labels | styles、resources/security、skia 测量协议 |
| accessibility metadata | 既有纯值可保留；不扩展 DOM/ARIA 或交互无障碍协议 | excluded_by_static_scope 的行为断言保留来源 |
| links/interaction/security | 仅保留静态输入/资源安全；事件、导航与交互元数据排除 | 图种、resources、display/API |
| icons/images/resource policy | resources/security | geometry、labels、skia |
| layout engines | layout | model、纯计算、图种适配 |
| handdrawn/random seed | geometry/numerics | config、display、图种选择 |
| exports/scale/background | rendering/skia 与 runtime | config、display、API/CLI |
| diagnostics/errors/UTF-16 | model/parsing | 全部模块统一产出结构化诊断 |
| threading/lifecycle | runtime、rendering/skia | 缓存、资源和 API |
| offline deployment | resources/security/runtime、打包 | 所有 import/依赖/资源入口 |

这些归属不改变 [compatibility.json](compatibility.json) 的验证状态。纯交互和 DOM 无障碍行为由用户明确排除，不要求元数据替身或宿主协议；混合条目中的静态内容与安全断言仍属于最终核查范围。

## 6. 公共模块的增量扩建原则

1. **先有真实消费者。** F01 只建立所需的数据与操作；F02/F03 等出现新需求时扩展公共模块。共性由职责和语义决定，不以“复制了两次”作为唯一标准，也不预建整个 D3/DOM 框架。
2. **单一事实来源。** 颜色/字体/路径/源位置/安全策略等共享行为只有一个 owner；图种不得维护私有复制品。图种专有的状态机、布局语义和字段留在本图种。
3. **先加契约后接线。** 公共字段/操作扩展要写清来源符号、默认值/单位、消费者和迁移方式。P1 只做接口和代码接线的机械检查；对应功能/单元测试统一由 P2 依据上游建立。
4. **扩展默认兼容。** 新字段优先可选且有明确默认，新增能力优先协议方法/命令类型；禁止为了新图种改变旧图种默认语义。确需破坏性内部调整，由公共 owner 一次迁移全部调用者并记录影响面。
5. **不给公共模块注入图种开关堆。** 不以 `if family == ...` 链在通用 labels/layout/skia 中散落专用语义。使用图种适配器、数据驱动的 shape/marker 描述或明确的专用算法入口。
6. **不做全功能 common.py。** 一项工具必须有明确领域：纯几何、数值、配置、资源或某图种。只有格式相同但含义不同的数据不能强行共用一个 dataclass。
7. **计算和绘制分离。** 新算法产出纯数据，新图形编译为已有或扩展后的 DrawCommand。只有 skia adapter 添加必要公开 Canvas 调用；禁止图种直接调 Canvas 或引入另一绘图库。
8. **源映射贯穿扩建。** P1 同步记录 upstream commit/path/symbol → Python 职责；允许合并 DOM helper，但不能把某项未实现功能写成“DOM 淘汰”。所需数值/布局/文字内容仍须有实现归属。
9. **包和资源按目标需要引入。** 原始 npm 树保留溯源，目标 Python 依赖只由保留的功能论证；候选包的许可、依赖闭包和 Python/平台范围先记录，P2/P3 再完成行为验证与必要替换。

## 7. 并行协作与接口变更

每个公共目录/接口和每个图种包有唯一写入 owner。图种 worker 可只读公共模块并提出扩建请求，不跨 owner 并发改相同文件。四槽执行时由协调者维持注册表/契约和主线，其他 worker 按无冲突路径实现；单独 worktree 的变更也要由协调者顺序集成。

公共扩建请求必须包含：请求 ID、功能/来源符号、缺失能力、拟定输入输出、单位/默认/异常、预期调用位置、是否影响现有消费者、owner 和依赖任务。纯新增且不影响其他 worker 的实现可随 owner 任务推进；跨接口变更先由协调者给出统一版本和调用者迁移清单，再由单一 owner 落地。

worker 交付至少说明修改路径、完成的真实算法/分支、输入输出契约、需要的公共扩展、未实现能力、源映射和机械检查结果。P1 的“语法正确/import 可加载/接口已连接”与 P2/P3 的“功能符合上游”是不同状态；先完成全部源码不意味着批准 stub 或未经记录的范围缩减。

公共接口阻塞时，worker 可以继续阅读和编写不依赖该接口的本地计算或其他独立功能，但不能以临时假结果让任务通过。协调者将缺口显式挂到 owner，并在 P1 源码阶段结束前完成接线。P2 依原实现独立建立测试后，统一缺陷记录驱动 P3 按根因修改公共模块及受影响图种。

## 8. 交接时必须保持的边界

全部 38 detector、13 跨图能力、外部 ZenUML、错误/frontmatter 入口和原有功能分母保留。默认布局为 ELK，使用独立 py-elk，不因 Mermaid 原始 elkjs 版本较旧要求已完成项目回退。只使用公开 py-skia-canvas；Canvas 缺口在其仓库单独解决，不复制底层实现。

本文件完成的是模块规划。具体 grammar 分支、shape/主题/选项全集和 Python 依赖最终 pin 仍需执行会话在 P1 按锁定源码编写、在 P2 依据原实现设计用例并验证；不能从模块名和状态表推断全部功能已经实现。
