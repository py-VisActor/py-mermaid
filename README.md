# py-mermaid

中文 | [English](README.en.md)

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) 将 Mermaid 图语言迁移到 Python，使用 py-skia-canvas 测量、绘制和编码，使用独立 py-elk 布局。生产运行无需 Node、浏览器或 JavaScript 引擎。

**当前交付范围为 F01.1 基础流程图。** 支持 `flowchart` / `graph`、TD / LR、矩形与普通文字、`-->`、单节点、链、分支和合流。进度见[执行计划](docs/F01_1_EXECUTION_PLAN.md)、[使用说明](docs/F01_1_USAGE.md)和[账本](docs/execution-state.json)。源码版本 `0.0.1a0` 为本地开发版本，未发布到 PyPI。

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
```

## 支持边界

Mermaid 固定 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`；真实布局依赖 `py-visactor-elk==0.1.0`，测量/绘制依赖 `py-skia-canvas==0.1.0a18`。有效流程图默认为图种级 `redux-color/neo`：白矩形、深色边框/文字、普通黑箭头、阴影及实测文字换行。系统 fallback 字体不捆绑。

边标签、子图、其他形状、HTML/Markdown/math、其他主题/look、Dagre、插件和非PNG导出尚未实现，明确报错。本切片不代表完整 flowchart 或 Mermaid 兼容完成。Windows 本地证据与 Linux/no-loader 未验项分别记录。

验收比较功能、内容、关系、可读性和安全；跨 DOM/Canvas 像素仅诊断。正常字体/抗锯齿/自然尺寸/合法路由差异允许存在，漏内容和错误关系必须失败。

## 研发入口

本轮顺序为源码 → 来源测试 → 分组运行/根因修复 → 同候选最终验收。见[计划](docs/F01_1_EXECUTION_PLAN.md)、[接口](docs/F01_1_INTERFACES.md)、[测试工具](tools/oracle/README.md)及[发布状态](docs/RELEASE_STATUS.md)。

[完整迁移计划](docs/FULL_MIGRATION_PLAN.md)、[任务图](references/migration-execution.json)、[完整功能分母](docs/compatibility.json)及[依赖来源树](docs/DEPENDENCY_MIGRATION.md)保留为后续规划；当前不扩其他图种。[Canvas冒烟示例](examples/canvas_smoke.py)只验证基础依赖。
