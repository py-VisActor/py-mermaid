# py-mermaid

中文 | [English](https://github.com/py-VisActor/py-mermaid/blob/main/README.en.md)

正式发行名为 `py-visactor-mermaid`，导入名为 `py_mermaid`，命令行为 `py-mermaid`。源码版本为 `0.1.0`，实际验证和发布状态见[收口记录](https://github.com/py-VisActor/py-mermaid/blob/main/docs/CLOSURE_BATCH_PLAN.md)。图表能力及其供应方边界由 py-vchart 管理；本批集中补齐其余语法、日期、关系与静态绘制能力。所有输出均为静态图像。

原生图表 DSL v1 使用 `vchart <类型>`、属性赋值、`table`、纯值变量、配置块及轴/系列声明，复用全部68个注册类型的正式渲染链路。语言范围与验证状态见[语法规范](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_DSL_DESIGN.md)与[执行计划](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_DSL_EXECUTION_PLAN.md)记录实际状态。

```python
from pathlib import Path
from py_mermaid import compile_vchart, render

source = """vchart bar
size 640 360
data = { values: table(month, value) {
  ["Jan", 120]
  ["Feb", 180]
} }
xField = "month"
yField = "value"
"""
compiled = compile_vchart(source)
print(compiled.spec())
Path("dsl.svg").write_bytes(render(source, format="svg").data)
```

CLI 可用 `py-mermaid chart.vchart --compile -o compiled.json` 检查完整 spec、地图/SVG资源、来源映射和诊断；直接渲染仍使用原 `-f/--backend` 等参数。旧 `vchart` 加严格 JSON 及 Python spec API 保留。

2026-11-07：已接入 `py-visactor-vchart` 0.1.1，以显式 VChart spec 支持全部 68 个二维静态类型，并恢复此前暂缓的 7 类 Mermaid 图表入口。依赖从 PyPI 解析 `py-visactor-vchart==0.1.1`，文件与 [GitHub 正式发行](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.1) 的验收 SHA-256 完全一致。[接入验收](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_INTEGRATION.md)。下方 31 入口是历史批次范围；非图表22条旧缺口的修复和验证以最新收口记录为准。

```python
from pathlib import Path
from py_mermaid import render_vchart, supported_vchart_types

print(supported_vchart_types())
result = render_vchart({
    "type": "bar", "width": 400, "height": 240,
    "data": [{"values": [{"name": "A", "value": 8}, {"name": "B", "value": -3}]}],
    "xField": "name", "yField": "value",
}, format="svg", backend="auto")
Path("chart.svg").write_bytes(result.data)
```

文本入口为 `vchart` 首行加严格 JSON，可用现有 `render`/`arender` 和 CLI；异步 spec API 为 `arender_vchart`。图表规格不经 Mermaid directives/HTML 改写；图表配置写在 spec 中，独立资源使用 `maps`、`svgs` 与 `ResourceBundle`。全部类型指 py-vchart 的实际二维入口，不宣称 3D、交互或所有 JS 高级样式。运行时无 Node、浏览器或 skia-python；使用正式发行依赖，不读取相邻仓库源码。

CLI 通过 `--vchart-maps maps.json` 提供 name→GeoJSON 的离线映射，`--vchart-svgs svgs.json` 提供 name→SVG 源文本；图片和字体沿用 `--resources`。Venn 继承当前供应方最多三个集合的限制；Treemap 使用 VChart binary 布局，部分数值格式明确拒绝，自定义字体绑定单个 `fontFamily`，按内容哈希隔离；自定义 fallback 列表明确报错。具体边界与真实验证见上面的执行记录。

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) 将 Mermaid 图语言迁移到 Python，使用 py-skia-canvas 测量、绘制和编码，使用独立 py-elk 布局。生产运行无需 Node、浏览器或 JavaScript 引擎。

**下表为历史静态批次的 31 个入口：29 个新增入口及 2 个流程图回归入口。** 范围见下表，统一 API、CLI 和资源合同见 [批次用法](https://github.com/py-VisActor/py-mermaid/blob/main/docs/BULK_USAGE.md)，实际验收状态见[账本](https://github.com/py-VisActor/py-mermaid/blob/main/docs/execution-state.json)。已有流程图支持五个方向及别名、经典与新形状、静态边和双端标记、样式、子图、富文本、ELK、手绘及显式离线资源，详见 [F01.4 用法](https://github.com/py-VisActor/py-mermaid/blob/main/docs/F01_4_USAGE.md)。适用的 `htmlLabels=true` 标签通过正式 [py-visactor-katex](https://pypi.org/project/py-visactor-katex/0.1.0/) 原生绘制 `$$...$$`，导入名 `py_katex`；`htmlLabels=false` 保留原实现的文字分支。数学覆盖见 [py-katex 文档](https://github.com/py-VisActor/py-katex#readme)。所有模块只考虑静态渲染。源码版本为 `0.1.0`；发布状态由收口记录单独记实。

| 类型 | 本批入口 |
| --- | --- |
| 流程图 | flowchart-v2、flowchart-elk |
| 关系建模 | classDiagram、stateDiagram、er、requirement、usecase、c4 |
| 时序 | sequence、zenuml |
| 时间与过程 | gantt、journey、timeline、gitGraph |
| 层级 | mindmap、treeView |
| 结构 | block、packet、kanban、architecture |
| 业务 | swimlane、agentflow、eventmodeling、ishikawa、wardley、cynefin |
| 铁路语法 | railroad、railroadEbnf、railroadAbnf、railroadPeg |
| 信息 | info |

上一批排除的统计图表（pie/quadrantChart/xychart/radar）、矩形树图（treemap）、桑基图（sankey）、韦恩图（venn）共 7 个入口，本轮已接入 `py-vchart`，以本页开头的新验收记录为准。原始来源清单保留全部 38 个入口。入口验收不代表全部语法和配置分支覆盖，后续功能复核见[当前计划](https://github.com/py-VisActor/py-mermaid/blob/main/docs/NEXT_ITERATION.md)。已接入 HTML 表单控件的初始静态绘制，包括 input、button、select、textarea、meter/progress 和 fieldset/legend；[本轮范围与验收状态](https://github.com/py-VisActor/py-mermaid/blob/main/docs/HTML_HOST_ACCEPTANCE.md) 单独记录，不代表任意浏览器 HTML/CSS 的完整兼容。`video` / `audio` 已由用户整体排除，包括播放、解码、封面/占位、控制条和初始静态外观；不作为待办或验收项，输入中遇到时保留明确拒绝。普通图片/图标继续保留。

## 安装与调用

需要 CPython 3.13（Windows AMD64 / Linux x86_64）。正式包安装命令如下，实际发布状态见[发行记录](https://github.com/py-VisActor/py-mermaid/blob/main/docs/RELEASE_STATUS.md)；源码安装可用 `python -m pip install .`：

```shell
python -m pip install py-visactor-mermaid==0.1.0
```

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    result = render("flowchart TD\nA[Start] --> B[End]")
    Path("flowchart.png").write_bytes(result.data)
    print(result.width, result.height, result.mime)
```

ELK 使用进程 worker，脚本入口应有 main 保护。异步环境使用 `await arender(...)`，解析模型使用 `parse(...)`。Canvas 原生对象留在调用线程，只返回 bytes 和不可变数据。`backend="auto"` 保留默认策略，`cpu` 显式禁用 GPU，`gpu` 要求实际 GPU，否则失败。

```shell
python examples/basic_flowchart.py --out test-runs/my-flowchart.png
python examples/enhanced_flowchart.py --out test-runs/my-enhanced-flowchart.png
python examples/rich_flowchart.py --out test-runs/my-rich-flowchart.png
```

## 支持边界

Mermaid 固定 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`；真实布局依赖 `py-visactor-elk==0.1.0`，测量/绘制依赖 `py-skia-canvas==0.1.0a18`。有效流程图默认为图种级 `redux-color/neo`：白矩形、深色边框/文字、普通黑箭头、阴影及实测文字换行。系统 fallback 字体不捆绑。

经典形状支持 square、round、stadium、subroutine、cylinder、circle、doublecircle、diamond、hexagon、odd、trapezoid、inv_trapezoid、lean_right、lean_left。经典 `A(-Ellipse-)` 能解析，但固定上游缺少渲染处理器，渲染明确报告 `UPSTREAM_SHAPE_MISSING`。子图允许空组及只有组的图；组内方向支持 TD/TB/LR/RL/BT。

前处理保留到原文字符/UTF-16 位置的映射，配置按 site/frontmatter/directive 及图种默认优先级解析，主题使用固定源码的 11 个名称与 `null`。富标签通过不可变文字 run 与公开 Canvas API 测量/绘制，生产不创建 DOM。`htmlLabels=false` 按上游 SVG 文本含义处理标签，不是通用剥 HTML；Markdown 保留上游实际支持的粗体、斜体等分支，不宣称完整 CommonMark。适用的主题 CSS 映射为原生字体/颜色/描边等意图，浏览器交互样式不进入生产运行。

F01.4 源码扩展涵盖五向及方向别名、批量连接、边 ID/标记/线型、style/class/linkStyle、`@{shape}` 新形状、初始折叠子图、ELK 家族选项、手绘、显式离线资源及 PNG/JPG/WebP/SVG/PDF 静态导出。数学依赖为正式 `py-visactor-katex==0.1.0`，无需相邻源码目录接线。关系图使用真实 ELK，mindmap/tidy、architecture、泳道、时间日历、Git、C4、铁路图和 ZenUML 保留各自专用算法；treeView 使用源 preorder 行布局。原生布局和图种可通过 Python provider 注册。Dagre 功能、选项、目标依赖与算法回退完全排除，见[布局策略](https://github.com/py-VisActor/py-mermaid/blob/main/docs/LAYOUT_POLICY.md)。各入口的实现、分组复验与同候选验收分别记账，不以源码存在或少量图片宣称完整兼容；本批执行同候选回归及 Windows/Linux 隔离安装门禁；实际结果和不同平台证据见[发行状态](https://github.com/py-VisActor/py-mermaid/blob/main/docs/RELEASE_STATUS.md)。

验收比较功能、内容、关系、可读性和安全；跨 DOM/Canvas 像素仅诊断。正常字体/抗锯齿/自然尺寸/合法路由差异允许存在，漏内容和错误关系必须失败。

## 研发入口

本轮顺序为全部保留源码 → 来源独立测试 → 全分组首跑/批修 → 同候选最终验收。见[当前计划](https://github.com/py-VisActor/py-mermaid/blob/main/docs/CLOSURE_BATCH_PLAN.md)、[共享接口](https://github.com/py-VisActor/py-mermaid/blob/main/docs/BULK_STATIC_INTERFACES.md)、[统一批次日志/报告](https://github.com/py-VisActor/py-mermaid/blob/main/tools/BULK_REPORTS.md)及[发布状态](https://github.com/py-VisActor/py-mermaid/blob/main/docs/RELEASE_STATUS.md)。

[完整迁移计划](https://github.com/py-VisActor/py-mermaid/blob/main/docs/FULL_MIGRATION_PLAN.md)、[任务图](https://github.com/py-VisActor/py-mermaid/blob/main/references/migration-execution.json)、[完整功能分母](https://github.com/py-VisActor/py-mermaid/blob/main/docs/compatibility.json)及[依赖来源树](https://github.com/py-VisActor/py-mermaid/blob/main/docs/DEPENDENCY_MIGRATION.md)保留全范围来源；当前范围为全部38个 Mermaid 入口及 VChart 接线，按[收口计划](https://github.com/py-VisActor/py-mermaid/blob/main/docs/CLOSURE_BATCH_PLAN.md)与图表供应方职责验收；[31入口批次](https://github.com/py-VisActor/py-mermaid/blob/main/references/bulk-scope.json)仅为历史记录。[Canvas冒烟示例](https://github.com/py-VisActor/py-mermaid/blob/main/examples/canvas_smoke.py)只验证基础依赖。

固定上游 ELK radial 容器可能产生子节点超出原外框的已知缺陷；保留真实引擎框与 A/B 图并单独标记，不通过扩大边框掩盖。外部 Font Awesome CSS 需以同名离线 IconResource 显式提供；字体、图片不自动联网。全语言自动断词字典不在当前原生标签合同中。
