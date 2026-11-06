# 批量静态迁移接口 v1

2026-11-06，本接口由 root 唯一维护。用户已恢复批次，继续暂缓 pie、quadrantChart、xychart、radar、
treemap、sankey、venn 共 7 个入口。本批调整为 29 个新增入口 + 2 个流程图回归入口，共 31 个；
13 项跨图能力按保留图种的适用范围收口。上游 38 入口来源清单保留。Dagre 与交互依既有用户决定排除。
以下文件 owner 为当前执行责任边界；暂缓目录只保留既有成果。

## 文件 owner

- root：`model/scene.py`、`runtime/**`、`rendering/skia/scene.py`、`api.py`、`__init__.py`、
  总注册、包元数据、工具与总状态。现有 flowchart 管线保持兼容。
- A：`diagrams/modeling/**`（classDiagram/stateDiagram/er/requirement/usecase/c4）、
  `diagrams/hierarchy/**`（mindmap/treeView；treemap 暂缓）、`diagrams/structures/**`
  （block/packet/kanban/architecture）；对应独立 source maps。
- B：`diagrams/temporal/**`（gantt/journey/timeline/gitGraph）、
  `diagrams/business/**`（swimlane/agentflow/eventmodeling/ishikawa/wardley/cynefin）。
  `diagrams/charts/**` 与 `diagrams/flows/**` 本批暂缓。
- C：`diagrams/sequence/**`、`diagrams/railroad/**`（四入口）、`diagrams/zenuml/**`、
  `diagrams/info/**`。对应独立 source maps。

如确需公共扩展，先发 root，不交叉修改。每个图种需真实专用语法、模型、算法、配置、
样式与错误路径；不得把所有语法投影成万能流程图/圆点网格作为实现。

## 模型和模块协议

公共类型位于 `py_mermaid.model.scene`：

```python
@dataclass(frozen=True)
class Diagram:
    kind: str
    source: SourceDocument
    config: tuple[tuple[str, object], ...]  # recursive freeze_value
    model: object  # family-owned frozen dataclass/tuples/scalars
    diagnostics: tuple[str, ...] = ()

@dataclass(frozen=True)
class TextBox:
    text: str
    width: float
    height: float
    ascent: float
    descent: float
    runs: tuple[MeasuredTextRun, ...]
```

每图种模块导出：

```python
def parse(document: SourceDocument, config: dict) -> Diagram: ...
async def build(diagram: Diagram, painter: Painter) -> Scene: ...
```

`document.cleaned` 为去 frontmatter/directive/comments 的输入，映射保留在原文。
`config` 为经全局与图种 defaults、site/frontmatter/directive 合并后的原生字典。
用 `runtime.common.make_diagram(kind, document, config, model)` 构造纯值 Diagram；
`runtime.common.config_dict(diagram)` 返回独立解冻字典。错误使用既有 MermaidError，
`runtime.common.error(document, offset, message, code='SYNTAX_ERROR')` 创建含原始 span 的异常。
空行/分号/引号/嵌套结构不能仅靠逐行 split 粗略模拟全部 grammar。

## Painter 公共方法

Painter 位于 `rendering.skia.scene`，由 root 唯一实现，是 owner-thread 原生会话。
图种 build 只调用以下方法，不直接 import py_skia_canvas。

```text
p.config                             # dict for this diagram; do not mutate
p.measure(text, *, size=None, family=None, weight='normal', italic=False,
          html=None, width=None, align=None, label_kind='text', style=None) -> TextBox
p.text(text_or_box, x, y, *, size=None, family=None, weight='normal',
       italic=False, color=None, align=None, html=None, width=None,
       id='', role='label', rotation=0, label_kind='text', style=None, clip=None) -> TextBox
p.rect(x,y,w,h, *, fill=None, stroke=None, line_width=None, radius=0,
       dash=None, id='', role='shape', opacity=None, style=None)
p.ellipse(cx,cy,rx,ry, *, fill=None, stroke=None, line_width=None, id='', role='shape', opacity=None, style=None)
p.path(d, *, fill=None, stroke=None, line_width=None, dash=None, id='', role='path', opacity=None,
       transform=(1,0,0,1,0,0), style=None, rough_options=None)
p.line(x1,y1,x2,y2, *, stroke=None, line_width=None, dash=None, id='', role='line', opacity=None, style=None)
p.polyline(points, *, stroke=None, line_width=None, dash=None, id='', role='edge', opacity=None, style=None)
p.polygon(points, *, fill=None, stroke=None, line_width=None, id='', role='shape', opacity=None, style=None)
p.marker(x,y,dx,dy, *, kind='point', size=8, color=None, fill=None, id='', line_width=1)
p.asset(resource_id,x,y,w,h, *, kind='image', id='', color=None, style=None)
p.finish(*, width=None, height=None, padding=None, background=None,
         layout=None, measured=(), diagnostics=()) -> Scene
```

marker kind 支持 point/open/extension/aggregation/composition/dependency/lollipop/
circle/cross/bar/crow/one/zero；端点多标记可组合调用。text 使用现有富标签与正式数学包。
图种可直接使用既有 Point/Box/DrawEvent 等纯数据。primitive 绘制均会记录 trace。
`finish` 根据真实命令/文字边界与指定尺寸联合决定画布，不裁切负坐标内容。
family 的源码逻辑负责正确的相对关系，不能用增大画布掩盖重叠或布局错误。

`p.font_size(value, *, base=None, family=None, weight='normal', italic=False) -> float`
按原生宿主 CSS 字号合同返回 px。`base` 是源父节点的计算字号，不是该配置项默认值；
未提供时使用当前标签根字号。em/% 基于该父字号、rem 基于 16px 根、物理单位按 96dpi。
ex/ch 由公开 Canvas 的实际 x 字形 ink/零字形 advance 换算，保持创建线程所有权；
错误单位明确失败。只有原源码真正消费 CSS 的配置项调用该接口，源码拼接 `number + 'px'` 的项不额外扩展单位。

`DrawEvent` 兼容追加 `dash: tuple[float,...]=()`；场景 path 记录实际提交给 Canvas 的 dash，
marker 的实际 kind 记录于既有 `marker` 字段。二者是绘制证据，不代替 PNG 或独立源码几何断言。

## ELK 通用输入

`runtime.graph.layout_graph(nodes, edges, *, direction='TB', parents=(), options=None,
node_spacing=50, rank_spacing=50)` 为 async 真实 pyelk 布局。

- nodes：序列字典 `{id,width,height,parent?}`，尺寸来自 Painter.measure/专用节点尺寸。
- edges：序列字典 `{id,source,target,label?,label_width?,label_height?,source_port?,target_port?}`。
- parents：序列字典 `{id,parent?,padding?,title_height?}`。
- 输出 `GraphLayout`：`nodes: dict[id,Box]`、`edges: dict[id,tuple[Point,...]]`、
  `groups: dict[id,Box]`、`labels: dict[id,Box]`、width/height/engine/version。

该 adapter 不作算法回退。真实原实现使用 tidy/COSE/fCoSE/Sankey/Venn/泳道等的图种，
必须移植其实际专用数值/布局，不能用 ELK 替换后登记全部兼容。

## 阶段与验收

### v1 兼容扩展（2026-11-06）

- `measure`、`text` 追加 `label_kind='text'|'markdown'`、`style: ResolvedStyle|None`。
  预测量 TextBox 已包含嵌套 runs 的完整样式；绘制时不覆盖其局部透明度/装饰。
- `style(classes, tag='rect', id='', base=None, ancestors=()) -> ResolvedStyle`：
  `base` 为源 palette 的字段字典或 ResolvedStyle；祖先为 `(tag,classes,id)` 序列。
  源 classDef/inline 在 CSS 后按来源级联；primitive 显式 paint 参数覆盖 `style`，
  因此最终样式调用只传 `style=`，不要再次显式传旧 palette。
- `rect/ellipse/path/line/polyline/polygon` 追加 `style=`；原生实现渐变、阴影、blend。
  ResolvedStyle 追加 `fill_gradient`、`gradient_direction=(0,0,1,0)`、
  `blend_mode='source-over'`、`text_stroke_color`、`text_stroke_width`。
- `path` 追加纯 affine `transform=(1,0,0,1,0,0)`；`asset` 追加 `color=None`。
  允许安全自包含 data URI；`svg(svg,x,y,w,h,id='',color=None)` 为相同资源路径便捷入口。
- `shape_geometry(kind,label_width,label_height,padding=None,metadata=(),direction='TD')`
  复用既有固定源 shape provider，返回纯 ShapeGeometry。
- `viewport_width` 为显式 config.viewportWidth，未提供时原生宿主 1200。
- `rough_enabled=False`；只有固定源实际支持手绘的 renderer 才在 build 中设 True。
- `runtime.common.label_config(config)` 与 `sanitize_text(text,config)` 是无 native 的共享清洗入口。
- ELK parents 允许 `direction='TB'|'BT'|'LR'|'RL'`；输出用不可变 Mapping，保留 get/items/索引访问。
- `html=None` 为 measure/text 默认，按有效根 htmlLabels / flowchart.htmlLabels / True 选择；
  显式 True/False 仍覆盖，原源要求 SVG literal text 的图种应显式 False。
- `style` 追加 `inherited=`，并在纯 `ResolvedStyle.paint_context` 保存祖先选择器上下文，
  嵌套 HTML/SVG 可保留真实父级样式与相对字体含义。
- `render_id` 读取原生宿主显式 `config.renderId`，缺省为 diagram.kind；Cynefin 的
  seed=0 按原 resolveSeed 消费此值。它适配 source render(id)，不冒称原 JS 固定该 id。
- `text(...,clip=Box|tuple[x,y,w,h])` 对全局 logical 坐标施加原生 clip，先裁再文字旋转；
  bounds 与 trace.clip 记录可见区域。图种负责源 line-clamp/ellipsis 的实际内容分配。
- `_explicitRootLayout` 只标记用户根 layout 的真实 presence，供 mindmap 原源 rootNode 布局选择；
  `_explicitLayout` 另外包含通用 scoped presence，不得混用。
- `runtime.layouts.register_layout(name, asyncprovider | 'module:symbol', algorithm=None)`
  注册原生纯值布局；签名为 layout_graph 的参数，返回 GraphLayout，不提供算法回退。
  `layout_graph` 追加 `config=None,algorithm=None`；ELK 使用固定源 elk.* 名称和策略。
  `finish_graph` 产生 rounded/straightenEdges/lineHops，输出 `edge_paths` 与保留原始的 `raw_edges`。
  图种在形状裁切后再次调用 finish_graph；绘制必须消费 edge_paths。
  nodes 的 `spreadPorts=True` 按 createElkNode 设置隐式 port 的 CENTER alignment，
  不以显式 port 或无效 port spacing 选项替代。
- 原源复用 flowchart renderer 的图种使用 `measure_flowchart(flowchart)` 获取完整测量和 annotations，
  `flowchart_scene(flowchart,FlowLayout,measured=...,annotations=...,group_overrides=())` 返回纯 FlowchartScene。
  专用泳道框通过 `p.rect/path/text` 生成 commands，每组 `p.take_commands()` 取出并清空，
  `group_overrides=((group_id,commands),...)` 在对应 group 的原绘制位置替换 frame/title；
  其余完整 F01 绘制分支和线程所有权不变。所有 override.bounds 进入视口预算。

### 泳道路由子租约

C 组另外独占 `diagrams/business/_swimlane_routing/**`，只写路由、方向和后处理；
B 的 business 写入边界排除该子目录。B 独占 `_swimlane_sugiyama.py`、
`_swimlane_prepare.py`、`_swimlane_intersect.py` 与 `swimlane.py`，负责组装和测量/绘制。
纯入口 `route_and_postprocess(layout:dict,direction:str)->None`，只修改 B 新建的局部数值字典。
节点 x/y 为中心坐标、初始 TB；输出最终方向的节点/路线与 label-node 坐标；不跨此边界传 native。

P1 允许来源阅读、纯语法编译/import/注册检查；暂不运行行为单测、图像与 oracle。
每个 owner 的 P1 回执必须标明已完成的实际分母、源码 SHA、原文件/符号和剩余缺口。
源码收口后才建立来源独立测试，再分组首跑、保留全部失败、统一修复与最终完整矩阵。
用户要求完整批量执行，不能完成一个切片就交付“后续再做”的停止点。
