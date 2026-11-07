# 第三轮：HTML 控件初始静态绘制

2026-11-06，用户授权继续下一轮。目标为完成保留 HTML 表单控件的初始状态、排版和 Canvas 静态绘制，并接入所有实际使用共享 HTML 标签的消费者；不新增图种。

范围以 [静态控件计划](STATIC_HTML_HOST_PLAN.md) 为准：22 种 input 类型、button、select/option/optgroup、textarea、meter、progress，以及字段分组 fieldset/legend 的实际静态内容。隐藏输入和 datalist 不增加可见图形；form 只保留静态容器与初始控件归属。video/audio 整体排除，交互和 Dagre 排除；7 类图表后续统一交给 py-vchart，安装验证继续暂缓。

## 实现与接口

- `model/controls.py`：不可变 ControlSpec/ControlOption、ControlPaint、ControlLayout；不保存 native 对象或浏览器对象。
- `rendering/labels/controls/semantic.py`：安全 HTML 之后的初始状态，纯值解析与 radio/fieldset/form 归一。sanitizer 独立保留来源允许的安全状态属性。
- `rendering/labels/controls/layout.py`：低优先级 UA 意图、尺寸/盒模型、控件元素/文字/图片布局。真实文字尺寸通过现有公开 Canvas 测量回调取得。
- `rendering/labels/rich.py`：控件不可拆原子进入 fragment → measure → run；button/fieldset 的富文本、公式与普通图片复用现有标签能力。
- `rendering/skia/controls.py`：执行公开 Canvas 原语，内容裁切、字体与装饰、字段分组标题；返回实际 DrawEvent。Session 处理 owner、资源、透明度与共享文字特效。

原版 Mermaid 把控件交给 HTML 宿主，本项目保留可见状态和内容，采用原生绘制意图，不实现 DOM 或系统控件兼容层。默认系统控件的字体外观、自然尺寸和日期显示可以有已解释的 native 差异；显式参数、状态、内容、几何可读性及安全仍须验收。复杂浏览器 CSS 不凭该模块宣称完整覆盖，未支持的输入须明确错误。

## 执行顺序与实际状态

1. P0 已读取固定来源及范围，记录起点脏树。既有修改与历史报告保留，不自动提交/推送/发布。
2. P1 全模块源码接线完成，候选 `881656d5439e4ba08b4f3182d215680020653592e2d6ba0f9e265af97faf8fe1`，仅编译/import机械检查，状态 `code_complete_unverified`。
3. P2 已建立来源独立的语义、布局、真实 Canvas 和安全/工具断言。首轮 216 方法/112 例之后按来源事实补齐至 257 方法/131 例；原版宿主只读采集初始状态，不赋值或触发事件。
4. P3 保存全部失败后集中修复，包含 textarea RCDATA/换行、单次实体、radio/form、宽色域转换、实际文字/裁切核对、列表可见项、零尺寸属性默认回退；具体失败与修复 Run 保留于执行状态与变更收据。
5. P4 最终候选 `b605642cc285e95735f18d32f13ff8f98908bcae8e3fefb46120891edf42e268` 已关闭，66 条命令成功且源码未变，2046 测试、865 输入三后端、严格 Zen 和 297 历史图回归通过。原保存导出在 P5 被文件绑定校验挡住，工具命名修复后由独立同候选 `HTML-HOST-P4-EXPORT-repair-20261106T130826Z-cebc530d` 完整重跑 915 导出；最终汇总显式关联补证，不更改原 P4。
6. P5 已完成带验收原始 A/B、8 门禁故障控制、页面 QA 与第三轮独立分页；当前 [验收](HTML_HOST_ACCEPTANCE.md) 和 [机器汇总](../references/html-host-verification-summary.json) 记录实际证据。131 新例与旧 734 例分轮展示，原始 PNG/SVG 不改字节。两份未完成交付尝试及原矩阵均保留，不借用失败记录宣称成功。

依赖不变：py-skia-canvas 0.1.0a18、py-visactor-elk 0.1.0、py-visactor-katex 0.1.0。生产不引入浏览器、Node、JS 或媒体依赖。当前源码完成状态与本轮功能验收分开记录。
