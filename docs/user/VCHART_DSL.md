# VChart DSL v1

[User documentation](../README.md) | [VChart guide](VCHART.md)

This is the supported chart text syntax. It compiles to the same VChart spec used by the Python API; available rendering options follow py-visactor-vchart. Use compile_vchart(text).spec() to inspect a spec, or render(text) to draw it. This extension is specific to py-mermaid.

## 1. 最小示例

下面是 py-mermaid 原生新语法；第三方 Mermaid JS 工具不识别此扩展。

```text
vchart bar
size 800 420

let sales = table(month, revenue) {
  ["Jan", 120]
  ["Feb", 180]
  ["Mar", 150]
}

data = { values: $sales }
xField = "month"
yField = "revenue"

bar {
  style {
    fill = "#1664ff"
  }
}

axis bottom { type = "band" }
axis left { type = "linear"; min = 0 }
```

确定性编译结果：

```json
{
  "type": "bar",
  "width": 800,
  "height": 420,
  "data": {"values": [
    {"month": "Jan", "revenue": 120},
    {"month": "Feb", "revenue": 180},
    {"month": "Mar", "revenue": 150}
  ]},
  "xField": "month",
  "yField": "revenue",
  "bar": {"style": {"fill": "#1664ff"}},
  "axes": [
    {"orient": "bottom", "type": "band"},
    {"orient": "left", "type": "linear", "min": 0}
  ]
}
```

不新增 `x`、`y`、`color by` 等对真实字段有歧义的别名。`xField`、`seriesField`、`angleField` 等保留供应方名称；单个字段和字段数组的意义由具体类型决定。

## 2. 语法规则

### 2.1 入口与兼容

| 输入 | 解释 |
|---|---|
| 首行只有 `vchart`，随后为 JSON 对象 | 现有严格 JSON 模式 |
| 首行 `vchart bar` / `vchart kdePlot` 等 | 新 DSL v1 |
| Python `render_vchart(spec)` | 现有对象 API |
| `pie`、`xychart`、`sankey-beta` 等 | 现有 Mermaid 语法，与新 DSL 独立 |

根据完整首行选择严格 JSON 或 DSL 模式；DSL 失败后不尝试 JSON 或其他图种。DSL 类型名称未知时提供类型建议，但不自动改大小写或切换相近类型。严格 JSON 输入的未知类型直接报告类型错误。

首行允许 BOM 和前置空白；头部之前不允许 `%%` 注释，头部之后才启用注释。DSL v1 不接受 YAML/frontmatter 或 Mermaid init 配置；`%%{...}%%` 指令在配置位置报错，字符串里的相同内容保持字面量。

### 2.2 值、语句与注释

- 字符串使用双引号及 JSON 转义。`true`、`false`、`null`、有限 JSON 数字保留类型；普通裸词不被猜测为字符串或枚举。
- 对象与数组保留 JSON 结构；对象键可用 ASCII 标识符或双引号字符串，成员/元素用逗号分隔，DSL 模式允许一个尾逗号。
- 语句以换行或分号结束；块关闭或 EOF 可结束最后一条语句。嵌套值内部的换行是空白。
- 缩进仅用于阅读，不参与语义。`%%` 在字符串外表示行注释；颜色、SVG、URL和数据中的文本不受注释处理影响。
- 不支持表达式、函数调用、模板插值、循环、导入、Python/JS 回调。`$name` 是唯一变量引用形式，不是表达式求值。

### 2.3 属性与配置块

```text
bar.style.fill = "#1664ff"

%% 与上句等价，但不要在同一文档重复写同一属性
bar {
  style { fill = "#1664ff" }
}
```

点路径创建对象层级，双引号键与方括号键可以表达含标点或中文的真实键；对象字面量中的键从不解释为路径。示例：`"custom.key" = 1` 是一个根键，`custom.key = 1` 是两层对象。

支持显式数组索引，例如 `axes[0].orient = "bottom"`，但只能连续创建，不以 `null` 补洞。一个数组只允许采用整体字面量、连续索引或语法糖追加中的一种构造方式。

重复对象键、重复写入（即使值相同）、给已整体赋值的父对象继续打补丁、把标量当容器，均为编译错误。配置块只打开容器，互不重叠的叶子可以分块声明；整体对象/数组赋值拥有整个子树。根 `type` 由首行拥有，正文不得覆盖。

### 2.4 表格与数据形状

```text
let rows = table("月份", revenue, region) {
  ["一月", 120, "华东"]
  ["二月", null, "华南"]
}
```

`table` 仅将每行数组与表头一一配对，得到普通对象数组。表头必须非空、唯一、区分大小写；列数不符立即报错，单元格仍可为任意嵌套值。不做 CSV 猜测、类型推断、日期转换、聚合、补值、排序或行丢弃。

**数据外形由用户明确书写**：

```text
data = $rows                         %% 原始行数组，常用于统计规格
data = { values: $rows }             %% 单个 values 对象
data = [{ id: "sales", values: $rows }]  %% 有名字的数据视图数组
```

这三行是可选写法，不能在同一图里叠加。编译器不会根据类型替用户增删包装层。`histogram` / `boxPlot` 尤须保留原始数据路径和预计算数据路径的差别：0.1.1 会按数据外形及字段配置选择实际绘制分支。

`let` 是单文档纯值声明，必须先定义后使用，不得重定义或形成循环。引用展开产生独立纯值，不共享可变容器；展开过程逐节点计预算，不能先无限展开再检查大小。字符串 `"$sales"` 保持字符串。

### 2.5 少量确定性语法糖

| 新语句 | 精确含义 |
|---|---|
| `size 800 420` | 写入 `width=800`、`height=420` |
| `axis bottom { ... }` | 向根 `axes` 追加 `{orient:"bottom", ...}` |
| `series bar { ... }` | 向根 `series` 追加 `{type:"bar", ...}` |
| `resource map "local" = value` | 声明本图内联 GeoJSON，不写入 spec |
| `resource svg "regions" = value` | 声明本图内联 SVG 字符串，不写入 spec |

`size` 与直接写 `width/height` 遵循重复写入规则。`axis` 的 `orient`、`series` 的 `type` 由块头拥有，不允许正文覆盖；顺序就是最终数组顺序，不按名字重排。

根关键字只在对应语句形态下有语法意义；`series = [...]` 等仍是原字段赋值。块内是原字段，不把字段名悄悄改成另一种配置。语法糖不意味着该图支持该组件：例如统计图可能拒绝 `axes`；当前 `common` 系列只支持 `bar` 和 `line`。

## 3. 复杂图示例

### 3.1 统计绘图：直接传原始样本

```text
vchart kdePlot
size 640 360
data = table(value) {
  [-2]; [-1.2]; [-0.8]; [-0.4]; [-0.4]
  [0]; [0.1]; [0.3]; [0.6]; [1.1]; [1.8]
}
estimation { bandwidth = "scott"; bandwidthAdjust = 1 }
sampling { points = 128; cut = 3 }
```

带宽、采样点数和统计计算仍由供应方执行；DSL 不计算 KDE，也不把原始样本转成柱状图。

### 3.2 柱线与双轴组合

```text
vchart common
size 800 420
data = { values: table(month, revenue, margin) {
  ["Jan", 120, 18]
  ["Feb", 180, 24]
} }
series bar { xField = "month"; yField = "revenue" }
series line { xField = "month"; yField = "margin" }
axis bottom { type = "band" }
axis left { type = "linear"; seriesIndex = [0] }
axis right { type = "linear"; min = 0; max = 100; seriesIndex = [1] }
```

该例使用当前 `common` 的共享数据和系列索引合同。不能由此推导任意68类型均能混合、每系列独立数据或多区域布局已支持；后端未有的能力不由语法层拼出近似图替代。

### 3.3 层级数据

```text
vchart treemap
size 640 400
categoryField = "name"
valueField = "value"
data = { values: [
  {name: "Group A", children: [
    {name: "A1", value: 8},
    {name: "A2", value: 5}
  ]},
  {name: "Group B", value: 3}
] }
label { visible = false }
splitType = "binary"
nodePadding = [5, 3]
```

层级、图关系、矩阵、数组型值都可使用同样的值语法。这里 `label.visible=false` 是当前供应方的实际约束；不能因新语法出现 `label` 块就承诺标签已支持开启。传统 Mermaid `treemap` 的文字绘制合同继续独立保留。

### 3.4 桑基图：保留节点和边结构

```text
vchart sankey
size 640 400
categoryField = "name"
sourceField = "source"
targetField = "target"
valueField = "value"
label { visible = false }
data = [{ values: [{
  nodes: [{name: "Input"}, {name: "Output"}],
  links: [{source: 0, target: 1, value: 5}]
}] }]
```

节点ID、引用方式、负值及非有限值仍由原合同校验，不自动制造缺失节点。

### 3.5 地图与 SVG

```text
vchart map
resource map "local" = {
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    properties: {name: "A"},
    geometry: {type: "Polygon", coordinates: [[[0,0],[0,1],[2,1],[2,0],[0,0]]]}
  }]
}
map = "local"
nameField = "name"
seriesField = "group"
data = { values: [{name: "A", group: "alpha"}] }
label { visible = false }
```

也可以不写 `resource`，由现有 `maps={...}` / CLI `--vchart-maps` 显式传入。`pictogram` / `imageCloud` 的 SVG 使用同样的内联声明或现有 `svgs` 参数，并保留真实 `svg` 字段名。

图像的 data URI / `resource:ID`、图标与字体沿用当前 `ResourceBundle`。字体路径只能由调用方显式授权的资源入口读取，不增加源文本里的任意文件加载。API/CLI与文档内联声明出现同种同名资源时，编译/绑定阶段报冲突，不使用优先级静默覆盖。命名空间 `(map,name)`、`(svg,name)` 分开。

## 4. 68 类型如何全部覆盖

当前依赖提供以下类型；以下分组去重后恰为68，不把 `histogram` / `boxPlot` 的双路径重复计数。

| 类别 | 数量 | 类型 |
|---|---:|---|
| 笛卡尔/组合 | 13 | bar、line、scatter、area、rangeArea、rangeColumn、waterfall、histogram、boxPlot、heatmap、mosaic、linearProgress、common |
| 极坐标/指标 | 6 | pie、rose、radar、gauge、circularProgress、liquid |
| 层级/关系/集合 | 7 | funnel、treemap、sunburst、circlePacking、sankey、correlation、venn |
| 二维扩展 | 14 | storyline、sequenceAnalysis、sequence、combinationCandlestick、pictogram、imageCloud、candlestick、conversionFunnel、rankingList、rankingBar、timeline、sequenceScatterPixel、sequenceScatterKDE、sequenceScatterLink |
| 地图/词云 | 2 | map、wordCloud |
| 统计独立名称 | 26 | learningCurve、seasonalPlot、timeSeriesPlot、autocorrelationPlot、residualPlot、pairedComparisonPlot、kdePlot、violinPlot、countPlot、screePlot、scatterPlot、embeddingPlot、qqPlot、stripPlot、ecdfPlot、calibrationCurve、rocCurve、precisionRecallCurve、shapBeeswarmPlot、pairPlot、hexbinPlot、featureImportancePlot、pointIntervalPlot、missingValueMatrix、correlationMatrix、confusionMatrix |

对任意现有 JSON spec：把根 `type` 移入首行，其余根属性逐个写为 `key = <值>`，值语法保留全部 JSON 结构。因此不依赖特殊缩写也能表达所有合法规格；表格和配置块只改善书写。



当前供应方的部分使用条件如下；完整图表说明以 [py-vchart 用户文档](https://github.com/py-VisActor/py-vchart/blob/main/docs/README.md) 为准：

- `common` 仅共享数据的柱线组合；双轴系列绑定使用原 `seriesIndex`，横向组合不支持右轴。
- `histogram` / `boxPlot` 的 raw-array 与预计算数据分支不同；统计图不会接受所有普通笛卡尔字段。
- Map 当前要求外环顺时针、洞逆时针，内联GeoJSON继承该校验，编译器不悄悄翻转坐标；
- `sequenceScatterPixel` 在0.1.1实际固定300×300；与其不一致的尺寸请求须显示已核实诊断，不能把 `size` 编译成功视作尺寸生效。
- 普通 `bar` 等类型不接受通用 `title` / `legends`；仅在对应类型支持这些字段时使用。
- 所有类型均输出静态画面，不提供交互或动画播放。

## 5. 诊断与输入限制

通过 `MermaidError.code` 读取错误类别。常见 DSL 错误包括 `VCHART_DSL_SYNTAX`、`VCHART_DSL_DUPLICATE_WRITE`、`VCHART_DSL_PATH_CONFLICT`、`VCHART_DSL_TABLE_ARITY`、`VCHART_DSL_REFERENCE`、`VCHART_DSL_RESOURCE_CONFLICT`，分别对应语法、重复赋值、路径冲突、表格列数、变量引用及资源冲突。

可定位的错误还提供 `MermaidError.span`。`compile_vchart(text)` 的结果可用 `.source_map` 查看原文与目标属性的对应关系；`.as_dict()` 包含规格、资源、诊断及位置编码信息。供应方的字段错误保留其错误消息，不保证每一种渲染错误都能精确定位到某个字段。

源文本上限为 8 MiB，值深度最多 128，展开后值节点最多 1,000,000。资源单项最多 32 MiB、bundle 最多 128 MiB；内联资源还受文本总大小约束。较大的资源使用显式 API/CLI 参数提供。
