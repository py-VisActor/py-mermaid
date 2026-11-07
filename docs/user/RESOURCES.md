# 资源与导出

[用户文档](../README.md)

## 显式离线资源

通过 `ResourceBundle` 传入图片、图标和字体。库不自动下载资源；源文本中的 URL 可作为资源查找 key，但不会触发联网。

```python
from pathlib import Path
from py_mermaid import FontResource, ImageResource, ResourceBundle

resources = ResourceBundle(
    images=(ImageResource("logo", Path("logo.png").read_bytes(), "image/png"),),
    fonts=(FontResource("MyFont", str(Path("font.ttf").resolve())),),
)
```

将 `resources=resources` 传给 `render` 或 `render_vchart`；字体还需在对应图种的配置中选用该 family。字体文件路径由调用者明确提供，不从源文本任意加载文件。

`IconResource(id, svg)` 提供独立 SVG 源文本。内联 SVG、data URI 和 SVG 图标仍受安全与预算校验，脚本、事件、外部引用或实体不会获得浏览器执行环境。外部 Font Awesome 名称需映射为同名离线图标资源。

CLI 使用 `--resources resources.json`。清单中的路径相对于清单文件解析，例如：

```json
{
  "images": {"logo": {"path": "logo.png", "mime": "image/png"}},
  "icons": {"my-icon": "icon.svg"},
  "fonts": [{"family": "MyFont", "path": "font.ttf"}]
}
```

## 数学标签

安装依赖 `py-visactor-katex` 已提供数学排版及离线数学字体。适用富标签分支使用 `$$...$$`；`htmlLabels=false` 保留普通文字分支。图种是否解释数学取决于它的标签语义。完整独立公式 API 见 [py-katex 用户文档](https://github.com/py-VisActor/py-katex/blob/main/docs/README.md)。

## 输出选项

```python
from py_mermaid import ExportOptions

options = ExportOptions(density=2, outline=True)
# render(source, format="svg", export_options=options)
```

| 选项 | 默认值 | 用途 |
| --- | --- | --- |
| `quality` | `0.92` | 有损编码质量 |
| `density` | `1` | 输出像素密度 |
| `matte` | `None` | 显式背景色 |
| `outline` | `False` | 将适用矢量导出的文字转为轮廓，方便无同字体的宿主查看 |
| `downsample` | `False` | 启用编码端下采样选项 |

SVG/PDF 使用 Canvas 静态编码，保留矢量图元；嵌入图片仍为栅格资源。导出不附带 Mermaid DOM 的链接、脚本或交互行为。
