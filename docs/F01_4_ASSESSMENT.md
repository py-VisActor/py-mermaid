> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

# F01.4 静态扩全评估与历史布局来源

2026-11-05。依据固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b` 的本地源码。本文是范围评估，不是 F01.4 已实现或 Dagre 已选型的声明。全项目遵守 [仅静态渲染](STATIC_RENDERING_SCOPE.md)，Dagre 已按用户决定从目标功能、选项和依赖中排除。来源文件及 SHA 见 [机器记录](../references/f014-dagre-assessment.json)。

## F01.4 静态功能分组

| 分组 | 保留内容与主要改造 |
| --- | --- |
| 语法/模型 | 补根方向、批量连接、属性块、边 ID、样式与静态配置；补充 marker/线型/长度约束/资源等纯值合同 |
| 边/曲线 | 无箭头/双向/圆点/叉号、粗虚线和不可见边、自环/多重边、曲线、端点裁切、边标签与几何边界 |
| shapes/样式 | flowchart 可达的新形状和别名、测量/轮廓/交点；style/classDef/class/::: /linkStyle 的静态样式与优先级 |
| ELK | Mermaid 暴露的算法、preset/层/排序/放置/组配置，微折线整理和交叉跳线；复用现有 py-elk，不重写算法 |
| 手绘/资源/标签 | 确定 seed 的手绘路径，显式离线图标/图片/字体，数学等剩余静态标签能力 |
| 静态导出 | 复用公开 Canvas PNG/SVG/PDF 等实际导出能力，核对视觉与格式结构，不建设交互 SVG、动画播放器或链接宿主 |

共享 shape 注册表中的其他图种形状不自动计入 flowchart；py-elk 的完整算法清单也不自动成为 Mermaid 配置接口。先形成 source/case/assertion 分母，区分静态保留、交互排除和源缺陷。

## 原实现如何选择 Dagre

1. 根 schema 的 `layout` 默认是 `elk`。流程图 `flowRenderer-v3-unified.ts::draw` 从有效配置读取 layout，调用 `getRegisteredLayoutAlgorithm(layout)`，再进入共享 `render(data4Layout, svg)`。
2. `rendering-util/render.ts::registerDefaultLayoutLoaders` 始终注册 `dagre` 的懒加载器；完整构建还注册 ELK 等大型功能，tiny 构建不注册 ELK。
3. `getRegisteredLayoutAlgorithm` 首先使用已注册的请求算法。未注册时尝试给定 fallback，最终回退 `dagre`。这是注册/选择阶段回退，不是 Dagre/ELK 计算抛错后自动切换引擎。
4. 所以固定基线的完整流程图默认走 ELK；显式 `layout: dagre` 走 Dagre；tiny 缺 ELK 或请求算法未注册时可以走 Dagre。不能将其他 Mermaid 版本的一般默认值代入本项目基线。

来源：`packages/mermaid/src/schemas/config.schema.yaml` 的根 layout；`rendering-util/render.ts` 的 `registerDefaultLayoutLoaders/getRegisteredLayoutAlgorithm/render`；`diagrams/flowchart/flowRenderer-v3-unified.ts::draw`。`flowRenderer-elk-default.spec.ts` 另覆盖缺省 ELK、显式 Dagre 等选择行为；它 mock 绘制，不能当作真实布局证据。

## 原 Dagre 的实际调用链

```text
parser / FlowDB.getData
  → LayoutData：节点、边、组、配置、方向与间距
  → prepareLayoutForDagre：构造复合多重图，改写组与自环
  → measureDagreLayout：取得真实节点/标签宽高，处理嵌套组
  → runDagreLayoutCore
      → dagreLayout(graph)：真实 Dagre 数值算法
      → applyDagreLayoutResult：转换/回写可用几何
  → common painter：静态节点、组框、边、marker、标签
  → 图标题与 viewport
```

`layout-algorithms/dagre/index.js` 直接从 `dagre-d3-es/src/dagre/index.js` 导入 `layout`，从该包 `graphlib` 导入图结构。固定依赖为 `dagre-d3-es@7.0.14`。

`prepareLayoutForDagre` 使用 `Graph({multigraph:true, compound:true})`，设置 rankdir、nodesep、ranksep、marginx/marginy，再以 setNode/setParent/setEdge 写入节点、父组与带 ID 的边。自环先增加两个虚拟节点、拆成三段，保留原边身份；后续合并为真正的逻辑自环，不能把辅助节点画出来。组和跨组边另经 `adjustClustersAndEdges` 处理。

`measureDagreLayout` 使用源渲染宿主的 shape/文字/边标签测量，不是将未测量的文本直接交给算法。复杂组包含递归测量与内部布局。之后才调用真正的 `dagreLayout(graph)`。

算法核心依次处理边标签占位、自环/去环、复合组与层级、rank、长边虚拟链、层内排序、坐标、恢复边/自环、标签坐标与边界交点等。rank 入口支持 network-simplex/tight-tree/longest-path，未指定时使用 network simplex；这不等于所有这些内部参数都已成为 Mermaid 的公开配置。

结果包含节点中心 x/y、复合节点宽高、边 points、边标签位置及总图尺寸。Mermaid 仍需转换组标题偏移、递归组坐标、自环和真实 shape 轮廓，并由共享 painter 生成可见曲线、marker 和标签；Dagre 本身不是 SVG 或 Canvas 绘制器。

源 `applyDagreLayoutResult` 自己标注了顶层归一化记录对递归组的限制：部分内部节点/边实际在递归测量与绘制中处理。因此后续对照不能只读顶层 LayoutData 就判定组内内容丢失，应同时采集实际静态绘制场景。

## 历史评估：当前不实施以下 Dagre 改造

移除交互逻辑不会移除 Dagre 的静态布局职责。可将需要的内容分为两层：

- 纯算法：有序复合多重图、去环/rank/order/position、虚拟节点及边路由，不依赖 DOM、事件或浏览器。
- Mermaid adapter：用 Canvas 实测尺寸组图，处理子图/跨组边/自环/标签，将结果转换为现有纯值布局与静态绘制指令。

源 Dagre 算法核心的主要值依赖是内部 graphlib、算法 helper 与 lodash-es 操作；D3/SVG painter 属于外层宿主。Python 无需引入整套 D3、DOM 或事件绑定来使用同一布局思路。用户现已决定不建立 Python Dagre 包、不移植其 adapter，不保留显式选择或回退；以下原调用链仅供来源追踪。默认 ELK 不变。


## 排除算法回退后，哪里仍必须使用 Dagre

2026-11-05，补查全部工作区 TS/JS 生产源码中的 Dagre 值导入、真实 layout 调用、detector/diagram/renderer 接线及配置选择。结论限定于固定基线的内置正常注册入口，属于静态来源审计，不是全部图种的运行验收。

| 情形 | 是否必须保留 Dagre 算法 |
| --- | --- |
| 用户显式选择 `layout: dagre`（全局、图种、frontmatter/directive 等最终有效配置） | 若要兼容该请求及其算法行为，则必须。ELK 可绘制同类图，但不等价于 Dagre |
| 默认流程图、类图、状态图、ER、需求图、用例图等统一渲染入口 | 未发现不可选择其他引擎的硬编码 Dagre；从有效配置选择布局，ELK 已注册时可用 ELK |
| 旧 classRenderer.js / stateRenderer.js / erRenderer.js | 这些文件直接调用 dagreLayout，但当前 class/state/ER detector 接入统一 renderer；文件存在不能作为当前默认入口硬依赖的证据。若另行保留或重新接入旧 renderer，需单独处理 |
| usecaseDb.getData 的 `layoutAlgorithm:'dagre'` 初值 | 不是最终选择：usecaseRenderer.draw 在 render 前用 getRegisteredLayoutAlgorithm(layout) 覆盖 |
| block/renderHelpers、createGraph 使用 graphlib | 图结构依赖，不是 Dagre 布局算法调用；Python 可用自己的有序/复合图表达 |
| flowChartShapes 引用矩形/多边形求交 | 纯几何工具，不要求保留 Dagre 算法，可由 geometry 模块承担 |
| 公共 renderer 清理 dagre/mermaid-graphlib 中的共享状态 | 源宿主组织耦合；不是 rank/order/position 算法必须执行的证据 |

因此，在用户已排除算法回退后，仍明确需要 Dagre 的是“显式 Dagre 算法兼容”。未发现其他当前内置默认图种的不可替代 Dagre 算法要求。若后续再决定不支持显式 Dagre，Dagre 可以从目标运行依赖和算法迁移范围移出；该决定现已由用户明确作出，目标 Dagre 已排除。`layout:dagre` 必须明确拒绝，不能静默交给 ELK；原始来源依赖树保持。

关键接线：`diagram-api/diagram-orchestration.ts`；`class/classDetector-V2.ts → classDiagram-v2.ts → classRenderer-v3-unified.ts`；`state/stateDetector-V2.ts → stateDiagram-v2.ts → stateRenderer-v3-unified.ts`；`er/erDetector.ts → erDiagram.ts → erRenderer-unified.ts`；`usecase/usecaseRenderer.ts` 的 layoutAlgorithm 覆盖。类图默认 ELK 与图种级显式 Dagre 另有 config.appearance.spec.ts 来源断言。
