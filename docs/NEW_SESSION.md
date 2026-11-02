# 新会话启动文档

2026-11-02：项目已迁移至 [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)，本地启动结构已建立。当前源码版本 `0.0.1a0` 仅表示骨架，未发布 Mermaid 渲染功能。当前事实见 [RELEASE_STATUS](RELEASE_STATUS.md)，逐图种见 [compatibility.json](compatibility.json)。

## 需求与基线

用户目标是**全面移植 Mermaid JS spec 渲染到 Python，渲染引擎基于 py-skia-canvas**。不是只支持 flowchart，也不是让 Python 调用 JS 或把浏览器 SVG 截图包装成 Python 渲染。

参考 [py-skia-canvas](https://github.com/xuanhun/py-skia-canvas) 的锁定来源、宿主边界、共享输入差分、真实输出证据与启动文档方法；不要照抄其“Rust 核心机械拆分”方案。Mermaid 的语法、配置、图布局与 SVG/DOM 渲染在本项目建立 Python 实现，Canvas 提供底层文本与绘图能力。

- Mermaid：`12.2.0`，tag `mermaid@12.2.0`，commit `1fb7869866dd619168d840291c9c54b4f129758b`。
- Canvas：`py-skia-canvas==0.1.0a18`。首轮 CPython 3.13，Windows AMD64 / Linux glibc 2.28+ x86_64。
- 研发源码 checkout：`.local/upstream-mermaid/`，只读且不进入产品包。
- 实际源码清单：37 个 core detector + ZenUML 插件；368 个测试源文件、2,366 个渲染 fixture、38 个 grammar、34 篇语法文档。尚未拆成逐断言清单。
- 当前没有 parse/render/CLI 产品接口；包只公开版本信息，模块目录仅划分职责。

## 首次操作

Windows PowerShell 可使用短路径新环境：

```powershell
py -3.13 -m venv C:\venvs\pymmd
C:\venvs\pymmd\Scripts\Activate.ps1
```

Linux shell 可使用：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

先按 [AGENTS](../AGENTS.md) 完成必读，检查 Git 状态。使用 CPython 3.13 独立环境，安装步骤见 [README](../README.md#开始开发)。然后执行：

```shell
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/canvas_smoke.py --out test-runs/session-canvas-auto-001
python examples/canvas_smoke.py --backend cpu --out test-runs/session-canvas-cpu-001
```

GPU 资源可用时另验 `--backend gpu`；未验 GPU 不得写 GPU 通过。命令输出已有时换新 run-id。bootstrap 不装 Canvas 也可运行；真实绘图需要安装固定 wheel。不要重新编译 Skia/Node 来完成启动资料检查。

## 下一批的具体任务

按[完整实施方案](IMPLEMENTATION_PLAN.md)和 [任务编号](TASKS.md)执行：先完成 M1 的用例/契约拆分及 M2 oracle 最小闭环，再进入 M3 flowchart 的完整垂直切片。第一轮至少固定：基础有向图、带标签边、子图、错误语法、frontmatter/theme、HTML 标签开关。每个用例保存官方 A 的 parse/model、SVG/布局测量、PNG、字体/浏览器/依赖指纹和 Python 候选输出。

2026-11-02 计划审计补充：锁定源码默认布局是 ELK，M3 需最小真实 ELK 路径；显式 Dagre 原型不算默认行为通过。实际 detector 注册顺序不同于 import 索引；`gitGraphParser.ts` 有内联测试，M1 要补查命名规则以外的断言。六组局部闭环不代表全量 M1/M2 已完成。当前没有新增 Mermaid 实现。

Node A 使用同一锁定源码发布物；浏览器和工具版本在 M2 固定，当前没有已实现的采集器或已捕获的 oracle。Canvas 冒烟输出不能代替 JS Mermaid 基线。先盘点浏览器 SVG 文本/HTML 差异，再确定等价契约；未获决策的不可等价行为保留 open 状态。

## 可直接粘贴给开发 AI

```text
在 py-VisActor/py-mermaid 完成 Mermaid JS spec 的 Python 移植，使用 py-skia-canvas。
先完整阅读 AGENTS.md 指定资料，检查 Git 状态并保留已有修改。
基线固定 mermaid@12.2.0 / 1fb7869866dd619168d840291c9c54b4f129758b，Canvas 0.1.0a18。
先运行 bootstrap 和 upstream check；资料通过不等于 Mermaid 渲染通过。
当前只有骨架和文件级清单；parse/layout/render、JS oracle 和发布都未完成。
下一步完成 M1 用例与宿主契约，再完成 M2 官方 JS 对照器与 M3 flowchart 垂直切片。
细化每个 spec 的输入、配置、期望、错误与源位置；全图种和跨图种能力留在分母。
生产运行不调用 Node/浏览器/JS；只使用 Canvas 公开 API，不复制其 Rust/Skia。
不改默认 GPU/CPU、字体 shaping 或底层编码；Canvas 对象只在 owner 线程使用。
保留修改前证据，用候选包、官方基线和独立断言检查语义、布局、输出与生命周期。
不要宣称浏览器 SVG 与 Canvas 天然逐像素相等，不隐藏差异或擅自放宽验收。
同批更新契约、双语 README、真实示例和图像来源；记录实际命令、SHA、限制及下一步。
本地交付不自动授权 commit/push/Release/PyPI，按本次用户授权处理。
```

## 恢复检查

读取最新 `docs/changes/` 记录与独立 `test-runs/`，确认源码 SHA/依赖/字体未变。若只存在本地文件，不能声称远端已有启动资料。旧会话通过只适用于其记录的源码、环境与范围。
