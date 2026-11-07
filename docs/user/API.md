# Python API 与命令行

[用户文档](../README.md)

## Python 入口

以下函数从 `py_mermaid` 导入。带 `*` 的参数均以关键字传递。

```text
parse(text, *, config=None)
render(text, *, config=None, format="png", backend="auto",
       resources=None, export_options=None, maps=None, svgs=None)
arender(text, *, config=None, format="png", backend="auto",
        resources=None, export_options=None, maps=None, svgs=None)
render_vchart(spec, *, format="png", backend="auto",
              resources=None, export_options=None, maps=None, svgs=None)
arender_vchart(spec, *, format="png", backend="auto",
               resources=None, export_options=None, maps=None, svgs=None)
compile_vchart(text, *, config=None, maps=None, svgs=None)
supported_vchart_types()
```

以上是签名说明；实际调用示例见[快速开始](QUICKSTART.md)及 [VChart 指南](VCHART.md)。

| 入口 | 用途与返回 |
| --- | --- |
| `parse` | 只解析，不创建 Canvas 或 ELK，返回不可变 `Flowchart` 或 `Diagram` |
| `render` / `arender` | 渲染 Mermaid 或 VChart 文本，返回 `RenderResult` 或 `DiagramRenderResult` |
| `render_vchart` / `arender_vchart` | 直接绘制 Python 中的 VChart spec 字典 |
| `compile_vchart` | 检查图表文本，返回 `VChartCompilation`；用 `.spec()` 读取编译规格 |
| `supported_vchart_types` | 返回当前依赖实际注册的 VChart 类型 |

`config` 是显式 Mermaid 配置映射。示例：`render(source, config={"theme": "dark"})`。VChart 样式在 spec 中配置，不经过 Mermaid 主题改写。`maps`、`svgs` 仅用于显式 VChart 输入。

编译成功只表明语法和基础结构检查通过，图表选项、统计计算、设备和字体仍须在渲染时校验。

## 结果、错误与线程

渲染结果的共同字段包括 `data`（bytes）、`width`、`height`、`mime`、`diagram`、`backend` 和 `diagnostics`。例如将 `result.data` 写入文件，或直接作为 HTTP 响应内容。

失败通过 `MermaidError` 显式报告，`exc.code` 为错误码；适用的语法错误还含 `exc.span` 原始文本位置。不要将错误当空图处理。布局脚本需要 main 保护；在已有事件循环中使用异步 API。原生绘制对象不应跨线程共享。

## CLI

```shell
py-mermaid input.mmd -o output.svg
python -m py_mermaid input.mmd -f png --backend cpu -o output.png
py-mermaid chart.vchart --compile -o compiled.json
```

| 参数 | 含义 |
| --- | --- |
| `input` | UTF-8 输入文件；省略或 `-` 从标准输入读取 |
| `-o`, `--output` | 输出文件；省略时将结果字节写到标准输出 |
| `-f`, `--format` | `png`、`jpg`、`jpeg`、`webp`、`svg`、`pdf`；默认按输出后缀推断，否则为 PNG |
| `--backend` | `auto`（默认）、`cpu` 或 `gpu` |
| `--config` | 显式本地 JSON 配置文件 |
| `--resources` | 显式图片、图标和字体资源清单 |
| `--vchart-maps`, `--vchart-svgs` | 名称到 GeoJSON、SVG 源文本的 JSON 映射 |
| `--metadata` | 另存尺寸、MIME、实际后端和诊断 |
| `--compile`, `--compile-only` | 仅编译 VChart 文本为 JSON，不绘图 |
| `--quality`, `--density`, `--matte` | 导出质量、密度及背景色 |
| `--outline`, `--downsample` | 导出文字轮廓或下采样选项 |

更多说明见[资源与导出](RESOURCES.md)。
