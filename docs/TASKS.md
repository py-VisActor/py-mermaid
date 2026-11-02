# 分阶段任务与验收

状态是当前事实；目标不等于实现。[完整实施方案](IMPLEMENTATION_PLAN.md)解释范围、架构、源码发现、算法依赖和决策点；所有 diagram/跨图能力详见 [compatibility.json](compatibility.json)。以下任务均为计划，不表示代码已存在。

| 阶段 | 工作与产物 | 进入下一阶段的门禁 | 当前状态 |
| --- | --- | --- | --- |
| M0 启动 | src 分层、开发依赖、来源锁、文件盘点、启动/兼容/测试资料、Canvas 依赖示例 | bootstrap/负控制通过，上游 SHA 与索引一致，真实 Canvas 输出已检查 | 已建立，实际验证见 RELEASE_STATUS |
| M1 spec 与宿主审计 | 从 368 个测试文件及补充内联/动态入口拆用例/断言；2366 个 fixture 关联图种/配置/资源；API、JS 值、DOM/HTML/CSS/math/interaction 对应；source map | 无无归属源文件/断言，逐项默认值与错误可追踪；不可等价项保留 open 并取得必要决策 | 待实施 |
| M2 官方 oracle | 固定 Node/npm integrity/浏览器/字体/layout/plugin；共享 fixture；parse/model、SVG、DOM geometry、PNG 采集及比较；负控制 | 同输入重采稳定，故意破坏模型/尺寸/像素会失败；报告原始差异；不依赖 JS runtime 的 Python runner 建立 | 待实施 |
| M3 首个垂直切片 | flowchart preprocessing/grammar/model/默认 ELK/Skia PNG；节点/标签边/子图/非法输入/frontmatter/theme/htmlLabels；独立断言 | 官方 A 语义/布局与 Python 候选比较；默认 ELK 路径真实实现；GPU/CPU 分组；非空输出、字体/线程/导出；未支持配置明确失败 | 待实施 |
| M4 公共渲染与图布局 | shape/marker/path/intersection、文字/HTML/Markdown/math、style/theme、Dagre/完整 ELK/tidy、swimlane、Cytoscape 系/D3/Venn；资源策略 | 共享边界/复杂标签/路由/选项逐项对照；不把不等价布局库当原实现 | 待实施 |
| M5 主要图种 | sequence、class、state、ER、requirement、gantt、journey、gitGraph、pie、quadrant、XY、timeline、mindmap、Sankey | 每个图种按 parser/layout/canvas 阶段验收，合法/非法/config/theme 全留证据 | 待实施 |
| M6 剩余图种与扩展 | C4、block、packet、kanban、architecture、radar、treemap、swimlane、agentflow、eventmodeling、treeView、ishikawa、venn、usecase、wardley、cynefin、railroad 四种、info、ZenUML、flowchart-elk | 37 core detector + plugin 和 error/frontmatter 诊断无遗漏；扩展独立许可/资源/依赖验收 | 待实施 |
| M7 全量与可靠性 | 全 spec、配置/主题、a11y/交互元数据、security、资源、离线、字体/CJK/RTL/emoji、UTF16、所有导出、性能/上限、并发/GC/取消 | 全清单有终态证据；Windows/Linux、GPU/CPU/no-loader 与不同导出独立验收；无隐藏 skip | 待实施 |
| M8 打包与发行 | 新候选 wheel、隔离安装、无 Node/浏览器/源码运行、第三方许可、文档/实际示例、发布元数据 | 同一候选字节全部门禁通过；按实际授权发布并下载核 SHA；受支持范围准确 | 待实施 |

M5/M6 顺序是规划，不缩减总分母。alpha 可以在真实功能子集通过后另行准备，必须声明准确范围；全量完成必须 M1/M7 清单闭环。

## 任务依赖与结项规则

主依赖为 M0 → M1 → M2 → M3 → M4 → M5/M6 → M7 → M8。允许 M1/M2 六组局部契约先支撑 M3 限定试验，同时持续全量审计；不能把局部通过记成整个 M1/M2 完成。高风险布局/宿主/许可审计从 M1 开始，对应共享工作包验收后再扩大图种实现范围。

任务结项至少绑定 assertion ID、实际源码 SHA、独立回归与证据；清单/schema/方案本身完成不等于实现完成。各图种的 parser/layout/canvas 状态只在其适用断言完整通过后提升，已通过子集单独记录。所有任务当前待实施，M0 的已有范围见 [RELEASE_STATUS](RELEASE_STATUS.md)。

## 可执行工作分解

表内路径为拟建产物，实际创建时同步 source map、测试和链接。依赖编号表示前置产物，不要求无关工作停等。

| 任务 | 工作与可审阅产物 | 依赖/结项检查 |
| --- | --- | --- |
| M0-01 起点复核 | 备份已有脏树、来源/环境指纹、新 run；bootstrap/负控制/upstream 校验 | 每批重复；不复用失配 SHA 的旧结论 |
| M1-01 清单协议 | 用例/断言/资源/source map 的 schema、ID 和状态规则 | M0-01；重复 ID、丢归属/证据、伪通过能被拒绝 |
| M1-02 补齐来源 | 内联测试、参数化/动态生成器、snapshot、fixture 配置/资源、非测试公开行为的补充索引 | M1-01；保留原 2806 文件索引，补查 `gitGraphParser.ts` 等内联测试 |
| M1-03 registry/配置审计 | 实际 detector 注册顺序/别名/副作用、full/tiny、schema/defaultConfig/调用处、11 主题及所有 look | M1-01；不能把 import 顺序当检测优先级；核实默认 ELK |
| M1-04 六组首批断言 | 基础图、标签边、子图、非法输入、frontmatter/theme、htmlLabels；逐组原文/config/期望/错误 | M1-02/03 对应局部完成；断言不是仅六张截图 |
| M1-05 Python/JS 契约 | API/类型/默认格式/异常/CLI/async 设计，JS 值/数值/UTF-16/日期、owner 和状态隔离 | M1-03/04；接口仍标设计，未实现调用不作可运行示例 |
| M1-06 宿主/依赖审计 | HTML/CSS/math/交互/安全/资源映射，ELK/字体/ZenUML 等来源、传递版本和许可 | M1-02/03；open 项和需决策差异完整保留 |
| M1-07 解析器技术验证 | 一个 Jison 和一个 Langium 入口；词法/歧义/恢复/错误位置、Python 生成/移植方式 | M1-04/05；无运行时 JS；选型绑定锁定 grammar 与证据 |
| M1-08 全量清单闭环 | 全图/跨图断言、port-map、宿主映射、资源 manifest 与无遗漏审计 | M1-01…07；全部来源有归属、必要决策有记录，未知数量不能写成 100% |
| M2-01 锁定官方 A | Node/包 integrity/browser revision、full/tiny 身份、插件/字体/locale/viewport | M1-03/06；核查 npm 发行物与源码行为关系，不能静默换基线 |
| M2-02 共享 fixture 协议 | 输入/config/theme/look/layout/seed、资源/字体 SHA、预期错误与 case 关联 | M1-01/04、M2-01；A/B 使用同一输入字节 |
| M2-03 语义采集 | detect/parse/DB→规范化 model、最终 config、诊断及原始来源 | M2-02；逐图适配，保留未知字段/异常 |
| M2-04 视觉/布局采集 | 原始 SVG、DOM/路径/label/marker/computed style、PNG/RGBA、稳定性记录 | M2-02/03；等待字体/图片/异步布局，保存原始输出 |
| M2-05 Python runner | 新候选包隔离执行，记录 model/layout/display/output、环境和 wheel/native SHA | M1-05、M2-02；产品路径无 Node/浏览器/参考源码依赖 |
| M2-06 比较器/profile | 模型/错误、几何/样式、尺寸/原始像素/差异图、导出结构 | M2-03…05；完整报告，无私设容差或图像后处理 |
| M2-07 负控制/全量接入 | 节点属性/box/端点/尺寸/单像素/错误/字体 SHA 破坏；各图采集接入 | M1-08、M2-06；破坏均失败、重复采集有证据；局部试验单独结项 |
| M3-01 预处理与检测 | 原文→frontmatter/directive/注释处理→有效 config/detector，保留位置映射 | M1-04/05/07、M2 局部闭环；顺序/优先级/错误符合 A |
| M3-02 grammar/model | flowchart 六组输入的合法/非法 grammar、typed model、引用/嵌套/diagnostics | M3-01；独立模型/source span 断言 |
| M3-03 标签与样式测量 | 对应 theme/style/htmlLabels、真实 Canvas 测量与最小宿主排版 | M1-06、M3-02；owner 线程、同字体、不能读 oracle 尺寸作生产输入 |
| M3-04 最小默认 ELK | 六组用例所需的真实 ELK/端口/分组/路由路径 | M3-02/03、M1-06；默认值保持 `elk`，未支持选项明确失败 |
| M3-05 Canvas PNG | shape/path/marker/label/clip/viewport→公开 Canvas 绘制/bytes | M3-03/04；实际内容/尺寸/像素与 A 逐层比较 |
| M3-06 隔离与设备 | 新候选包、GPU/CPU、owner、错误恢复与连续渲染状态隔离 | M2-05/06、M3-05；限定功能子集验证，非完整图种验收 |
| M3-07 可见交付 | 可运行 Mermaid 例子、未经后处理的输出、provenance、双语入口及限制 | M3-06；实际图已查看，所有差异如实记录 |
| M4-01 公共几何 | shapes/paths/intersections/marker/clip/transform/groups/viewport | M3；形状目录与边界、端点、层叠逐断言 |
| M4-02 完整标签/宿主 | 文本/HTML/Markdown/math、CSS/box model、复杂字体与换行 | M1-06、M3-03；不可等价项按决策记录，不剥内容 |
| M4-03 配置/主题/look | 完整 schema/defaults/级联、11 主题、handdrawn/RoughJS/seed | M1-03/06、M4-01/02；完整默认与随机模式独立检查 |
| M4-04 Dagre/graphlib | 图结构、rank/order/坐标、复合图/自环/多边、路由和标签 | M1-06、M4-01/02；算法/选项/tie-break/数值来源可追踪 |
| M4-05 完整 ELK/插件 | M3 路径扩至所有适用选项/preset/别名、其他 ELK 算法、注册/fallback | M3-04、M4-01/02；按算法和选项结项，不把最小路径当全部完成 |
| M4-06 swimlane 管线 | 泳道/分组、分层/排序/坐标、正交路由、后处理与验证器 | M1-06、M4-01/02；DDLT 等数据只作测试，不注入生产 |
| M4-07 树/力导向 | tidy-tree、cose-bilkent、architecture/fCoSE 约束及随机状态 | M1-06、M4-01/02；seed/停止条件/分组独立验收 |
| M4-08 D3/专用计算 | Sankey/hierarchy/treemap、scales/axes/arcs/curves、Venn、日期/时间轴 | M1-06、M4-01/02；数值、单位、排序和算法来源 |
| M4-09 资源/安全/元数据 | 图标/图片/字体、离线策略、sanitizer/URL、a11y/link/click、扩展 API | M1-05/06、M4-02/03；缺资源/恶意输入/注册错误有负例 |
| M5-01 关系图 | classDiagram/stateDiagram/er/requirement 的完整逐图包 | 对应 M4 工作包；逐图 grammar/model/layout/canvas/config 正负例 |
| M5-02 时序与流程 | sequence/gantt/journey/gitGraph/timeline 的完整逐图包 | 对应 M4 工作包；专用排布、日期/分支/循环及错误 |
| M5-03 数值与树 | pie/quadrantChart/xychart/mindmap/sankey 的完整逐图包 | 对应 M4 工作包；数值、坐标/轴、树/力导向和流量 |
| M5-04 flowchart 扩全 | M3 之外全部 flowchart grammar/shape/config/layout/look 断言 | M1-08、M2 全量接入、对应 M4；六组以外无隐藏遗漏 |
| M6-01 业务/分组 | c4/block/kanban/packet/architecture/radar/treemap 的完整逐图包 | 对应 M4；分组、栅格/位宽、端口、极坐标/面积 |
| M6-02 扩展专用图 | agentflow/swimlane/eventmodeling/treeView/ishikawa/venn/usecase/wardley/cynefin | 对应 M4；各自完整 grammar/语义/几何/资源断言 |
| M6-03 四种语法图 | railroad/railroadEbnf/railroadAbnf/railroadPeg | 对应 M4；四入口、组合/选择/重复与注释 |
| M6-04 别名与诊断 | flowchart-elk/info、error/---，detector 优先级/配置副作用 | M1-03、M5-04；与完整默认 ELK 路径一致，信息/错误独立验 |
| M6-05 ZenUML | 插件及 @zenuml/core 的 Python grammar/model/layout/render | M1-06、对应 M4；单独依赖/许可/资源，不用 JS 插件代渲染 |
| M7-01 全清单核对 | 37 core + ZenUML + 诊断 + 13 跨图能力，断言终态与来源一致 | M1-08、M2、M5/M6；失败/open/未验不计通过，无隐藏 skip |
| M7-02 字体/格式矩阵 | CJK/RTL/emoji/fallback、PNG/JPEG/WebP/SVG/PDF、density/background/metadata | M4/M5/M6；有损格式、向量结构/指定栅格器分组 |
| M7-03 平台/设备/部署 | Windows/Linux、auto/CPU/GPU-required/no-loader、无仓库/JS/网络隐式依赖 | M7-01/02；缺硬件/字体记未验，CPU 不替代 GPU |
| M7-04 生命周期/安全/性能 | owner/worker/GC/取消/恢复/并发、恶意输入/资源上限、耗时/峰值内存 | M7-01；不改变设备/线程默认值；随机/确定性分别检查 |
| M8-01 产品入口与候选 | 定稿 API/文件/CLI，候选 wheel、实际包内容、依赖/许可/元数据 | M1-05、相关实现；本地准备可早做，发行结项需 M7 |
| M8-02 同候选发行验收 | 相同 wheel 字节两平台隔离安装/真实渲染，README/例子和已知限制核对 | M7、M8-01；源码/构建变化后重验，不沿用旧包结论 |
| M8-03 按授权发布 | commit/push、远端 CI、Release/索引及重新下载核 SHA 分开登记 | M8-02 及实际授权；不发布占位包 |

## 下一批的具体交付

先执行 M1-01…06 与 M2-01…04 的六组限定工作，不同时批量生成几十个 parser/renderer。下一批至少留下：

1. 可验证的 ledger/source map schema 和六组真实 case/assertion，包含正负/边界、源码 SHA、config 与资源。
2. 实际 detector 顺序、默认 ELK、schema/defaultConfig/JS 值/UTF-16 与 API/owner 草案，内联测试等来源缺口清单。
3. ELK、HTML/math、字体与插件的依赖/许可/宿主映射和未决事项；无需等待决策的独立工作继续。
4. 锁定官方 A 的环境与身份核查，以及六组实际 model/error/config/SVG/geometry/PNG/RGBA 产物；采集失败原样保留。
5. 新 `docs/changes/<task-id>.json` 与 run 记录，明确只是局部契约/采集，尚未完成的全局 M1/M2 及 Python 实现保持待实施。

随后推进 M2-05…07 的局部比较与负控制、M3-01…07 的真实默认 ELK 切片。显式 Dagre 原型不满足 M3 默认布局门禁。总工期在 M1 得到断言规模、M2/M3 得到实际吞吐后估算，当前不虚报日历承诺。

每批先保存起点、记录验收与资源，再实现、构建候选、检查、更新资料、登记证据。`docs/changes/<task-id>.json` 至少包含 `baseCommit / startingStatus / objective / acceptanceCriteria / sourceSha256 / commands / evidence / documentationReview / limitations / nextStep`。命令写实际参数、退出码、日志和报告 SHA，不能手填不存在的通过结论。
