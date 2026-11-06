# F01.3 共享合同 v3

2026-11-05。只做 F01.3；F01.4/Dagre 已由用户暂停。所有字段兼容追加，原有位置参数不移动。纯值可含递归冻结的标量/tuple，不含 dict/native Canvas/DOM 或 JavaScript 对象。

- `SourceDocument(raw, normalized, with_comments, cleaned, processed_to_raw, frontmatter_line_offset, title, config_layers, diagnostics)`；`processed_to_raw` 长度 `len(cleaned)+1`，表示 cleaned 每字符边界到 raw Python 字符边界的映射，再由 raw 计算 UTF-16/行列。层级按 default/site/frontmatter/directive 保存，缺键与显式 null 不混淆。
- `FlowConfig` 追加 `security_level, markdown_auto_wrap, theme_variables, theme_css, title_top_margin, config_layers`；主题变量/配置层使用冻结键值 tuple，保留原始值。默认 ELK 不变；不以 ELK 冒充 Dagre。
- Node/Edge/Group 追加 `label_kind='text'|'markdown'`、`raw_label`；Node/Group 追加 `label_span`。旧普通标签规范化保持，Markdown 仅去外围语法界定，不提前剥内部 markup；HTML/实体含义由 labels 解释。Flowchart 追加 `title/acc_title/acc_description/source_document`。
- `ResolvedStyle` 为 Canvas 可执行的字体/颜色/描边/透明度/背景/对齐意图。纯函数 `rendering.styles.resolve_style(diagram, kind, semantic_id='')`，kind 为 canvas/node/edge/group/node-label/edge-label/group-title/title（diagram-title alias）。根负责实现与导出。源 CSS 的适用声明映射到语义绘制目标，不建立 DOM/虚拟 DOM。
- `MeasuredTextRun(text,x,baseline,width,ascent,descent,font_family,font_size,font_weight,font_style,color,decoration,background,ink_left,ink_right)`；x 是 label-local、textAlign=left 的绘制原点，baseline 相对 label box 顶。width 是 Canvas advance；可见 ink 为 `[x-ink_left,x+ink_right] × [baseline-ascent,baseline+descent]`，不能用 advance 裁掉 italic/CJK。相邻相同样式先合并再测量以保留 shaping/kerning。
- MeasuredNode/MeasuredGroup/MeasuredEdgeLabel 末尾追加 runs；旧 lines 保留可读语义和兼容，不与 runs 重复绘制。所有字体切换、测量和 draw 都由同一 Canvas owner 执行。
- `MeasuredTitle(width,height,ascent,descent,lines=(),runs=())`；annotations.title 可空；layout.title_box 可空。`layout_flowchart(..., measured_title=None)` 消费实测纯值。标题不伪装成 ELK 节点：按源 insertTitle，在真实内容 bbox 中水平居中、基线 y=-titleTopMargin，标题框 y=-margin-ascent。源字体 18px，可由 themeCSS 覆盖；源码标题是纯 text，不把 HTML 当标签渲染。最终 viewport 必须包含真实标题墨迹。
- `geometry_bounds` 可兼容追加 `include_engine=False` 计算真实内容 union，默认保留旧行为；不以 engine 空白大小冒充内容 bbox。
- `shape_outline_intersection(..., *, config=None)` 兼容追加配置，主题 radius 与实际形状绘制/端点保持一致，旧调用仍默认 F01.2 的 neo 规则。布局消费者显式传 diagram.config。
- API 仍 parse/render/arender，先前处理并解析，再测量注释、真实 ELK、Canvas；由根接线。trace 保留既有 kind，富文本 run 使用 text/edge-label/group-title，图标题新增 diagram-title；格式/字体等额外 trace 字段需求交给根追加。
- DrawEvent 兼容追加 font_family/font_size/font_weight/font_style/color/fill/stroke/stroke_width/opacity 值字段，供来源格式和实际像素联合核查。字体/墨迹仍由真实 Canvas 测量，trace 不代替绘制证据。

路径唯一 owner：parser_config 写 `config/**`、`parsing/**`、`diagrams/flowchart/**`；geometry_elk 写 `layout/elk/**`、`geometry/flowchart.py`；canvas_labels 写 `rendering/labels/**`、`rendering/skia/**`（如主题使既有 shape 尺寸分支变化，可在唯一自有 `geometry/shapes.py` 修复）；根写 model、API、`rendering/styles/**`、工具/文档/状态与聚合接口。先完成全部源码，才 S3 来源测试；S2 不执行行为测试/图像。

## S2 源码接线时的兼容追加

- FlowConfig 增加 `dompurify_config` 与 `dompurify_provided`，保留缺省与显式空对象的区别。递归 FrozenMap/FrozenArray 都是 tuple 子类，区分空对象/数组；`config.values.freeze_value/thaw_value` 为唯一转换入口。
- ResolvedStyle 补 `white_space/display/text_anchor/line_height_px/custom_properties/current_color/direction/stroke_gradient/shadow_dx/shadow_dy/shadow_blur/shadow_color/important_properties`。相对字号按真实父样式计算，绝对行高保留 px；`text_anchor` 与 HTML `text_align` 独立。native gradient/shadow 是内置主题画法，不是 F01.4 外部资源。
- `resolve_style(..., tag=None, base=None, css_classes=(), inherited_base=None)` 支持 HTML 标签默认样式与父继承分别输入；`apply_declarations(..., inherited=None, svg_text=False)` 对同一元素按 shorthand/longhand、importance 和先后处理。变量随样式冻结继承，`currentColor` 使用最终 color，显式 stroke 胜出时清除主题 gradient。图形默认声明携带源 specificity，不以低优先级祖先样式替代直接图形声明。
- MeasuredTextRun 追加 opacity/direction；MeasuredTitle 追加 `text_anchor='middle'`，布局根据 start/middle/end 放置同一个源锚点。标题 source font 18px，所用配置/样式在测量与实际绘制一致。
- `rendering.labels.sanitize.sanitize_markup(text, config)` 为 parser/labels 共享的纯值清洗边界，不创建 Canvas。parser label 保留 DB 清洗语义，raw_label 保留原值，labels 从 raw_label 单次解释实体/markup。
- 浏览器控件、外部资源/math、保留的 stylesheet 元素与无法对应的 browser sanitizer 返回值使用明确诊断，不通过静默剥内容伪称支持。SVG-off Markdown 原上游忽略部分 token 的行为保留 `SOURCE_MARKDOWN_TOKEN_OMISSION:*` 诊断，正式探针在 S4 核查；不把这一源缺陷冒充完整 CommonMark。

## S4 标题隐藏补充合同

`MeasuredAnnotations.title_suppressed: bool=False` 与 `layout_flowchart(..., title_suppressed=False)` 区分实际 `display:none` 和缺失测量。只有样式明确隐藏标题时测量层设置该标志，API 传递纯值；布局拒绝隐藏标志与非空标题测量同时出现，普通标题缺测仍失败。渲染核对同一合同。此字段兼容追加，不引入布局到渲染样式层的反向依赖。
