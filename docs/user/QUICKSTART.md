# 快速开始

[用户文档](../README.md) · [English](QUICKSTART.en.md)

## 安装

使用 CPython 3.13，平台为 Windows AMD64 或 Linux x86_64（glibc 2.28+）：

```shell
python -m pip install py-visactor-mermaid==0.1.1
```

依赖会随安装解析，不需要检出其他 py-VisActor 仓库或安装 Node.js。普通文字使用宿主字体；离线自定义字体见[资源指南](RESOURCES.md)。

## Python

保存为 `draw.py`，再运行 `python draw.py`：

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    source = "flowchart LR\nA[Input] --> B{Valid?}\nB -->|Yes| C[Save]\nB -->|No| A"
    result = render(source, format="svg", backend="auto")
    Path("diagram.svg").write_bytes(result.data)
    print(result.width, result.height, result.mime)
```

默认输出 PNG，也可选择 `jpg`、`jpeg`、`webp`、`svg`、`pdf`。布局会启动进程 worker，因此脚本入口需要 main 保护。

`backend="auto"` 使用默认设备策略；`cpu` 明确使用 CPU，`gpu` 要求可用 GPU，无法使用时会报错。文字外观受安装字体和绘制后端影响。

## 命令行

创建 UTF-8 文件 `diagram.mmd`：

```text
flowchart LR
    A[Input] --> B[Output]
```

```shell
py-mermaid diagram.mmd -o diagram.svg
py-mermaid diagram.mmd --backend cpu -f png -o diagram.png --metadata diagram.json
python -m py_mermaid diagram.mmd -o diagram.pdf
```

`--metadata` 输出尺寸、MIME、实际后端与诊断；完整参数见 [API 与 CLI](API.md)。

## 异步环境

在已运行的事件循环中调用 `arender`，避免同步接口的 `ACTIVE_EVENT_LOOP` 错误：

```python
from py_mermaid import arender

async def draw(source):
    result = await arender(source, format="png")
    return result.data
```

将 Canvas 等原生对象保留在创建线程，跨线程传递输出字节。

下一步：[选择图种](DIAGRAMS.md)、[绘制 VChart 图表](VCHART.md)、[配置资源和导出](RESOURCES.md)。
