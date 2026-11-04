# 日志与渲染报告复用规范 v1

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

final目录需要summary.json、source-candidate.json及每个compare-profile的report.json、场景JSON、PNG和诊断报告；oracle需要identity/manifest、场景、PNG和非法输入记录。当前场景结构沿用F01.1比较器：diagram nodes/edges、layout、trace、绘制节点/边和PNG指标。后续图种可复用日志/模板，但专用语义数据若不同，须先增加相应适配，不能靠改标题就宣称全图种兼容。

报告按fixture ID、profile分母、固定来源commit、候选身份、PNG尺寸和SHA校验输入；缺失/重复/错配产物明确失败并留日志，不生成成功白图或隐去难例。失败结果有完整图片时仍按原状态展示FAIL，不提升为PASS。HTML/template/case标题/profile选择已解耦，不再在脚本里写执行日期与固定run目录。

报告生成器内嵌原始PNG，不重绘或配准；功能状态与图像诊断分开。旧的 [build_f011_html_report.py](build_f011_html_report.py) CLI继续兼容，新增 `--spec/--fixtures/--profiles`；推荐workflow入口以同时获得统一日志。

## 本地HTTP服务

```shell
python tools/serve_reports.py --root reports --host 127.0.0.1 --port 8765
```

本地URL为 `http://127.0.0.1:8765/`，具体报告使用相应子路径。默认只监听loopback、只服务reports目录。新启动的服务会创建标准serve run，启动信息含pid、URL、root与日志目录；访问事件写events.ndjson，同时输出UTF-8 NDJSON。Ctrl+C退出后完成manifest；被强制结束时RUNNING记录表示尚未正常收口，verify不会伪称完整。

本次此前启动的8765服务保持运行，既有URL不变；它早于新日志模块启动，终端会话日志按历史记录保留，不伪装成新格式。下次直接使用上述命令即可获得标准服务日志。安装验证继续暂缓。
