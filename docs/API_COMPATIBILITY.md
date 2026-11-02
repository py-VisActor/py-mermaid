# API 与 spec 兼容规则

## spec 的含义

这里的 spec 同时指固定源码中的测试/断言、渲染 fixture，以及文档/grammar/config/default/style/renderer 定义的公开行为。不仅是 `.mmd` 语法解析成功或官网几张图。

[文件清单](../references/spec-inventory.json)只含源文件索引。M1 须拆分用例与断言：`id / upstreamPath / symbol-or-case / sourceHash / input / config / resources / expected / Python-entry / stage / evidence`。参数化测试、辅助生成器、负例、多断言和 snapshot 逐项定位，不用文件数作总测试数。

## 源码与默认行为

- 固定 Mermaid 12.2.0 commit；tag 和关键 SHA 在 lock。Node A 使用该官方基线，并记录 npm integrity、node/browser/字体、layout/plugin 版本。
- detect 顺序、别名、默认布局、frontmatter/directive/config 合并、themeVariables、CSS 优先级与错误从源码登记，不凭记忆实现。
- 本基线 schema 的根 `layout` 默认 `elk`；完整构建含 ELK，tiny 缺失时按上游规则回退 Dagre。Python 不能因 ELK 尚未实现而擅自改默认；显式 Dagre 原型不能作为默认布局验收。detector 的实际注册调用顺序与 import 文件清单分别审计。
- JS 的缺省/undefined/null/false/0/空串、Number、日期/时区、Unicode/UTF-16 位置、异常条件建立明确 Python 映射；不能直接用 Python `len` 代替 UTF-16 索引。
- 每种 grammar 同时验证合法/非法/不完整输入、注释/转义、嵌套与恢复；错误行列和 side effect 留证据。

## Python 产品接口（设计草案，尚未实现）

计划先提供 `parse(text, *, config=...) -> Diagram` 与 `render(text, *, config=..., format=..., backend=...) -> RenderResult`，随后提供显式文件写出和 CLI。具体签名、类型、默认输出格式、异常层次和 async 契约在 M1 用例/宿主审计后确定，不把草案写成已可复制调用。

`Diagram` 将包含不可变语义和 source span；`RenderResult` 计划含 bytes、实际尺寸/MIME/backend、diagnostics 与元数据。底层 Canvas 不跨线程暴露；各 worker 内独立创建/测量/绘图/导出。产品不隐式下载字体、图标、JS 或远端图片。

## 浏览器宿主对应：必须逐项解决

| 上游行为 | Python 移植要求 | 当前状态 |
| --- | --- | --- |
| SVG shapes/path/marker/clip/style | 直接产生 Canvas primitives；保留几何、锚点、层叠与 viewport | planned |
| SVG text 与 getBBox/getComputedTextLength | 同一声明字体，记录浏览器与 Canvas 测量/fallback 差异，逐断言核对 | planned |
| HTML foreignObject、Markdown、CSS | 盘点标签/换行/继承/box model，建立受控 Python 排版，不默默剥成纯文本 | open mapping |
| KaTeX/math、图标/iconify、外部图像 | 固定依赖/许可和资源输入，定义离线表达或显式不支持，不能丢失内容 | open mapping |
| click/link、DOM callbacks、bindFunctions | 静态输出携带链接/交互元数据，明确 Python 接口与不可等价项 | open mapping |
| securityLevel、sanitizer、URL policy | 拒绝脚本执行，建立输入/资源策略和恶意输入断言 | planned |
| accTitle/accDescr、SVG metadata | 语义模型保留；按导出格式登记元数据，不伪称 PNG 有 DOM accessibility tree | planned |
| handdrawn/rough 随机性、布局插件 | 保留 seed/算法/选项及依赖来源，未实现模式明确失败 | planned |

不可等价项保留在分母；改变默认行为或降低兼容标准需用户决策。支持状态不能仅看方法是否存在。

完整宿主/source map/依赖工作分解见 [实施方案](IMPLEMENTATION_PLAN.md)和 [M1/M4 任务](TASKS.md)。测试入口还须包含 `import.meta.vitest` 等内联测试；现有文件名索引不代表全部 assertion 已被发现。

## 分层验收

1. **语法/配置/语义**：规范化 AST/model、节点边/属性/默认值、错误与 source span；字段和数字按明确单位精确检查，不遗漏未知字段。
2. **布局/绘图语义**：节点/组边界、路由控制点、label box、marker 端点、层叠与 style；相同输入/字体/选项比对，禁止样例坐标补偿。
3. **渲染输出**：官方 browser PNG 与 Python Canvas 分别记录原始 RGBA、尺寸、字体/driver、差异图和数量。文本/抗锯齿链不同，不能预先保证天然逐像素相同；报告完整差异，不擅自设容差或把近似称完全兼容。
4. **稳定与导出**：同后端 Python 确定性回归要求精确像素；PDF/SVG 同一指定栅格器另验，字体/文本/页/viewport/metadata 结构独立检查。GPU/CPU 分组，不以不同 backend 图片互为零差异 oracle。

验收 profile 和未等价标准在 M1/M2 固定。全量完成要求全部断言有终态证据、跨图能力有契约、图像已审阅且无被隐藏的差异；不能只用 SSIM 或人眼判断覆盖完整 spec。

## Canvas 边界

`Canvas(w,h)` 默认策略保留；需要 CPU 时用 `canvas.gpu = False`，构造 options 中 `gpu:false` 不是已验证的禁用开关。`engine` 是状态记录，不独立证明每次 native 绘制路径。GPU-required、CPU/no-loader 和 owner 生命周期分别验收。

Windows 并行 PDF/SVG 文件序列继承 Canvas 已知非确定性；必要时记录显式 `RAYON_NUM_THREADS=1` 诊断，不改默认线程数或声称默认并发完全一致。系统字体不捆绑，不复制未知许可字体。
