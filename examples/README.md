# 可运行示例

[用户文档](../docs/README.md) · [快速开始](../docs/user/QUICKSTART.md)

安装 `py-visactor-mermaid` 后，在仓库根目录运行以下脚本。脚本使用带 main 保护的真实 Mermaid 输入，默认使用自动设备策略；已有输出文件会拒绝覆盖，请选择新文件名。

| 示例 | 内容 |
| --- | --- |
| [basic_flowchart.py](basic_flowchart.py) | 基础节点、分支与合流 |
| [enhanced_flowchart.py](enhanced_flowchart.py) | 增强节点、连线与样式 |
| [rich_flowchart.py](rich_flowchart.py) | 富文本与静态标签 |

```shell
python examples/basic_flowchart.py --out diagram-basic.png
python examples/enhanced_flowchart.py --out diagram-enhanced.png
python examples/rich_flowchart.py --out diagram-rich.png
```

例如显式选择 CPU：

```shell
python examples/basic_flowchart.py --backend cpu --out diagram-cpu.png
```

下图为已保存的基础流程图输出。字体和设备不同可能影响文字度量与外观；本次文档重整未重新绘制该图。

![基础流程图的分支与合流](../docs/assets/f011-branch-merge.png)

图表 spec 与 DSL 示例见 [VChart 指南](../docs/user/VCHART.md)。更多格式、资源和错误处理见 [API 与 CLI](../docs/user/API.md)。

[canvas_smoke.py](canvas_smoke.py) 只检查底层 Canvas 依赖，不是 Mermaid 使用示例。维护者需要核对原图来源时可查 [f011-manifest](../docs/assets/f011-manifest.json) 与 [Canvas manifest](../docs/assets/manifest.json)。
