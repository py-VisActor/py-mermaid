# py-mermaid

中文 | [English](README.en.md)

项目仓库：[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)。

将 Mermaid JS 的语法、配置、布局与 spec 渲染行为全面移植到 Python，唯一生产渲染引擎采用 [py-skia-canvas](https://github.com/xuanhun/py-skia-canvas)。目标运行环境无需 Node、浏览器或 JavaScript 引擎。

**当前为项目启动阶段：已建立结构、锁定上游、生成 spec 文件清单和开发入口；尚无 Mermaid 解析/布局/渲染 API，也未发布可用的 Mermaid 渲染包。** `examples/canvas_smoke.py` 仅验证真实 Canvas 依赖，不代表 Mermaid 渲染完成。

## 基线与范围

首轮固定 **mermaid@12.2.0**，源码提交 `1fb7869866dd619168d840291c9c54b4f129758b`；[锁定文件](references/upstream.lock.json)记录版本、关键文件 SHA256 与布局/解析扩展包版本。上游依据是[固定源码](https://github.com/mermaid-js/mermaid/tree/1fb7869866dd619168d840291c9c54b4f129758b)，在线文档只作导航。

[源码清单](references/spec-inventory.json)包含 **37 个核心 detector + ZenUML 外部插件**、368 个测试源文件、2,366 个渲染 `.mmd` fixture、38 个语法文件、34 篇语法文档。这是文件盘点，不是独立测试用例数或通过率。所有图种的解析、布局和渲染仍待实现，逐项状态见 [compatibility.json](docs/compatibility.json)。

目标覆盖全部图种、错误输入、frontmatter/directive、配置与主题、标签/字体、布局/路由、图形/marker、资源/安全、无障碍元数据及导出。浏览器 DOM/交互、HTML/CSS、数学和外部插件须建立明确的 Python 对应并验收，不能从兼容分母中消失。详见 [兼容规则](docs/API_COMPATIBILITY.md)。

Canvas 依赖固定 `py-skia-canvas==0.1.0a18`，首轮环境为 **CPython 3.13 / Windows AMD64 / Linux glibc 2.28+ x86_64**。Canvas 的 GPU/CPU 策略和线程约束沿用公开库；macOS/其他 ABI 尚未验收。Mermaid 的图布局由本项目移植，文字 shaping、绘制与编码由 Canvas 完成。

## 开始开发

在仓库根目录执行。以下 `python` 应指向 CPython 3.13 的独立虚拟环境；Windows 建议短路径，例如 `C:\venvs\pymmd`。

```shell
python -m venv .venv
```

先激活虚拟环境，再安装本地开发骨架与固定依赖：

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -m pip install -e ".[dev]"
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/canvas_smoke.py --out test-runs/my-canvas-auto
python examples/canvas_smoke.py --backend cpu --out test-runs/my-canvas-cpu
```

源码资料检查无需安装 Canvas；`upstream.py` 需要 Git 和首次下载网络。生产包将不包含 `.local` 或研发 oracle。GPU 依赖示例可另用 `--backend gpu`，若实际不是 GPU 则失败。新输出目录已存在时会拒绝覆盖。

## 结构与工作入口

| 路径 | 职责 |
| --- | --- |
| [AGENTS.md](AGENTS.md)、[NEW_SESSION](docs/NEW_SESSION.md) | 人与 AI 的启动顺序及可复制的新会话任务 |
| [实施方案](docs/IMPLEMENTATION_PLAN.md)、[任务清单](docs/TASKS.md) | 分层架构、阶段交付和下一批验收 |
| [兼容规则](docs/API_COMPATIBILITY.md)、[测试方案](docs/TEST_AND_RELEASE.md) | spec 边界、对照协议、GPU/CPU/字体/导出门禁 |
| [src/py_mermaid](src/py_mermaid) | parsing / model / layout / diagrams / config / rendering/skia 模块边界 |
| [references](references/README.md) | 上游锁、只读来源与 spec 文件索引 |
| [tests](tests/README.md)、[tools/oracle](tools/oracle/README.md) | 启动断言、测试输入及待实现的官方 JS 对照工具 |
| [examples](examples/README.md) | 已可运行的 Canvas 依赖检查 |
| [发布状态](docs/RELEASE_STATUS.md) | 启动状态、实际证据与未验收项 |

完整迁移路线已细化为 [M0–M8 实施方案](docs/IMPLEMENTATION_PLAN.md)和[逐项工作分解](docs/TASKS.md)，覆盖全部图种、共享能力、布局算法、官方对照及发行门禁。锁定源码默认布局为 ELK，首个 flowchart 切片也必须验证该默认路径；计划整理不表示新增渲染能力。

遵循 MIT 许可；保留[上游版权](references/licenses/mermaid-LICENSE)和[第三方说明](THIRD_PARTY_NOTICES.md)。本仓库使用 Canvas 公开 Python API；发现 Canvas 缺口时在其仓库单独修复和验证，不复制或修改其 Rust/Skia 核心。
