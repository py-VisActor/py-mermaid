# AGENTS.md

## 1. 适用范围与职责

本文件适用于本仓库内执行任务的 AI coding agent。负责按当前用户请求修改、验证和交付本项目；库用户从 [用户文档](docs/README.md) 开始。

本文件只保存稳定工作规则。当前任务以会话指令为准；版本从 `pyproject.toml` 读取，发行事实从 [发布状态](docs/RELEASE_STATUS.md) 和具体 tag 读取。旧计划、旧授权、旧待办不自动启动新的任务。

## 2. 开始工作

1. 确认工作目录为本仓库，执行 `git status --short`，保留用户已有修改。
2. 阅读 [开发者入口](docs/development/README.md)，按任务选择相关指南，不默认重读全部迁移历史。
3. 涉及行为时核对 `references/upstream.lock.json`、相关源码、来源映射和当前范围；涉及发行时核对已发布 manifest，不以 main 的文档推断旧包字节。
4. 明确影响目录、验证范围和产出。多人工作时按 [协作规范](docs/PARALLEL_EXECUTION.md) 划定单文件 owner，共享文件只有一个写入者。

## 3. 仓库地图

| 路径 | 职责 |
| --- | --- |
| `src/py_mermaid/` | 公开 API、纯语义模型、语法、配置、布局、资源与静态绘制 |
| `src/py_mermaid/rendering/skia/` | 调用公开 Canvas API，管理原生对象生命周期 |
| `tests/` | 按功能和批次组织的回归；测试工具不进入产品运行路径 |
| `examples/`、`docs/user/` | 用户示例、API、语法和使用边界 |
| `docs/development/` | 开发规则、文档分工与历史入口 |
| `references/` | 固定来源、许可、范围与机器证据 |
| `tools/`、`scripts/` | 检查、独立来源采集、日志、报告及发行工具 |
| `test-runs/`、`reports/` | 本地执行产物，不作为公共文档的默认入口 |

## 4. 常用命令

使用 CPython 3.13。需要源码开发环境时运行 `python -m pip install -e ".[dev]"`，依赖与版本以项目元数据为准。

```shell
git status --short
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python tools/workflow.py --help
```

纯文档修改只运行文档、链接、元数据及相关示例检查，不重建或安装包。行为修改先保存起点证据，选择受影响的来源独立回归；完整矩阵与发行流程见 [验证与发行](docs/TEST_AND_RELEASE.md)，不因小改动反复运行全部已通过组。

## 5. 修改约束

- 行为来源固定 Mermaid 12.2.0 及锁文件中的提交；升级另开任务。生产不依赖 Node、浏览器、JavaScript 引擎、skia-python 或相邻源码目录。
- 只用公开 py-skia-canvas API；ELK、KaTeX、VChart 使用正式依赖。原生 Canvas、字体和图像对象留在创建线程。
- 只实现约定静态范围。交互、动画、Dagre、video/audio、任意 HTML/CSS 扩展及 3D 不自动加入任务。
- 不用成功 stub、白图、吞异常或少量案例冒充完整支持。字体和引擎正常差异按语义、内容、关系及可读性评估，像素分数仅作诊断。
- 保留用户改动、来源锁、许可证和原始失败。不要重写旧证据、移动已发布标签或覆盖发行资产。
- 用户指南写在 `docs/user/`；研发规则和状态留在开发入口。README/PyPI 不放会话指令、轮次日志或本机报告，详见 [文档规则](docs/development/DOCUMENTATION.md)。

## 6. 验证与完成条件

执行日志使用 [标准流程](tools/RUNS_AND_REPORTS.md)，新证据写入唯一 `test-runs/<run-id>/`，记录真实命令、退出码、来源和候选身份。报告生成成功不等于功能通过；新文档不能将旧源码验收重绑到当前工作树。

交付前审阅 diff，执行必要检查，同步相关中英文文档；代码、测试、工具或打包任务按规则写 `docs/changes/<task-id>.json`。最终说明改动、实际验证与未验证限制。

commit、push、tag、Release、PyPI 依据当前用户授权执行；历史任务记录不授予新权限，也不重复索取已经覆盖当前动作的授权。普通实现选择自主推进，改变兼容基线、默认行为或验收标准时由用户决定。
