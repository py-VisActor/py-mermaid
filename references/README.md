# 上游资料与 spec 索引

固定官方 [Mermaid 12.2.0 源码](https://github.com/mermaid-js/mermaid/tree/1fb7869866dd619168d840291c9c54b4f129758b)，详细版本和关键 canonical Git blob 的 SHA256 见 [upstream.lock.json](upstream.lock.json)。[spec-inventory.json](spec-inventory.json)记录每个源文件的路径、Git blob ID 与类别；checkout 位于被忽略的 `.local/upstream-mermaid`。

```shell
python scripts/upstream.py fetch
python scripts/upstream.py check
```

命令在仓库根执行。`fetch` 只在 checkout 不存在时 clone 精确 tag，然后核 commit/版本/关键 SHA/干净状态；已有 checkout 不做 reset、pull 或覆盖。`check` 从锁定 Git tree 重建内存索引并比较已提交清单，发现漂移立即失败。

首次建立新基线时，`python scripts/upstream.py inventory` 可写入**不存在**的索引文件；日常不能删除旧索引再生成以掩盖变化。升级需新任务、保留旧基线、审阅范围并更新全部状态/对照证据。

索引覆盖全仓 `.spec/.test` JS/TS 文件、`e2e/**/*.mmd`、Jison/Langium grammar、syntax docs。包含示例/基础设施测试；不是全部独立 test case 的数量。M1 仍需拆开动态/参数化测试、多断言、fixture 配置和 snapshot。

37 个 core detector 文件由 `diagram-orchestration.ts` 的 import 清单提取；这不是运行时检测优先级，后者须审计 `addDiagrams` 中的实际注册调用顺序、构建开关和配置副作用。ZenUML 为独立外部插件，其包版本在 lock 单独记录。`error`/`---` 单独登记诊断。检测器是源码范围清单，Python 实现均未开始。

文件名索引也不是全部测试入口：锁定源码的 `diagrams/git/gitGraphParser.ts` 含内联测试。M1 应补查 `import.meta.vitest`、动态/参数化用例、snapshot 和其他公开行为，保留原索引并建立补充 assertion/source map。完整任务见 [实施方案](../docs/IMPLEMENTATION_PLAN.md)和 [M1 工作分解](../docs/TASKS.md)。

checkout 只读、不随 wheel 发布、不作 runtime fallback。复制或移植第三方代码时保留 upstream path/commit、MIT 版权和其他依赖许可；仅锁某个 package.json 不等于已审计其全部传递依赖。当前许可证原文见 [mermaid-LICENSE](licenses/mermaid-LICENSE)。
