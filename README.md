# py-mermaid

中文 | [English](README.en.md)

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) 将 Mermaid 图语言迁移到 Python，使用 py-skia-canvas 测量、绘制和编码，使用独立 py-elk 布局。生产运行无需 Node、浏览器或 JavaScript 引擎。

**当前静态批次保留 31 个入口：29 个新增入口及 2 个流程图回归入口。** 范围见下表，统一 API、CLI 和资源合同见 [批次用法](docs/BULK_USAGE.md)，实际验收状态见[账本](docs/execution-state.json)。已有流程图支持五个方向及别名、经典与新形状、静态边和双端标记、样式、子图、富文本、ELK、手绘及显式离线资源，详见 [F01.4 用法](docs/F01_4_USAGE.md)。适用的 `htmlLabels=true` 标签通过正式 [py-visactor-katex](https://pypi.org/project/py-visactor-katex/0.1.0/) 原生绘制 `$$...$$`，导入名 `py_katex`；`htmlLabels=false` 保留原实现的文字分支。数学覆盖见 [py-katex 文档](https://github.com/py-VisActor/py-katex#readme)。所有模块只考虑静态渲染。源码版本 `0.0.1a0` 为本地开发版本，未发布到 PyPI。

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

统计图表（pie/quadrantChart/xychart/radar）、矩形树图（treemap）、桑基图（sankey）、韦恩图（venn）共 7 个入口本批暂缓，不计入本批验收。原始来源清单保留全部 38 个入口。

## 安装与调用

需要 CPython 3.13，安装本地源码及固定依赖：

```shell
python -m pip install .
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

F01.4 源码扩展涵盖五向及方向别名、批量连接、边 ID/标记/线型、style/class/linkStyle、`@{shape}` 新形状、初始折叠子图、ELK 家族选项、手绘、显式离线资源及 PNG/JPG/WebP/SVG/PDF 静态导出。数学依赖为正式 `py-visactor-katex==0.1.0`，无需相邻源码目录接线。关系图使用真实 ELK，mindmap/tidy、architecture、泳道、时间日历、Git、C4、铁路图和 ZenUML 保留各自专用算法；treeView 使用源 preorder 行布局。原生布局和图种可通过 Python provider 注册。Dagre 功能、选项、目标依赖与算法回退完全排除，见[布局策略](docs/LAYOUT_POLICY.md)。各入口的实现、分组复验与同候选验收分别记账，不以源码存在或少量图片宣称完整兼容；本批安装验证继续暂缓，历史数学安装和不同平台证据的范围见[发行状态](docs/RELEASE_STATUS.md)。

验收比较功能、内容、关系、可读性和安全；跨 DOM/Canvas 像素仅诊断。正常字体/抗锯齿/自然尺寸/合法路由差异允许存在，漏内容和错误关系必须失败。

## 研发入口

本轮顺序为全部保留源码 → 来源独立测试 → 全分组首跑/批修 → 同候选最终验收。见[当前计划](docs/BULK_STATIC_EXECUTION.md)、[共享接口](docs/BULK_STATIC_INTERFACES.md)、[统一批次日志/报告](tools/BULK_REPORTS.md)及[发布状态](docs/RELEASE_STATUS.md)。

[完整迁移计划](docs/FULL_MIGRATION_PLAN.md)、[任务图](references/migration-execution.json)、[完整功能分母](docs/compatibility.json)及[依赖来源树](docs/DEPENDENCY_MIGRATION.md)保留全范围来源；当前执行范围以 [31 保留 / 7 暂缓](references/bulk-scope.json)为准。[Canvas冒烟示例](examples/canvas_smoke.py)只验证基础依赖。

固定上游 ELK radial 容器可能产生子节点超出原外框的已知缺陷；保留真实引擎框与 A/B 图并单独标记，不通过扩大边框掩盖。外部 Font Awesome CSS 需以同名离线 IconResource 显式提供；字体、图片不自动联网。全语言自动断词字典不在当前原生标签合同中。
