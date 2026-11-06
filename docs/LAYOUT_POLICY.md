# 布局策略：完全剥离 Dagre

2026-11-05，用户明确要求“去掉 dagre 的功能选项，完全剥离”。本决定适用于全部图种、API/配置、目标依赖、源码任务和验收分母，覆盖此前“暂停/待评估/可选兼容 Dagre”的表述。机器策略见 [layout-policy.json](../references/layout-policy.json)。

## 目标产品

- 删除 Dagre、Dagre wrapper 及旧 Dagre renderer 的目标功能与迁移任务，不建立 Python Dagre 包或 adapter，不保留可选开关、插件入口或算法回退。
- 默认图布局继续使用真实 py-elk。其他图种自身需要的 Sankey、tidy、COSE/fCoSE、泳道等专用静态算法不因本次决定而删除。
- 显式请求不支持的布局必须在进入布局/Canvas 前报错。当前流程图只开放 `elk`，`dagre`、`dagre-wrapper` 等不被识别成可选功能，也不静默转成 ELK。后续 ELK 算法/选项扩全仍按独立任务实现。
- graphlib 的图结构职责由自有有序/复合图模型承接；求交、曲线等保留几何需求由 geometry/numerics 承接。不能借 helper 的旧包名重新引入 Dagre 算法或包依赖。
- `dagre-d3-es`、`@dagrejs/dagre`、`dagre` 及其专用 wrapper 不进入 Python 运行、可选依赖或目标依赖清单。原 npm/浏览器仅可作为固定源码的研发参考环境。

## 计划与验收

移除 P1-10 Dagre 实现任务，以及流程图、关系图和总集成对该任务的前置依赖；执行账本、模板和共享模块 provider 同步。布局跨图项使用目标名称 `layout-engines`，原 `layout-engines-dagre-elk-tidy` 仅保留为来源 ID 映射。

F01.4 保留静态语法、方向、边/曲线/marker、新形状、样式、ELK 选项/算法、资源/复杂标签、手绘和静态导出。Dagre 明确标为 `excluded_by_user`，不再属于未完成项，也不计“实现通过”。测试可保留 Dagre 请求作为“已删除功能必须拒绝”的负控。

固定上游 checkout、lock、完整原始依赖边、旧 source map、历史报告与已关闭 run 不删除、不改写。它们记载的是原实现和历史事实，不代表目标支持。依赖图的来源节点保留，但目标处理策略标为排除；既有许可证中的来源事实也保留。

先前 F01.3 的报告/验收指纹作为历史候选证据保留。本次产品改动只将非 ELK 请求的诊断从“延期”改为明确不支持；正常 ELK 绘图逻辑不变。当前变更单独记录测试和新源码身份，不冒用旧候选指纹。

全项目 [仅静态渲染](STATIC_RENDERING_SCOPE.md) 的范围规则继续有效。安装验证仍暂缓，本次不安装、构建、发布或提交推送。

## 剥离验证

本次已完成：移除 P1-10 及所有任务前置引用，当前 60 个活动任务；生产 Python 源码无 Dagre 引用、目录、分支或声明依赖。280 项产品回归、26 项工具回归和14项依赖测试通过，任务图/文档/生成清单检查通过。显式布局拒绝覆盖多种配置入口，Canvas 未分配。见 [机器验证记录](../references/dagre-removal-verification.json)。原上游图节点/边保持不变，旧渲染报告只代表其保存候选；此次未重新渲染图片。
