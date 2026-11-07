# VChart DSL v1 实现与验收

2026-11-07。**原生 DSL v1 已完成本地静态范围验收**。正式依赖为 PyPI `py-visactor-vchart==0.1.1`，没有发布新的 py-mermaid 版本。供应方全部68类型接线与供应方所有分支穷尽覆盖是不同结论，详见下文。

## 交付功能

原生 `vchart <type>` 语法覆盖正式 `py-visactor-vchart==0.1.1` 的全部68个已注册二维静态类型。保留旧 `vchart` 严格 JSON、Python spec API 与七类 Mermaid 图表入口。新增第三方运行依赖为零。

- 完整 JSON 值、任意字符串键、属性/嵌套配置块、点/括号路径及连续数组索引。
- `table` 表格、前置不可重绑 `let` 纯值引用、`size`、`axis`/`series` 追加块。
- 显式内联 GeoJSON 和 SVG，与外部调用参数隔离；同名冲突、外链资源及预算超额明确报错。
- 公开 `compile_vchart()` 返回不可变模型、全新 spec/资源副本、源位置和诊断；编译不绘制、不加载字体、不进行文件或网络读取。
- `render()`、`arender()` 与 CLI 自动识别新语法；`--compile`/`--compile-only` 导出可审查编译 JSON。PNG、JPEG、WebP、SVG、PDF 复用既有实际绘制链路。
- UTF-16 错误位置、引用声明关联、重复/父子写入冲突、数组洞及混合构造模式拒绝。源映射本身采用 Python code-point 偏移，编译 JSON 中显式标明编码。

使用方式：

```python
from py_mermaid import compile_vchart, render

text = '''vchart bar
size 640 360
data = {values: [{month: "Jan", value: 120}, {month: "Feb", value: 180}]}
xField = "month"
yField = "value"
'''
compiled = compile_vchart(text)
spec = compiled.spec()
image = render(text, format="svg", backend="cpu")
```

```shell
py-mermaid docs/proposals/vchart-v1/examples/bar.vchart --compile -o compiled.json
py-mermaid docs/proposals/vchart-v1/examples/bar.vchart -o chart.svg --backend cpu
```

规范：[语言](VCHART_DSL_DESIGN.md) · [计划](VCHART_DSL_EXECUTION_PLAN.md) · [模块合同](VCHART_DSL_INTERFACES.md) · [8组完整示例](proposals/vchart-v1/examples/README.md)。

## 验证分母与失败保留

固定301案例 = 225供应方原规格 + 68类型代表 + 8手写示例。分组来源有重叠，这是301案例，不是301图种。每个后端都单独比较原 spec API 与实际 DSL 的结构、资源、场景及 PNG；原浏览器参考为额外来源核实，同后端精确相等不意味着跨引擎像素相等。

首轮完整 Run：`VCHART-DSL-P3-batch-20261107T071015Z-cae93e0e`，整体 FAILED，所有失败保留。301案例三后端矩阵全部通过，但单测发现两处入口边界及新测试的正例地图方向、不可写字体方法 mock 问题。集中修复后，`VCHART-DSL-P3-REPAIR-batch-20261107T071557Z-37375aad` 的330个相关方法通过。原有错误合同不因新增 DSL 改写；测试夹具修正与产品修正分别记录。

全新环境：wheel `VCHART-INSTALL-wheel-20261107T071751Z-d6268c2c`、sdist `VCHART-INSTALL-sdist-20261107T071829Z-d552a24f` 均成功，产品指纹均为 `fe2c293f8ed4ea76e04d34669c8739c27a32063447026e144928bfd6b4ac0bb2`。每环境实际绘制68 spec与68 DSL并核精确PNG、内联地图/SVG、数学、真实 ELK 和矢量导出；依赖由正常 PyPI 解析，不使用相邻仓库回退。

最终 P4：`VCHART-DSL-P4-batch-20261107T072312Z-7cdc1791`，SUCCESS，`sourceUnchanged=true`、`testToolsUnchanged=true`。源码与上述两个新环境完全一致。实际日志核得2364个方法通过：146新 DSL、156既有 VChart、2062受影响旧回归；9项独立比较负控另列，不混入方法数。

CPU、auto、GPU各301例，共903组 spec API/DSL 对照通过；每组严格比较编译结构/资源、场景、实际解码 PNG，同后端像素完全一致。68代表类型各后端另有SVG/PDF/JPEG/WebP共816个实际导出文件，PNG保存在各案例中。225原规格另核固定浏览器文字/结构：223例直接通过，2例词云使用既有锁定原生字体/遮罩策略并保留精确差异，不改输入或放宽阈值掩盖差异。

实际看图原收据为 `test-runs/vchart-dsl-visual-review-first-20261107T072100Z.json`：68代表和8手写示例逐张查看76张原始 DSL PNG；API侧76张与之逐字节一致，仅做哈希绑定。最终图像全部同字节，复用绑定收据位于 `VCHART-DSL-REVIEW-binding-20261107T072540Z-f3832b39/artifacts/visual-review.json`，没有冒称又看了76张。225原规格和任意空数据分支不主张逐张视觉核实。

已记录供应方原表现：correlation外圈到画布边界裁切、部分gauge顶端标签重合、sequenceScatterKDE密度笔画到边界、双轴示例同色线局部被柱遮挡。两侧原字节相同；它们不算本轮 DSL 回归，也不声称已修复。

机器汇总：[vchart-dsl-verification-summary.json](../references/vchart-dsl-verification-summary.json)。[第六轮 HTML 对比报告](http://127.0.0.1:8765/VCHART-DSL-P5-delivery-20261107T072726Z-cd08a488/index.html)：26个案例页及独立首页，每页最多12例。交付 Run `VCHART-DSL-P5-delivery-20261107T072726Z-cd08a488` SUCCESS，4194个原始附件本地/HTTP SHA、全部301案例状态/链接、1440/390视口及3项报告负控通过；最终无网络重试。8张原始报告截图另实际查看，布局收据为 `test-runs/vchart-dsl-report-layout-review-20261107T073000Z.json`。

首次交付 `VCHART-DSL-P5-delivery-20261107T072548Z-d40f369a` 在HTTP读取第4116个附件后发生连接中断并失败，原记录完整保留。仅报告QA降低并发至4，并对中断的只读请求加入最多3次、逐次留痕的重试；收到的错误HTTP状态或SHA不符仍立即计失败。修复不改产品/测试，后处理工具另存于成功交付 Run；闭合P4和安装证据保持原样。

## 范围与实际限制

本轮完成语言表达与既有供应方能力接线，不重写其算法。任意 JSON 可表达不等于供应方接受任意选项或任意组合；完整选项有效性仍在实际绘制边界检查。能力清单是68类型派发和高风险条件的有限源码审计。原计划中“逐项穷尽全部供应方字段/条件”的要求未达到；实际以无损表达、既定语法合同、225规格和68类型有限验证验收，不能据此宣布所有参数组合或 JS VChart 分支覆盖完成。

静态限制继续保留，包括 common 组合/双轴限制、部分类型 `label.visible=false`、受限词云布局、Venn 集合数、Treemap 布局以及 `sequenceScatterPixel` 固定300×300等。后者在编译结果附诊断，仍保留用户原始规格。没有结构化路径的供应方错误仅附可靠整段位置，不推测精确字段。

交互、动画、3D、Dagre、video/audio、任意 HTML/CSS 扩展按既有决定排除。此前22条已确认 Mermaid 分支缺口仍在独立修复队列，不被本轮 DSL 覆盖。此任务不发布 py-mermaid。
