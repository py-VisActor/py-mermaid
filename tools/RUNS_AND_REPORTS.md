# 日志与渲染报告复用规范 v1

## 非 VChart 统一收口与发行复用

收口入口为 `run_closure.py`。它冻结产品、完整测试/工具字节、原始夹具和原版来源身份；全部分组首跑闭合后才能批修，失败 Run 不覆盖。最终统一执行：

```shell
python tools/run_closure.py --phase final --profiles cpu auto gpu --regressions --install --historical --vchart
python tools/run_closure_delivery.py --run test-runs/<closed-final-run> --visual-review <actual-review.json>
```

`finalize_closure.py` 只核已有闭合日志、动态分母、原版对照、三后端、旧回归、导出和附件 SHA。人工看图收据必须绑定候选 Run、源码 SHA 和实际检查的原图 SHA，工具不能代写已看图事实。`build_closure_report.py` 每页最多12例；`qa_closure_report.cjs` 核全部 HTTP 原字节、ID/状态、链接及桌面/移动布局。报告成功、静态合同通过、Linux门禁和正式发布分别记录。

正式发行名为 `py-visactor-mermaid`，导入与命令行为 `py_mermaid` / `py-mermaid`。提交冻结候选后，`release_package.py build --out <new-dir>` 构建一次并生成 `release-manifest.json`，wheel/sdist 位于该目录的 `packages/`。`release_package.py install --manifest <manifest> --packages <packages-dir> --out <new-dir>` 在仓库外顺序新建环境，安装真实文件和正式 PyPI 依赖，检查实际绘制、CLI、单测、原版日历/布局观测和模块来源。Windows 无法执行的真实 IANA 时区切换明确标为未证，Linux CI 必须实测通过；纯函数 DST 控制不能替代此门禁。

`release_github.py create/download/dispatch/status/promote` 固定 tag、提交、manifest SHA 和发行文件 SHA，不覆盖不同的已上传字节。工作流 `publish-pypi.yml` 对相同文件进行 Windows/Linux wheel/sdist 验证，然后通过 Trusted Publisher 上传，回读实际 PyPI 两个文件并核 SHA 后提升 GitHub stable。`--allow-dirty` 只用于开发安装相关批，不是正式发行证据。Venn、Treemap 和图表供应方字段范围由 py-vchart 管理，保留原历史观察，不在此批扩大。

原版复用可显式传 `run_closure.py --historical-oracle <closed-source-union> --legacy-oracle-root <f011-to-f014-root>`；内部仍核所有输入字节与固定源码身份，绝不复用原生绘制结果。`merge_bulk_oracles.py --replace-case-id <ID>` 仅允许显式替换旧输入，旧证据仍完整核SHA并记录supersededInputs，且必须有另一闭合成功source producer与最终完整行严格匹配；缺替换、误ID、重复或损坏旧证据均拒绝。`freeze_closure_b_source.py --run <closed-donor> --out <new-dir>` 只接收原版B输入/观测，保存原source producer和bundle/map/module身份，不能把native结果作为golden。donor整体失败与其成功source命令分别记实。

## 按迭代轮次分页交付

后续大批次报告以分页总入口交付，单页完整报告保留为不可变来源证据。复用命令：

```shell
python tools/run_report_rounds.py --spec tools/report_specs/iteration-rounds.json --base-url http://127.0.0.1:8765/
```

先运行已有报告服务；`--base-url` 指向其根 URL，并启用浏览器 QA。不传时只生成/发布，明确记为未执行浏览器 QA。每次新建标准 `REPORT-ROUNDS-delivery-*` Run，保存命令、输入/工具指纹、输出、退出码和浏览器证据；页面发布在 `reports/<run-id>/index.html`，不会覆盖历史目录。该工具不渲染产品、不安装依赖，也不会把来源报告的失败状态提升为通过。

配置 [iteration-rounds.json](report_specs/iteration-rounds.json) 显式指定来源 HTML/metadata 路径与 SHA、各轮 `caseFiles` 或 `caseIds`，以及更早轮次的固定报告链接。更新候选时显式更换来源与指纹，不扫描目录猜测最新版；轮次分组仅表示输入属于哪轮，首页明确首批输入使用同一最终候选的回归画面。重复、遗漏、未知案例或指纹错误均拒绝。

默认每页 12 例，`--page-size` 支持 1～24。首页与轮次概览不内嵌案例图片，提供轮次入口、案例定位和跳页；案例页仅搜索当前页，支持上一页/下一页、跳页以及 CPU/auto/GPU 选择。只展示所选 B 后端，其他后端原图仍保留在该页。原始 PNG/SVG 分配到各分页后逐字节、逐次数复核，不裁切、重采样或更改案例状态。分页报告 `functionalStatus=NOT_EVALUATED`，原报告状态单独记录，不冒充新候选验收。

`qa_report_rounds.cjs` 校验所有分页 HTTP/文件指纹、完整唯一案例分母及原始图片字节，再用现有开发 Chrome 验证轮次/案例导航、跳页、后端切换、桌面与窄屏；截图和 QA JSON 留在标准 Run。`test_report_rounds.py` 覆盖丢例、重例、错图、改状态、指纹漂移和路径边界。


2026-11-06 功能复核：`check_gap_audit.py` 校验功能组对应与来源引用，不能据此推定分支覆盖率。`merge_bulk_oracles.py` 可把多份已关闭、原版采集命令成功的证据严格合并到新目录：逐行输入、固定 source identity、浏览器、Run artifact SHA 与完整分母必须一致，原始图片不变换；整 Run 的其他测试失败不被改写为成功。

完整运行仍使用 `run_bulk.py final`。可显式传 `--skip-legacy-pixels`，仅省去历史 F01 的重复 A/B 热图/统计子进程；同候选的全部历史实际渲染、文字/关系/几何、实际墨迹及负控制照常执行，新批次的原始 A/B 和像素诊断照常生成，输出明确标记 `SKIPPED_EXPLICIT_NON_GATING_DIAGNOSTIC`。默认仍生成历史诊断。已知未迁移功能用 `--scope-note` 显示在报告顶部，不借图种验收隐藏。

2026-11-06：31 入口静态批次工具已进入 P2 设计，入口 [BULK_REPORTS](BULK_REPORTS.md)。
`run_bulk.py` 复用同一 Run 标准，扩展来源校验、全分组首跑和通用 A/B HTML；下文 F01 工具继续保留供历史回归。

统一入口是 [workflow.py](workflow.py)，使用Python标准库管理执行记录；所有命令都不会安装依赖。当前场景适配器为F01.1，产品的parse/render和安装验证不因日志标准化而扩大范围。已有历史报告、失败和日志原样保留，新执行使用新run，不将旧数据补写成新验证。

## 直接复用

只从已有证据生成报告（不重新渲染/测试/安装）：

```shell
python tools/workflow.py report --spec tools/report_specs/f011-baseline.json
```

命令自动创建日志run，并将HTML和报告manifest复制到 `reports/<run-id>/index.html`。终端JSON分别输出 `manifest`（执行日志run.json）、`report`（可打开HTML）和 `reportManifest`（报告输入/输出指纹），不会混用。保留之前的 `reports/f011-render-comparison.html`。

明确需要新效果时，重新采集官方A、运行Python B、像素诊断并生成报告：

```shell
python tools/workflow.py render --fixtures tests/f011/cases.json --profiles cpu --dry-run
python tools/workflow.py render --fixtures tests/f011/cases.json --profiles cpu
```

`--dry-run`只输出将执行的argv，不创建run、不执行产品或安装。去掉该参数才实际运行；CPU仅表示本批CPU结果。需要已有设备上的三个profile时使用 `--profiles cpu auto gpu`；GPU-required不得静默退CPU。依赖/固定上游和开发Chrome由调用环境提供，工具不会安装、升级或下载缺失依赖。产品Python默认使用当前解释器，可通过 `--python`指定已有环境；Node可用 `--node`指定已有可执行文件。

新渲染run自动保存当时的fixture快照、源码候选、A/B产物、比较结果、诊断日志和本批报告配置。它没有运行单元测试或构建wheel，页面明确显示“本批未执行单测”和“未提供wheel”，不借用历史85项测试或旧wheel身份。

记录任意一次明确命令：

```shell
python tools/workflow.py record --scope F01.1 --name language --input references/f011-language-assertions.json -- python -m unittest discover -s tests/f011 -p test_language.py -v
```

执行命令用参数数组与 `shell=False`，不拼接shell字符串。`--`后传原始argv。`--timeout`单位秒；返回实际退出码，超时124、无法启动127、Ctrl+C中断130。stdout/stderr各存原始字节，不合并、截断或由locale重新编码。超时只保证终止直接子进程，具体worker/子进程树生命周期仍由工具和产品各自负责。

按计划执行功能测试（只有明确调用才运行）：

```shell
python tools/workflow.py batch --plan tools/plans/f011-tests.json --dry-run
python tools/workflow.py batch --plan tools/plans/f011-tests.json
```

默认失败即停，`--keep-going`继续收集后续命令，整体仍保留第一个失败退出码。计划内只展开 `{repo}`、`{run}`、`{python}`，没有任意表达式或shell展开。环境覆盖值由计划显式提供，运行清单不复制整个环境变量表。

## 日志目录

每次run ID形如 `F01.1-report-YYYYMMDDTHHMMSSZ-随机后缀`，默认目录为 `test-runs/`；可用 `--runs-dir`更改。scope可由报告配置/命令计划推导，或通过 `--scope`显式指定。

```text
test-runs/<run-id>/
  run.json                  执行身份、状态、环境、源码、命令、输入和产物指纹
  events.ndjson             每行一个带schema/runId/UTC时间的事件
  git-status.txt            起点Git状态（Git可用时）
  error.txt                 编排异常的完整traceback（发生时）
  commands/001-<name>/
    command.json            原始argv/cwd/timeout/开始时间
    stdout.log              子进程原始stdout字节
    stderr.log              子进程原始stderr字节
    result.json             实际退出码/结束时间/耗时/两份日志SHA
  artifacts/                fixture、计划、配置、候选与A/B产物
  report/index.html         单文件离线HTML
  report/index.manifest.json
```

活动run允许原子更新run.json；完成后不再追加，重复运行生成新ID。文件完整性清单不包含run.json自身；其他产物及发布副本记录SHA/字节数。状态是 `RUNNING/SUCCESS/FAILED/ERROR/INTERRUPTED`，命令另有 `TIMEOUT`。事件包括run_started、command_started、command_finished、report_generated、report_published、run_finished和HTTP访问事件。

候选指纹只覆盖真实产品源/元数据/许可，排除egg-info、缓存、构建目录和日志；前后源变化单独记录 `sourceUnchanged`。通用logger记录Python、平台、现有依赖版本、Git HEAD、logger/编排器自身SHA、argv里实际脚本文件SHA与显式输入指纹；具体字体/native/资源身份仍由对应采集器补充，不能从通用日志推断所有运行路径已被追踪。

验证保存的日志/报告有没有丢失或变化：

```shell
python tools/workflow.py verify --run test-runs/<run-id>
```

此命令只核对文件，不重新运行测试。`integrityStatus=PASS`表示日志完整，即使 `executionStatus=FAILED`也可能完整；`functionalStatus`独立记录，不能由日志完整、命令成功或像素diagnostic退出0推定功能通过。只有显式渲染比较批次汇总真实比较器结果；纯报告生成run为NOT_EVALUATED。

机器格式见 [run schema](schemas/run.schema.json)、[事件schema](schemas/event.schema.json)、[命令计划schema](schemas/command-plan.schema.json)、[报告配置schema](schemas/report-spec.schema.json)与[报告manifest schema](schemas/report-manifest.schema.json)。格式版本变化应升级schema，历史记录不原地重写。文件指纹流式计算，stdout/stderr不截断，不把整份大日志一次载入内存。

## 报告配置

复制 [基线配置](report_specs/f011-baseline.json)，修改scope/title/final/oracle/fixtures/profiles即可复用。配置路径以仓库根为基准，也支持绝对路径；从其他cwd调用workflow仍按同一规则解析。不要用目录时间猜测最新A/B组合，必须显式选同一候选的证据。

```json
{
  "schema": "py-mermaid-render-report-spec/v1",
  "scope": "F01.1",
  "title": "本轮基础流程图对比",
  "final": "test-runs/某次候选结果",
  "oracle": "test-runs/对应官方结果",
  "fixtures": "test-runs/该批输入快照.json",
  "profiles": ["cpu"]
}
```

final目录需要summary.json、source-candidate.json及每个compare-profile的report.json、场景JSON、PNG和诊断报告；oracle需要identity/manifest、场景、PNG和错误记录。F01.1/F01.2场景包括diagram nodes/edges/groups、经典shape、独立edge labels、真实layout与trace、实际绘制节点/边/组/标签及PNG指标。后续图种可复用日志/模板，但专用语义数据若不同，须先增加相应适配，不能靠改标题就宣称全图种兼容。

fixtures的`negativeCases`只放官方语法非法输入；`renderErrorCases`单独记录能解析但固定上游无法渲染的案例（F01.2经典ellipse）。每例有id/text/code，oracle记录parsed/renderRejected与原错误，Python需解析成功并匹配明确错误code；不伪造PNG。报告分别核对三类分母。每个正例可带config、shapes、edgeLabels、groups及独立手写语义期望；渲染批次同时传递config给A/B。`--default-case`可指定报告默认显示的正例。

F01.2复用入口：

```shell
python tools/workflow.py batch --plan tools/plans/f012-tests.json --keep-going
python tools/workflow.py render --scope F01.2 --fixtures tests/f012/cases.json --profiles cpu auto gpu --title "流程图增强 · F01.2 对比" --default-case enhanced-overview
python tools/workflow.py record --scope F01.2 --name html-qa -- node tools/qa_html_report.cjs --url http://127.0.0.1:8765/<run-id>/index.html --out test-runs/<new-qa-dir>
```

`qa_html_report.cjs`仅使用已有开发浏览器依赖，逐正例/错误例及后端验证HTML导航、图片原始尺寸、输入文本与保存结果，检查叠加/诊断模式、桌面/移动布局和浏览器错误，保存截图及QA JSON；不执行产品渲染或安装。开发浏览器工具不进入生产依赖。

报告按fixture ID、profile分母、固定来源commit、候选身份、PNG尺寸和SHA校验输入；缺失/重复/错配产物明确失败并留日志，不生成成功白图或隐去难例。失败结果有完整图片时仍按原状态展示FAIL，不提升为PASS。HTML/template/case标题/profile选择已解耦，不再在脚本里写执行日期与固定run目录。

报告生成器内嵌原始PNG，不重绘或配准；功能状态与图像诊断分开。旧的 [build_f011_html_report.py](build_f011_html_report.py) CLI继续兼容，新增 `--spec/--fixtures/--profiles`；推荐workflow入口以同时获得统一日志。

## 本地HTTP服务

```shell
python tools/serve_reports.py --root reports --host 127.0.0.1 --port 8765
```

本地URL为 `http://127.0.0.1:8765/`，具体报告使用相应子路径。默认只监听loopback、只服务reports目录。新启动的服务会创建标准serve run，启动信息含pid、URL、root与日志目录；访问事件写events.ndjson，同时输出UTF-8 NDJSON。Ctrl+C退出后完成manifest；被强制结束时RUNNING记录表示尚未正常收口，verify不会伪称完整。

本次此前启动的8765服务保持运行，既有URL不变；它早于新日志模块启动，终端会话日志按历史记录保留，不伪装成新格式。下次直接使用上述命令即可获得标准服务日志。安装验证继续暂缓。


## F01.3 复用约定

F01.3 使用相同 `batch`、`render`、`report`、`verify` 入口：测试计划是 `tools/plans/f013-tests.json`，输入为 `tests/f013/cases.json`，交付报告配置为 `tools/report_specs/f013-final.json`，默认显示 `rich-overview`。`qa_html_report.cjs` 遍历所有正例/后端和错误例，校验图片原始尺寸、源输入、各显示模式、桌面与移动布局以及无外部请求；它只查看已保存报告。

## F01.4 静态收口复用

`assemble_f014_cases.py` 只组装独立来源夹具，不从候选输出生成期望。先运行 `workflow.py batch --plan tools/plans/f014-unit-tests.json --keep-going`，再执行 `f014-legacy-visual.json` 和 `f014-final-visual.json`；全部通过后，`f014-delivery.json` 将矩阵证据复制到新目录，汇总同候选结果并生成 HTML。每次运行创建新目录，失败不覆盖。计划中明确引用的历史证据路径属于该次候选输入；换候选时更新引用，不能把旧通过结果改写成新结果。

`reuse_oracle.py` 校验固定来源身份、案例分母、执行输入及复制后的每个文件 SHA；新增或改变的案例必须显式 `--refresh`，删除案例拒绝复用。无 refresh 时重新校验固定源码身份，直接复用不可变 A 图；CPU/auto/GPU 的 B 图始终从当前候选重新生成。来源采集保留 SVG 的真实绘制顺序：手绘状态圆最后的 CSS 不透明 outline fill 会覆盖先前 hatch，不能只用底层 computed stroke 推断可见底色。

`export_static_samples.py` 经公开 API 生成五种真实静态导出。`finalize_static_evidence.py` 核验同一源码、实际 unittest 数和三后端完整分母，生成 summary 与 report spec；`workflow.py report` 将已保存证据生成可下载导出样例的单文件 HTML。`qa_html_report.cjs` 验证所有案例、后端、错误页、显示模式、导出指纹、桌面/移动布局和无外部请求。人工看图另存 receipt，自动 PASS 不能替代人工核查。

大型单文件 HTML 可能超过 Chromium inspector 的响应体缓存。QA 用独立 HTTP 读取计算文件 SHA，浏览器继续逐项验证实际加载页面；不依赖 inspector 的 `response.body()` 缓存，也不跳过案例遍历。

增加独立第四类 `unsupportedCases`：官方语法接受，Python 对本切片范围外的输入返回列明的 `codes`。该类只执行官方 parse，不为 Dagre/新语法等范围外功能触发官方渲染，也不生成成功 PNG。原语法负例、上游渲染缺陷和正例分母保持独立。

富文本核对同时使用手写意图、官方真实 computed styles/文字 run 与 Python 实际 PNG。多行边界允许软换行，同一行格式 run 不允许凭空加空格；一像素线可有分数覆盖，但颜色须符合预期前景/背景混合。空 `<br/>` 边标签没有可见文字，不能要求一个空文字事件作为漏绘负控。边标签可以同时有外层与 run 背景，检查实际文字容纳和背景存在，不将重复合法事件判为漏绘。

非有限 JavaScript 主题值通过 `scene_codec.py` 的显式 `$jsNumber` 标签保存，不能输出裸 NaN/Infinity 导致 HTML JSON.parse 失败。sandbox 对照保留原 iframe HTML，并只展开原始 SVG 进行截图；不调整其布局和样式。纯 Python 产品路径不使用该研发转换。

Windows 活跃 manifest 使用原子替换；只有临时共享/访问锁错误才做有上限重试，持久失败仍抛出，旧完整文件保持。关闭后的 run 不重写；原始失败、错误断言快照及后续修复证据分别存储。详情与本轮实际结果见 `docs/F01_3_ACCEPTANCE.md`。


## HTML 静态控件与按轮分页复用

`run_bulk.py final` 默认冻结 `tests/bulk/cases-*.json` 与 `tests/html_host/cases*.json`，执行控件单测、三 profile 原版状态/真实绘制核对，以及独立的控件类型代表五格式矩阵。控件分母由冻结夹具派生，不能把原版 IDL 或容器 trace 冒充实际文字/勾选绘制。`bulk_export.py` 对每个 fixture/profile/format 使用独占文件名并记录保存后的 SHA；重复文件名或持久化字节变化必须失败。

闭合 P4、实际人工 A/B 记录齐全后使用：

```shell
python tools/finalize_html_host_evidence.py --p4 test-runs/<closed-final-P4> --visual-review <actual-review.json> --out <new-finalized-dir>
python tools/run_report_rounds.py --spec tools/report_specs/iteration-rounds-html-host.json --base-url http://127.0.0.1:8765/
```

汇总工具核对源归档、完整冻结控件夹具、实际测试数、所有 profile、导出笛卡尔积及保存文件 SHA、全部31入口人工抽查与 reviewRequired 用例；不生成看图记录。命令仍经 `workflow.py record` 或 `Run.command` 保存标准日志。报告生成必须显式传 `--unit-runs` 指向已关闭的同候选 P4，再传该汇总 acceptance，不使用执行中或失败的 manifest 充当验收。

仅导出证据因工具缺陷需重跑时，可使用 `--exports-run <closed-HTML-HOST-P4-EXPORT-repair>`。它不绕过原 P4：要求两个导出矩阵均重新运行、同产品候选、相同冻结 fixture/选择/profile argv、执行工具归档一致、全部文件唯一且 SHA 完整，并把原无效导出与补充 manifest 一起记录。不得覆盖已关闭 P4 的产物或改写失败尝试。常规新 P4 使用修正后的导出工具，不需要此补证参数。

本次配置把第三轮131例、第二轮64例、第一轮670例分为11/6/56个案例页，每页最多12例；后续新增轮次应创建新的 spec，显式绑定最新已验收原始报告与夹具，保持旧 spec/报告证据。分页纯展示的 NOT_EVALUATED 与源报告验收状态分别保留，原PNG/SVG字节、失败/上游缺陷状态不提升。


## 保留分支核实复用

本轮核实入口为 `tools/plans/branch-verification-first.json` 与 `branch-verification-followup.json`，执行仍使用 `workflow.py batch --plan ... --keep-going` 保存每个真实退出码。前者保留最初诊断输入，部分源触发/预期已被推翻；当前解释以 `references/branch-verification-summary.json` 为准，不能把重跑该计划当成功回归套件。失败是重要结果，不覆盖首跑。

`freeze_branch_inputs.py` 保存当前产品候选、完整输入归档、原始fixture、按组输入与browser fixture；原始fixture的pureProbes保留，不能只冻规范化渲染行而丢掉纯函数分母。`check_branch_catalogue.py` 验证固定source/map sourcesContent SHA、条件/arms、case与pureProbeID、精确既有测试归档及其通过日志。它只核目录/引用完整，不推断功能或全项目覆盖率。Windows checkout与canonical git blob分开记录；固定source-map中的依赖版本优先于可能漂移的开发node_modules。

纯日期取证统一使用UTC；serializer用纯Gregorian算术而非Windows CRT naive timestamp。不得修改产品日期函数去掩盖实际输出/异常。对应原版模块、输入、sourceExpected/sourceActual/nativeActual各自保存。源预期不成立、未触发条件或工具错误必须单列，不自动归为产品缺口。

`build_bulk_report.py --allow-subset` 仅用于定向核实，显式拒绝与whole-batch acceptance同时使用；不取消默认31入口完整性要求。生成原A/B后用 `run_report_rounds.py --spec tools/report_specs/branch-verification-round4.json --base-url http://127.0.0.1:8765/` 按最多12例分页，保留失败状态和原PNG/SVG字节。换证据时新建spec，不修改闭合报告。

`build_branch_summary.py --summary RESULT_JSON --comparison-url URL --out NEWDIR` 把明确归因结果分组、每页最多12条，不提升任何分类；`qa_branch_summary.cjs --url URL --report SUMMARY_REPORT_JSON --out NEWDIR` 核对全122（动态分母）记录的状态/文件指纹、每个案例链接及桌面/移动页面。摘要JSON按原字节下载。当前报告中的22条确认功能缺口尚未修复，通用绘制门禁成功与报告QA通过均不等于功能通过。

## VChart 发行与接入复用

`run_vchart_validation.py` 使用标准 Run 保存每组真实退出码、两侧源码/夹具指纹和完整输出。首轮使用 `--phase first`，会保留所有分组首失败；最终使用 `--phase final --packages <已审阅正式发行目录> --profiles cpu auto gpu --regressions`。`--supplier-python` 指向供应方的独立测试解释器，默认生产解释器运行宿主测试。最终阶段拒绝 dirtySource 构建，实际安装正式 wheel，不把相邻仓库放入生产导入路径。原版 oracle、225 原生输入、旧 reference、68 API、七语法及旧回归分别保存，不混用验收结论。

`verify_vchart_install.py --kind wheel` 和 `--kind sdist` 各建立仓库外的新环境，从真实 py-mermaid 构建文件进行正常依赖解析。禁止提前安装 VChart；验证 pip 下载 URL、SHA、site-packages 来源、68 类型实际绘制、数学公式与 ELK，并保存 pip report/freeze。交付渠道和 PyPI 状态读取 `references/vchart-release-lock.json`，GitHub stable 不能被记作 PyPI 已发布。

已关闭同候选运行使用 `collect_vchart_report_inputs.py` 合并供应方、68 API 及七语法原始证据，再由 `build_vchart_report.py` 生成三组分页 HTML，每页最多 12 例。所有 PNG/SVG/PDF 等附件按原字节复制并核 SHA；原生词云的明确差异、原语法错误和范围限制保留。生成报告和浏览器 QA 成功只代表报告可读、附件完整；最终功能状态还须绑定同候选测试和实际看图收据。每次输出到新目录，禁止覆盖已关闭报告。

完整交付使用 `run_vchart_delivery.py --p4 <closed-run> --visual-review <receipt.json> --install-runs <wheel-run> <sdist-run> --ci-summary <supplier-ci-summary.json> --release-proof <stable-release.json>`。该命令顺序执行证据汇总、原字节归集、分页报告和实际 HTTP/浏览器 QA，并保存所用后处理工具的完整字节。当前源码须与候选一致；汇总必须拒绝失败运行、旧图收据或损坏附件。默认报告地址为 `http://127.0.0.1:8765/<new-run-id>/index.html`，要求 `serve_reports.py` 已服务仓库 `reports/`。


PyPI渠道切换使用 `verify_vchart_pypi_delivery.py` 绑定发布回读Run、正常index安装的wheel/sdist Run、原同候选P4、实际检查Run及CI核验ZIP；核对发布文件同SHA、渲染源码未变及当前包装说明差异。汇总另存 `references/vchart-pypi-verification.json`，旧GitHub渠道验收/报告不改写。`verify_vchart_install.py` 同时支持已锁定的GitHub历史渠道与当前PyPI渠道；PyPI须无direct_url.json，并核正常pip report下载URL/SHA。

## VChart DSL v1 复用

`run_vchart_dsl.py --phase first --profiles cpu auto gpu --regressions` 完整收集首跑，再集中修复；最终使用 `--phase final`。冻结产品/测试/工具完整字节及 225 原规格、68 类型代表、8 手写独立预期，共301案例。分组有来源重叠，不代表301图种。同后端 spec API/DSL 的编译类型、对象成员顺序、离线资源、场景和实际PNG分别比较；不能把跨引擎像素差诊断当成功或失败的唯一依据。

新环境分别顺序执行 `verify_vchart_install.py --kind wheel --dsl`、`--kind sdist --dsl`。共享构建目录不能并行；每环境实际绘制68 spec及68 DSL，并核正式PyPI依赖、Math、ELK及矢量导出。

闭合最终 Run 和真实看图收据具备后执行：

```shell
python tools/run_vchart_dsl_delivery.py --run test-runs/<P4> --wheel test-runs/<wheel> --sdist test-runs/<sdist> --visual-review <receipt.json>
```

该工具保存汇总、分页报告和HTTP/浏览器QA真实退出码，输出到独立第六轮目录。`finalize_vchart_dsl_evidence.py` 核闭合日志和原文件身份；`build_vchart_dsl_report.py` 逐字节复制原始源/JSON/资源/图像/导出，每页最多12例。`qa_vchart_dsl_report.cjs` 检查全部案例、链接、下载SHA、桌面与移动布局及负控。报告只展示已有结论，不生成验收或看图事实。旧候选预演须显式 `--rehearsal`；即使其矩阵全绿也不能提升整体失败 Run。

## 最终能力复查与有缺口时的发布判定

`inventory_release_capabilities.py --out NEWDIR` 核当前39注册入口/68正式供应方类型的实际接线、生产导入根、显式异常候选及包/工作流/PyPI只读元数据。它不绘制、不发布；无TODO、无空函数或资料核验成功均不能推断功能完整。AST扫描只列显式raise候选，不能替代公开入口、动态调用路径或静默错画的独立来源验证。

对当前源单独复跑确认缺口的来源探针和断言，用标准Run保存所有退出码；生成当前A/B/C/root审计以及主汇总。来源生产者成功、原生“重现错误”断言成功和完整性检查成功，不计为功能修复。源代码未变时可以明确绑定旧完整回归/安装证据，不能冒称本轮重跑。

```shell
python tools/build_final_capability_report.py --summary references/final-capability-review.json --out reports/<new-report>
node tools/qa_final_capability_report.cjs --report reports/<new-report> --out <new-qa-dir> --url http://127.0.0.1:8765/<new-report>/index.html
```

这两步通过 `Run.command` 或 `workflow.py` 留存原始日志。报告明确保持 `REVIEW_COMPLETE_RELEASE_BLOCKED`，按功能缺口、图表限制、发行门禁、未证项分组，每页最多12条；所有附件逐字节复制。QA核对全部ID/状态、HTTP附件SHA/链接、1440/390视口和篡改负控，只使用隔离研发浏览器。QA成功不提升功能状态，不触发上传；原始失败和之前验收不改写。当前统一待修队列为 `references/final-capability-repair-queue.json`，保留旧22条清单作为历史。


### Event ???????

`tests/closure/cases-event.json` ?? portable `test_eventmodeling.py`?`event-source-expectations.json` ???????`run_closure.py` ?????? `cases-*.json` ???????????????

```powershell
python tools/check_eventmodeling_paint.py --fixtures <frozen/cases-event.json> --oracle <same-run/oracle> --native <same-run/native-cpu> --out <new-comparison-event-cpu.json>
```

checker ????????????????? trace/PNG??? lane ????????????????????/????/code ?????????? glyph ???????trace ??????????????????? raw HTML ???????????????????? `#amp; ? &` ????? HTML ??? hash ??????????????????source-only DOM ?????? native ????????
