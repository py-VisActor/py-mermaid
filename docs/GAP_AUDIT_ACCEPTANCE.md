> 2026-11-06 报告展示已按轮次拆页：[分页总入口](http://127.0.0.1:8765/REPORT-ROUNDS-delivery-20261106T110340Z-823e8bf0/index.html)。第二轮 64 例/6 页，第一轮 670 例/56 页，每页最多 12 例；更早 F01.1～F01.4/数学报告从首页进入。734 案例与 2746 PNG/685 SVG 原字节核对通过，原验收状态和历史报告不改写。此项仅重组报告，不是新渲染或新功能验收。

> 2026-11-06 后续范围变更：用户已将 **video/audio 整体排除**，含初始静态外观、封面/占位和控制条。下文 9 类差异是本次决策前的历史采证；当前仅 7 类控件样例保留为待迁移功能。原验收数字、候选 SHA 和关闭报告均保持原事实，不把 2 类排除项计为实现通过。见[范围决策](../references/media-exclusion.json)。

# 功能分支复核与修复：本轮验收

2026-11-06。本轮补齐保留图种的具体语法、配置及绘制分支，**没有新增图种，也不代表所有静态功能已经迁移完成**。HTML 控件及音视频的初始静态外观仍未实现，已由原版和原生的实际运行确认；见[下一模块](STATIC_HTML_HOST_PLAN.md)。

[原始 A/B HTML 对比报告](http://127.0.0.1:8765/GAP-P5-delivery-20261106T090602Z-1b174f02/index.html) · [五格式导出](http://127.0.0.1:8765/GAP-P5-delivery-20261106T090602Z-1b174f02/exports.zip) · [原始日志](http://127.0.0.1:8765/GAP-P5-delivery-20261106T090602Z-1b174f02/logs.zip)。报告内搜索 `gap-` 可筛选本轮新增输入。

当前源码候选：`fae1001df0d2c07ada1b8474eb03901429af0a5f81c9b7dfbf5e65b89e962062`。固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`。运行依赖仍为 Canvas 0.1.0a18、py-visactor-elk 0.1.0、py-visactor-katex 0.1.0。

## 实际修复

- 通用配置：无效 look 的来源层级跳过、既有 scoped appearance 同步、未知全局主题归一、空字体 legacy 桥接，以及 null 主题/仅覆盖变量时的 palette 计算时序。
- 流程图和共享绘制：显式 flowchart-elk 的模型类型、统一 site config 中其他图种设置的接收、visibility 与祖先 opacity 的分别继承及实际绘制。
- A 组：Packet 标题注释和空白转换、泛型 cssClass 目标、Block 空标签/空 composite、Kanban 空标签的原版语法边界。
- B 组：Gantt 季度日期、Ishikawa UTF-16 字数换行、EventModeling 自有 HTML 分支、Cynefin seed 的 JS 有限 number 判断。
- C 组：ZenUML 隐藏修饰词、多变量赋值、Unicode 名称、隐藏换行及头部声明优先级；时序图生命周期端点、编号字号和字体别名；四个铁路入口的主题派生 fallback。

Git 字面换行最初被静态审计误报为缺口，首跑确认已由共享标签管线正确处理，没有为此修改生产实现。

## 最终验证

| 项目 | 实际结果 |
| --- | --- |
| 单测与验证工具 | 1780 方法全部通过 |
| 输入 | 734：旧 670 + 新 64；每个 CPU/auto/GPU 配置均为 687 实际绘制、46 精确预期错误、1 静态排除 |
| 严格 ZenUML | 每配置 186 正例（原 148 + 追加 38）全部通过；1990 个变异负控制全部拒绝 |
| 导出 | 31 入口 × 3 配置 × PNG/JPG/WebP/SVG/PDF，465 项通过 |
| 历史流程图 | 297 正例 × 3 配置重新实际绘制，并通过语义、关系、几何、墨迹及负控制 |
| 人工复核 | 63 对代表/复杂图覆盖 31 入口；旧审查只在原 A/B 字节完全相同时复用，改图及新增关键分支另行实际看图；不是人工逐图检查 734 输入 |
| HTML/浏览器 | 2746 张 PNG、685 份 SVG 原字节/次数核对；38 代表样例、搜索、桌面及窄屏通过 |
| 验收负控制 | 错候选、失败全量、改图指纹、漏类型审查、缺设备配置 5 项均拒绝 |

完整 P4：`BULK-P4-final-20261106T084124Z-83cc2c1e`，61 命令全部退出 0，`sourceUnchanged=true`，完整产物指纹已复核。交付：`GAP-P5-delivery-20261106T090602Z-1b174f02`，同候选未变。

第二轮显式使用 `--skip-legacy-pixels`，只省去历史 F01 的重复热图/统计子进程，全部新鲜渲染及功能/实际像素墨迹断言仍执行。734 输入的原始 A/B 与本批像素诊断照常生成。图片未缩放重采、裁切、配准或后处理；字体、自然布局和 seed=0 手绘差异保留。

## 失败、纠正与来源复用

首轮新测试和第一次完整 P4 的失败均保留。第一次 P4 在三后端发现 ZenUML 头部声明被错误并入后续赋值，导致 RTL 创建关系反向；按原版 head 优先级修复后，对新候选重新执行完整矩阵。

新增 typed-head 测试原先误以为 `Result` 属于赋值类型；已采原版表明它先成为参与者，因此精确纠正并增加 body typed/quoted/multiline 控制。销毁端点测试改为读取实际路径端点，保留原 3px 期望，不再把保守 paint bounds 当几何边界。原失败、旧测试 SHA 和来源依据见[回执](changes/gap-P4-repair-C.json)。

严格 Zen 工具原只覆盖 148 个指定来源输入；现扩大到全部 186 个静态正例，同时保留原 148 ID/来源门禁。关系、端点、PNG 和变异检查函数未放宽。

原版 734 个输入由四份已关闭的原版采集严格合并：逐行输入、固定 source/browser identity 和每个复制文件的 Run artifact SHA 均核验，来源目录未改。源采集命令成功与其所在整 Run 的其他测试是否失败分开记账，工具有 14 项独立负控，不把整个失败 Run 改称成功。

## 仍未完成的功能

**HTML 静态宿主仍需迁移**：输入框、checkbox、按钮、select、textarea、meter、progress、video/audio 初始外观，9 类最小样例原版均可见，原生均明确拒绝。它们未获用户排除，也不计本轮兼容完成。[实际差异诊断](http://127.0.0.1:8765/G02-static-host-preview-20261106T084708Z-fc6820ed/index.html) · [迁移方案](STATIC_HTML_HOST_PLAN.md)。

功能组审查和当前用例通过不等于逐语法、逐配置、逐异常分支或任意浏览器 HTML/CSS 的完整覆盖证明。初始 219 组对应、未展开分母和审计误报分别保留，不换算覆盖率。

7 类图表继续排除，后续由 py-vchart 覆盖；目前未接线、未新增依赖。交互与 Dagre 继续排除。安装、Linux/no-loader 和发行验收未在本轮执行；没有发布或提交推送。

[机器摘要](../references/gap-verification-summary.json) · [初次 P4](changes/gap-P4-initial.json) · [Root](changes/gap-repair-root.json) · [A](changes/gap-repair-A.json) · [B](changes/gap-repair-B.json) · [C](changes/gap-repair-C.json) · [来源复用](changes/gap-oracle-merge.json)。
