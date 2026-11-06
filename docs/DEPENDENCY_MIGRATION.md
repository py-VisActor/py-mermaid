> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

# 完整依赖树与自底向上的 Python 迁移方案

执行时序已由用户更新，权威见 [FULL_MIGRATION_PLAN](FULL_MIGRATION_PLAN.md)：P1 一次写完全部功能源码，P2 原实现驱动测试/单测，P3 统一排查批修，P4 最终全量。本文 D00…D10 是依赖与职责参考，不是每个图种先完成测试闭环再继续的门禁。

2026-11-04。依据 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b` 的完整 pnpm 锁，补齐上一轮只覆盖声明生产闭包的边界。本次交付依赖图、候选调查和实施顺序，未开始重写 Mermaid 产品代码。

用户已进一步确认 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)：上游树是溯源资料，目标不逐包复制 DOM 栈。DOM/D3 selection/fastdom/React 浏览器层等直接淘汰，其图形职责由 Python 语义模型、样式、布局和 Canvas 绘制指令承接；所用算法与功能仍保留。处理策略和生成索引已同步该决定。

## 1. 从哪里查看完整树

| 产物 | 用途 |
| --- | --- |
| [产品与实际源码额外值导入树](../references/dependency-tree.txt) | 从 Mermaid、parser、ELK/tidy/ZenUML 插件以及 js-yaml/Langium/fastdom/tidy 算法向下展开到包管理叶节点 |
| [全部工作区及开发工具树](../references/dependency-toolchain-tree.txt) | 包含构建、生成器、测试、文档/编辑器的全部锁定传递依赖 |
| [完整机器图](../references/dependency-tree.json) | 每个精确版本/peer/patch 上下文、工作区链接、可选边、反向归属、方案与 SCC 层号 |
| [从底层向上的逐节点索引](../references/dependency-bottom-up.md) | 产品相关每个节点的依赖层、处理策略、Python 候选和工作包 |
| [可审阅的处理策略](../references/dependency-porting-policy.json) | 精确包规则、前缀规则、类型/测试排除理由及工作包依赖 |
| [Python 候选元数据](../references/python-candidates.json) | 本次查询 PyPI 得到的候选版本、Requires-Dist、官方地址、元数据与 wheel 指纹；不是已采纳的运行依赖锁 |

当前分母：**2,419 个 registry snapshot + 13 个工作区 = 2,432 节点，5,118 条解析边，缺失目标 0**。直接和可选依赖的边分别保存，peer 上下文和补丁不合并；包声明的 peer 范围另存，不伪造未解析的 provider。

其中，上一轮五个产品包的声明生产闭包为 344 个 registry snapshot；加入四个额外值导入及其传递依赖后为 **360 个 snapshot、335 个唯一 registry 包名**，另有 5 个产品工作区。类型包和声明但未必进入 bundle 的代码仍留在树里，不能把 335 当成要新增的 Python 运行包数量。

文本树每个节点只完整展开一次，重复引用和循环用 `[Nxxxx]` 回指首次展开位置；没有深度裁剪或 `...` 隐藏子树。机器图保留全部边。产品图存在 **3 组循环**，分别涉及 Babel、browserslist 和 Iconify 的 mlly/pkg-types；先缩为强连通分量（SCC）再排序，不能用普通拓扑排序丢掉循环或无限递归。

这里的“完整”指固定锁文件的全部包管理节点和边。KaTeX 内置数学布局、Dagre 内置 graphlib、ELK 内置算法、ZenUML 内置 grammar 等不是独立 npm 边，下面另列内部能力树；字体、图标和 native Canvas 的内部依赖也不能因 npm 树已到叶子就视为已审计。

## 2. 主要算法链（阅读导航，完整边见文件）

```text
Mermaid / 同仓库插件
├─ elkjs 0.9.3
│  └─ 内置 ELK 算法 → 独立 py-elk；Mermaid 适配单独完成
├─ dagre-d3-es 7.0.14
│  ├─ 内置 graphlib / Dagre rank-order-position-route
│  ├─ lodash-es 4.18.1 → Python 值/集合适配
│  └─ d3 7.9.0
│     ├─ array / internmap → 数值、键与稳定顺序
│     ├─ path / shape / polygon → 路径、曲线与区域
│     ├─ hierarchy / quadtree / force → 树、空间索引与迭代
│     ├─ delaunay → delaunator → robust-predicates
│     └─ scale / interpolate / color / time / format
├─ cytoscape-cose-bilkent 4.1.0
│  └─ cose-base 1.0.3 → layout-base 1.0.2
├─ cytoscape-fcose 2.2.0
│  └─ cose-base 2.2.0 → layout-base 2.0.1
├─ non-layered-tidy-tree-layout 2.0.2 → 树布局
├─ d3-sankey 0.12.3 → D3 的流量布局及相应版本数值分包
├─ @upsetjs/venn.js 2.0.0 → 内置集合布局/几何
├─ roughjs 4.6.6
│  ├─ hachure-fill → 扫描线填充
│  ├─ points-on-curve → 曲线采样
│  └─ points-on-path → path-data-parser / 曲线采样
├─ @mermaid-js/parser / Chevrotain / Langium
│  └─ lexer / grammar / AST / 引用和服务 / 错误定位
├─ marked / js-yaml / stylis / khroma / dayjs
│  └─ Markdown / schema / CSS / 颜色 / 日期适配
├─ DOMPurify / sanitize-url / Iconify / KaTeX / fastdom
│  └─ 安全与离线资源 / HTML与数学排版 / 测量及绘制宿主
└─ @zenuml/core 3.49.2
   ├─ antlr4 4.11.0 → ZenUML 语法及生成代码
   ├─ Babel / React / Tailwind 等声明链 → 追踪图形入口实际所用表面
   └─ @napi-rs/canvas 及各平台可选包 → 需要的绘制语义映射到现有 Canvas
```

导航图省略的是外围工具说明，不作为完整依赖清单。ZenUML 插件实际调用 `renderToSvg`，来源为 `packages/mermaid-zenuml/src/zenumlRenderer.ts`；不能据 React 或原生 Canvas 的声明就认定该入口实际执行了全部依赖，也不能无证据删除它们。

## 3. Python 选型初稿

以下结论区分“现有项目复用”“候选 + 适配”“Python 重写”。候选名称相似或能画出同类图形，均不足以证明算法等价。本轮只调查官方文档与发行元数据，没有安装/执行候选库或宣称其通过 Mermaid 差分。

| JS 能力 | Python 路径 | 已核实能力与仍需处理的差异 |
| --- | --- | --- |
| ELK | 复用 `py-visactor-elk` | 独立项目已有 0.1.0 正式包；本项目仍需适配模型/选项/端口/标签/路由，不要求回退其 0.12.1 基线 |
| 底层 Canvas、字体 shaping、编码 | 复用 `py-skia-canvas==0.1.0a18` | 沿用既定 native 渲染边界与公开 API，不重复移植 Skia，也不新增其他 native 后端 |
| UUID/日期/集合工具 | 标准库 + 小型行为适配 | `uuid`、`datetime`、`zoneinfo`、`collections`、`copy`、`textwrap` 等；JS 值/排序/日期格式/DST/缩进/错误须匹配。源码 UUID 用 v4、v5，不因 npm 包支持 v7 就扩展需求 |
| Jison/Chevrotain/Langium | 候选 `lark` 1.3.1 + grammar/actions/services 重写 | [Lark](https://lark-parser.readthedocs.io/en/stable/index.html)提供 Earley/LALR/CYK；不是上述框架的兼容 API，词法优先级、恢复、UTF-16、反射/服务需迁移 |
| js-yaml | 候选 `PyYAML` 6.0.3 + resolver/constructor 适配 | [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)提供 Python 和 LibYAML 两种路径；选择 Python Loader，按上游 JSON_SCHEMA 定义标量/标签/别名/合并与错误，不能仅调用 safe_load |
| Marked | 候选 `markdown-it-py` 4.2.0 + `mdit-py-plugins` 0.6.1 | [官方文档](https://markdown-it-py.readthedocs.io/en/latest/using.html)支持 token/renderer 和不同 preset；Marked 的方言、HTML、换行、转义等另做适配，输出接 Python 标签模型 |
| Stylis、选择器、HTML | Python 样式/标签模型；tokenizer 等候选仅在保留输入功能需要时评估 | [tinycss2](https://doc.courtbouillon.org/tinycss2/stable/)、[cssselect2](https://doc.courtbouillon.org/cssselect2/stable/)、[html5lib](https://html5lib.readthedocs.io/en/latest/)仅是早期研究的解析工具，不是必选运行依赖；不构建 DOM、CSS 注入、通用浏览器排版或 DOMPurify 兼容层 |
| Khroma | 候选 `coloraide` 8.14，必要时小型 Python 重写 | [ColorAide](https://facelessuser.github.io/coloraide/)提供颜色转换/运算；仍需验证 Khroma 的 darken/lighten/adjust/isDark、clamp、舍入和字符串输出 |
| RoughJS 及其几何子依赖 | 优先评估 `rough` 1.6；必要时移植算法；路径候选 `svg.path` 7.1 | [rough](https://pypi.org/project/rough/)声明为 Python RoughJS 移植且无必需第三方依赖；[svg.path](https://pypi.org/project/svg.path/)提供路径段与解析。未证明 RoughJS 4.6.6 的 seed、随机流、填充、控制点和输出操作等价 |
| graphlib / 通用图结构 | 自有轻量有序图，不复刻 graphlib API；`networkx` 3.7 仅作算法候选 | [NetworkX](https://networkx.org/documentation/stable/install.html)基础包为纯 Python、无硬依赖；首批直接表达节点/边/顺序并对接 py-elk，图模型可复用不表示其布局等价 Dagre |
| D3 数值、COSE/fCoSE、tidy、Sankey、Venn | 按锁定源码所用接口重写 Python | 本轮未确认可以直接替换并保持全部原算法输出的 Python 组件。Grandalf 有同类布局，但这不足以证明 Dagre/COSE 等价，不纳入直接替换方案 |
| KaTeX | 候选 `latex2mathml` 3.81.1 处理语法；数学布局自行实现 | [项目页](https://pypi.org/project/latex2mathml/)定义的是纯 Python LaTeX→MathML 转换；不能替代 KaTeX 的宏、公式 box、字体度量、伸缩操作符与最终绘制 |
| ZenUML ANTLR | 候选 `antlr4-python3-runtime`，或转换 grammar 后 Python 重写 | [ANTLR](https://www.antlr.org/download)提供 Python target；必须找到原 grammar/语义动作并匹配生成器/runtime。当前 JS 锁到 4.11.0，调查到最新 Python 4.13.2 不表示可直接混用 |
| React/DOM/事件/fastdom/资源辅助 | 淘汰浏览器实现层，重写为 Python 数据和 Canvas 绘制流程 | 不移植 React/DOM/调度库；保留需要的图形布局、样式、链接/交互元数据、错误和资源策略 |

本轮查询的候选版本和 Requires-Dist 全文保存在元数据文件中，**没有改 pyproject.toml**。这些版本是研究时观察值，不是已通过兼容测试的 pin。Grandalf 的许可字段也仅记录发行元数据，不作为许可审计结论。

候选自身依赖同样要向下审查：markdown-it-py 的基础链含 mdurl，tinycss2/cssselect2 含 webencodings，html5lib 含 six/webencodings；启用 linkify 等能力会增加额外链，必须在实际选型时形成解析后的 Python 锁与完整树。不能把候选研究文件当成已解析的 Python 安装依赖树。

Lark 的 Nearley extra 声明 js2py，不能引入；NetworkX 的 default extra 会引入 NumPy/SciPy/Matplotlib 等，不能为图结构复用而隐式安装；PyYAML 不使用 CLoader，HTML 不选 lxml treebuilder，数学不调用 JS/TeX 子进程。既有 py-skia-canvas 是明确保留的 native 边界，所谓“Python 重写”指上层语义和算法不再运行 JS。

## 4. 真正的实现顺序：能力叶节点先行

执行入口以 [功能拆分](FEATURE_MIGRATION.md)为准：**先迁移 F01.1 基础流程图**，确定该功能的契约和 parser-model 后，只取其需要的 D00…D09 子集从底层向上实现。本节列的是共享能力依赖，不要求按整包逐一完成，也不要求等整个 D00/D3/CSS 完成才交付首图。

包管理层号只表示外部包依赖；例如 elkjs 几乎不依赖其他 npm 包，但自身是大型布局引擎。实施要先拆内部能力，再按工作包依赖推进。具体节点归属见策略文件和自动索引。

| 工作包 | 从底层向上的内容 | 前置 | 退出条件 |
| --- | --- | --- | --- |
| D00 | JS 值/undefined/null、数字、UTF-16、稳定顺序、键、随机、集合/字符串适配 | 无 | 独立语义边界和负例，stdlib 不等价点显式处理 |
| D01 | 点/矩形、相交、Bezier/弧、路径解析、采样、精确方向谓词、Rough 填充和 PRNG | D00 | 对照路径操作、退化输入、seed 流与填充边界 |
| D02 | 日期/颜色/YAML/离线资源基础；候选选型最小验证 | D00 | resolver、时区/舍入、资源与错误语义明确；候选依赖锁可审计 |
| D03 | 有序/复合/多重图、队列/堆、遍历/连通分量、空间树 | D00/D01 | 插入顺序、复合关系、循环、空图/自环和 tie-break 符合来源 |
| D04 | grammar、lexer、AST、引用、错误/恢复及 parser 服务 | D00/D02 | Jison 与 Langium 各一真实入口先验证，再扩全 grammar；不把全部框架 API 逐一机械翻译 |
| D05 | Markdown/HTML/CSS 输入与安全策略、数学语法 | D00/D01/D02 | 标签/转义/选择器/安全模式/恶意 URL 等实际调用面可追踪 |
| D06 | D3 scales/ticks/format/interpolate/shape/hierarchy/force 等所用数值能力 | D01/D02/D03 | 稳定排序、曲线、时区、迭代、数值边界符合对应分包版本 |
| D07 | 两套 COSE/layout-base、fCoSE、tidy、Sankey、Venn 与 py-elk 适配 | D01/D03/D06 的实际所用子集 | 原算法的参数/顺序/seed/停止条件/标签与路由验证；各布局可按自身子依赖分别推进 |
| D08 | CSS/HTML box、文字和数学布局、图标/SVG 几何、测量/绘制阶段、Canvas primitives | D01/D02/D05/D06 的实际所用子集 | 真实字体测量/标签 box，未实现内容明确失败，owner 线程正确 |
| D09 | Mermaid 图种模型、配置/主题、注册器、默认 ELK、导出组装 | D04/D07/D08 的对应切片 | 首个真实 flowchart，再按原 M4/M5/M6 扩全；不以局部通过替代完整图种 |
| D10 | ZenUML grammar/语义/布局/style 与 Canvas 绘制链 | 对应 D04/D05/D07/D08 | 以 renderToSvg 为参考入口保留功能；淘汰 React/DOM/浏览器 UI 层，所需语法/算法按调用契约迁移 |

D07/D08 是聚合工作包，表中前置不要求等待 D06 所有功能做完才开始默认 ELK 切片。先复用已完成的 py-elk，补其实际所需的模型、测量、配置和渲染链；不要再次重写 ELK，也不要为整个 D3 Umbrella 建全功能替代库后才开始画图。

迁移工作规则：

1. 为每个实际调用建立 upstream commit/path/symbol → Python entry、默认值、单位、异常、状态/顺序、seed 与 UTF-16 的映射；下层只暴露本项目需要的稳定接口。
2. 先评估已有 Python 候选的相关调用面；相关行为完全一致则复用，有局部差异则加适配层，核心算法不同或缺少能力则重写。候选与上游的名称、示例相似都不计为等价证据。
3. 新 Python 第三方依赖引入前检查其生产依赖闭包、Python 3.13/Windows/Linux 路径、源码与许可；不允许包装 JS、启动 Node/browser 或退到另一个 native 渲染器。
4. 按最新用户策略，P1 只做必要编译/import/接线机械检查；全功能源码收口后 P2 设计用例/单测，P3 排查修复时只回跑变更调用面和受影响项，P4 最后统一全量。不把源码齐备或局部通过写成全量成功。
5. DOM/浏览器机制按用户授权直接替换，记录其功能如何由 Python/Canvas 承接；其他计算/内容的排除仍需实际入口或功能证据。类型、测试、开发工具及所有来源边保持可追踪，不从原始完整树删除。

## 5. 已知未完成项

每个节点已有一个处理策略，但策略不是“候选已等价”或“迁移已完成”。待后续完成：实际 bundle/包内源码可达性、第三方 tarball 与许可、字体/图标/数学资源、所用 API/断言清单、候选差分验证与最终 Python 依赖锁。`trace-*` 策略明确表示先追踪，再实现相关 Python 表面或证明可排除，不能直接当成删除许可。

完整包管理树和自底向上索引已可用于排优先级；完整 Mermaid 移植仍按 [实施方案](IMPLEMENTATION_PLAN.md)、[任务清单](TASKS.md) 与兼容规则验收，M1-06 尚未整体完成。

## 6. 新会话复核

以下都在仓库根目录执行，生成与检查不联网、不安装包、不执行 Mermaid 或候选库：

```shell
python scripts/upstream.py check
python scripts/audit_dependencies.py --check
python scripts/build_dependency_tree.py --check
python -m unittest discover -s tests/dependencies -v
```

审阅过来源和策略变更后，用 `python scripts/build_dependency_tree.py --build` 同时重建四个视图；日常检查不能自动重写来掩盖漂移。修改 Python 候选研究资料不等于引入生产依赖，正式选型需单独记录来源指纹、pin 与对应验证。
