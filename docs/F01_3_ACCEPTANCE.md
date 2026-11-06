# F01.3 本地验收记录

2026-11-05，本切片完成，状态 **PASS_LOCAL**。已实现前处理、frontmatter/directive、配置层级、11 个主题及字符串 `"null"` sentinel、HTML/Markdown 节点/边/子图标签、图标题和适用原生样式。固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`；未提升完整 flowchart 或其他图种兼容状态。

[打开 HTML 对比报告](http://127.0.0.1:8765/F01.3-render-20261105T022709Z-575768e1/index.html) · [本地报告](../reports/F01.3-render-20261105T022709Z-575768e1/index.html) · [机器汇总](../references/f013-verification-summary.json) · [使用说明](F01_3_USAGE.md)

## 最终同一候选

产品源码/元数据/许可指纹：`5cb792fadbd7685a0d65a4a4d0e397ff59566eae340f4aaa87d0a7041d18b08f`。完整测试与三组 A/B 均 `sourceUnchanged=true`，所有证据文件完整性核验通过。CPython 3.13.15、Canvas 0.1.0a18、py-visactor-elk 0.1.0，现有 Windows 环境；CPU 显式禁用 GPU，auto/GPU 实际为 NVIDIA GeForce RTX 5080 / Vulkan。

| 测试组 | 方法数 | 结果 |
| --- | ---: | --- |
| f011-language | 39 | PASS |
| f011-layout | 21 | PASS |
| f011-canvas | 23 | PASS |
| f011-api | 5 | PASS |
| f012-language | 29 | PASS |
| f012-layout | 19 | PASS |
| f012-canvas | 18 | PASS |
| f013-language | 62 | PASS |
| f013-layout | 14 | PASS |
| f013-styles | 16 | PASS |
| f013-canvas | 33 | PASS |
| tooling | 25 | PASS |

合计产品 **279** 项、工具 **25** 项，共 **304** 项通过。只按方法计数，不重复计算方法内参数子例。测试记录：`test-runs/F01.3-batch-20261105T022709Z-dcd8b609/run.json`。渲染 run 的 `tests=null` 仅表示其批次没有执行单测，单测证据在上述独立批次；不能用报告生成或像素工具退出码替代功能结果。

| A/B 分母 | CPU | auto | GPU-required |
| --- | --- | --- | --- |
| F01.3：50 正例 / 8 语法负例 / 6 范围外诊断 / 1 上游渲染缺陷 | PASS | PASS | PASS |
| F01.2 回归：35 正例 / 8 语法负例 / 1 上游渲染缺陷 | PASS | PASS | PASS |
| F01.1 回归：12 正例 / 3 语法负例 | PASS | PASS | PASS |

本轮三组原始证据分别位于 `test-runs/F01.3-render-20261105T022709Z-575768e1/artifacts`、`test-runs/F01.2-render-20261105T022709Z-f9ad5a6b/artifacts`、`test-runs/F01.1-render-20261105T022709Z-7fdedf49/artifacts`。范围外案例只做官方 parse 与 Python 明确诊断，未渲染 Dagre/新 shape 等暂停功能。

## 真实绘制与报告

核对语义内容/标签种类、配置派生与请求隔离、原文 UTF-16 定位、真实文字 run/颜色/字体与 PNG、节点和子图包含、图标题锚点/墨迹、边/箭头、空富文本标签及安全清洗。白图、漏绘、错内容/格式/关系、反箭头和裁剪负控有效；细线抗锯齿与正常通道变化允许存在。

HTML QA 遍历 F01.3 的 **150** 个正例/后端选择及 **15** 类错误展示，核对原始图片尺寸/内容、并排/叠加/差异模式、桌面与移动布局，无脚本错误或外部请求。记录 `test-runs/f013-html-qa-final-002/report.json`；F01.2/F01.1 报告分别 105/36 次正例选择也通过。已人工查看最终综合 A/B、Unicode 标题、GPU 深色主题、实际示例及桌面/移动截图。PNG 原始字节未修改，图像尺寸/字体与合法 ELK 路由差异作为诊断保留。

## 首轮失败与修复

- 原始候选和失败测试在首次修复前保存于 `test-runs/F01.3-initial-evidence-snapshot-20261105T021024Z-38c90a72`。修复 YAML 数字与块标量分支、配置合并、Markdown 定位/闭合、SVG 标签词间隔、零宽边标签输出、标题隐藏与 CSS unset。相关记录见 [总记录](changes/20261105-f013-execution.json) 及各模块 change/source map。
- 原 neo 阴影与默认 inline-style 的部分测试预期错误，已按固定来源和官方 computed style 更正；保留原错误断言与失败，未修改官方输出。比较工具另修复部分 shape 覆盖、富文本多背景、行边界及薄线颜色覆盖判断。
- 自动检查通过的旧候选 `5f3a058baf1157c7b9cc8cabbe0aad9644044875262ec5ee7c3babcd1a5fd9ac` 在人工看图时被判失败：Canvas 将 `italic normal` 的后一个 normal 当作样式重置，实际绘制直立文字。共享原生字体入口将 normal/bold 字重规范为 400/700；使用独立 literal `italic 400` 像素正参考和 normal400 负控覆盖节点/边/组，并独立核对 bold700/italic700。没有复制或修改 Canvas 核心，没有安装字体。所有最终验证均在新候选重新执行，未沿用旧候选的通过结论。
- Windows 临时 manifest 共享锁增加有限原子替换重试，持久错误仍抛出；新增故障测试。首次示例缺少 PYTHONPATH、错误 probe 及旧候选日志均保留，修正后使用新 run。

## 保留边界

根方向仍 TD/LR，经典形状 14 种；上游 ellipse 能解析但缺少渲染处理器，单独报告 `UPSTREAM_SHAPE_MISSING`。Markdown 保留上游实际 token 行为，SVG 路径忽略部分 token 时给出诊断，不宣称完整 CommonMark。浏览器表单控件、资源、数学、保留 stylesheet 元素、浏览器专用 sanitizer 选项等明确拒绝；生产不使用 DOM、JS 或浏览器 fallback。研发 sandbox 截图只展开并保存原始 SVG/iframe 包装证据。

**F01.4 与 Dagre 保持暂停，等待重新评估。** 现有 ELK 不冒充 Dagre；新 shape、其他边类型、style/class/linkStyle、手绘与资源/导出扩全不属于本轮。安装验证按要求 **未执行**，未重新安装、构建或发布包；Linux/no-loader 未验。**本轮未 commit/push。**
