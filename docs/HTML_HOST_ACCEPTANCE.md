# 第三轮 HTML 静态控件验收

2026-11-06，本轮保留范围已完成本地验收。最终源码 `b605642cc285e95735f18d32f13ff8f98908bcae8e3fefb46120891edf42e268`；固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`，不引入生产浏览器或 JS 宿主。

[分轮报告](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/index.html) · [直接查看第三轮](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778/rounds/html-controls/index.html) · [机器汇总](../references/html-host-verification-summary.json) · [执行记录](HTML_HOST_EXECUTION.md)。第三轮 131 例分 11 页，每页最多 12 例；第二轮 64 例和第一轮 670 例为同候选的重新回归画面，各自独立分页。

## 已验收范围

22 种 input 初始静态类型，以及 button、select/option/optgroup、textarea、meter、progress、fieldset/legend。覆盖初始 value/placeholder/checked/selected、有效 disabled/readonly、radio/form 分组、字段组首 legend 豁免、日期/数字/范围/颜色归一、尺寸默认值和盒模型、文字及图片、内容裁切与共享富文本接线。hidden 不增加可见控件；form/datalist 不增加交互界面。

修复包含固定来源的样式分号预处理、普通/Markdown textarea 换行与单次实体解码、列表截图时的真实初始可见项、跨节点 radio 分组、非红色宽色域转换、size/cols/rows=0 恢复属性默认值。公式和普通图片复用既有静态标签能力。

## 实际证据

| 项目 | 结果 |
| --- | --- |
| 同候选 P4 测试 | 2046 方法，其中新增控件 257 方法 |
| 主输入 | 865 例：旧 734 + 新控件 131 |
| 每个 CPU/auto/GPU profile | 818 正常绘制、46 预期错误、1 静态排除 |
| 新控件原版状态/真实绘制核对 | 131 例 × 3 profiles，通过 |
| 严格 ZenUML | 186 例、1990 故障负控制 / profile |
| 历史流程图 | 297 正例 / profile，含原负例和诊断核对 |
| 五种格式 | 31 入口 × 3 profiles × 5 = 465；30 个控件代表 × 3 × 5 = 450 |
| 报告验收故障控制 | 8 个应拒绝情形全部被拒绝 |
| 报告原始内容 | 3270 PNG / 816 SVG 字节及分母一致 |

原始自动矩阵是 `test-runs/BULK-P4-final-20261106T125300Z-435e50af`，66 条命令 SUCCESS、sourceUnchanged=true。P5 汇总额外发现导出工具 SVG 尺寸循环复用了文件名变量，导致原目录后续文件覆盖；**原 P4 保存导出不作为最终导出证据**。修复工具后，独立同候选 `test-runs/HTML-HOST-P4-EXPORT-repair-20261106T130826Z-cebc530d` 完整重跑 465+450 导出，文件名唯一，逐文件 SHA/大小、实际内容、后端与尺寸通过。原 P4 其他同候选测试/渲染证据保留；汇总显式绑定补充 Run，不改写旧目录或冒称旧导出已完整。见 [导出修复记录](changes/html-host-export-artifact-repair.json)。

最终交付 `test-runs/HTML-HOST-P5-delivery-20261106T131153Z-15f07388` 包含严格汇总、带验收报告、8 个实际门禁故障控制及桌面/移动页面 QA。分页 Run `test-runs/REPORT-ROUNDS-delivery-20261106T131320Z-1382c778` 校验 865 个唯一案例、全部 73 个案例页以及原始 PNG/SVG 字节，无重绘或图像后处理。纯分页功能状态为 NOT_EVALUATED，来源报告功能状态另为 RETAINED_STATIC_LOCAL_ACCEPTED。

人工记录绑定 78 组 A/B：16 组为本次实际查看的原始图片，另 62 组在原/原生两端 SHA 完全相同后转移既有实际看图记录。覆盖全部 31 入口及本轮复杂控件；包含必须查看的零尺寸回退案例。它是代表性抽查，不是全部 865 例逐一人工检查。

## 适配边界

只承诺本轮明确的静态状态、内容和绘制范围；不宣称任意浏览器 HTML/CSS 或全部源码表达式穷尽兼容。默认字体、自然尺寸、边框、日期语言、文件选择按钮文案以及非活动选择灰底/原生蓝底可以有已记录的宿主外观差异，状态和可读性必须保留。

复杂 calc/min/max/clamp、非实色背景、椭圆角、上下文/系统/相对颜色及 CSS Color 5 不属于一般浏览器 CSS 解释器承诺。SVG/PDF 是原生静态图形，无活表单或 foreignObject 交互宿主。

video/audio 整体排除；交互与 Dagre 排除。7 类暂缓图表仍留待后续 py-vchart，未纳入本轮或引入新依赖。依赖保持 py-skia-canvas 0.1.0a18、py-visactor-elk 0.1.0、py-visactor-katex 0.1.0；新增来源许可记录随包保留。

安装、Linux、no-loader 和发行验证未执行；本轮未提交、推送或发布。
