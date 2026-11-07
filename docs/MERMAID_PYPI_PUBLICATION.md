# py-visactor-mermaid 0.1.0 正式发布

`py-visactor-mermaid==0.1.0` 已正式发布至 [PyPI](https://pypi.org/project/py-visactor-mermaid/0.1.0/) 和 [GitHub Release](https://github.com/py-VisActor/py-mermaid/releases/tag/v0.1.0%2Bverification.1)。双平台发行验证、OIDC 上传、公开包 SHA 核对、公开 wheel/sdist 独立安装与正式版提升均已成功。

```shell
python -m pip install py-visactor-mermaid==0.1.0
```

Python 导入名为 `py_mermaid`，命令行为 `py-mermaid`。本次目标平台为 CPython 3.13、Windows AMD64 和 Linux glibc 2.28+ x86_64。生产运行不需要 Node、浏览器、JavaScript 引擎或同目录源码仓库。

## 发布与验证证据

- [正式发行流水线 42371152814](https://github.com/py-VisActor/py-mermaid/actions/runs/42371152814)：四个任务全部 SUCCESS。Windows、Linux 分别独立安装同一组 wheel、sdist，四个安装均通过；OIDC 上传后，Linux 又独立安装两个公开发行文件并通过所有门禁。
- [审阅候选及固定文件 manifest](https://github.com/py-VisActor/py-mermaid/releases/tag/v0.1.0%2Bverification.1)：标签 `v0.1.0+verification.1` 绑定验证提交 `e7cf107a73e15dd924b31c4c916aabd43598bcff`，包版本仍为 `0.1.0`。
- manifest SHA-256：`623e511c1832181081771ef49a421da8325f6667dc10455ef98765ec36fd2a2e`。
- 原构建提交：`fd96813db5cb5c5df753eea1b3f76edf29d0eeb8`。后续仅修订文档和验证资料，没有重建、重打包或移动旧标签。
- 产品源 SHA-256：`fca211bbfc3b75db6a2553b0c01f24d37753dbb87eab3f21c4f3ff8f289db14a`。
- 本机实际 PyPI 回读日志：`test-runs/CLOSURE-RELEASE-actual-PyPI-download-readback-20261107T121322Z-b1b11c6b`。
- 双平台 CI 原始 ZIP 与选读文件：`test-runs/CLOSURE-RELEASE-dual-platform-CI-acquisition-20261107T121259Z-1fa0589d`。
- 公开包 CI 原始 ZIP、安装结果与正式版凭据：`test-runs/CLOSURE-RELEASE-published-PyPI-CI-acquisition-20261107T121533Z-49aa7790`。两个公开文件各通过 132 个方法，零失败、错误或跳过，真实时区对照全部通过。
- [可复查发布记录](../references/mermaid-publication-0.1.0.json)记录文件身份、任务、原始 CI 资产摘要和收据。

| 公开发行文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `py_visactor_mermaid-0.1.0-py3-none-any.whl` | 652648 | `25b888a4fe9c7e6a3ab0d55cfcbd0edabc2a405aab1d4cd2be46288aef72a5cf` |
| `py_visactor_mermaid-0.1.0.tar.gz` | 565531 | `c9b67cf4895cdd851d85483361cca5cf8607ccc6f92c2564488e30b76cdbb5d6` |

## 验收范围及历史

每个安装均收集 132 个合同验证方法，无失败或错误。Linux 的 132 个方法全部通过；Windows 通过 130 个，明确跳过两个依赖 Linux `tzset` 的真实时区方法。Linux 对照原版的日历及布局检查为 243 PASS、1 个预期的原版异常，四个真实时区公开 Gantt 输入全部 PASS。Windows 明确保留四个真实时区输入为 NOT_VERIFIED，其余 239 PASS、1 个预期的原版异常；这些时区项由 Linux 闭合。

首次发行工作流因错误的夏令时测试前提失败，上传被门禁阻止；修订记录见[本批验收](CLOSURE_BATCH_ACCEPTANCE.md)。旧 40 例快照和所有失败日志保留，新增两例真正跨切换的独立原版控制使用单独快照目录。当前发行夹具为 134 输入，其中 121 个绘图输入、13 个 parserOnly；这不改写旧 P4 的 132 输入和 119 个绘图输入。

本地完整 P4、866 个历史输入、301 个 VChart DSL 案例的三后端验证、255 项追加导出、105 张原图实际复核，以及 119 例、12 页报告均保持原收据。[查看本地分页报告](http://127.0.0.1:8765/CLOSURE-P5-delivery-20261107T113304Z-8513c1b4/index.html)。报告原始附件、链接及桌面/移动布局已验证，服务保持运行。

本次完成约定的静态渲染范围。VChart 图表能力及其供应方限制由 py-vchart 管理；交互、动画、Dagre、video/audio、任意 HTML/CSS 扩展与 3D 不纳入支持范围。字体、绘制引擎及手绘种子的正常差异按可见内容、关系和布局验收，不承诺跨引擎像素一致。
