> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

# Mermaid 第三方依赖盘点

2026-11-04，依据本仓库锁定的 **Mermaid 12.2.0**，commit `1fb7869866dd619168d840291c9c54b4f129758b`。审计输入为只读 `.local/upstream-mermaid` 的五个产品包、根工作区清单、`pnpm-lock.yaml`、补丁和源码 import。这里的版本均为该锁文件的实际解析版本，不是在线最新版。

本次完成依赖分类与静态盘点，未实现 Python Mermaid 功能，也未完成 M1-06 的全部宿主、资源和许可审计。机器清单见 [dependencies.json](../references/dependencies.json)，来源身份见 [upstream.lock.json](../references/upstream.lock.json)。

后续补充已落地：[完整依赖树与 Python 迁移方案](DEPENDENCY_MIGRATION.md)覆盖所有工作区及锁定节点，并把额外源码值导入的传递链补入产品视图；完整树和底层逐节点索引不再局限于本文的 344 个声明闭包节点。Python 候选与内部算法拆分见该方案。

目标依赖处理现按用户确认的 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)：本文列出的是上游真实依赖，不是 Python 必须逐个迁移的库。DOM、D3 selection、fastdom、React 浏览器层、CSS 注入/DOM 清洗机制淘汰；所需图形和安全语义由 Python 模型/样式与 Canvas 实现。

## 1. 核心包的 23 项直接声明

`packages/mermaid/package.json` 的 `dependencies` 共 23 项，包含 1 个同仓库 parser 和 1 个类型声明包。声明在此字段中不等于全部进入每种发行 bundle。

| 包 | 锁定版本 | 主要职责及 Python 迁移边界 |
| --- | --- | --- |
| `elkjs` | 0.9.3 | ELK 图布局、端口/分组/路由；按用户决定接入独立 `py-elk`，接入尚未实施 |
| `dagre-d3-es` | 7.0.14 | Dagre 分层布局、内部 graphlib、D3 渲染辅助；原源码用途；目标 Dagre 功能与依赖已排除 |
| `d3` | 7.9.0 | 数据处理、比例尺、轴、弧/曲线、层级/力导向及 SVG/DOM 操作；保留所用计算语义，绘制映射到 Canvas |
| `d3-sankey` | 0.12.3 | Sankey 节点/流量/连线布局 |
| `cytoscape` | 3.34.0 | 图模型与布局基础，architecture 等使用 |
| `cytoscape-cose-bilkent` | 4.1.0 | COSE-Bilkent 复合图/力导向布局 |
| `cytoscape-fcose` | 2.2.0 | architecture 等使用的 fCoSE 约束布局 |
| `@upsetjs/venn.js` | 2.0.0 | Venn 集合区域布局/几何 |
| `@mermaid-js/parser` | workspace 2.0.1 | 同仓库语言解析器，不能计作第三方算法库 |
| `chevrotain` | 13.2.0 | 词法/语法解析基础 |
| `@types/d3` | 7.4.3 | TypeScript 类型；不需要给 Python 新增对应运行依赖 |
| `dayjs` | 1.11.21 | 日期/时间处理，尤其 Gantt 等；格式、时区、locale 边界需保留 |
| `marked` | 16.3.0 | Markdown 标签解析 |
| `katex` | 0.18.11 | 数学排版及字体/资源；Canvas 普通文本 shaping 不能直接代替数学布局 |
| `roughjs` | 4.6.6 + patch | 手绘路径/填充、随机状态；路径生成后交给 Canvas 绘制 |
| `khroma` | 2.1.0 | 颜色运算与主题派生 |
| `stylis` | 4.3.6 | CSS 解析/编译；需映射到 Python 样式与宿主排版 |
| `@iconify/utils` | 3.0.2 | 图标数据、SVG 与资源辅助；实际图标包/字体需另查来源和许可 |
| `@braintree/sanitize-url` | 7.1.2 | URL 安全处理 |
| `dompurify` | 3.4.12 | HTML/SVG 清洗及安全策略；Canvas 输出仍须定义输入、链接和资源安全语义 |
| `es-toolkit` | 1.45.1 | 集合/对象等通用工具；注意值、复制、合并语义 |
| `ts-dedent` | 2.2.0 | 多行文本缩进处理 |
| `uuid` | 14.0.0 | ID 生成；输出稳定性和随机边界需纳入测试 |

机器清单保留声明范围、实际解析版本、peer 上下文和补丁 hash。例如 KaTeX 声明 `^0.18.0` 实际锁到 `0.18.11`；UUID 的多版本范围实际锁到 `14.0.0`；不能只记录 package.json 中的下限。

## 2. 解析器和三个扩展包

| 同仓库包 | 包版本 | 额外依赖/边界 |
| --- | --- | --- |
| `@mermaid-js/parser` | 2.0.1 | 声明依赖 `@chevrotain/types` 13.2.0；开发字段还有 Chevrotain、Langium，后者有真实值导入 |
| `@mermaid-js/layout-elk` | 1.0.1 | D3、dagre-d3-es、dayjs、DOMPurify、elkjs、KaTeX；peer 为 Mermaid。为需要外部加载 ELK 的构建提供插件 |
| `@mermaid-js/layout-tidy-tree` | 1.0.1 | D3，加上实际调用的 `non-layered-tidy-tree-layout`；peer 为 Mermaid |
| `@mermaid-js/mermaid-zenuml` | 1.0.1 | `@zenuml/core` 声明 `^3.47.9`，实际锁到 **3.49.2**；需单独迁移 grammar/model/layout/render |

五个同仓库包清单的 license 字段均为 MIT；这不是所有传递第三方包的许可结论。

## 3. 不能按 devDependencies 字段直接排除的包

| 包 | 锁定版本 | 源码证据与影响 |
| --- | --- | --- |
| `js-yaml` | 4.3.0 | 根工作区 devDependency，但 `mermaid/src/diagram-api/frontmatter.ts:4` 有真实导入，并调用 `yaml.load`/`yaml.JSON_SCHEMA`；其他图种也有导入。Python YAML 默认 schema 不能直接认定等价 |
| `langium` | 4.4.0 | parser 的 devDependency，但 `parser/src/language/*/module.ts` 有实际值导入；解析器服务与生成代码语义需要审计 |
| `non-layered-tidy-tree-layout` | 2.0.2 | tidy-tree 的 devDependency，但 `mermaid-layout-tidy-tree/src/layout.ts:3` 实际导入 `BoundingBox`、`Layout` |
| `fastdom` | 1.0.12 + patch | Mermaid 的 devDependency；`mermaid/src/rendering-util/fastdom.ts:2–3` 实际导入，分离 measure/mutate，优先使用 `queueMicrotask`，否则 `setTimeout`；Python 需明确测量/写入阶段与所有权 |

以上路径均相对上游 `packages/`。`.esbuild/util.ts` 还表明：full 构建会打包依赖，core 构建将声明 dependencies/peerDependencies 外置；tiny 通过构建开关裁剪大型特性。因此静态字段、源码引用与实际 bundle 需要分开看。

构建与验证另有 Jison 0.4.18、Langium CLI 4.4.0、TypeScript/esbuild、Vitest、浏览器/E2E、文档站工具。Jison/Langium CLI 参与生成解析器；这些 JS 工具不能成为 Python 产品运行依赖。具体工具配置仍以锁定根 package.json、`.build/` 和 `.esbuild/` 为准，本次没有把整个 monorepo 开发链当成产品运行依赖。

静态扫描还发现 `@iconify/types`、`d3-selection`、`type-fest` 的类型导入。`rendering-util/layout-algorithms/ddlt/baselineDdltSpec.ts` 虽不符合常规 `.spec.ts` 命名，仍是测试，扫描中的 Vitest 候选不表示产品需要 Vitest。`import.meta.vitest` 内联测试同样需要按构建处理。

## 4. 重要传递依赖与补丁

- `cytoscape-cose-bilkent@4.1.0 → cose-base@1.0.3 → layout-base@1.0.2`。
- `cytoscape-fcose@2.2.0 → cose-base@2.2.0 → layout-base@2.0.1`。两套版本共存，不能合并成一个未经验证的实现。
- `dagre-d3-es@7.0.14 → d3@7.9.0 + lodash-es@4.18.1`。graphlib 是该包内的源码路径，不是 Mermaid 另行声明的 `@dagrejs/graphlib`。
- D3 下有 array、shape、path、hierarchy、force、scale、selection 等分包；Sankey 等路径还引入较旧版本，不能仅用 `d3@7.9.0` 概括全部数值行为。
- `@zenuml/core@3.49.2` 的锁定闭包包含 React 19.2.5、Babel 等；ZenUML 不是只加一个语法文件即可迁移。
- Langium 的解析链含 Chevrotain、chevrotain-allstar 等；其 dev 字段来源与下面的声明生产闭包分开记录。
- `roughjs.patch` 仅调整类型默认导出形式；`fastdom.patch` 涉及 ESM 导出及类型声明。机器清单保存补丁全文与 SHA，不把类型/模块补丁描述成几何算法修改。

五个包的声明生产依赖遍历得到 **344 个 pnpm snapshot 上下文节点，未解析边为 0**。该数包含声明的类型包、可选依赖和具体 peer 上下文，既不是 344 个唯一包名，也不是实际 bundle 的最小运行清单，更不是需要新增的 Python 依赖数量。上节 dev 字段中的额外值导入不自动计入此闭包。

锁文件 registry integrity 已按节点关联到清单；本次没有下载并验证第三方 tarball，也没有读取每个包内的许可证。传递依赖、字体、图标、数学资源的许可与再分发审计继续保留为未完成项。

## 5. Python 侧的处理顺序

当前 `pyproject.toml` 唯一生产依赖仍是 **`py-skia-canvas==0.1.0a18`**。它负责底层文字 shaping、路径绘制、图像和编码；图语法、布局算法、Markdown/HTML/math 排版及安全语义仍需上层实现。

按用户决定，ELK 使用独立 `py-elk` 项目，已发布的 Python 分发名为 `py-visactor-elk`，版本 0.1.0。Mermaid 当前锁定 `elkjs@0.9.3`，py-elk 的迁移基线为 0.12.1；记录这一来源差异，用单独的 Mermaid 适配步骤检验图模型/选项/端口/标签/路由，不要求 py-elk 回退旧版本。**py-mermaid 尚未添加该依赖或完成接入。**

后续实现依赖可按以下顺序展开；这不是本次新增的实现：

1. 预处理、frontmatter、安全/配置和解析器：固定输入、错误与模型边界。
2. 标签测量、默认 ELK 的 py-elk 适配和 Canvas 最小真实输出，支撑 M3 flowchart。
3. 自有图模型、D3 所用计算、COSE/fCoSE、tidy、Sankey、Venn，按实际图种依赖展开。
4. Markdown/HTML/CSS/math、RoughJS、图标/字体/资源、主题等共享能力逐项扩全。
5. ZenUML 独立审计与迁移；最终统一验证完整产品和打包运行依赖。

## 6. 复核方法与限制

在仓库根目录执行；首次获取源码用现有的 `upstream.py fetch`，已有 checkout 不会被本工具重置：

```shell
python scripts/upstream.py fetch
python scripts/audit_dependencies.py --check
python -m unittest discover -s tests/dependencies -v
```

审计脚本只需 Python 标准库和 Git，不安装 npm 包、不联网、不执行 Mermaid/JS 或 Python 产品代码。先验证源 commit、干净工作区及锁中关键 canonical blob SHA，再比较清单；从 canonical Git blobs 扫描源码，避免 Windows CRLF 导致指纹漂移。修改清单、源清单或 Python 声明依赖后，`--check` 会在与已保存内容不符时失败。

首次生成或明确审阅过的清单更新使用 `python scripts/audit_dependencies.py --build`；该命令会重写清单，不用于消除未调查的漂移。关键锁输入发生变化仍须遵守基线升级规则，不能改 SHA 来掩盖变化。

pnpm 读取器只支持本固定 v9 锁文件需要的 mapping/scalar 结构，不是通用 YAML 库；重复键、未解析依赖边等会失败。字面 import 扫描不是完整 TypeScript AST、tree shaking、生成代码或动态 import 可达性分析，保留了 `type_only` 与 `value_or_mixed_candidate` 标记。正式 bundle、第三方 tarball 和许可证 SBOM 需要后续独立证据。本次结果不提升任何 Mermaid spec 兼容状态。
