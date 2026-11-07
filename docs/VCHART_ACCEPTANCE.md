# VChart 发行与接入验收

2026-11-07。本轮已完成 py-vchart GitHub 正式发行及 py-mermaid 静态接入；PyPI 已正式发布，py-mermaid 已切换正式版本依赖；[发布补证](VCHART_PYPI_PUBLICATION.md) 另行绑定新渠道安装和元数据。[分页对比报告](http://127.0.0.1:8765/VCHART-P5-delivery-20261107T045848Z-3903b480/index.html) 已上线；[机器汇总](../references/vchart-verification-summary.json) 绑定全部独立证据。

## 实际交付

- 供应方：[py-visactor-vchart 0.1.1 正式发行](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.1)，源码提交 `ff16c91d38ab61e57d03b58579d5bf1beb2a1840`；正式文件不覆盖、不移动 tag。精确文件、SHA 与安装渠道见 [release lock](../references/vchart-release-lock.json)。
- 消费方：`render_vchart`、`arender_vchart`、`vchart` JSON 文本和 CLI，支持供应方全部 68 个实际注册二维静态类型。`supported_vchart_types()` 返回完整清单。
- Mermaid 语法：pie、quadrantChart、xychart、radar、treemap、sankey、venn 恢复接线，通过正式依赖公开布局 API 实现静态绘制。离线 maps/SVG/图片/字体资源按请求隔离。
- 格式与后端：PNG/JPEG/WebP/SVG/PDF；本机真实 CPU、auto、GPU。默认生产路径使用公开 Canvas API，不依赖 Node、浏览器或 skia-python，也不读取相邻仓库源码。

## 最终同候选证据

最终运行：`test-runs/VCHART-P4-batch-20261107T045154Z-dd03474c`，SUCCESS，两侧源码运行期均未改变。消费者源码 SHA-256：`756a21de6e1845dd81ab9d6ca7e08a84c8e8190e9d7ec03312cc923e872d6dc3`。

| 验证 | 实际结果 |
|---|---|
| 单元与既有回归 | 2283 方法通过：供应方 67、接入 156、旧 11 组 2060 |
| 原生 VChart | 固定 225 输入 × CPU/auto/GPU，覆盖 68 类型 |
| 旧 reference | 225 例严格门禁保持，通过 |
| Mermaid 规格 API | 68 类型实际绘制、来源内容/图元核对 |
| 七类语法 | 42 输入 ×三后端：30 渲染、10 原语法拒绝、2 明确原生限制 |
| 多格式 | 供应方每类型代表五格式；七语法每类型代表四种附加格式，三后端分别 28 文件 |
| 实际看图 | 30 张最终 CPU 原图逐张查看；原版同 SHA 图片绑定先前实际查看收据，GPU/auto 只作哈希关联 |
| 消费方安装 | wheel、sdist 两个全新仓库外环境，正常解析正式 wheel，68 类型、数学、实际 ELK、SVG/PDF 通过 |
| 供应方 CI | Windows/Linux × Canvas a18/a19，四组验证成功；wheel/sdist 共八次独立安装，每次 225 例和 36 项原生/负控方法 |

消费者源码、测试与脚本完整字节归档于最终运行的 `artifacts/consumer-candidate.zip`，SHA-256 `918725d99373fccb42a07361b10681dae1f47896a511e5edae0a4d780d7c5a31`；每项文件指纹另存 `consumer-candidate.json`。后处理工具在交付运行中另行归档。

最终人工收据：`test-runs/vchart-visual-review-final-20261107T045500Z.json`，结论 `PASS_WITH_DOCUMENTED_SOURCE_DIFFERENCES`。修复了 Pie 标题基线、Quadrant 默认无效颜色继承、XY 柱宽、Treemap 父色/透明度与文字样式、共享粗曲线描边边界。原版三例 Treemap 透明叶白字实际不可见；本端仅在缺失父填色时回退普通文字色，保留显式样式，让标签和值可读，未放宽实际墨迹门禁。

独立安装运行：`VCHART-INSTALL-wheel-20261107T045110Z-b3e13278` 与 `VCHART-INSTALL-sdist-20261107T045143Z-d4d79369`；两者源 SHA 与最终候选一致，VChart 未预装，由正常解析器下载正式 GitHub wheel 并核 SHA。供应方 [CI 42337813981](https://github.com/py-VisActor/py-vchart/actions/runs/42337813981) 原资产已按 GitHub API 的 ZIP SHA 回读归档；第1次尝试发布步骤失败；账户配置完成后第2次尝试6个job全部通过，详见发布补证。

## 限制与保留失败

全部类型指 68 个实际注册二维入口，不等于 VChart JS 所有高级选项、3D、动画或交互。Venn 最多三个单集合；Treemap 使用 binary 布局，部分数值格式明确拒绝。自定义资源字体绑定单个 `fontFamily`，自定义 fallback 列表明确拒绝。既有 22 条 Mermaid 分支缺口仍未修复；Dagre、交互、video/audio、任意 HTML/CSS 扩展继续排除。

两例词云的装饰重复数受 Canvas 字形占用影响，原始精确 multiset/结构差异继续展示，另以主体词、权重字号、真实字形墨迹和蒙版边界验证；旧 reference 严格阈值未改。像素差异只作诊断，不以其证明全部功能分支兼容。

首次分组失败、采集 CRLF 的首次 CI 失败、两次人工复核发现的真实缺陷、安装构建配置/并行目录竞争以及后处理汇总工具的首次 schema 失败全部保留于独立 Run，未覆盖、未把失败改为通过。详见 [执行记录](VCHART_INTEGRATION.md) 及 [变更收据](changes/vchart-integration.json)。

**PyPI 已发布**。Trusted Publisher 配置已完成，正式上传和下载SHA核对通过；当前通过 PyPI `py-visactor-vchart==0.1.1` 安装。[发布补证](VCHART_PYPI_PUBLICATION.md) 保留原阻塞及重跑记录。


## 分页报告与复用

[第五轮报告](http://127.0.0.1:8765/VCHART-P5-delivery-20261107T045848Z-3903b480/index.html) 共335条展示记录、29页，每页最多12例：供应方225、规格API68、七语法42；这些展示组有来源重叠，不作为335个独立新语法功能点。全部2537个原始附件（873 PNG、107 SVG）通过文件与HTTP SHA核验；两个验收附件、完整案例状态/分母、桌面/390px窄屏和3个报告负控均通过。最终8张布局截图已实际查看，图表内容验收另以上面的30张人工收据为准。

交付运行：`test-runs/VCHART-P5-delivery-20261107T045848Z-3903b480`；报告布局收据：`test-runs/vchart-report-visual-final-20261107T045848Z-3903b480.json`。标准复用入口为 `tools/run_vchart_validation.py`、`tools/verify_vchart_install.py`、`tools/run_vchart_delivery.py`，详见 [RUNS_AND_REPORTS](../tools/RUNS_AND_REPORTS.md)。每次使用新Run和新输出目录，保留真实失败，不重写闭合证据。

本轮 py-vchart 源码和正式发行已推送；py-mermaid 接入保留在当前工作树，未发布 py-mermaid 包，未对既有多轮脏树作无范围的大提交。
