# 官方 JS Mermaid 对照工具

## 标准执行与日志

后续统一使用 [workflow.py](../workflow.py)：`report --spec tools/report_specs/f011-baseline.json`只从已有证据生成HTML，`render --profiles cpu`明确启动新采集/比较/报告；record/batch记录任意明确命令。每次新run保留stdout/stderr、真实退出码、输入/产物指纹，失败不会被覆盖。参数、格式与直接复用示例见 [日志和报告规范](../RUNS_AND_REPORTS.md)。旧CLI继续可用，但不得把已有报告生成当新功能验证；本轮不执行安装验证。

## 当前可用：F01.1

现有结果可生成单文件离线总览，无需重新采集或渲染：`python tools/build_f011_html_report.py --out reports/new-f011-comparison.html`。已生成的 [HTML效果报告](../../reports/f011-render-comparison.html)包含12个正例、3个非法输入与三种后端，支持并排、叠加、热图和掩码；详见 [报告说明](../../reports/README.md)。该生成命令只读取已有证据，不执行安装验证。

本轮按 [F01.1计划](../../docs/F01_1_EXECUTION_PLAN.md)执行，已实现 `f011_capture.cjs` 与 [Python runner/比较器](../f011_validate.py)。范围仅基础流程图，以下旧全功能工具职责继续保留为后续规划。

开发环境安装固定版本（不进入产品wheel）：

```shell
npm install --prefix .local/f011-oracle --ignore-scripts --save-exact mermaid@12.2.0 playwright@1.62.1 jison@0.4.18
python -m pip install -r tools/pixel_compare_requirements.txt
```

需要本机Google Chrome。先按现有upstream工具取得固定checkout；捕获器会比较发行物source map与固定Git canonical blob（包括Jison0.4.18生成转换），源码不匹配则拒绝。使用本机浏览器版本并在manifest记录，默认阻止网络资源。官方产物保留原始SVG、PNG、语义、几何/样式和错误，不改写图片。

```shell
node tools/oracle/f011_capture.cjs --out test-runs/new-official-a
python tools/f011_validate.py --oracle test-runs/new-official-a --out test-runs/new-python-b --backend cpu
```

运行Python runner前安装本地包，或显式使用开发src路径。输出目录必须新建。12个正例、3个非法输入的共享来源定义见 `tests/f011/cases.json`；L1/L2/L3和真实像素检查决定PASS，pixel_compare的diagnostic exit0不代表功能通过。包含白图、漏node/text/edge/arrow、错内容/关系/箭头、裁切负控制，以及正常单通道变化允许通过的控制。

本地S4证据见 `test-runs/f011-s4-official-003/`、`test-runs/f011-s4-compare-cpu-001/`；当前最终同候选证据由执行账本索引。旧inline注释探针错误、产品超额接受和全局/图种默认混淆的失败与修复记录保留，不覆盖。

## 后续完整迁移工具职责

本目录定义旧 M2 的工具职责，尚无完整业务 capture/语义 compare、browser 锁或 JS 结果。用户最新 [执行方案](../../docs/FULL_MIGRATION_PLAN.md)将这些正式工具与用例工作安排在全部功能源码完成后的 **P2**；P3 分组运行，P4 最终全量。P1 不以 oracle 先完成为前置。官方 Mermaid 只用于开发采集，生产解析/布局/绘制不依赖它。

通用 PNG 像素分析已作为独立工具提前提供，见 [pixel_compare.py](../pixel_compare.py)和[使用说明](../PIXEL_COMPARE.md)；完整业务 capture/语义场景/功能比较器仍未实现。P2 将其接到 L4 诊断，不把像素不同当跨 DOM/Canvas 功能失败。

## 固定环境

Mermaid 精确版本和源码以 [lock](../../references/upstream.lock.json) 为准，其 Node engine 为 `>=22.12.0`。M2 选择并固定实际 Node、npm/pnpm lock integrity、Playwright/browser revision、字体/资源、时区/locale、deviceScaleFactor 与 viewport。不能只写 latest，不能用另一个 Mermaid 包/在线编辑器代替基线。

核心包与 ZenUML、ELK/tidy 扩展分开安装并锁版本，保存传递依赖和许可。需区分官方 npm 发行物和源码重建物，不能静默互换。

在采集前核查发行物与锁定源码的 detector、主题、布局及构建开关是否一致。锁定 schema 的默认布局为 `elk`；完整构建与 tiny 的 loader/fallback 行为须分别登记，不能拿显式 Dagre 采集结果代替默认路径。随机默认用例保留原始行为，确定性比较另用显式 seed，不暗改默认值。

## 采集契约

1. 读取同一 fixture/config/resources；每个用例使用干净 config/DB，显式等待字体、图片和异步 layout。
2. 保存 detect/parse 的标准化语义和错误、最终配置、官方 SVG、实际 DOM box/path/label/marker/样式以及 PNG/RGBA。动态 ID 只在结构比较中做可追溯映射，原始文件完整保留。
3. 保存实际源码/npm/browser/font SHA、版本和命令；重采验证 seed、布局和资源稳定性。
4. 支持合法/非法输入，不把异常或空图当成成功。每份报告绑定 fixture/config/候选与环境 SHA。
5. Python runner 在无 Node/浏览器 PATH 的隔离安装环境执行；不能调用本工具生成产品输出。

按用户确定的 [功能一致规则](../../docs/RENDER_CONSISTENCY.md)，跨 DOM/Canvas 不要求像素/绝对坐标/自然尺寸相等。采集结果映射为语义场景，按功能、实际内容、关系/可读性和安全导出判定；原始图片及相似度仅诊断。正/负控制同时证明：漏内容/错箭头/裁切/no-op 绘制被拒，正常抗锯齿/合法度量和位置差异可通过。单像素只在指定确定性自身回归 profile 中作拒绝条件。

工具分解见 [P2-V01…V07 任务](../../docs/TASKS.md)和 [来源验证](../../docs/SOURCE_BASED_VERIFICATION.md)；少数 flowchart 采集不代表完整测试分母闭环。oracle 几何/fixture size 只能作预期结果，不能输入产品布局来替代 Canvas 测量或算法计算。
