# F01.1 基础流程图：本地交付记录

2026-11-04。当前范围仅基础流程图，完整Mermaid迁移仍为后续规划。用户最新要求“先不要做安装验证”，后续不继续或复跑该项。指令到达前已有的隔离安装及检查结果保留为历史记录。

## 已完成内容

支持flowchart/graph、TD/LR、矩形、普通文字、有向边与箭头、单节点/链/分支/合流；真实Canvas测量、默认py-elk布局、默认外观、PNG输出、源位置与明确错误、状态隔离。公开接口为parse/render/arender，示例为 `examples/basic_flowchart.py`。

默认外观按固定上游图种级redux-color/neo解析，包含14px有效字体、白矩形、深色边框/文字、黑边/箭头、最小标签宽120、换行宽120、16/12 padding和4px阴影。站点值与有效值区分保存。

## 已有验证结果

| 项目 | 实际结果 |
| --- | --- |
| 语言与配置 | 36个测试方法通过，含参数子用例，不冒称上游全部case |
| 几何与真实ELK | 21个测试方法通过，含输入/损坏输出、取消与worker关闭控制 |
| Canvas/标签/生命周期 | 23个测试方法通过，含真实PNG内容、阴影、线程所有权和设备策略 |
| 公开API | 5个测试方法通过，含async真实渲染和无native分配的import |
| 官方对照 | 12个正例、3个非法输入；CPU/auto/GPU三个profile均通过，来自同一wheel |
| 比较器控制 | 白图、漏节点/文字/边/箭头、错内容/关系、反向箭头与裁切被拒；正常单通道变化允许通过 |
| 资料保护 | 12项bootstrap负控制通过，上游来源和长期任务图检查通过 |
| 图片审阅 | 分支/合流、Unicode/emoji、长标签及GPU原始图已直接审阅，内容完整、可读、无裁切 |

上述85项测试及三种profile运行结果均在用户最新安装验证指令到达前产生，不会因安装验证暂缓而重复运行。图片不要求跨浏览器/Canvas像素相等；原始差异保留用于诊断。

## 来源、候选与证据

可视化入口：[离线HTML渲染对比报告](../reports/f011-render-comparison.html)。汇总已有12个正例、3个非法输入和CPU/Auto/GPU结果，支持并排/叠加/热图/掩码、原图下载及来源查看。报告生成未运行产品或安装验证，PNG保持已有原始字节。报告输入和自身指纹见 `reports/f011-render-comparison.manifest.json`。

Mermaid12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`，Canvas0.1.0a18，py-visactor-elk0.1.0；Windows AMD64 / CPython3.13.15。官方npm产物与固定Git canonical源码进行身份核对，Jison使用0.4.18按上游构建转换核对，浏览器156.0.8078.76，GPU为NVIDIA RTX5080/Vulkan。

候选wheel：`dist/f011-20261104/py_mermaid-0.0.1a0-py3-none-any.whl`。

SHA256：`b5fee226f8eba18b659bcdf38c978320b494a8ed4f8652475a4167433d7a25e4`。

原始证据目录：

- `test-runs/f011-s5-final-001/`：同候选85项日志、CPU/auto/GPU比较报告、依赖/字体身份、包清单、原始PNG和诊断报告。
- `test-runs/f011-s5-official-001/`：官方语义、SVG、PNG、样式/几何、错误和来源身份。
- `test-runs/f011-s4-official-001/`、`002/`：原始注释差异失败，保留不覆盖。
- `test-runs/f011-s4-language-fix-20261104T133941Z/`、`f011-s4-language-theme-fix-20261104T134306Z/`、`f011-s4-canvas-defaults-001/`：根因修复及定向回归。
- `docs/assets/f011-manifest.json`：六张真实样例图的原始字节、尺寸和源码来源指纹。

初版指纹工具把生成的egg-info算入源清单；构建后这些缓存变化，修正清单只包含真实产品源/元数据，保留原manifest及更正说明。wheel字节和被测产品源未改变，无需重跑产品测试。隔离检查初版探针错误阻止了Windows asyncio本地self-pipe；修正后仅放行标准库loopback，仍禁止外部网络、开发源码读取和Node/browser。旧探针失败保留，产品未因探针修改。

## 支持限制和暂缓事项

边标签、子图、其他形状、富标签/数学、其他主题/look、其他布局和非PNG输出明确拒绝，详见 [使用说明](F01_1_USAGE.md)。字体不捆绑，记录候选fallback文件身份，不宣称完整字形解析路径已追踪。

Linux、no-loader、完整Mermaid兼容及native全路径追踪未验收。安装验证按最新指令暂缓；已有历史记录不代表新增授权。不执行commit、push、远端CI、Release或PyPI发布。本轮源码和本地构建交付不等同发行发布。
