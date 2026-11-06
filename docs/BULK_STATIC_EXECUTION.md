> 2026-11-06 本批31入口（29新增+2流程图回归）已完成本地静态验收与HTML交付：1702测试、670输入×CPU/auto/GPU、465导出、297历史正例×3通过；原源7异常独立确认。当前入口 [BULK_STATIC_ACCEPTANCE](BULK_STATIC_ACCEPTANCE.md)。7暂缓入口不计完成；安装验证暂缓，不提交推送发布。下方旧阶段/未实现/执行中状态按历史保留。

> 当前第二次P4：候选 `a6d05b852e156aac3227d839f1521f3e9a71a808ba8b701ad33b1443e993f2a0` 已重新冻结。原版新采 `BULK-P3-fixed-original-refresh-20261106T062015Z-fe05c71f` 只证明固定原版，不冒充Python候选；输入字节一致且身份新校验后使用。当前没有最终整批通过结论。

> 当前：初次P4完整执行但未验收，进入P3集中修复；见 [初次P4回执](changes/bulk-P4-initial.json)。后文早期冻结状态为历史，修后重新冻结并整批重验。

# 静态迁移批次（范围调整后）

2026-11-06。用户已恢复推进本批；此前暂缓的统计图表、矩形树图、桑基图和韦恩图继续暂缓。
本批目标覆盖固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`
中本批保留的静态能力；既有 F01 和正式数学依赖作为回归基线，本批新增迁移调整为 **29 个入口**。
加上既有流程图 2 个回归入口，本批验收范围为 **31 个入口**。
用户已明确恢复执行，当前 **P4 / final_full_validation**；本轮按调整后的范围推进。本文件是当前执行入口，历史验收继续保留。

## 本批暂缓

| 分类 | 入口 |
| --- | --- |
| 统计图表（4） | pie、quadrantChart、xychart、radar |
| 矩形树图（1） | treemap |
| 流与集合（2） | sankey、venn |

以上 **7 个入口**标记为 `deferred_by_user`，不纳入本批源码收口、测试门禁或 HTML 报告必验范围。
已有源码、来源映射与历史日志保留，不删除，也不将暂缓记为已完成或永久排除。
公共能力只围绕本批保留图种收口；仅供暂缓图种使用的专用算法同步暂缓。

## 范围与责任

| 组 | 范围 | 状态与责任 |
| --- | --- | --- |
| F01 | flowchart-v2、flowchart-elk | 既有静态实现，最终候选重新回归；root 保持原管线 |
| F02 | classDiagram、stateDiagram、er、requirement、usecase、c4 | A：独立 grammar/model/布局/绘制 |
| F03 | sequence | C：时序、参与者、消息、组合片段与激活语义 |
| F04 | gantt、journey、timeline、gitGraph | B：时间日历、排期、时间线与提交图专用算法 |
| F05 | pie、quadrantChart、xychart、radar | 本批全部暂缓 |
| F06 | mindmap、treeView | A：源布局；treeView 按实际 preorder 行布局；treemap 暂缓 |
| F07 | sankey、venn | 本批全部暂缓 |
| F08 | block、packet、kanban、architecture | A：图种专用语法、布局与资源 |
| F09 | swimlane、agentflow、eventmodeling、ishikawa、wardley、cynefin | B：业务图专用模型与几何 |
| F10 | railroad、railroadEbnf、railroadAbnf、railroadPeg | C：四 grammar 与铁路图组合几何 |
| F11 | zenuml | C：固定外部插件与 core 源语法、时间布局和静态资产 |
| F12 | info | C：实际版本信息静态图 |
| 公共层 | 13 跨图能力与 API、包元数据、日志和总报告 | root：唯一写 owner；接口见下文 |

上游来源总清单仍为 37 个 core detector + 1 个 ZenUML detector；其中 7 个本批暂缓，31 个纳入本批。
另有 error/错误 frontmatter 诊断入口。13 项跨图能力按本批适用范围验收，原来源总清单继续保留。
源码任务必须覆盖对应 grammar、DB、renderer、styles、config、算法与错误路径。
文件存在、注册成功或少量样例可运行都不能证明图种已完成。

## 固定边界

- 所有模块只交付静态渲染。链接导航、事件、动画播放、命中测试、DOM 可访问性行为排除；可见内容和资源安全保留。
- Dagre 完全剥离，既不提供选项，也不作算法回退。ELK 使用真实 `py-visactor-elk==0.1.0`；原源用其他专用算法的分支仍须移植。
- 只使用公开 `py-skia-canvas==0.1.0a18` API。生产不依赖 Node、浏览器、Playwright、JS 解释器、skia-python 或 `.local`。
- 正式数学依赖为 `py-visactor-katex==0.1.0`，导入 `py_katex`；不退回 sibling src。
- Canvas/Context/Image/Path/字体对象留在创建线程；跨线程只能传不可变值或 bytes。
- 资源必须自包含或显式提供，不隐式访问网络和任意本地路径。
- C4 将原宿主 `screen.availWidth` 适配为显式 `viewportWidth`；未提供时原生宿主默认 1200，不能说成源算法固定宽度。
- `handDrawn` 只在原 renderer 实际支持的分支启用；源忽略该选项的图种保持相同行为。
- 不覆盖现有脏树或历史证据。本批不自动提交、推送或发布 py-mermaid。

## 执行顺序与门禁

P1 源码已冻结，当前按 [P2 测试设计合同](P2_BULK_VERIFICATION.md)编写独立测试；后续阶段按下述门禁顺序执行。

1. **P0 范围与恢复点**：固定源码、确认本批 31 个入口与 7 个暂缓项、保存起点、分配文件 owner 和接口。
2. **P1 本批全部源码**：完成本批保留图种与适用公共能力；仅允许编译、无副作用 import、签名、注册和包装配等机械检查。
   全部真实源码分支收齐前，不编写正式功能断言、不运行行为测试、不采集 oracle 图片。
3. **P2 来源独立测试**：按固定 grammar/spec/fixture 建立全分组测试与来源映射，明确预期、负例、安全、布局、静态画面、设备和导出判定。
4. **P3 首轮全分组与批修**：先完成所有组首次执行，保留所有失败，统一归类并修根因，再做相关回归。
5. **P4 同候选完整验证**：冻结候选源码身份，运行全部功能与静态渲染矩阵、CPU/auto/GPU、资源/字体/数学、安全与五格式导出。
   环境未具备项必须单独记未验，不借用其他环境或旧版本结果。
6. **P5 交付**：标准日志、原始 A/B HTML 对比报告、可复用采集/比较/报告脚本、真实状态与许可资料全部绑定同候选。
   安装验证按既有用户决定及当前专项范围记录；不把历史数学安装验证冒充全图种包验收。

渲染按用户已确定规则：功能、内容、关系、几何、可读性、安全和导出是门禁；像素差异仅诊断，不能通过缩放/裁剪/后处理掩盖问题。

## 当前事实

本批当前 **P4 / final_full_validation**。A 组 12、B 组 10、C 组 7 个新增入口与完整泳道路由、
共享纯模型、配置、真实 ELK adapter、Painter、总注册/API、CLI 和 11 个主题规则均已冻结。
31 个入口完成机械接线检查，301 处直接 Painter 调用通过签名检查。
P1 状态仅为 `code_complete_unverified`，临时产品写租约均已关闭，P2 不改产品源码。
此时没有本批功能/渲染通过结论，没有新批次 HTML 效果可冒充验收。

- P1 候选：`97b353ebf7e176a750a736a714c85638e0a497b722e451dc77570579a2d36cbb`。
- 整批装配：`BULK-P1-assembly-20261106T040205Z-6d6594fb`。
- 冻结与包资源接线：`BULK-P1-freeze-20261106T040338Z-8ecb17c2`，未构建/安装。

- 基线正式数学接入：`d2d0f36c2e2b8eb2818e1377cf1e25b81d81b846b3c0807ddc916639af917737`。
- 接管快照：`test-runs/BULK-start-20261106T021725Z-6f4d326b/`。
- 固定 defaults 提取：`BULK-record-20261106T022141Z-0ee1dc7f`，仅元数据提取。
- 共享 compile：`BULK-record-20261106T023954Z-a75ddfc7`，仅机械检查。
- import/签名/38 注册：`BULK-record-20261106T023529Z-8a46cd09`，未分配原生对象。
- 11 主题规则翻译：`BULK-record-20261106T023908Z-90dcb59c`；来源 SHA 见 `references/bulk-themes-sources.json`。
- 早期命令失败原样保留在各独立 run；不修改为成功。

接口与单文件 owner：[BULK_STATIC_INTERFACES](BULK_STATIC_INTERFACES.md)。
实时机器状态：[execution-state.json](execution-state.json) 的 `bulkStaticMigration`。
既有日志规范：[RUNS_AND_REPORTS](../tools/RUNS_AND_REPORTS.md)。

P2 整批冻结：1092 个来源独立测试方法、656 fixture（617 render），31 入口齐全。机械日志 `BULK-P2-whole-freeze-20261106T042905Z-abe1ecc4`。P3 按 [全分组首跑协议](P3_BULK_FIRST_SWEEP.md)执行，此条不表示行为通过。

P3 全组根因批修与相关CPU已收齐，当前联合候选 `51c9c8f75ec4518680450e985ac24e1e576850ae4522fe697d8725b1e23cf248`。P4 统一运行 670 fixture × 三后端、31 入口五格式及 297 历史正例回归；7 项上游异常独立核实，不能等同于源画面完整渲染。P4 完成前无整批最终通过结论。
