# 下一轮：修复已确认的保留分支缺口

2026-11-06，第四轮分支核实已完成归类，结果见 [核实结果](BRANCH_VERIFICATION_RESULTS.md)、[机器汇总](../references/branch-verification-summary.json)和[分页结论](http://127.0.0.1:8765/BRANCH-VERIFY-P5-delivery-20261106T150821Z-81018151/index.html)。

本次核实 122 条有限记录：66 条限定验证 + 6 条精确既有验证、22 条确认功能缺口、4 条纯值差异，其余历史审阅/未证/源异常与适配边界分别保留。未改生产源码，不能把本轮报告理解为功能全部通过。

待修复的 9 簇为 Cynefin 字符串、Architecture 多行元数据输入、Gantt 日期/格式、D3 轴格式、多周刻度相位、AgentFlow 折叠自环、Sequence 中央连接/编号/self 填色、Zen 注释转义、ABNF 独立注释。完整 ID 与证据见 [修复队列](../references/branch-repair-queue.json)。标题/纯值归一和额外语法接受独立记录。

当前只完成核实，修复尚未执行。后续按具体根因批修并保留新候选回归，不用前三轮 865 例的通过数冒充新增分支已通过。

静态 HTML/CSS 扩展明确排除、不列为待迁移；已验收的基础静态 HTML 控件/富文本/样式保留。video/audio、交互、Dagre 和 7 个待 py-vchart 图表继续排除。安装、Linux/no-loader、发行验证继续暂缓；不自动提交推送发布。

第三轮 [HTML 控件验收](HTML_HOST_ACCEPTANCE.md)及此前报告保留为其限定用例历史证据。仍未证的 C4 sprite 几何、原版有效组算法等边界，在第四轮逐条结果中明确列出，不声称全项目表达式分支覆盖率。
