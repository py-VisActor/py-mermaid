# py-mermaid 开发者与 AI agent 文档

本入口面向修改本仓库的维护者。应用开发、安装、绘图与 API 请阅读[用户文档](../README.md)。AI agent 首先遵守根目录 [AGENTS.md](../../AGENTS.md)。

## 开始工作

确认当前用户需求、`git status --short` 和影响范围。版本与依赖读取 `pyproject.toml`，已发布文件身份读取发行 manifest；旧计划和验收仅证明其记录的候选与范围。原静态迁移已经发行，不根据历史待办重复启动迁移。

需要源码环境时使用 CPython 3.13：

```shell
python -m pip install -e ".[dev]"
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
```

纯文档任务不需要构建、重新安装或运行渲染矩阵。例子的语法检查不等于实际绘制验证；新增或改变绘制行为时按影响范围补真实检查。

## 按任务阅读

| 任务 | 入口 |
| --- | --- |
| 文档与公共元数据 | [文档分工规则](DOCUMENTATION.md) |
| 理解设计边界 | [Canvas 原生架构](../CANVAS_NATIVE_ARCHITECTURE.md)、[模块设计参考](../MODULE_BOUNDARIES.md)（含历史拟建描述，以源码为准） |
| 兼容行为与来源 | [固定来源](../../references/README.md)、[来源验证](../SOURCE_BASED_VERIFICATION.md)、[兼容规则](../API_COMPATIBILITY.md) |
| 多人或多 agent 协作 | [单文件 owner 与协作规范](../PARALLEL_EXECUTION.md) |
| 日常验证与报告 | [日志及报告](../../tools/RUNS_AND_REPORTS.md)、[测试目录](../../tests/README.md) |
| 构建及发行 | [测试与发行](../TEST_AND_RELEASE.md)、[已发布记录](../RELEASE_STATUS.md) |
| VChart 编译实现 | [模块接口](../VCHART_DSL_INTERFACES.md)、[EBNF](../syntax/vchart-v1.ebnf)、[用户语法](../user/VCHART_DSL.md) |

## 状态、历史和证据

- 当前发行：[简明状态](../RELEASE_STATUS.md)、[机器发行记录](../../references/mermaid-publication-0.1.1.json)。旧 [0.1.0 发行记录](../../references/mermaid-publication-0.1.0.json)保留原始提交和文件身份。
- 跨项目文档修订：[五项目新版本汇总](WORKSPACE_RELEASE_20261107.md)。
- 本轮文档重整前的 README、AGENTS、会话入口和语法设计：[原字节快照与 SHA](history/documentation-before-20261107/manifest.json)。快照只作历史，不是可执行指令。
- 历史迁移：[总计划](../FULL_MIGRATION_PLAN.md)、[统一收口计划](../CLOSURE_BATCH_PLAN.md)、[任务账本](../execution-state.json)。这些文件保留原始任务顺序，不自动授予当前操作权限。
- 历史验收：[收口验收](../CLOSURE_BATCH_ACCEPTANCE.md)、[VChart DSL](../VCHART_DSL_ACCEPTANCE.md)、[基础流程图](../F01_1_ACCEPTANCE.md)、[数学接入](../MATH_RELEASE_INTEGRATION.md)。旧图、旧失败和旧计数不改写。

`docs/` 根目录保留原有设计、计划、验收和来源记录路径，便于已有收据查找；新增用户指南集中到 `docs/user/`，维护规则集中到本目录。[逐文件角色清单](documentation-inventory.json)区分用户、开发、历史、证据和许可资料；本地 `test-runs/` 与报告不进入用户首页。

需要核对整个 py-VisActor 工作区的文档入口时，运行 `python tools/audit_workspace_docs.py --workspace .. --out test-runs/NEW-DOC-AUDIT --write-inventory`。该命令只检查文档与元数据，可更新各仓分类清单；不执行安装、绘图或发布。
