# F01.3 执行目标

2026-11-05，用户将本轮目标收窄为“先完成 F01.3，Dagre 重新评估”。该指令覆盖此前 F01.3/F01.4 联合目标。本轮仅继续 F01.3；F01.4、Dagre 实现和布局替换暂停。

交付范围：固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b` 上的前处理、frontmatter、init/initialize/wrap 指令、配置层级和主题、HTML 标签开关、普通 HTML 与 Markdown 标签入口，以及这些入口在现有节点/边/子图/图标题上的真实 Canvas 测量和绘制。保留原文 UTF-16 位置、请求隔离、安全清洗、真实 ELK 和 PNG 输出。

主题分母使用固定源码 themes/index.js 的 11 个主题及 `null` sentinel，不能按旧文档中的五个主题缩减。Markdown 保留普通、粗体、斜体、换行、实体和上游对未识别 token 的原文行为；HTML 标签解释与 htmlLabels=false 路径按固定 createText/common/splitText 来源分别实现。前处理的配置优先级、secure 项清洗和资源预算有独立来源记录。

不扩展本轮范围：Dagre、全 flowchart 新语法/新 shape、style/class/linkStyle 语句、其他边类型、手绘 look、图标/图片资源、数学排版和新增导出格式；属于 F01.4 或后续共享能力，维持明确诊断。既有 14 种经典形状及 F01.2 ellipse 原缺陷保持。主题 CSS 中适用于 Canvas 的字体/颜色/描边等声明由纯值样式层承接；浏览器宿主行为不引入生产路径。

## 顺序与验收

1. S0 保存未提交 F01.2 起点、核对固定来源和 F01.3 完整入口。
2. S1 冻结兼容追加的数据合同、单文件 owner 和模块接线。
3. S2 先完成本切片全部源码及 source map，仅编译/import/签名机械检查，记 `code_complete_unverified`。
4. S3 从固定原实现独立设计语言/配置、布局/位置、富文本/安全/主题测试及官方对照，迁移旧范围拒绝断言。
5. S4 同一源码候选初跑全部组，保存失败，再按根因修复和相关回归。
6. S5 在最终同一候选完成 F01.1/F01.2 回归、F01.3 分母和 CPU/auto/GPU 对照，实际查看 PNG 与 HTML，并更新验收/用法/账本。

判断功能、内容、格式、关系、可读性、安全清洗和导出；跨浏览器/Canvas 像素差仍只诊断。标准日志/报告继续使用 `tools/workflow.py`。安装验证暂缓，不安装或发布候选包，不自行 commit/push。

## 当前起点

F01.2 完成源码指纹 `b4df33aa602c178c9d8fd5f4f39685a68d58c1eaaf863c545f5dce7f3886b5e7`；67 个未提交/未跟踪文件已备份至 `test-runs/F01.34-start-20261105T010728Z-1de7376b`。旧报告和失败日志全部保留。固定来源检查 `test-runs/F01.34-record-20261105T010730Z-002ce8f5/run.json` 通过。

## 分工

主协调负责 model/API、纯值样式解析、工具/报告和总状态。parser_config 负责 preprocessing、config/themes 和现有 flowchart parser 的 F01.3 标签接入；canvas_labels 负责富文本测量与 Canvas 绘制；geometry_elk 负责现有 ELK 接线和标题/标签几何。所有 Canvas 原生对象留在创建线程，布局只消费不可变测量数据。具体接口及路径租约见 F01.3 合同和当前账本。

## 执行完成

2026-11-05，S0～S5 已完成本地交付；最终同候选 279 产品 + 25 工具测试、三后端 F01.3 与 F01.1/F01.2 回归及 HTML/人工 QA 通过。见 [验收记录](F01_3_ACCEPTANCE.md)。F01.4/Dagre 和安装验证维持暂停，未提交推送。
