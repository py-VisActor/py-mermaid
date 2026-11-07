# 已验收范围：HTML 控件的初始静态外观

2026-11-06。HTML 表单控件的初始静态绘制已完成限定范围的本地验收，见 [HTML 控件验收](HTML_HOST_ACCEPTANCE.md)和[最终机器汇总](../references/html-host-verification-summary.json)。本文件保留来源、功能合同和执行次序，不表示下一轮仍待启动。**video/audio 已按用户要求整体删除出迁移范围**：播放、解码、封面/占位、控制条、初始静态外观及媒体专用依赖/导出/验收均排除，不再作为未完成迁移。见[范围决策](../references/media-exclusion.json)。普通静态图片和图标继续保留。

## 来源与现状

固定 Mermaid 12.2.0 的 `diagrams/common/common.ts:70–96` 清洗 HTML 标签；`rendering-util/createText.ts:34–56,341–354` 将内容交给 `foreignObject` 的 HTML 宿主。固定 bundle source map 内 DOMPurify **3.4.12** 的标签和状态属性规则用于溯源，不跟随本机其他版本。

历史诊断中，Python `rendering/labels/rich.py` 对控件报 `DEFERRED_HTML_CONTROL`，7 类已采证控件原版可见而原生拒绝。该诊断属于原候选，已由本轮纯值模型、安全属性保留、初始状态归约、实际测量、原生绘制和 131 个控件案例的新证据解决；旧失败不删、不改成通过。本轮不以这些案例或方法数量声称浏览器全部 HTML/CSS 分支均已覆盖。

历史诊断实际采集了 9 类，另 2 类 video/audio 已被用户排除。原版事实、失败 Run 和历史报告保持原样，不将排除改记为通过。历史与当前验收层次见[机器记录](../references/static-html-host-gap.json)。媒体标签拒绝和 sanitizer 安全过滤仅是输入边界，不是未来媒体实现接线。

## 功能范围

| 功能 | 需要保留的静态含义 |
| --- | --- |
| input | 适用类型的初始边框、value/placeholder、勾选/单选、disabled/readonly、尺寸；hidden 不产生可见内容 |
| button | 初始标题/内联内容、边框和禁用外观 |
| select / option / optgroup | 收起时已选项及适用的静态列表外观；不实现下拉打开和选择行为 |
| textarea | 初始文字、行列尺寸和可见换行；不实现编辑、光标和滚动交互 |
| meter / progress | value/min/max 等定义的静态填充与文字/轨道；不实现动态更新或动画 |
| fieldset / legend | 实际边框、富文本首 legend、正文和首 legend 的 disabled 继承豁免；标题不被正文 clip 裁掉 |
| 容器与样式 | sanitizer 后的内容、静态状态、继承字体/颜色、尺寸及嵌套顺序；HTML 标签关闭时保留既有 literal 分支 |

input 覆盖 hidden、text、search、tel、url、email、password、date、month、week、time、datetime-local、number、range、color、checkbox、radio、file、submit、image、reset、button 共 22 种类型的初始静态含义。按钮正文沿用富文本、正式数学和显式图片资源管线；图片输入使用资源自然尺寸并保留单轴尺寸的宽高比。

## 本轮验收与限制

冻结源码为 `b605642cc285e95735f18d32f13ff8f98908bcae8e3fefb46120891edf42e268`。2046 个测试方法通过，865 个输入（734 个既有输入、131 个控件输入）在 CPU、auto、GPU 下每后端均为 818 个正常检查通过、46 个预期错误、1 个范围排除。最终 P4 为 `BULK-P4-final-20261106T125300Z-435e50af`，源码未变化。

原 P4 导出工具因 key 变量复用造成文件名覆盖，其保存的导出文件不用于完整导出验收。915 项导出（465 项既有回归、450 项控件导出）通过独立同候选运行 `HTML-HOST-P4-EXPORT-repair-20261106T130826Z-cebc530d` 完成；原运行及被 P5 门禁拒绝的尝试保留。最终交付 `HTML-HOST-P5-delivery-20261106T131153Z-15f07388` 包含原始查看器检查和故障控制，见[三轮分页](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/index.html)及[第三轮](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/rounds/html-controls/index.html)。

实际补修包括 CSS 边框长属性级联、UA box-sizing 和字体、radio 白环与选中中心、控件文字效果、textarea 实体与首换行、select 首次 paint 后的初始视口，以及零值 size/cols/rows 的默认尺寸恢复。尺寸核验不能只证明有外框；初始文字和选项必须在相应视口内真实可见。

Mermaid 本身把这些控件委托给浏览器宿主，本模块用原生 UA 静态意图承接，不复制浏览器坐标或要求自然外观逐像素相同。平台字体、配色细节和日期/时间区域显示可能不同；初始内容、状态、关系与裁切仍须验收。复杂 CSS `calc/min/max/clamp` 长度、需要上下文解析器的颜色、非纯色控件背景及其他显式未支持的 CSS，不得被静默当作已实现。通用浏览器 HTML/CSS 排版、交互和全部源码分支覆盖不属于本轮结论。

点击、提交、编辑、焦点、下拉和动画行为继续排除。video/audio 无论是否带 controls/poster、是否离线提供资源，均不纳入本模块；保留现有明确拒绝，不加载、不解码、不创建静态媒体占位。普通图片资源不受该决策影响。

## 依赖与改造方案

本轮复用公开 py-skia-canvas、标签测量/样式、ResourceStore 和静态导出，没有新增第三方运行依赖。不增加媒体依赖，生产不引入浏览器、Node 或 JS 引擎。以下是本轮已经执行的迁移次序，具体证据以验收及机器汇总为准。

1. 从固定清洗规则和原版 HTML 宿主展开控件属性/默认状态，记录输入、状态、单位、错误及来源 SHA。
2. 建立不可变静态控件模型，把尺寸、文字和可见状态接入 fragment → measure → run 数据链。
3. 在 owner 线程用 Canvas 公开文字、路径、填充、描边及普通图片资源绘制；SVG/PDF 沿用静态导出，不携带事件或表单交互协议。
4. 补齐控件静态外观所需的安全属性保留，继续拒绝脚本、隐式外部资源和不安全 URL；不扩建音视频语义或资源模型。
5. 全部本模块源码收齐后，独立设计原源断言/采集；统一首跑、批修，再冻结同一候选执行三后端、格式、资源安全和既有图种回归。音视频仅保留明确拒绝的安全回归，不作为功能兼容用例。
6. 交付标准日志、原始 A/B 和 HTML 报告。内容、状态、几何及可读性作为门禁，不要求复刻浏览器/系统控件的每个像素。

安装验证继续暂缓。本轮只接受上述初始静态控件合同，不宣称全部浏览器 HTML 标签功能迁移完成。7 类排除图表仍留给后续 py-vchart，尚未接线，也不计完成。
