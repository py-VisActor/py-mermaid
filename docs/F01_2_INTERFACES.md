# F01.2 内部合同 v2

共享类型位于 `model/flowchart.py`，原有位置参数不改变，新增字段均默认兼容。逻辑px，span仍原文Python字符/UTF16/1-based行0-based列，所有最终box和路由为absolute top-left。

- FlowNode追加shape（使用flow.jison规范名，默认square）、parent_id。FlowEdge追加label、label_span。
- FlowGroup(id,label,span,members,parent_id,direction,color_index)；groups按上游归约闭合顺序保存，成员按源DB规则；color_index按声明前序独立分配。组/节点共用语义ID空间；forward组端点解析后统一解决，组不再作为重复普通节点。
- Flowchart.groups默认为空。FlowConfig新增inherit_direction、round_radius、edge标签宽/背景及组padding/title margin/palette；只承接来源必要项，不建立通用主题框架。
- MeasuredNode追加label_box（node-local）、outline纯SVG path字符串、details纯path tuple。native Path2D只能在Canvas adapter中转换。非矩形不得用矩形假成功。
- MeasuredGroup(id,label_width,label_height,lines)；MeasuredEdgeLabel(id,width,height,lines)。MeasuredAnnotations(groups,edge_labels)作为独立注入值，不把边标签/组标题冒充普通节点。
- CanvasSession.measure(diagram)保留节点tuple；新增measure_annotations(diagram)->MeasuredAnnotations。layout_flowchart(diagram,measured,*,measured_groups=(),measured_edge_labels=())；CanvasSession.render(...,*,annotations=None)。API依次显式调用并传递测量，不让布局创建Canvas。
- FlowLayout追加groups:tuple[PlacedGroup]、edge_labels:tuple[PlacedEdgeLabel]。PlacedGroup(id,box,parent_id,engine_origin,title_box)，frame与engine_origin明确分离；PlacedEdgeLabel(id,box)。全部最终坐标absolute；ELK container-local坐标按真实container/LCA递归转换，不二次偏移。
- RenderResult追加annotations，trace新增group/group-shadow/group-title/edge-label/edge-label-background，以及双圆内圈的node-detail-shadow；所有位置为最终PNG坐标，用于真实内容/几何/像素联合验证。

唯一形状实现文件geometry/shapes.py由canvas_labels持有：提供纯ShapeGeometry(width,height,label_box,outline,details)、shape_geometry(kind,label_width,label_height,config)及shape_outline_intersection(kind,box,port,toward)。path在node-local top-left空间；交点沿ELK端口最后/最初的正交轴延伸至真实outline，不能用中心射线造成斜stub。geometry_elk只读消费该函数，公共聚合导出由主协调单写。

原矩形已有直接绘制路径可保留以维持F01.1结果；其他形状必须真实path。空组允许有测量标题/最小几何；仅有组时布局不能因没有leaf node误拒绝。engine错误保留cause，不无条件回退。ellipse的上游缺口按源错误单独登记，不能使用其他椭圆handler冒称原实现成功。
