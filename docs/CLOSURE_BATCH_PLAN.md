> 2026-11-07 ?????????????????????132 ??????119 ??????255 ???866 ??? VChart 301?3/816 ?????105 ????????12???????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`????????????Linux real-TZ ? PyPI ??????????????????[????](CLOSURE_BATCH_ACCEPTANCE.md)???? pending/??????????

> 2026-11-07 ??????? Event ???????132 ? portable ???5 ?????????????/??/??/???????? HTML/F01.3/??/B ????????? `fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`?????????????132 ???119 ???13 parserOnly??255 ???866 ????? VChart??????????????????? Windows/Linux ????? Linux TZ?OIDC ? PyPI ??????????????????????????????

# 非 VChart 能力统一收口批次

2026-11-07。目标：在一个批次内补齐最终复查列出的非图表缺口和验证空白，形成可发布的 py-mermaid 候选。用户明确四集合Venn、Treemap数值格式由py-vchart包含并管理；本批不修改它们或供应方，不再将这两项作为py-mermaid发布阻塞。旧报告保持原事实，新范围单独记录。

## 范围

P3完整旧分支回归另外确认 Info 在 neo-dark/redux-dark/redux-dark-color 使用了错误的文字颜色角色；本批一并修为原版 `textColor`，保留 CSS 覆盖，未修改既有期望。该项不重算原22条缺口。发行分发名为 `py-visactor-mermaid==0.1.0`，Python 导入名 `py_mermaid`、CLI `py-mermaid` 和 GitHub 仓库名保持原合同；发布状态与代码版本分开记录。

| 工作 | 必须结果 | 唯一源码owner |
|---|---|---|
| 语法与纯值 | Cynefin STRING六分支；Architecture多行metadata；ABNF独立注释；Zen注释转义；4项title/metadata纯值；Event原版拒绝输入的严格性 | A：cynefin、architecture、railroad/parser、zenuml/parser与注释layout、tree_view、eventmodeling |
| 时间与关系 | Gantt日期fallback/星期/ISO、D3轴locale/转义/padding/远年、多周相位；AgentFlow折叠genuine自环 | B：_dates/_civil/_gantt_data/gantt、_agent_parser/agentflow |
| 绘制 | Sequence中央连接点、反向编号、自环路径；核方向/activation/central/half分支 | C：sequence/layout、presentation |
| 既有未证项 | C4 sprite独立几何控制；DST、多方向Git标签；组算法实际消费/跨层清除；数值异常 | A：C4；B：日期、Git、ELK |
| 接线与发行 | 共享collapse策略hook、范围/版本/包资料、完整runner、平台/安装/发行CI与正式上传回读 | root：共享flowchart/parser、API/包配置、工作流与发行工具 |

22条旧功能分支分为9个修复簇，不按22个独立算法计。标题/a11y纯值保真不增加ARIA/交互输出。内部Wardley DB mutator等未承诺的公开API不凭内部函数出现而扩大范围。供应方全字段穷尽审计属于VChart管理范围，不作为本批新任务。

交互、动画、Dagre、video/audio、任意HTML/CSS扩展及3D维持既有排除。全部VChart类型/七图表入口/DSL、数学/ELK、静态资源与五格式保留，需做受影响回归；不删除既有功能来获得通过。

## 顺序与验收

1. **P0**：起点 `fe2c293f8ed4ea76e04d34669c8739c27a32063447026e144928bfd6b4ac0bb2`，完整产品/测试/工具及旧审计归档于 `CLOSURE-P0-acquisition-20261107T075501Z-2f1df0de`。保留整个脏树，不清理、不覆盖旧Run。
2. **P1**：上述全部源分支集中实现，仅编译/import/签名等机械检查；唯一文件owner，公共接口变更先固定合同。不先逐项跑行为或写新测试。
3. **P2**：根据固定Mermaid、Langium、Dayjs、D3等实际原实现设计独立测试/探针；期望来自原始来源。Event错误的“原版正例”期待必须以真实拒绝事实纠正并保留旧期待；不得改期望迎合原生输出。未知项建立独立正/负控制。
4. **P3**：先收齐所有分组首跑再集中归因修复，保留全部失败。受影响旧测试与新来源断言同跑；重复case、纯helper、原版异常、真实漏内容/错关系分别统计。
5. **P4**：所有源码/测试/工具/README/依赖冻结，同候选完整回归；CPU/auto/GPU新绘制、实际看图、多格式；保留VChart/数学/ELK回归。真实wheel/sdist在Windows/Linux仓库外干净安装，禁止Node/浏览器/相邻源码回退。
6. **P5**：每页最多12例的独立收口报告；机器汇总、实际看图、原始附件SHA及HTTP/桌面/手机QA。候选版本拟为`0.1.0`，所有范围内缺口与发行门禁通过才发布同组文件，核PyPI/Release实际下载SHA。账户publisher配置若缺失，先完成可审查候选和双平台验证再处理配置。

功能通过、有限源码覆盖、报告生成成功、远端CI、正式发布分别记实。不能因测试/资料完整就推断全字段/全表达式覆盖；剩余验证边界须明确，不能隐藏有证的保留功能失败。

## 当前直接HTML消费链修复（2026-11-07，覆盖下方此前状态）

第二轮完整P4 `test-runs/CLOSURE-P4-batch-20261107T103937Z-ea2939c1` 已关闭，机器SUCCESS、source/testTools unchanged，历史866及全部VChart DSL通过；但新增窄范围多行JSON原图审查确认Event数据框标题越框、宽度严重误测，因此该候选仍为人工拒收，不能发布。旧机器成功与人工缺陷同时保留，不重写其Run。

固定原版SVG实际小表确认ASCII TAB/CR/LF/连续space折叠并trim首尾，而NBSP不能一起折叠。normal HTML实测确认单末尾`br`只结束当前行，不另造尾空行，双`br`仍保留一空行，block code为满宽/左对齐；普通ASCII边缘空白修剪，NBSP保持宽度。字面`\n`/`$$`不能走flow标签预处理。数据源传输还须保留Diagram全图encodeEntities在DB substring裁切之前、尺寸测量保占位串、最终SVG decodeEntities的顺序；标准HTML实体只解析一次，数值实体保留源端额外amp行为。以上均为限定源独立实证，不是任意HTML/CSS兼容声明。

统一应用的修复包括Event局部ASCII空白规范化、保护数据先encode再原substring、最终直接HTML消费，以及root提供的normal行盒/有限宽度/NBSP/显式br规则和C的独立实证测试。相关Run `test-runs/CLOSURE-EVENT-HTML-P3-related-20261107T110330Z-53265a55` 正在执行；源码机械通过不等于相关或最终行为验收。

当前待验收分母为132个新增方法（120+Event12）、132条输入（119绘制/13 parserOnly），收口五格式255项（17代表×3后端×5格式）。下方120/127/130等只记录对应历史阶段，不全局改写。新源冻结后不再额外扩审，仍须完成全部既定门禁。

后续最终P4不重复开发安装。正式clean build一次产出的exact wheel和sdist，须在同一个workflow由Windows/Linux分别对两个工件独立安装，并通过Linux真实时区23/25小时等门禁；OIDC上传job必须`needs: validate`，不得在验证后重建或换工件。正式上传后回读实际PyPI两工件SHA，并在仓库外安装回读。Publisher已配置，既有条件发布授权持续有效；所有门禁闭合前不正式发布，无需重复询问授权或账户配置。Windows受控aware-offset和看图不替代Linux real-TZ。

## 当前修复状态（2026-11-07，覆盖下方历史执行状态）

旧最终 P4 `test-runs/CLOSURE-P4-batch-20261107T101239Z-1852a0e5` 已关闭，机器 SUCCESS、source/testTools unchanged；但人工原图核查确认 Event Modeling 同 lane 的 Place 被后画的 Orders 遮挡。该候选为 **NEEDS_REPAIR**，机器通过不能提升为人工验收通过，也不能发布。原始机器结果及人工拒收事实均保留。

根因位于 Event Modeling 专有测量消费者：固定原版 `calculateTextProps` 将包含 `<b>`、`<code style=...>` 的内容交给 `calculateTextDimensions`，由 SVG `.text()` 按字面字符串测量；原生曾按 HTML 可见内容测量，短框全部缩小，返回同 lane 时遮挡。专用字面测量、两字体选择/round、源 `wrapLabel`/`breakString` 和精确 code 开标签字面串已由来源独立提案应用；`calculateX`、lane.r/maxR 原规则不变。独立三份原版夹具、七个验证方法和几何/像素反控已应用，相关 Run `test-runs/CLOSURE-EVENT-P3-related-20261107T103759Z-d4488fc8` 正在执行，**尚未行为验收**。

当前待验收分母为127个新增方法、130条输入（117绘制/13 parserOnly）；收口五格式为225项（15代表×3后端×5格式）。下方120/127/114及旧导出计数只描述对应历史阶段，不全局改写。旧P4、先前失败、source-only提案及独立验证准备均保留。

后续顺序为：相关分组收齐并集中修复 → 新冻结候选最终P4完整回归/三后端/原图复核/分页报告 → 正式 clean wheel/sdist 一次构建 → Windows/Linux CI对两个实际工件分别在仓库外独立安装，完成依赖/数学/ELK/静态导出与Linux real-TZ门禁 → 同一组工件正式发布及下载SHA回读。最终P4不再重复开发安装；这不免除正式双平台双工件门禁。Windows两项真实IANA时区观测继续未证，aware-offset或图像不能替代Linux实跑。

Pending Publisher 已由用户确认添加，发行名 `py-visactor-mermaid==0.1.0`，导入 `py_mermaid`、CLI `py-mermaid`；既有条件发布授权持续有效，门禁全部通过后直接发布，无需再次询问。当前未达到正式发布条件。保留既有静态排除和VChart范围转交，不扩大范围。

## 执行入口（以下为此前阶段历史）

2026-11-07 P3补充收口：首次完整P4 `CLOSURE-P4-batch-20261107T085101Z-2d330c0d` 保留FAILED，source/testTools均未变。其历史矩阵的6个失败均来自同一条Event旧分类：原版在解析阶段拒绝的独立title曾被标为upstream_defect；原输入保留为语法负例，并增加固定原版成功绘制的完整五类型正例，历史输入增至866。实际看图发现的Cynefin SVG空白消费者、Gantt百分号格式、Git cherry-pick继承、Agent折叠容器主题/外观/部件四项均已集中修复。

当前120个新增合同方法已分组通过（A46、日期24、布局21、Sequence22、collapsed7）。新版夹具共127条：114个真实绘制输入、13个parserOnly；CR/TAB三项XML安全输入已从parserOnly移入绘制矩阵，NUL/BS/FF/VT等不可序列化控制字符保留纯值边界。六个collapsed原版控制覆盖普通flowchart/Agent、调色板/经典/手绘，三后端角色、低对比度丢点、圆角与separator阴控均已验证。相关通过不等于最终P4，原全部失败及错误测试假设保留。

原版B已用 `freeze_closure_b_source.py` 重新冻结191 pure、11 host、40 browser的真实来源JSON，旧快照逐字节保留。原版历史矩阵使用严格并集：864条未变输入复用原文件，修正旧Event负例与新增合法正例重新采集；Source union为866。F01原版亦仅在输入/固定源码身份检查通过后复用；新候选的全部原生绘制、单测、五格式与安装仍须重新执行。

Pending Publisher 已由用户确认添加，发行名 `py-visactor-mermaid`、仓库 `py-VisActor/py-mermaid`、工作流 `publish-pypi.yml`、环境 `pypi`。最终同候选P4、实际看图/分页报告及Windows/Linux实际工件验证通过后直接发布同一组文件；账户配置完成不代表已发布。

范围：[closure-batch-scope.json](../references/closure-batch-scope.json)；状态：[execution-state.json](execution-state.json)；变更：[closure-batch.json](changes/closure-batch.json)。各阶段Run和报告完成后在账本记录真实路径与指纹。本文件是执行合同，不是预先通过声明。
