# F01.1 内部接口 v1.1

当前数据合同为 `src/py_mermaid/model/flowchart.py`。共享数据均为 frozen dataclass/tuple，无 Canvas/Context/Font 对象。逻辑坐标px，节点box为左上角，ELK全局坐标；路径保留各section start/bends/end。SourcePosition.index为Python字符偏移，utf16_offset为JS单位，line从1开始、column为UTF-16从0开始；span半开。

唯一接口owner为主协调。以下函数按合同实现，新增字段先向主协调请求：

- `config.resolve_config(config: Mapping | None) -> FlowConfig`，仅允许本轮已实现配置，超范围明确失败；默认值须源映射。
- `parsing.parse_flowchart(text: str, *, config: Mapping | None = None) -> Flowchart`，不创建native对象。入口同时由diagrams/flowchart导出，不修改顶层包聚合。
- `layout.elk.layout_flowchart(diagram: Flowchart, measured: tuple[MeasuredNode,...]) -> Awaitable[FlowLayout]`，真实async pyelk，with/close生命周期，禁止在实现内部asyncio.run。
- `rendering.skia.CanvasSession(backend='auto')`，在创建线程使用；`measure(diagram) -> tuple[MeasuredNode,...]`；`render(diagram, measured, layout) -> RenderResult`。measure/render native对象属于session；auto保留Canvas默认，cpu使用公开setter，gpu要求实际GPU否则失败。
- 主协调提供 `parse(...) -> Flowchart`、`render(...,format='png',backend='auto') -> RenderResult` 和 `arender(...)`。同步render在已有event loop内明确提示使用arender；所有native操作始终留在调用线程。

超范围/非法语法使用MermaidError并给code/span；引擎错误传播并附原始cause，不能假成功。输入/资源预算只拒绝，不截断。普通标签保留内容；富标签未支持时明确拒绝。

S4 官方对照纠正默认外观：`config.ts:resolveAppearance/setDiagramConfigScope` 让流程图采用 schema 的 `redux-color/neo` 默认，覆盖全局 `default/classic`。FlowConfig存有效字体14px、Recursive Variable/Arial fallback、白节点、#28253D边框/文字、黑边；补充padding_x/y=16/12、min_node_width/wrapping_width=120、stroke=2、shadow=(4,4,0.06)，均有固定源码依据。site_font_family/site_font_size保留站点值；显式fontFamily传入主题字体，root fontSize不等于themeVariables.fontSize，不能用它暗改有效14px。标签测量按真实Canvas宽度换行并保留全部文字；最小宽为空标签不强制。source row-height由有效font与htmlLabels决定。
