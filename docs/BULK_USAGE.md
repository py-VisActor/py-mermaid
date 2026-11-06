# 静态图种、API 与 CLI

固定源 Mermaid 12.2.0；本批 31 个入口，7 个入口暂缓，见 [机器范围](../references/bulk-scope.json)。
本文件说明调用合同，验收结果单独见 [当前执行](BULK_STATIC_EXECUTION.md)与账本，不把示例视为全部功能证明。
全部模块忽略交互、动画播放与交互元数据。SVG/PDF 是 Canvas 静态导出，不承诺 Mermaid DOM/事件/无障碍行为。

## Python

```python
from pathlib import Path
from py_mermaid import parse, render

if __name__ == '__main__':
    source = 'classDiagram\nAnimal <|-- Duck\nAnimal : +int age\nDuck : +swim()'
    diagram = parse(source)
    print(diagram.kind)  # classDiagram
    result = render(source, format='svg', backend='cpu')
    Path('classes.svg').write_bytes(result.data)
    print(result.width, result.height, result.mime, dict(result.backend))
```

`parse` 不分配 Canvas 或 ELK，返回不可变的 `Flowchart | Diagram`；普通家族的 `Diagram.model` 是各自纯语义值。
既有流程图仍返回 `Flowchart`，保持 `diagram_type`、nodes/edges/groups 等合同。
`render` 返回 `RenderResult | DiagramRenderResult`，包括 bytes、尺寸、MIME、模型、测量/布局、绘制 trace 与实际后端。
异步应用调用 `await arender(...)`，不要在已运行的事件循环中调用同步 `render`。

`backend='auto'` 保持 Canvas 默认策略；`cpu` 显式使用 CPU，`gpu` 要求实际 GPU，缺设备明确失败。
Canvas、字体、Path、Image 等原生对象留在创建线程，跨线程只传 bytes 或不可变模型。
ELK 使用 worker 的脚本必须有 main 保护；关闭和取消由相应 provider 管理。

格式：`png`、`jpg`/`jpeg`、`webp`、`svg`、`pdf`；`ExportOptions` 可显式传质量、密度、matte、outline、downsample。
需要在未安装同字体的宿主查看 SVG 时可使用 `ExportOptions(outline=True)` 将文字转为轮廓。
不支持的格式、配置、资源或语法返回有 code 的 `MermaidError`；适用的语法错误附原文/UTF-16 位置。

## 输入头与算法

| 入口 | 示例头 |
| --- | --- |
| flowchart-v2 / flowchart-elk | `flowchart LR` / `graph TD` / `flowchart-elk` |
| 建模六类 | `classDiagram`、`stateDiagram-v2`、`erDiagram`、`requirementDiagram`、`usecase-beta`、`C4Context` |
| C4 变体 | C4Context / C4Container / C4Component / C4Dynamic / C4Deployment |
| 时序、时间 | `sequenceDiagram`、`zenuml`、`gantt`、`journey`、`timeline`、`gitGraph` |
| 层级、结构 | `mindmap`、`treeView-beta`、`block-beta`、`packet-beta`、`kanban`、`architecture-beta` |
| 业务六类 | `swimlane-beta`、`agentflow-beta`、`eventmodeling`、`ishikawa-beta`、`wardley-beta`、`cynefin-beta` |
| 铁路四入口 | `railroad-beta`、`railroad-ebnf-beta`、`railroad-abnf-beta`、`railroad-peg-beta` |
| 信息 | `info` |

入口数不等于 provider 文件数，例如四个铁路入口共享绘制组合器，C4 多个头归一个 detector。
完整语法、正负边界、资源与来源符号见 `tests/bulk/cases-*.json` 和 `references/bulk-*-assertions.json`。

ELK 使用真实 `py-visactor-elk==0.1.0`。默认及显式 ELK 家族保留，不提供 Dagre 或算法回退。
mindmap 默认 COSE、可显式选择适用的 tidy-tree；architecture 使用专用 fCoSE。
泳道保留 Sugiyama、端口、A* 路由与 materialized 后处理；C4、日历/Git、treeView、铁路及 ZenUML 保留专用几何。
`viewportWidth` 是显式原生宿主适配，未提供时为 1200；浏览器/Canvas 的自然尺寸和字体度量可以不同。
新增 provider 使用 `register_diagram` 或 `register_layout`，见共享接口文档；注册的专用算法有自己的输入适用条件。

## 离线资源与数学

生产直接依赖仅 `py-skia-canvas==0.1.0a18`、`py-visactor-elk==0.1.0` 和正式 `py-visactor-katex==0.1.0`。
Node、浏览器、Pillow 和固定上游 checkout 仅供研发对照，不是渲染 fallback。
数学仅在原 renderer 使用共享富标签的分支启用，未消费公式的图种保持源行为。
图片/图标/字体必须使用显式 `ResourceBundle` 或 CLI 清单，资源不隐式联网。
源内置 SVG、KaTeX 数学字体与许可随包保留；系统 fallback 字体由宿主提供。

外部 SVG 中的脚本、事件、外部引用与实体/DOCTYPE 不进入原生解码。
锁定内置 ZenUML 资产的非绘制 W3C DOCTYPE 仅在该可信 adapter 中去除，原始资源与许可字节仍保留。

## CLI

```powershell
python -m py_mermaid classes.mmd -o classes.svg --backend cpu --metadata classes.json
python -m py_mermaid sequence.mmd -o sequence.pdf --config config.json --resources resources.json
```

输入 `-` 表示 UTF-8 stdin；未指定输出文件时向 stdout 写 bytes，JSON 错误写 stderr。
默认格式由输出后缀推断，也可用 `--format` 指定；`--outline`、`--quality`、`--density`、`--matte`、`--downsample` 对应静态编码选项。
输出不能覆盖输入、配置或资源清单；图片与 metadata 也不能共用同一路径。

资源清单仅指向调用者明确提供的本地文件，路径相对清单目录：

```json
{
  "images": {"photo": {"path": "photo.png", "mime": "image/png", "sha256": "文件SHA256"}},
  "icons": {"test:user": {"path": "user.svg", "sha256": "文件SHA256"}},
  "fonts": [{"family": "Fixture Font", "path": "font.ttf", "sha256": "文件SHA256"}]
}
```

源码 `0.0.1a0` 尚未发布为 py-mermaid 发行包；本批安装验证、commit、push 与发布均不自动执行。
