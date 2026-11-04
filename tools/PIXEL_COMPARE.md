# PNG 像素对比工具（已实现）

入口：[pixel_compare.py](pixel_compare.py)，独立工具测试：[test_pixel_compare.py](../tests/pixel_compare/test_pixel_compare.py)。本轮按用户要求预先提供通用图片诊断工具；不运行 Mermaid、DOM、Canvas 或布局引擎，不改变 P1 全功能源码后再进入 P2 正式测试设计的顺序。

工具使用 **Pillow==12.3.0** 解码 PNG 与写诊断图，依赖单独记录在 [pixel_compare_requirements.txt](pixel_compare_requirements.txt)，不进入产品运行依赖，不是第二个产品绘制后端。实现采用 [Pillow ImageChops](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html) 的通道差分和 [Image](https://pillow.readthedocs.io/en/stable/reference/Image.html) 的解码/alpha composite。

## 1. 安装与运行

在仓库根目录的开发虚拟环境中：

```shell
python -m pip install -r tools/pixel_compare_requirements.txt
python tools/pixel_compare.py --reference test-runs/A.png --candidate test-runs/B.png --out test-runs/pixel-diff-001
python -m unittest discover -s tests/pixel_compare -v
```

`A.png`/`B.png` 是调用者已有的原图，示例路径不是已采集的 Mermaid 输出。输出目录必须不存在，已存在会拒绝，不覆盖旧报告/原图。

只想先检查工具安装是否正常，可以对仓库已有 Canvas 依赖示例做自身比较（不代表 Mermaid 验证）：

```shell
python tools/pixel_compare.py --reference docs/assets/canvas-smoke.png --candidate docs/assets/canvas-smoke.png --out test-runs/pixel-tool-smoke-001 --mode exact
```

跨 DOM/Canvas 使用默认 **diagnostic** 模式：即使像素不同也正常生成报告并返回 0，结果为 `DIAGNOSTIC_ONLY`，`functionalStatus=NOT_EVALUATED`。返回 0 只代表工具成功完成对比，不能据此判 Mermaid 功能通过。

同环境、固定字体/资源/seed/后端且已证明确定性的指定 Canvas 自回归，可以显式使用：

```shell
python tools/pixel_compare.py --reference test-runs/baseline.png --candidate test-runs/current.png --out test-runs/pixel-exact-001 --mode exact
```

**exact** 模式检查尺寸、解码后的完整 RGBA 像素和颜色元数据：相同返回 0，不同返回 1。它不验证字体/driver/seed 等环境身份，报告中 `environmentIdentityVerified=false`；P2/P3 runner 必须用自己的环境 manifest 判断是否具备使用 exact 的前提。该模式不作跨 DOM/Canvas 兼容门槛。

输入/参数错误、预算超限或已存在输出目录返回 2。输出目录新建后发生错误时保存 `error.json`；目录本身已存在时保留其原有文件不写入。

## 2. 计算指标

| 指标 | 定义与用途 |
| --- | --- |
| 原始 RGBA 不同像素数/比例 | 一个像素任一通道不同即计一次；包含 alpha，保留透明像素隐藏 RGB 的差异 |
| MAE、RMSE、最大通道差 | 在两图公共区域、解码后的 0–255 通道值上统计，RGBA 四通道都参与 |
| 差异包围盒 | `[left, top, right, bottom)`，正确检测“RGB 不同但 alpha 相同”的差异 |
| 白底/黑底 composite 差异 | 识别透明度/隐藏 RGB 引起的原始差异与实际可见差异，分别报告，不混成一个数 |
| 尺寸/覆盖差异 | 不缩放或裁图，按左上角统一坐标；公共区域比较与仅一图存在的区域分开统计 |
| 局部 tile 差异 | 默认 64×64，列出变化块与缺失覆盖像素；帮助从大背景中定位少量标签/箭头异常 |

尺寸不同时，`unionAreaPixels = area(A)+area(B)-area(overlap)`；只在其中一张图存在的像素计为 `coverageMismatchPixels`。若两图一宽一高，右下角两边都不存在的区域不算比较分母。不通过自动缩放/平移/对齐消除真实差异。

这些是**编码通道空间的像素指标**。当前不做 ICC/gamma 色彩管理转换、不实现 SSIM/感知指标，也不判断节点/文字/箭头或语义；颜色元数据不同时给出告警，exact 模式不放行。SSIM、语义区域映射和批量 case 汇总是 P2 完整比较器的后续能力，不能声称本工具已经具备。

## 3. 输出与可视化

| 文件 | 内容 |
| --- | --- |
| `reference.png`、`candidate.png` | 原始输入字节的完整副本，不重新编码，记录 SHA256 |
| `diff-raw.png` | RGBA 通道差热图：红/黄为差异，蓝为只有一张图存在的区域 |
| `diff-white.png`、`diff-black.png` | 分别在白/黑背景 composite 后的 RGB 差热图 |
| `mask-raw.png` | 精确差异及缺失覆盖的二值掩码，保留所有不同像素 |
| `mask-threshold.png` | 仅供诊断显示的阈值掩码；原始指标不会因此变化 |
| `report.json` | 指标、tile、输入/输出 SHA、尺寸/颜色元数据、命令、Python/Pillow/脚本身份、警告与结果 |
| `report.html` | 可离线打开的并排图、透明度滑杆叠图、热图、掩码及完整指标；无外部网络资源 |

图像尺寸不一致时，热图使用完整包围画布，缺失覆盖标蓝；原始图保持自身尺寸。HTML 缩略图可为展示缩放，但保存的 PNG 和数值计算不重采样。

`--gain 4` 是默认热图放大倍数；`--channel-threshold 4` 可以隐藏显示中很小的通道变化，**不会改原始不同像素数、MAE/RMSE 或原始掩码**。exact 模式只允许 threshold=0。

`--tile-size` 控制局部统计块；`--max-pixels` 默认 16,000,000，分别限制单图和完整包围画布，超限报错。当前只接受静态 PNG、1/2/4/8 bit 输入（解码为 RGBA8）；拒绝 16-bit、APNG 多帧和非 PNG，避免静默降精度或只比较一帧。

## 4. 作为完整迁移测试方案的一部分

P2 的比较流程应为：

```text
case 输入与环境 manifest
  ├─ 官方 A 语义场景/原图
  └─ Python B 语义场景/原图
       → L1 语义 + L2 实际内容 + L3 几何/可读性硬断言
       → 本工具的 L4 像素报告
       → 规则汇总：PASS / FAIL / REVIEW / UNVERIFIED
```

通用工具已经可用，不意味着 P2-V05 的完整 Mermaid 比较器或 P2-V06 故障注入已完成。后续 P2 负责批量 case manifest、语义元素对应、区域诊断、图像预警校准、环境身份与综合报告；P3 实际分组运行，P4 最终全量。

必须同时验证：漏节点/文字/箭头、错关系、裁切和 no-op 绘制可被对应语义/质量检查拒绝；正常抗锯齿/合法度量/位置变化可被解释后放行。像素工具用于量化与定位，不能因“只差一个像素”自动否决跨渲染器功能，也不能因“相似度高”放行漏字。
