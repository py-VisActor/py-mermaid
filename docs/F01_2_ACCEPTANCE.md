# F01.2 本地验收记录

2026-11-04，本切片完成，状态 **PASS_LOCAL**。实现普通边标签、14 种经典形状、子图/嵌套/组方向、跨组与组端点连线，保持 F01.1 基础流程图行为。固定 Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`；未提升完整 flowchart-v2 或其他图种兼容状态。

[打开 HTML 对比报告](http://127.0.0.1:8765/F01.2-render-20261104T145729Z-0ece5e77/index.html) · 本地报告?`reports/F01.2-render-20261104T145729Z-0ece5e77/index.html`????????????????? · [机器汇总](../references/f012-verification-summary.json) · [使用说明](F01_2_USAGE.md)

## 最终同一候选

产品源码/元数据/许可指纹：`b4df33aa602c178c9d8fd5f4f39685a68d58c1eaaf863c545f5dce7f3886b5e7`。最终测试及两组 A/B run 均 sourceUnchanged=true。CPython 3.13.15、Canvas 0.1.0a18、py-visactor-elk 0.1.0，现有 Windows 环境；CPU 使用公开 setter 禁用 GPU，auto/GPU 实际为 NVIDIA GeForce RTX 5080 / Vulkan。

| 测试组 | 方法数 | 结果 |
| --- | ---: | --- |
| f011-language | 37 | PASS |
| f011-layout | 21 | PASS |
| f011-canvas | 23 | PASS |
| f011-api | 5 | PASS |
| f012-language | 27 | PASS |
| f012-layout | 19 | PASS |
| f012-canvas | 18 | PASS |
| tooling-workflow | 17 | PASS |

合计产品测试 **150**、工具测试 **17**，共 **167** 项通过。方法内另含形状、方向及错误输入参数组合，未把这些子情形重复算成方法数。测试记录：`test-runs/F01.2-batch-20261104T145729Z-d57a2cd8/run.json`。

| A/B 分母 | CPU | auto | GPU-required |
| --- | --- | --- | --- |
| F01.2：35 正例 / 8 语法负例 / 1 上游渲染缺陷 | PASS | PASS | PASS |
| F01.1：12 正例 / 3 语法负例 | PASS | PASS | PASS |

F01.2 原始 A/B：`test-runs/F01.2-render-20261104T145729Z-0ece5e77/artifacts`。F01.1 同候选回归：`test-runs/F01.1-render-20261104T145729Z-049d66dd/artifacts`。报告生成只读取这些已有证据，未把报告生成成功或像素工具退出 0 当成功能通过。

## 实际内容与看图

检查语义节点/形状/边标签/组/成员/方向、真实轮廓端点、标签容纳、父子包含、边/箭头绘制、阴影、裁切和纯值/owner 线程。官方 source-map 25 项与固定 Git/Jison 转换核对；原 33 例语义由独立审阅核对，另加长标题修复回归与综合示例，共 35 例。

浏览器 QA：105 个正例后端选择及全部错误例、原始图片尺寸/内容、并排/叠加/诊断模式、桌面及移动布局均通过，无脚本错误或外部请求。记录 `test-runs/f012-html-qa-final-001/report.json`，截图同目录。已实际查看综合流程、长组标题，以及形状/内圈/圆柱 cap、多行中文标签和嵌套/组端点等 PNG。报告默认适应栏宽，允许切回 100% 查看；PNG 原始字节未修改。

## 首轮失败、根因与修复

- 初始同候选分组：`test-runs/F01.2-batch-20261104T144510Z-1fc0bf60`。布局长标题失败：纵向 INCLUDE_CHILDREN 的 pyelk 最小尺寸使用转轴空间。修复布局输入约束并真实重算，未后扩组框；19 项布局方法及多方向/嵌套/错误负控通过。详见 [修复记录](changes/20261104-f012-title-floor-fix.json)。
- 实际看图发现圆/双圆漏阴影，源 styles.ts 被误读。已恢复外圈和双圆内圈独立阴影、白色内盘，新增真实像素断言；原错误预期与失败看图记录保留，详见 [Canvas 记录](changes/20261104-f012-canvas.json)。
- 初次比较工具误把 tuple/list、SVG 复合形状容器样式当差异，及错误负控越界异常。已修工具，保存原失败、补三类分母和 source/PNG SHA 校验；白图、漏内容、错组、错标签/形状等负控均生效。初始记录未覆盖。
- 最终补充随包 Mermaid 许可说明中的 F01.2 来源映射，仅 NOTICE 改变候选指纹；所有产品 Python 代码保持，已对上述最终指纹重新完整验证。历史两个候选的证据分别保存。

## 保留边界

经典 ellipse `A(-text-)` 在官方可解析但缺渲染处理器。官方原错误与 Python `UPSTREAM_SHAPE_MISSING` 单独展示，不生成成功图片。根方向仍 TD/LR，组内支持 TD/TB/LR/RL/BT；跨层时保留真实引擎合法路由，不宣称 elkjs 0.9.3 与 Python ELK 0.12.1 坐标等价。空组几何大小、字体/抗锯齿及自然尺寸差异已保留。内部边穿过组标题的原上游路由模式在 A/B 中一致且可读；尚未新增 terminal-jog straightening/line-hop painter，属于后续路由外观范围。

安装验证按用户要求 **未执行**；未重新安装、构建或发布包。Linux/no-loader 与系统字体打包未验。F01.3/F01.4 及其他图种不属于本轮。**本轮未 commit/push。**
