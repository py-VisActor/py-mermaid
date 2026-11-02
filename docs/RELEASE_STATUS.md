# 当前状态

2026-11-02：**项目启动阶段，未实现 Mermaid 解析/布局/渲染，未发布渲染包。** `0.0.1a0` 是本地骨架源码版本，不表示 PyPI 可用。

已建立：src 模块边界、固定 Canvas 依赖、上游源码锁/只读 checkout、spec 文件索引、完整图种与跨图能力清单、启动/实施/兼容/测试资料、bootstrap CI 和负控制、可运行 Canvas 依赖示例。

基线 Mermaid 12.2.0，commit `1fb7869866dd619168d840291c9c54b4f129758b`。源清单有 37 个 core detector + ZenUML 插件、368 个测试源文件、2,366 个渲染 fixture、38 个 grammar、34 篇 syntax 文档。**这些不是测试通过数**；[逐项状态](compatibility.json)中的 parser/layout/canvas 均 planned。

本批实际检查（Windows / CPython 3.13.15），由任务记录 [20261102-bootstrap.json](changes/20261102-bootstrap.json)登记命令、文件 SHA 和证据路径：

| 检查 | 实际范围 |
| --- | --- |
| bootstrap 与负控制 | 12 项测试，含图种遗漏、依赖 pin、伪通过/缺失证据、fixture 越界、坏链接、图片 provenance、来源 commit/dirty/hash 漂移 |
| upstream check | 精确提交、关键 canonical blob SHA、干净源码、2,806 个索引文件及全部 detector 与已保存索引一致 |
| Canvas GPU 依赖示例 | NVIDIA GeForce RTX 5080 / Vulkan；360×140 PNG、内部 RGBA/文字宽度/尺寸检查通过，图像已审阅 |
| Canvas CPU 依赖示例 | 公开 setter 显式 CPU；相同尺寸/内部像素/文字测量检查通过，图像已审阅 |
| 本地骨架 wheel | 已构建并装入独立新环境；仓库外 `-I`、PATH 未设置时 import、模块来源与包内文件核对通过，无产品 render 接口 |
| Canvas README 文档 | 双语生态入口、链接/代码/图片来源结构检查通过；保存起点并确认既有非 README 修改原样保留 |

候选骨架 `py_mermaid-0.0.1a0-py3-none-any.whl` SHA256 为 `8b48962da2adbf709715157bf288cbae7a38b07bd2e2d27c341b9678049cb507`，仅用于本地骨架打包检查，未上传。实际示例图见 [examples](../examples/README.md) 和 [provenance](assets/manifest.json)。

这些检查**没有通过任何 Mermaid spec**，也不构成 Canvas 全 API/native trace 验收。CPU 示例不证明无 Vulkan loader 部署。Linux 本批未执行，沿用的 Canvas 平台范围不等于本项目已通过双平台验收。

当前官方 JS oracle、逐断言 spec ledger、Python Mermaid 渲染和双平台发行验收均未完成。CI 配置已准备，远端 CI、commit/push、Release/PyPI 未在本任务执行。首次隔离 import 的测试探针因 PowerShell 删除空 PATH 而失败，已用新 run 修正探针并通过；原失败文件保留。

下一步：[TASKS](TASKS.md) 的 M1 用例/宿主审计、M2 官方对照工具和 M3 flowchart 垂直切片。Canvas 示例输出仅验证基础依赖，不能提升 Mermaid 兼容状态。

2026-11-02 迁移计划梳理：已补全 [实施方案](IMPLEMENTATION_PLAN.md)和 [逐项任务](TASKS.md)，明确默认 ELK、实际 detector 顺序、内联测试及更多布局/主题来源。当前源码和兼容状态未改变。本轮重新运行的 bootstrap/12 项负控制、上游校验与 Windows Canvas auto/CPU/GPU 冒烟证据见 [20261102-migration-plan.json](changes/20261102-migration-plan.json)；仍无 Mermaid spec、Linux/no-loader 或发行验收通过结论。

2026-11-02 组织迁移收尾：用户已将仓库迁入 [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid)。本轮核实仓库 ID `1442682877`、默认分支 `main` 和提交与迁移前一致，当前账号仍有管理员权限；本地 `origin`、包元数据 URL、双语 README 和新会话入口已同步。证据见 [20261102-org-transfer.json](changes/20261102-org-transfer.json)。本地已有修改已备份保留，未执行 commit/push、组织权限变更或发布；Mermaid 兼容状态不变。
