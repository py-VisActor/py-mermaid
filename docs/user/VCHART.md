# VChart 图表指南

[用户文档](../README.md) · [完整 DSL 语法](VCHART_DSL.md)

支持 py-vchart 当前注册的 68 个二维静态图表类型。用 `supported_vchart_types()` 查询实际名称；可用字段和条件限制见 [py-vchart 用户文档](https://github.com/py-VisActor/py-vchart/blob/main/docs/README.md)。

## Python spec

```python
from pathlib import Path
from py_mermaid import render_vchart, supported_vchart_types

if __name__ == "__main__":
    print(supported_vchart_types())
    result = render_vchart({
        "type": "bar", "width": 400, "height": 240,
        "data": [{"values": [{"month": "Jan", "value": 8}, {"month": "Feb", "value": -3}]}],
        "xField": "month", "yField": "value",
    }, format="svg")
    Path("bar.svg").write_bytes(result.data)
```

异步应用使用 `await arender_vchart(spec, ...)`。

## 文本 DSL

保存为 `chart.vchart`：

```text
vchart bar
size 640 360
data = { values: table(month, value) {
  ["Jan", 120]
  ["Feb", 180]
} }
xField = "month"
yField = "value"
```

```shell
py-mermaid chart.vchart -o chart.svg
py-mermaid chart.vchart --compile -o compiled.json
```

Python 中可用 `render(text)` 绘制，或 `compile_vchart(text).spec()` 查看编译结果。DSL 保留供应方字段名称，支持数组、对象、变量、配置块、轴、系列和内联资源；详见[语法参考](VCHART_DSL.md)。该扩展不能直接交给 Mermaid JS 渲染。

## 严格 JSON

首行只有 `vchart` 时，后续内容必须是严格 JSON 对象：

```text
vchart
{"type":"bar","width":400,"height":240,"data":[{"values":[{"x":"A","y":8}]}],"xField":"x","yField":"y"}
```

严格 JSON 不允许注释、裸键或尾逗号；DSL 模式不会在解析失败后回退为 JSON。

## 地图、SVG 与图像

显式使用 `maps={"name": geojson}`、`svgs={"name": svg_text}` 提供单次绘制的离线资源；CLI 对应 `--vchart-maps maps.json` 和 `--vchart-svgs svgs.json`。图片和字体通过 `ResourceBundle` 或 `--resources` 提供，见[资源与导出](RESOURCES.md)。

同名同类资源在内联声明与 API 参数中冲突时会报错，不静默覆盖。图表 spec 不经过 Mermaid 的主题或富标签改写；样式在 spec 中配置。编译成功不表示供应方已接受所有图表选项，完整校验发生在实际渲染时。
