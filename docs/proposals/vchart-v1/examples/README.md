# VChart DSL v1 完整示例

这些 `.vchart` 现可直接交给 `compile_vchart()` 或 `render()`。每个示例独立保存手写预期 JSON 及显式资源；预期不是由被测编译器生成。8例均纳入独立编译对照、三后端真实绘制及报告，结果见 [验收记录](../../../VCHART_DSL_ACCEPTANCE.md)。

| 场景 | 设计源 | 预期 spec | 资源 |
|---|---|---|---|
| 柱状图/表格/变量/配置块 | [bar](bar.vchart) | [JSON](bar.expected.json) | [资源](bar.resources.json) |
| KDE 原始样本/统计参数 | [kde](kde.vchart) | [JSON](kde.expected.json) | [资源](kde.resources.json) |
| 柱线/双轴/系列索引 | [common-dual-axis](common-dual-axis.vchart) | [JSON](common-dual-axis.expected.json) | [资源](common-dual-axis.resources.json) |
| 嵌套层级与原生限制 | [treemap](treemap.vchart) | [JSON](treemap.expected.json) | [资源](treemap.resources.json) |
| 节点和边的复合数据 | [sankey](sankey.vchart) | [JSON](sankey.expected.json) | [资源](sankey.resources.json) |
| 数组型表格单元格/集合 | [venn](venn.vchart) | [JSON](venn.expected.json) | [资源](venn.resources.json) |
| 内联 GeoJSON | [map](map.vchart) | [JSON](map.expected.json) | [资源](map.resources.json) |
| 内联 SVG/图形数据绑定 | [pictogram](pictogram.vchart) | [JSON](pictogram.expected.json) | [资源](pictogram.resources.json) |

完整规则见 [语法规范](../../../VCHART_DSL_DESIGN.md)，阶段顺序见 [执行计划](../../../VCHART_DSL_EXECUTION_PLAN.md)。

在当前开发环境重新预览**预期 JSON 的实际可用性**（历史设计预览工具）：

```sh
python tools/preview_vchart_dsl_design.py
```

该工具创建独立标准Run，复制设计源、预期JSON和资源，以现有 `render_vchart(spec)` 绘制PNG；输出明确标注 `dslExecuted=false`，不解析 `.vchart`，也不证明新DSL已经通过验收。实际输出位于新Run的 `artifacts/<示例>/expected-json.png`。

2026-11-07 的8例预期JSON预览成功：`VCHART-DSL-DESIGN-expected-json-preview-20261107T064126Z-3fa0cbed`。首次地图环方向错误保留于 `...064105Z-fe18cef6`，只修正了设计源与预期资源的方向，没有修改供应方或放宽验证。
