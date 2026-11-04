# 测试与发布方案

最新执行时序见 [FULL_MIGRATION_PLAN](FULL_MIGRATION_PLAN.md)和 [SOURCE_BASED_VERIFICATION](SOURCE_BASED_VERIFICATION.md)：**全部功能源码 P1 写完后，P2 才正式设计用例/单测/oracle，P3 分组首次运行、统一排查修复，P4 最终全量。** P1 仅运行编译/import/引用/签名/注册等机械检查，不以逐图单测或图片通过作为继续写码前置。下列现有资料检查不属于 Mermaid 功能验收。

## 目前能运行的检查

独立 PNG 像素对比工具也已可运行，开发依赖/命令/报告解释见 [PIXEL_COMPARE](../tools/PIXEL_COMPARE.md)。它不调用产品渲染器，默认仅诊断；不能将工具返回 0 当成 Mermaid 功能通过。

以下是源码/资料与依赖检查，均不证明 Mermaid 渲染通过：

```shell
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/canvas_smoke.py --out test-runs/new-canvas-auto
python examples/canvas_smoke.py --backend cpu --out test-runs/new-canvas-cpu
python examples/canvas_smoke.py --backend gpu --out test-runs/new-canvas-gpu
python -m build --wheel
```

构建只用于骨架打包检查，不上传占名。将来生产代码变更使用新构建候选，在仓库外、`python -I`、无 Node/浏览器 PATH 的新环境中运行。旧包只作修改前对照。

## 待实现的差分体系

按照用户确定的 [Canvas 原生架构](CANVAS_NATIVE_ARCHITECTURE.md)，DOM tree、React component tree、选择器调用或浏览器调度顺序只可作为上游诊断信息，不要求 Python 复制。Python 比较对象为语义、解析后样式、文字/节点 box、路由与绘制输出；富文本/配置含义与安全功能仍要验证，视觉差异完整报告。该变化不允许生产使用浏览器测量或 oracle 坐标。

用户已确定渲染**功能一致即可，不要求 DOM/Canvas 完全像素一致**。以 [分层判定规则](RENDER_CONSISTENCY.md)为准：语义、实际内容、几何关系/可读性和安全/导出是门禁；像素差/SSIM 仅诊断。合理字体度量、抗锯齿、自然尺寸与满足约束的坐标/路由变化可通过。

官方 JS oracle 尚未实现，入口要求见 [tools/oracle](../tools/oracle/README.md)。不提供虚构的 capture/compare 命令。M2 实现后再补可执行步骤和锁文件。

- 一份共享输入：文本、config/theme、seed、资源/字体、layout、尺寸/density/backend 与预期错误。
- A 记录：实际 Mermaid/npm integrity、源码 SHA、Node/browser/dependencies、字体 SHA、解析模型、标准化配置、SVG、DOM 测量/布局、PNG/RGBA。
- Python 记录：候选包/native SHA、相同输入与字体、model/layout/display primitives、Canvas engine、PNG/RGBA、SVG/PDF 及异常。
- 比较分层：模型/错误、语义绘制场景、几何关系/可读性、导出/安全，另保存原始 RGBA/差异图作诊断。自然坐标/尺寸不设跨引擎相等门槛，显式尺寸约束仍检查。
- 必须有正/负控制：漏节点/标签、错箭头、错连接、裁切或 no-op 绘制等必须失败；仅正常抗锯齿/合法度量和位置变化不能误判失败。单像素破坏只在明确指定的确定性自身回归 profile 要求拒绝。

## 测试分组

| 分组 | 内容 |
| --- | --- |
| bootstrap/source | 文档链接/代码语法、版本/依赖锁、registry 与源文件索引、覆盖清单完整性、漂移负控制 |
| parser/config | 全部 grammar 与预处理、正负例、JS 值/UTF16/时区、schema/default/theme/security |
| layout/render | 每个图种几何/路由/marker/style/labels、复杂文本、HTML/Markdown/math、布局插件/seed |
| resources/security | 离线图标/图片/字体、缺资源、非法 URL/HTML、大小/深度/并发资源上限 |
| exports | 所有声明格式、透明/背景、density/viewport、PDF 页/字体、SVG 元数据/链接；不同栅格器不混用 |
| owner/lifecycle | 跨线程错误、worker 自建对象、GC、错误恢复、连续渲染无状态污染、取消/退出 |
| deployment | Windows/Linux、CPU/GPU 分组、无 Vulkan/no-loader、无 Node/浏览器/参考源码、实际安装路径 |

系统字体不随包复制；共享可再分发字体应固定许可与 SHA，fallback/CJK/RTL/emoji 独立登记。GPU-required 不允许自动回退 CPU 后通过。Canvas `engine` 仅状态信息，声明 native GPU 验收还需对应真实观测。

## 证据与文档

新 run 目录不得覆盖旧输出。记录命令/退出码/源码与资源 SHA；失败原样保存。产物 JSON 应含 status、范围、环境、断言/差异、文件 SHA 与未验收项。任务记录引用真实日志/报告；修改源码或例子后重跑相关检查，不能沿用旧 SHA。

新可见能力交付实际可运行例子与输出、图像 provenance 和视觉审阅；README 双语、契约和状态同时更新。bootstrap CI 不代表实际 GPU/CPU、视觉、全 spec 或发行验收。

## 发行门禁

首发支持范围暂随固定 Canvas：CPython 3.13、Windows AMD64、Linux glibc 2.28+ x86_64。其他 ABI/平台未验收。实际发布前必须：

1. 真实功能子集和剩余清单公开，不能发布空骨架占名。
2. 同一新候选 wheel 在两平台干净安装，无 Node/浏览器/工作区运行；记录依赖与 wheel/native SHA。
3. 相关 spec/字体/导出/owner/GPU/CPU 验收，已知限制和文档/例子准确。
4. 打包 README/METADATA/许可独立检查；PyPI README 来源于上传字节，GitHub 更新不会改旧包描述。
5. 按本次授权 commit/push、实际 CI、Release/索引发布及重新下载核验，各自记录状态；本任务未授权发布。
