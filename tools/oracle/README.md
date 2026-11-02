# 官方 JS Mermaid 对照工具（待实现）

本目录只定义 M2 的交付要求，尚无 capture/compare 实现、browser 锁或 JS 结果。官方 Mermaid 只用于开发采集，生产解析/布局/绘制不依赖它。

## 固定环境

Mermaid 精确版本和源码以 [lock](../../references/upstream.lock.json) 为准，其 Node engine 为 `>=22.12.0`。M2 选择并固定实际 Node、npm/pnpm lock integrity、Playwright/browser revision、字体/资源、时区/locale、deviceScaleFactor 与 viewport。不能只写 latest，不能用另一个 Mermaid 包/在线编辑器代替基线。

核心包与 ZenUML、ELK/tidy 扩展分开安装并锁版本，保存传递依赖和许可。需区分官方 npm 发行物和源码重建物，不能静默互换。

在采集前核查发行物与锁定源码的 detector、主题、布局及构建开关是否一致。锁定 schema 的默认布局为 `elk`；完整构建与 tiny 的 loader/fallback 行为须分别登记，不能拿显式 Dagre 采集结果代替默认路径。随机默认用例保留原始行为，确定性比较另用显式 seed，不暗改默认值。

## 采集契约

1. 读取同一 fixture/config/resources；每个用例使用干净 config/DB，显式等待字体、图片和异步 layout。
2. 保存 detect/parse 的标准化语义和错误、最终配置、官方 SVG、实际 DOM box/path/label/marker/样式以及 PNG/RGBA。动态 ID 只在结构比较中做可追溯映射，原始文件完整保留。
3. 保存实际源码/npm/browser/font SHA、版本和命令；重采验证 seed、布局和资源稳定性。
4. 支持合法/非法输入，不把异常或空图当成成功。每份报告绑定 fixture/config/候选与环境 SHA。
5. Python runner 在无 Node/浏览器 PATH 的隔离安装环境执行；不能调用本工具生成产品输出。

浏览器与 Canvas 抗锯齿/字体测量未必完全相同；按 [兼容规则](../../docs/API_COMPATIBILITY.md)逐层报告，不悄悄加入容差。比较器须用模型、几何和单像素破坏负控制证明可检测差异。

分解任务和六组局部闭环门禁见 [M2 任务](../../docs/TASKS.md)；少数 flowchart 的采集完成不代表全量 M1/M2 结束。oracle 几何/fixture size 只能作预期结果，不能输入产品布局来替代 Canvas 测量或算法计算。
