# 当前执行目标：F01.2 流程图增强

2026-11-04，用户明确要求“完成 F01.2”。本轮接续已提交的F01.1，在其现有接口和默认ELK/Canvas路径上实现边标签、经典形状、子图与跨组连线。安装验证继续暂缓；不自动commit/push或发布新成果。

## 功能分母

- 普通边标签：`A -->|条件| B`、`A -- 条件 --> B`，包括普通Unicode/多行、真实测量、ELK标签box及实际绘制；富标签留F01.3。
- 14种真实经典形状：square、round、stadium、subroutine、cylinder、circle、doublecircle、diamond、hexagon、odd、trapezoid、inv_trapezoid、lean_right、lean_left。覆盖专用尺寸、标签容纳、真实轮廓与连线交点；保留原F01.1矩形行为。
- 经典ellipse `A(-text-)` 在固定flow.jison有语法，但上游shape registry缺handler且源码注明broken；保留解析语义和明确渲染错误，S3用独立官方探针验证，不能伪造等价成功。
- 子图：显式ID/标题、自动ID、嵌套、成员关系、重复声明归并、组内部direction、默认继承规则、空组及只有组的图。
- 连线：组内、节点跨组、组内外、组端点/组间及祖先组端点；保留语义端点、分段路由与真实坐标换算。算法版本造成的合法路由变化按功能规则核查。

本轮根方向继续TD/LR；组内可表达TD/TB/LR/RL/BT。前处理指令、frontmatter、富文本/数学、样式语句、@{shape:...}新形状系统、legacy带属性rect、其他线型/marker、Dagre与其他导出仍为后续范围，明确诊断，不静默删内容。

## 执行顺序

| 阶段 | 产物与退出条件 |
| --- | --- |
| S0 来源/接管 | 干净起点b5af187，固定Mermaid12.2.0 / 1fb7869866dd619168d840291c9c54b4f129758b；复用Canvas0.1.0a18与py-visactor-elk0.1.0，不安装或重编 |
| S1 合同 | [接口v2](F01_2_INTERFACES.md)、唯一owner/路径租约、完整形状和group责任 |
| S2 源码 | 先完成本切片全部源码/接线和source map，仅编译/import/签名检查，标code_complete_unverified |
| S3 来源测试 | 从固定grammar/shape/ELK/DB源码和spec设计独立单元/组合/官方对照及负控制；对原F01.1“未支持”断言按新范围明确迁移 |
| S4 首轮与根因修复 | 同一源候选分组运行并保留失败；优先公共几何/标签/父坐标/层级根因，相关回归 |
| S5 本地验收 | 同候选F01.1回归+F01.2分母、CPU/auto/GPU适用场景、真实PNG/HTML效果与明确限制；不做安装验证 |

## 分工

主协调写model/api/工具/账本/总接口与集成。parser_config写parser/config及对应来源；geometry_elk写layout/elk和geometry/flowchart.py；canvas_labels写rendering及唯一geometry/shapes.py。共享geometry/__init__.py由主协调汇总。所有源和布局数据纯值，native对象只在Canvas owner线程。

## 验收

语义节点/组/成员/边/标签正确，实际绘制内容完整，标签容纳，端点在真实形状或组边界，组包含与层级正确，标题/边标签可读且无裁切。覆盖嵌套、重复ID/组声明、方向、空组、自环/多边、异常和连续运行。对同候选保留官方原始SVG/PNG与Python原始PNG/trace/布局；像素仅诊断，不追求跨引擎相等。继续使用统一workflow日志/报告，历史证据不覆盖，Linux/no-loader不冒称已验。
