> 2026-11-05 用户已决定 **完全剥离 Dagre 功能、配置选项、目标依赖和算法回退**，不再暂停待评估，也不作为可选兼容任务。默认 ELK 与其他保留的专用静态算法继续推进。见 [布局策略](LAYOUT_POLICY.md)；下文旧 Dagre 计划/来源说明以此覆盖。

> 2026-11-05 用户范围决策：**全部图种和共享模块只做静态渲染，忽略交互逻辑。** 点击/回调/悬停/导航/命中测试、动画播放、交互元数据与 DOM 无障碍行为不作为交付或验收项；静态画面、资源与输入安全保留。以 [静态范围规则](STATIC_RENDERING_SCOPE.md) 为准，覆盖本文旧交互要求。

> 2026-11-04 当前执行范围仅F01.1基础流程图，已实现接口见 [使用说明](F01_1_USAGE.md)，本地结果见 [验收记录](F01_1_ACCEPTANCE.md)。安装验证按用户最新要求暂缓，后续不继续或复跑。下方完整迁移范围和旧时序仅作后续规划/历史来源，当前以 [F01.1计划](F01_1_EXECUTION_PLAN.md) 为准。

# API 与 spec 兼容规则

本文定义最终应保持的行为，不规定测试必须先于源码。执行顺序采用用户最新 [完整方案](FULL_MIGRATION_PLAN.md)：P1 先全部功能源码，P2 来源测试/单测，P3 排查修复，P4 最终全量；旧 M1/M2 编号仅作历史范围追踪。

## spec 的含义

这里的 spec 同时指固定源码中的测试/断言、渲染 fixture，以及文档/grammar/config/default/style/renderer 定义的公开行为。不仅是 `.mmd` 语法解析成功或官网几张图。

[文件清单](../references/spec-inventory.json)只含源文件索引。M1 须拆分用例与断言：`id / upstreamPath / symbol-or-case / sourceHash / input / config / resources / expected / Python-entry / stage / evidence`。参数化测试、辅助生成器、负例、多断言和 snapshot 逐项定位，不用文件数作总测试数。

## 源码与默认行为

- 固定 Mermaid 12.2.0 commit；tag 和关键 SHA 在 lock。Node A 使用该官方基线，并记录 npm integrity、node/browser/字体、layout/plugin 版本。
- detect 顺序、别名、默认布局、frontmatter/directive/config 合并、themeVariables、CSS 优先级与错误从源码登记，不凭记忆实现。
- 本基线 schema 的根 `layout` 默认 `elk`；完整构建含 ELK，tiny 缺失时原实现回退 Dagre（仅来源事实，目标不迁移该回退）。Python 不能因 ELK 尚未实现而擅自改默认；目标已删除 Dagre 与算法回退，显式请求必须拒绝。detector 的实际注册调用顺序与 import 文件清单分别审计。
- JS 的缺省/undefined/null/false/0/空串、Number、日期/时区、Unicode/UTF-16 位置、异常条件建立明确 Python 映射；不能直接用 Python `len` 代替 UTF-16 索引。
- 每种 grammar 同时验证合法/非法/不完整输入、注释/转义、嵌套与恢复；错误行列和 side effect 留证据。

## Python 产品接口（设计草案，尚未实现）

计划先提供 `parse(text, *, config=...) -> Diagram` 与 `render(text, *, config=..., format=..., backend=...) -> RenderResult`，随后提供显式文件写出和 CLI。具体签名、类型、默认输出格式、异常层次和 async 契约在 M1 用例/宿主审计后确定，不把草案写成已可复制调用。

`Diagram` 将包含不可变语义和 source span；`RenderResult` 计划含 bytes、实际尺寸/MIME/backend、diagnostics 与元数据。底层 Canvas 不跨线程暴露；各 worker 内独立创建/测量/绘图/导出。产品不隐式下载字体、图标、JS 或远端图片。

## 浏览器宿主对应：必须逐项解决

用户已确认 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)：DOM/虚拟 DOM、D3 selection、浏览器布局与渲染调度等实现机制被替换，Python 不模拟这些 API。以下对应保留的是 Mermaid 的语义、图形表达和配置含义，不要求重现 DOM 树、操作次数或组件生命周期。具体功能缺口与视觉差异仍需记录和验证。

| 上游行为 | Python 移植要求 | 当前状态 |
| --- | --- | --- |
| SVG shapes/path/marker/clip/style | 直接产生 Canvas primitives；保留几何、锚点、层叠与 viewport | planned |
| SVG text 与 getBBox/getComputedTextLength | 同一声明字体，记录浏览器与 Canvas 测量/fallback 差异，逐断言核对 | planned |
| HTML foreignObject、Markdown、CSS | 将所需标签/换行/样式含义解析为 Python text runs/boxes 并用 Canvas 绘制；不建立 foreignObject、DOM 或通用浏览器 CSS 排版器，不默默丢失内容 | open functional mapping |
| KaTeX/math、图标/iconify、外部图像 | 固定依赖/许可和资源输入，定义离线表达或显式不支持，不能丢失内容 | open mapping |
| click/link、DOM callbacks、bindFunctions | 识别相应语法时安全忽略行为，不要求链接/回调/命中区域等交互元数据 | excluded_by_static_scope |
| securityLevel、sanitizer、URL policy | 保留 Python 标签/资源安全与恶意输入断言；不执行导航/脚本，不复刻 DOMPurify 的 DOM 操作机制 | planned |
| accTitle/accDescr、SVG metadata | 兼容保留既有纯值；只验证必要静态格式结构，不要求 DOM/ARIA、屏幕阅读器行为或新增无障碍导出协议 | static-only |
| handdrawn/rough 随机性、布局插件 | 保留 seed/算法/选项及依赖来源，未实现模式明确失败 | planned |

保留功能的不可等价项仍需记录；用户明确排除的纯交互断言保留来源并标为 excluded_by_static_scope，不计待迁移或通过。其他默认行为/兼容变更仍需用户决策。支持状态不能仅看方法是否存在。

完整宿主/source map/依赖工作分解见 [实施方案](IMPLEMENTATION_PLAN.md)和 [M1/M4 任务](TASKS.md)。测试入口还须包含 `import.meta.vitest` 等内联测试；现有文件名索引不代表全部 assertion 已被发现。

## 分层验收

用户已确定**功能一致，跨 DOM/Canvas 渲染不用完全像素一致**，具体判定以 [RENDER_CONSISTENCY](RENDER_CONSISTENCY.md)及其机器策略为准：

1. **功能/语义**：规范化 AST/model/config，核对节点边/分组、标签/公式内容、方向/约束、默认值、错误、安全和适用元数据。所保留功能必须一致，不以图片相似度替代。
2. **绘制结构**：将 A/B 映射为语义场景，核对实际绘制的元素、标签、箭头、资源和解析后样式；B 的 DisplayList 还要有真实 Canvas 输出证据，不只检查模型存在。
3. **几何关系/可读性**：核对端口/端点连接、图种方向/排序、分组包含、内容容纳/无意裁切、遮挡和显式尺寸约束。绝对坐标、节点自然尺寸、合理换行及路由可因引擎和字体度量不同而变化；纯算法单测仍按自己的数值契约验证。
4. **图像诊断/自身回归**：保存原始 A/B 图及诊断指标，跨引擎不要求像素零差或固定 SSIM。只有冻结环境且证明确定性的指定 Python 自回归用例可选择精确像素；不同 GPU/CPU/driver 不互为零差异基准。

P2 将规则和允许差异类别版本化，P3/P4 按功能与质量门禁判定。正常引擎差异记 `expected_renderer_variation`，可以通过；功能错误必须失败，无法解释的采集/视觉异常先复核或标未验。全量完成不要求所有像素差消失，仍要求全部必要功能/质量断言有终态证据，不隐藏失败或篡改原始图。

## Canvas 边界

`Canvas(w,h)` 默认策略保留；需要 CPU 时用 `canvas.gpu = False`，构造 options 中 `gpu:false` 不是已验证的禁用开关。`engine` 是状态记录，不独立证明每次 native 绘制路径。GPU-required、CPU/no-loader 和 owner 生命周期分别验收。

Windows 并行 PDF/SVG 文件序列继承 Canvas 已知非确定性；必要时记录显式 `RAYON_NUM_THREADS=1` 诊断，不改默认线程数或声称默认并发完全一致。系统字体不捆绑，不复制未知许可字体。
