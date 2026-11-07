# 图种与兼容范围

[用户文档](../README.md)

## Mermaid 文本

按以下首行或语法头选择图种。方言基于 Mermaid 12.2.0；py-mermaid 的业务图与 VChart 扩展不保证能在其他 Mermaid 工具中使用。

| 类别 | 语法头 |
| --- | --- |
| 流程图 | `flowchart LR`、`graph TD`、`flowchart-elk` |
| 建模 | `classDiagram`、`stateDiagram-v2`、`erDiagram`、`requirementDiagram`、`usecase-beta` |
| C4 | `C4Context`、`C4Container`、`C4Component`、`C4Dynamic`、`C4Deployment` |
| 时序 | `sequenceDiagram`、`zenuml` |
| 时间与过程 | `gantt`、`journey`、`timeline`、`gitGraph` |
| 层级 | `mindmap`、`treeView-beta` |
| 结构 | `block-beta`、`packet-beta`、`kanban`、`architecture-beta` |
| 业务 | `swimlane-beta`、`agentflow-beta`、`eventmodeling`、`ishikawa-beta`、`wardley-beta`、`cynefin-beta` |
| 铁路语法 | `railroad-beta`、`railroad-ebnf-beta`、`railroad-abnf-beta`、`railroad-peg-beta` |
| 图表 | `pie`、`quadrantChart`、`xychart-beta`、`radar-beta`、`treemap-beta`、`sankey-beta`、`venn-beta` |
| 信息 | `info` |

另有 [VChart 图表输入](VCHART.md)：Python spec、严格 JSON 和 `vchart <type>` DSL。

## 流程图示例

```text
flowchart LR
    A@{shape: doc, label: "Input"} --> B{Valid?}
    B -->|Yes| C[Save]
    B -->|No| A
    classDef selected fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
    class C selected
```

支持 TB/TD、LR、RL、BT 方向、子图、边标记与线型、节点和连线样式、形状声明、静态折叠状态及手绘外观。适用的富标签支持 Markdown 和 `$$...$$` 数学；普通文字标签按其分支保留文字含义。

默认 ELK 布局，以及适用图种的专用布局可用；没有 Dagre 选项或算法回退。不同图种的配置和标签含义可能不同，不能将一个图种的全部字段直接套用到另一个图种。

## 兼容边界

- 所有输出为静态画面，SVG/PDF 不包含浏览器 DOM、事件处理、点击导航或交互无障碍行为。
- 不提供动画、Dagre、video/audio、任意浏览器 HTML/CSS 扩展或 3D。
- 字体、换行、自然尺寸、抗锯齿和有效路由可能与浏览器实现不同，不承诺像素一致。
- 图片、图标和字体必须显式提供，见[资源指南](RESOURCES.md)；不自动下载外部字体或图标 CSS。
- 图表具体字段和限制由 [py-vchart 用户文档](https://github.com/py-VisActor/py-vchart/blob/main/docs/README.md) 管理，类型注册数量不表示所有 VChart JavaScript 选项均兼容。
- 不支持的输入和选项会明确报错；例如经典 `A(-Ellipse-)` 会触发固定来源缺少形状处理器的 `UPSTREAM_SHAPE_MISSING`。

更多完整文本示例见[示例目录](../../examples/README.md)。
