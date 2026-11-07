# F01.4 共享合同 v1

2026-11-05。所有字段兼容追加、默认值保持旧普通图行为。纯值中不放 Canvas、Image、Font 或其他 native/DOM 对象。模型已在 `model/flowchart.py` 追加，下面的名称为当前合同。

- FlowConfig：curve='basis'、elk_options（冻结键值）、hand_drawn_seed=0、deterministic_ids=False、deterministic_id_seed=None。layout 仅保留 ELK 家族；13 个公开 elk 项由 config 负责缺省/显式值区分，布局负责源派生选项。
- FlowNode：classes/styles 元组、metadata 冻结映射、props 冻结映射。metadata 保留源 key，资源字段 icon/form/pos/img/constraint/w/h 不另改命名。节点原 shape 字段使用 geometry.shape_registry.canonical_shape 的内部语义名。
- FlowEdge：现有 id=eN 不变；source_id、is_user_defined_id 供声明选择和来源身份；marker_start/end 为 none/point/circle/cross；stroke=normal/thick/dotted/invisible；min_length=1；curve 可空；classes/styles、animate/animation 和 metadata；edge_type 保留原 arrow_open/arrow_point/arrow_circle/arrow_cross/double_arrow_* 枚举。
- FlowGroup：classes/styles、metadata，保留 view/algorithm。collapsed 初始归约由 parser/FlowDB 层承担：隐藏后代、重写跨边和抑制折叠诱发自环；不能通过假布局代替。
- ClassDefinition(name, styles=(), text_styles=())，FlowClassDefinition 为同一类型别名；Flowchart.class_definitions/default_edge_styles/default_edge_curve。来源 classDef 的 shape/text style 数组可分开保存。方向扩 TD/TB/LR/RL/BT；源异常方向单列，不发明对角布局。
- ShapePart(path,fill='none',stroke='node',opacity=1)：path 是纯 SVG 路径值，paint 的 node/stroke/white/none 是语义引用，或明确字面色。MeasuredNode 追加 parts/assets；经典 outline/details 保持兼容。ShapeGeometry 由根在 geometry/shapes.py 兼容追加 parts，shape_geometry(...,metadata=(),asset_size=None) 的 asset_size 仅为纯自然宽高。
- MeasuredAsset(resource_id,box,kind='image',fit='contain',opacity=1)，box 为 node-local。MeasuredTextRun 追加 kind='text'/asset_id/asset_box 供 inline image；所有 native decode、测量、字体注册仅在 session owner。
- RoutedEdge 保留真实 sections，追加 paint_points、effective_curve、path、paint_bounds。path/bounds 为全局逻辑坐标的纯值；原 ELK sections 不被绘制后处理覆盖。源有路由时有效 curve=rounded，无路由时按源 linear；声明 curve 与实际 curve 分开记录。特殊非路由算法的源直线绘制不是算法回退。
- DrawEvent 追加 path/curve/marker/resource_id。只有实际 native 绘制后才记 trace，trace 不代替 PNG/矢量实际内容证据。
- ImageResource(id,data:bytes,mime='',sha256='')；IconResource(id,svg:str,sha256='')；FontResource(family,path,sha256='')；ResourceBundle(images=(),icons=(),fonts=())。字体路径必须由调用者显式提供，图片URL只可作显式bundle key，不自动联网。资源 owner 验证SHA/安全/预算，native缓存不出 session。
- ExportOptions(quality=.92,density=1,matte=None,outline=False,downsample=False)。API parse 保持纯解析；render/arender 追加 resources=None、export_options=None，format 支持 png/jpg/jpeg/webp/svg/pdf（raw 为 Canvas 原能力，不作为 Mermaid 对外必需格式）。session 接受 resources；render(...,format='png',export_options=None) 同线程编码。RenderResult.width/height 是真实输出尺寸，MIME 与格式一致；逻辑 layout 保持不因导出倍率而重算。
- 手绘纯计算归 geometry/rough.py，由 C 单独写：复用固定 roughjs4.6.6 所需 seeded随机流/double stroke/Bezier/scanline hachure，输出纯路径和真实边界。seed0 保留源随机语义，非零seed稳定；不对图片后处理。

单文件 owner：根 model/api/rendering/styles/geometry/shapes.py/geometry/shape_registry.py；A config/parsing/diagrams/flowchart；B layout/elk/geometry/flowchart.py/geometry/edges；C rendering/labels/rendering/skia/resources/geometry/rough.py。__init__ 聚合仅根修改或明确单独交接。S2 不写/跑行为测试或图片；先全部源码收口。

## S2 接线补充

- source INVALID split-link 保留 edge_type/stroke='INVALID'，min_length 可为 None；使用原渲染器的默认线型，不伪造解析拒绝或长度约束。
- FlowNode.color_index 保留初始 collapsed group 的原调色板序号。
- shape_geometry 追加 direction='TD'，forkJoin 在 LR/RL 为 10×70，其余为 70×10。shape_outline_intersection 接收测量 outline；正交路由沿端口轴，非正交路由按中心射线与真实轮廓相交；text/store/brace 按源虚拟矩形交点。
- PlacedNode.box 是 ELK 真实物理框；box/rectpacking 可按源规则扩张，MeasuredNode 的原轮廓/文字不缩放，绘制起点为物理框中心减测量尺寸之半。
- ResolvedStyle 追加 line_cap/line_join/dash_offset、letter_spacing/word_spacing（px 字符串）、text_transform/overflow_wrap/word_break/hyphens、text_shadows（dx,dy,blur,color 元组）。MeasuredTextRun 追加同名 spacing/shadows，保证 measure/draw/bounds 一致。全语言 hyphens:auto 无字典时明确诊断，不默默忽略。
- inline SVG 与 data:image;base64 属显式离线资源，校验后通过公开 Canvas Image 解码。audio/video 整体排除（含初始静态外观、封面/占位和控制条），无迁移或验收要求；数学独立后续。

## S4 来源边界与 paint 合同补充

- 九个源无标签形状的 label_width/height/lines/runs 均为零；保留输入语义 label，但不产生字体行高、空文字事件或最小文字宽度。
- ShapePart 追加 fill_style（hachure/solid）与 dash（None 继承、元组显式覆盖）；MeasuredNode/ShapeGeometry.paint_outline=False 表示 attachment 虚拟框由 parts 绘制。datastore 保留闭合填色，仅绘制横边；brace 的 source RoughJS stroke 子路径不虚构整块填色。
- PlacedNode/PlacedGroup 追加 paint_box。box 与 engine_origin 始终保留真实引擎值；固定源 alignDegenerateNodeToAnchor 在 paint_box 中记录小节点沿侧轴的平移，raw sections 不改、children 不随 group 平移，title_box 是最终 paint descriptor。不调用其他布局算法。
- 源 constructor 形状原型查询会返回成功但漏画节点，Python 提前明确拒绝；这属于上游静默漏画，不得误写成原实现必然抛渲染异常。radial 容器外框缺陷单列并保留原图。
# 人工 QA 修复补充

`rendering.styles.resolve_inline_svg_style(diagram, kind, semantic_id, *, tag, base, css_classes=())` 为直接内嵌 SVG 子图元计算宿主默认 CSS 与 themeCSS。kind 使用 node-label/group-title/edge-label；base 包含继承和 presentation attributes，SVG 元素自己的 inline style 在返回后应用并保留 important 优先级。它不把外层节点的本地 inline 绘制样式当作祖先样式，不对 img/data URI 内的 SVG 调用。生产端仍只传不可变样式值和资源字节。

来源 SVG 的 rough outline 也可能被 CSS 填色；状态圆按真实绘制顺序覆盖较早的 hatch。离屏 Canvas 含 source-in 的记录不能直接重放到不透明主画布，需先快照为 owner 线程的 Image 后绘制，或直接绘制有色 glyph，保留正确 alpha。


## Static collapsed child and literal text contracts

ShapePart adds trailing css_classes, tag and optional stroke_width fields. Empty classes and None width preserve the prior generic-part defaults. Collapsed separator and circles resolve their own source classes and primitive paint, independently of outer inline fill; geometry stays immutable path data. DrawEvent records actual resolved fill/stroke/width/opacity/dash, physical box and source child classes. Source line/circle primitives remain ordinary shapes inside a hand-drawn outer container. No DOM, event handling or Canvas private API is introduced.

Painter.measure accepts literal=False; literal=True is a text-only, non-HTML measurement path. It bypasses br, entity, slash-n, math and whitespace rewriting and preserves one unwrapped literal fragment. Cynefin first applies its source SVG ASCII whitespace rule, then measures literally; raw model/getter values are unchanged. Other text/markdown consumers retain their prior default behavior.


## Event ?? HTML ?????2026-11-07?

?? `Painter.measure(..., raw_html=False)` ?????????????? HTML/CSS ?????`raw_html=True` ???????? `.html()` ?????????? `html=True`?`label_kind="text"`?? `literal=True` ???????????Event ??????????????????? literal SVG ???????

?? HTML ?????? sanitizer??? HTML reader ??? Canvas ??????????????CSS normal ASCII ???NBSP??? br ??? containing block ??????????????????????Mermaid hash ??? KaTeX ????normal ?? br/block ?????????????? transport ? Event ???????? Diagram.encodeEntities ? ? substring/wrap/dimensions ? ?? decodeEntities ??????parser/model ???????

????????? `CLOSURE-EVENT-SVG-whitespace-source-probe-20261107T104410Z-281b126b`?`CLOSURE-EVENT-HTML-linebox-source-probe-20261107T105708Z-a25cc0ce` ? `CLOSURE-EVENT-C-ENTITY-source-batch-20261107T105251Z-6b8d6c97`???? source-only ??????????????????????????
