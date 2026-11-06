# 静态批次工具：复用入口

范围读取 `references/bulk-scope.json`，本批 31 保留入口、7 暂缓入口。工具不安装依赖、不提交推送、不发布。
当前初次 P4 已完整执行但被人工画面与旧验收资料问题拒收，正在集中批修并准备新冻结候选。
以下命令实际用于 P3/P4；历史失败与原始图不覆盖。

```powershell
C:/venvs/pymmd-20261102/Scripts/python.exe tools/run_bulk.py first --dry-run
C:/venvs/pymmd-20261102/Scripts/python.exe tools/run_bulk.py first
C:/venvs/pymmd-20261102/Scripts/python.exe tools/run_bulk.py final
```

`first` 依次记录 A/B/C/shared 和 F01.1～F01.4/数学单测、固定官方图、CPU 新批次图、比较与 HTML。
任何组失败仍继续后续组，所有原始失败保留。执行期间不得改产品源码。
`final` 在同一候选上执行 CPU/auto/GPU，并重新验证 297 个历史正例及原负例/范围诊断。
GPU 必须是真实 GPU；失败单列，不以 CPU 替代。安装验收继续暂缓。

各次创建 `test-runs/BULK-P3-first-*` 或 `BULK-P4-final-*`，使用 `run_support.Run` 保存原始命令参数、
stdout/stderr、真实退出码、输入/工具/源码 SHA、环境、部分进度与产物 SHA。已关闭 run 不追加修改。
命令超时由标准日志记录，产品仍负责自己的 worker 生命周期。

工具分工：

| 工具 | 职责 |
| --- | --- |
| `collect_bulk_cases.py` | 验证 fixture 来源 SHA、范围和 ID，冻结输入与显式离线资源；不调用产品 |
| `check_bulk_tests.py` | 仅编译、导入和 unittest 发现，报告方法数；不执行方法、不将数量称为覆盖率 |
| `oracle/bulk_capture.cjs` | 固定 Mermaid 12.2.0 原图、DB、配置、DOM 几何/样式及错误；Zen 原 core 3.49.2 |
| `bulk_validate.py` | 原生结果、真实后端、完整纯场景、可见文字/像素/画布边界和负控制 |
| `bulk_compare.py` | 读取既有 A/B，比对主题派生变量及源期望文字，生成仅诊断的像素指标和热图 |
| `bulk_export.py` | 每个保留入口 × CPU/auto/GPU × 五格式，解码/解析真实编码和绘制内容，保存全部原始文件 |
| `check_zenuml_parity.py` | 对全部 148 个锁定源样例比较原 geometry/SVG、实际原生 trace/PNG 的消息、编号、箭头与片段结构；精确处理两项原源内容丢失，含变异负控制 |
| `build_bulk_report.py` | 只读既有证据，将原始 PNG 字节嵌入离线 HTML；不渲染、不缩放处理原图 |
| `qa_bulk_report.cjs` | 检查 HTTP 与 HTML 指纹、全部内嵌 PNG/SVG 原始字节及次数、31 图种和复杂样例解码/尺寸、搜索筛选、桌面和窄屏；只用既有固定开发浏览器 |
| `run_bulk.py` | 阶段编排、全分组继续收集、同候选检查和统一日志 |

只重建报告，使用真实目录替换示例；不重新运行产品：

```powershell
python tools/run_bulk.py report --oracle test-runs/ACTUAL/artifacts/oracle --native test-runs/ACTUAL/artifacts/native-cpu
```

报告区分 `CHECKS_PASSED_REVIEW_REQUIRED`、失败、上游疑点和静态范围排除。
单例绘制检查通过不等于完整图种验收；必须合并来源独立语义/算法单测和画面复核。
相似度、像素工具退出 0、HTML 成功生成、日志完整，都不单独构成功能通过。
允许浏览器与 Canvas 自然尺寸、字体度量和布局坐标差异，漏内容、错连接、裁切与不可读仍是失败。

已有 oracle 仅在明确提供 `--oracle` 且其固定源、fixture/config/resources 身份一致时复用；
P4 默认重新采集，避免默用旧证据。`--legacy-oracle-root` 是四组旧 oracle 的显式复用入口。
候选源码变化需要重新验证，新产物不能混拼旧候选的通过结果。

复用 oracle 必须匹配冻结的完整 fixture/config/resources 字节 SHA，且重新验证当前固定源、插件和传输身份。
历史流程图 oracle 也必须提供 fixture SHA；缺旧指纹的历史目录不能直接复用。
tidy oracle 注册锁定原扩展，Node 内置 TypeScript 擦类型后运行原算法语句，原 non-layered 模块按原字节加载；
Git Windows CRLF checkout、canonical git blob 和传输代码分别留 SHA，真实 loader 调用次数写入结果，禁止默拿 COSE 回退作为 tidy 基准。
原版采集仅使用固定 JS 来源，不消费 Python 产品源码，允许在批修期间独立采集；该 Run 只能证明原版，
不能用其 Python sourceUnchanged 或命令成功声称新候选通过。最终 P4 仍需新候选 unit/native/export 完整验证。

fixture ID 必须跨平台唯一：拒绝仅大小写不同、末尾点或设备保留名。
本次 4 个 Gantt ID 的移名及历史证据不可复用说明见 `references/bulk-case-id-aliases.json`；
source/config/expect 和 115 个 B 案例分母保持不变，原大小写不同的语言 token 继续分别验收。

原生生产代码不导入这些工具，不依赖浏览器、Node、开发资源目录或报告服务。
最终 HTML 服务仍使用 `serve_reports.py` 标准访问日志；服务仅供本地查看，不代表外部发布。
