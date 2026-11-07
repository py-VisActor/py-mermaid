# py-mermaid

中文 | [English](https://github.com/py-VisActor/py-mermaid/blob/main/README.en.md)

在 Python 中将 Mermaid 文本绘制为静态图像。支持流程图、时序图、关系建模和业务图，也可通过 VChart spec 或图表 DSL 绘制统计图表。运行时无需 Node.js、浏览器或 JavaScript 引擎。

## 安装

需要 CPython 3.13，支持 Windows AMD64 和 Linux x86_64（glibc 2.28+）。发行包名为 `py-visactor-mermaid`，Python 导入名为 `py_mermaid`。

```shell
python -m pip install py-visactor-mermaid==0.1.1
```

## 绘制流程图

将以下代码保存为 Python 文件并运行：

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    result = render("flowchart LR\nA[Start] --> B[End]", format="svg")
    Path("flowchart.svg").write_bytes(result.data)
```

布局使用进程 worker，脚本需要 `if __name__ == "__main__"` 保护。在已有事件循环中使用 `await arender(...)`。

命令行可直接读取 Mermaid 文件，按输出后缀选择格式：

```shell
py-mermaid diagram.mmd -o diagram.svg
```

## 能力与边界

- 输出 PNG、JPEG、WebP、SVG、PDF；支持主题、静态富文本与数学标签，以及显式提供的图片、图标和字体。
- 通过 `render_vchart(spec)` 或 `vchart <type>` 文本调用 py-vchart 的 68 个二维静态图表类型；具体选项遵循供应方的支持范围。
- `backend="auto"` 自动选择设备；可显式使用 `cpu` 或 `gpu`。字体和设备会影响文字度量与外观。
- SVG/PDF 为静态导出。不提供交互、动画、Dagre、音视频、任意浏览器 HTML/CSS 扩展或 3D。

## 文档

- [用户文档](https://github.com/py-VisActor/py-mermaid/blob/main/docs/README.md)：安装、Python API、CLI、图种及资源。
- [VChart 图表指南](https://github.com/py-VisActor/py-mermaid/blob/main/docs/user/VCHART.md)：spec、DSL 与离线地图资源。
- [可运行示例](https://github.com/py-VisActor/py-mermaid/tree/main/examples) · [版本发布](https://github.com/py-VisActor/py-mermaid/releases) · [问题反馈](https://github.com/py-VisActor/py-mermaid/issues)。

维护仓库或使用 AI agent 参与开发，请从 [开发者文档](https://github.com/py-VisActor/py-mermaid/blob/main/docs/development/README.md) 开始。

## 许可

项目原创代码采用 [MIT](https://github.com/py-VisActor/py-mermaid/blob/main/LICENSE)。移植代码、字体和资源的许可见 [第三方声明](https://github.com/py-VisActor/py-mermaid/blob/main/THIRD_PARTY_NOTICES.md)。
