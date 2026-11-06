# F01.4 流程图静态收口执行计划

2026-11-05，用户要求“继续完成流程图收口”。本轮覆盖 F01.1～F01.3 之后全部保留的静态流程图能力。最新用户回复明确：**数学模块独立后续实现，本轮先完成其余静态流程图能力。** [Dagre 完全剥离](LAYOUT_POLICY.md)、[所有模块仅静态渲染](STATIC_RENDERING_SCOPE.md)、安装验证暂缓继续有效。

## 交付分母

- 固定 flow.jison/FlowDB 的保留语法：方向/别名、批量连接链、所有普通边/标记/线型/长度、边 ID、旧属性语法和新 metadata、样式语句与 class、子图/嵌套/初始 collapsed 状态等；click 安全识别后忽略行为，仅保留初始可见样式影响。
- flowchart 可达的新形状及别名：固定 shapesDefs 的 53 个定义、141 个通过源 lowercase/no-underscore 检验的别名，加 state/choice/note/composite/icon/anchor 等可达入口；资源节点和 collapsed group 内部入口单列。经典 ellipse 源缺陷保留，不伪造修复。
- 有效语义和绘制样式：style/classDef/class/::: /linkStyle、声明顺序、线型、双端 marker、边动画 t=0 静态外观；无播放或事件宿主。
- ELK 顶层 7 个入口、源允许的组算法、13 个公开配置、4 个 preset，微折线整理/交叉跳线及真实路由/组尺寸。只复用 py-visactor-elk，不回退至其他算法。
- 确定 seed 的 handDrawn 路径与排线，离线图片/图标/字体及真实测量，PNG/JPG/WebP/SVG/PDF 的静态导出。

来源库存不是通过数。共享 shape 中其他图种专用且对 flowchart 不可达的入口不扩入；任意 ELK 原始 options/编译实验开关不发明成用户配置。数学、交互逻辑和 Dagre 各自按明确范围标记，不能混成“后续待补”分母。

## 执行顺序

S0 起点与固定来源 → S1 纯值合同/单文件 owner → S2 全部本轮源码及 source map（仅机械检查）→ S3 原实现驱动的独立测试/fixture/oracle设计 → S4 分组首跑、保存失败、根因批修 → S5 同候选最终测试、CPU/auto/GPU 与静态格式检查、HTML报告、人工看图和文档/账本。

初始源码 `f75ee6fa7fc7d0f3a04df190a125c8553599705c547258ae52c5f73a5b6ba76f`；起点备份 `test-runs/F01.4-execution-start-20261105T082500Z-149317c2`。现有未提交改动与旧报告保留，不安装验证、不提交推送。

## 分工

主协调：model/API、静态样式级联、新 shape 注册及纯几何、总状态/工具/报告。parser_config：config/parsing/flowchart parser、语法归约和源配置。geometry_elk：layout/elk、geometry/flowchart.py、geometry/edges（选项/真实路由/端点/marker/straightening/hops）。canvas_labels：rendering/skia、rendering/labels、resources 与独占的 geometry/rough.py（原生绘制/资源/手绘/静态导出）。接口细节见 [共享合同](F01_4_INTERFACES.md)。

## 执行结果

S0～S5 已完成本地静态范围验收；同候选 486 项测试、三后端矩阵、五种导出及 HTML/人工 QA 均通过。见 [验收记录](F01_4_ACCEPTANCE.md)。数学、Dagre、交互与安装各自维持本计划的范围决定。
