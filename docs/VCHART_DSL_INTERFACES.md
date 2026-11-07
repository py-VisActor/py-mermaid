# VChart DSL v1 模块接线合同

2026-11-07，P1源码合同，**尚未完成行为验收**。完整语言规则见 [设计](VCHART_DSL_DESIGN.md)，阶段见 [执行计划](VCHART_DSL_EXECUTION_PLAN.md)。

## 纯语法与lowering

`parse_dsl(text) -> Node` 只做词法/语法，节点冻结且只含纯值；所有 `start/end` 为原始 Python code-point 半开区间。`document.children[0]` 为 `header`，其范围定位首行类型，document本身覆盖全文。

| Node.kind | value | children |
|---|---|---|
| header | 类型字符串 | 空 |
| literal | JSON标量 | 空 |
| array | None | 值节点 |
| object | None | member节点 |
| member | 原始字符串键 | 单个值 |
| reference | let名称 | 空 |
| table | 列名tuple | 行array节点 |
| assignment | 路径tuple[str/int] | 单个值 |
| group | 路径tuple | 属性语句 |
| let | 名称 | 单个值 |
| size | None | 两个数值literal |
| axis / series | orient / type | 属性语句 |
| resource | (map/svg, 名称) | 单个值 |

`lower_dsl(text, ast=None) -> LoweredVChart` 进行确定性编译，不导入图表/Canvas模块。输出：`spec_json`、`maps_json`、`svgs` tuple、`source_map` tuple、`diagnostics` tuple。字典成员插入顺序必须保留；禁止对帧数据排序。变量展开独立复制并计预算，禁止重绑/前向引用。属性路径和整体赋值拥有关系、连续索引与追加模式严格按RFC处理。

`SpecSpan(path,start,end,namespace='spec',declaration_start=None,declaration_end=None)` 的 namespace 为 spec/map/svg。引用后的路径指向本次 `$use`，并关联直接 let 完整声明范围；不冒称生成JSON位置为原始位置。

`dsl_error(...)` 返回既有 `MermaidError`，主 `SourceSpan` 使用现有1-based行与0-based UTF-16列/偏移合同；附加 `spec_path` 和纯CP `(start,end)` pairs形式的 `related_spans`。JSON编译检查对没有可靠字段路径的provider错误只给可靠范围和真实消息。

预算在建AST/展开时检查：源8MiB、深度/路径128、值节点1,000,000；流式lexer和有限token预算避免先构造无限token列表。资源/序列化大小仍受既有bridge限制。所有失败必须有明确异常，不能返回空spec或默认图冒充成功。

## 公共入口与资源

`compile_vchart(text, *, config=None, maps=None, svgs=None)` 返回冻结 `VChartCompilation`。保留 `Diagram.model` 为 `VChartModel`，新增字段均有兼容默认值：inline资源JSON/tuple、source_map、diagnostics、syntax。旧Python对象API直接走原spec模型，不经过DSL。

编译结果提供 `spec()`、`maps()`、`svg_sources()` 独立副本、尺寸/模式属性及 `as_dict()`；字典输出包括完整 `spec/maps/svgs/source/source_map/diagnostics` 和基础验证范围说明。来源映射的序列化编码明确为 code-point，不能将其误称为全量UTF-16坐标。

编译不调用render、Canvas、FontLibrary或测量。VChart公开构造器可验证显式地图/SVG的纯资源快照；这不代表所有图种字段已通过实际绘制验证。资源与外部API参数同种同名冲突时明确拒绝，即使字节相同。图像/字体仍使用已有显式资源入口。

CLI `--compile` / `--compile-only` 输出完整检查JSON，`-o` 保存该JSON；`--vchart-maps` / `--vchart-svgs` 保留。该模式显式拒绝渲染专用 `--resources` / `--metadata`，避免遗漏资源或意外加载字体；实际渲染和导出参数仍走现有命令。输出不能覆盖任一输入/资源配置文件。

模式标识为 `json` / `dsl`，结构schema版本为 `/v1`；语言版本仍为DSL v1。首行单独 `vchart` 保持严格JSON解析，带类型首行走新DSL，禁止错误后回退到其它图种。固定300×300的pixel序列图保留请求spec并给可检查诊断。

## 验证分工

P1只编译/导入/签名等机械检查。全部源码完成后，A独立编写词法/语法/source位置/预算测试，B编写lowering/写入/引用/条件测试，C编写API/CLI/资源/纯编译与兼容测试；root编写225规格/68类型来源对照、三后端、导出、安装和分页报告工具。P3首跑前全员停止产品/测试/工具写入，保留全部分组失败后集中修复。
