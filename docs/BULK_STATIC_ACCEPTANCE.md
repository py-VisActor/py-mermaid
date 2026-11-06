# 保留静态图种：本地验收

2026-11-06，本批 **31 个入口（29 新增 + 2 流程图回归）完成本地静态验收**。固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`；联合源码候选 `a6d05b852e156aac3227d839f1521f3e9a71a808ba8b701ad33b1443e993f2a0`。

[打开完整原始 A/B HTML 报告](http://127.0.0.1:8765/BULK-P5-delivery-20261106T071012Z-ec4937fd/index.html) · [五格式导出 ZIP](http://127.0.0.1:8765/BULK-P5-delivery-20261106T071012Z-ec4937fd/exports.zip) · [原始日志 ZIP](http://127.0.0.1:8765/BULK-P5-delivery-20261106T071012Z-ec4937fd/logs.zip)。

本批未安装验证、未提交推送、未发布 py-mermaid。源码版本仍 `0.0.1a0`；正式数学依赖已采用 `py-visactor-katex==0.1.0`，不退回相邻源码。

## 范围

- 保留：flowchart-v2、flowchart-elk、classDiagram、stateDiagram、er、requirement、usecase、c4、sequence、gantt、journey、timeline、gitGraph、mindmap、treeView、block、packet、kanban、architecture、swimlane、agentflow、eventmodeling、ishikawa、wardley、cynefin、railroad、railroadEbnf、railroadAbnf、railroadPeg、zenuml、info。
- 暂缓：pie、quadrantChart、xychart、radar、treemap、sankey、venn，共7入口；不计完成，来源总清单38仍保留。
- 全部模块只交付静态渲染，排除导航/回调/悬停/播放/命中与DOM无障碍行为。可见静态样式、输入与资源安全保留；Kanban链接文字的下划线已实际绘制。
- Dagre 功能、选项、依赖与回退已剥离。默认真实 ELK 和源专用静态算法保留。

## 实际验证

环境为 Windows、CPython 3.13.15、公开 Canvas 0.1.0a18；CPU、auto、真实GPU策略均验证。

| 门禁 | 最终结果 |
| --- | --- |
| 单元/验证工具测试 | 1702 方法全通过：A599、B152、C351、shared64；F01/math469；工具67 |
| 新批次输入 | 670，每后端626实际绘制、43精确预期错误、1静态排除；三配置完整执行 |
| 来源分类 | 621正常渲染、41负例/诊断、7原源异常、1静态排除；没有将错误都算成成功图片 |
| ZenUML独立结构 | 148源样例 × CPU/auto/GPU；每配置1597个变异负控制全部拒绝 |
| 静态导出 | 31入口 × 3配置 × PNG/JPG/WebP/SVG/PDF，465项真实解码/结构/内容检查通过 |
| 历史流程图 | 297正例 × 3配置，连同原负例/源异常/排除项全部回归；两条历史数学延期ID转为公式/glyph/基线/实际墨迹正向断言 |
| 主题与配置 | 11主题、47配置的完整派生变量与固定原源一致；静态消费、级联与短palette边界另有单测 |
| 人工图审查 | 47组代表/复杂图覆盖31类型，使用原始PNG SHA绑定当前候选；不是声称人工逐图检查670个case |
| HTML交付 | 2502张PNG及624份SVG内嵌字节/次数一致；38代表/复杂样例浏览器解码、搜索筛选、桌面/窄屏通过 |
| 反伪验收 | 错候选、失败P4、改图指纹、漏类型审查、缺设备配置5项均被拒绝 |

原始A/B未缩放重采、裁切、配准或后处理；浏览器页面仅按视口显示。像素指标/热图是独立诊断，不作为零差门禁。自然字体度量、画布背景/视口、合法路由和手绘seed0抖动差异如实保留。

## 原源异常（保留分母）

| 案例 | 固定原实现 | 当前处理 |
| --- | --- | --- |
| A architecture endpoint | 原renderer错误 | 精确UPSTREAM_ARCHITECTURE_ENDPOINT，不伪造空成功图 |
| A mindmap explicit ELK | elkjs0.9.3内部null.re | 真实py-ELK完成绘制，原异常单列 |
| B Gantt topAxis DSL | 原TopAxis/DB方法大小写不一致 | Native完整静态绘制，另有合法配置分支 |
| B EventModeling title | 原词法优先级吞title | Native保留完整元数据与可见内容 |
| B cyclic Gantt | 原SVG坐标NaN、退化图 | 精确CYCLIC_GANTT_DEPENDENCY |
| C Zen emoji-colon override | 原恢复丢notify() | 固定原缺失/存在文本实证，Native完整作者意图合同 |
| C Zen emoji conditions | 原恢复丢wait()/deny() | 同上，未对整类Zen放宽 |

具体ID、错误码和证据见[机器验收摘要](../references/bulk-verification-summary.json)。原ANTLR损坏/不完整输入的编辑器恢复措辞不承诺逐字一致；完整静态分支、错误类别/位置及上述两项恢复丢失有明确来源合同。

## 可追溯证据与复用

- 完整联合P4：`BULK-P4-final-20261106T065144Z-03962368`，61命令均退出0，`sourceUnchanged=true`，已重新校验全部产物完整性。
- 原版独立新采：`BULK-P3-fixed-original-refresh-20261106T062015Z-fe05c71f`。只运行固定JS来源，不消费Python产品；P4重新校验fixture/config/resources SHA与原版/插件身份后使用，不冒充Python候选证据。
- 最终图审查：`BULK-P4-parent-visual-review-20261106T065841Z-a1801db7`。
- 功能验收：`BULK-P5-functional-acceptance-20261106T070724Z-0042dbcf`。
- 报告/浏览器/原字节：`BULK-P5-delivery-20261106T071012Z-ec4937fd`，所有命令通过，源码未变。
- 初次被拒收的P4、全部根因批修、误读纠正、大小写ID覆盖事件和证据目录误写事件完整保留；不把旧候选报告拼成新候选通过。

日志/报告入口：[BULK_REPORTS](../tools/BULK_REPORTS.md)、[RUNS_AND_REPORTS](../tools/RUNS_AND_REPORTS.md)。重新验证使用 `python tools/run_bulk.py final`；显式复用原版时必须通过严格输入/源码/插件指纹检查。生成验收报告还需同候选成功P4和带图片SHA的人工审查，不接受单独改状态。

[使用与CLI](BULK_USAGE.md) · [兼容账本](compatibility.json) · [初次P4回执](changes/bulk-P4-initial.json) · [交付回执](changes/bulk-P5-delivery.json)。
