# 正式 py-visactor-katex 接入验收

2026-11-06：**py-mermaid 已接入正式 `py-visactor-katex==0.1.0` 并通过实际安装验证。**

```shell
python -m pip install .
```

需要 CPython 3.13。安装当前 py-mermaid 会从 PyPI 解析 `py-visactor-katex==0.1.0`，
Python 导入仍为 `py_katex`。无需相邻 `py-katex/src`，无需 PYTHONPATH 接线。
数学模块正常包导入、节点/边/组数学、混排和 `htmlLabels=false` 字面分支均保留。
py-mermaid 仍为本地开发版本 `0.0.1a0`，本任务没有发布 py-mermaid。

## 实际验证

| 验证 | 结果 |
| --- | --- |
| 安装路径 | 当前 wheel 和 sdist 分别安装到仓库外的全新 venv |
| 依赖解析 | pip 正式 PyPI 报告中的数学 wheel SHA 与已发布版本逐字节一致 |
| 模块位置 | py_mermaid / py_katex / pyelk / py_skia_canvas 均位于相应 venv |
| 隔离 | Python `-I`、无 PYTHONPATH、空 PATH，Node 不可用 |
| 既有回归 | 17 数学 + 5 公开 API，在两种安装环境各通过，22 唯一方法/44 次执行 |
| 集成图 | 8 例 × CPU/auto/必需 GPU × 两环境 = 48 份结果 |
| 静态导出 | 含节点、边、组数学的 PNG/JPG/WebP/SVG/PDF，三后端两环境共 30 份 |
| 人工查看 | CPU 混排/组/边公式、GPU 矩阵原图内容完整 |

来源实现没有扩展。运行源码只调整缺少数学依赖时的包名提示，其余数学桥接与绘制字节保持；
主要修改是依赖元数据和公开安装/许可说明。数学能力仍采用固定 KaTeX 核心静态范围，
不增加交互或其它图种。

## 证据与复用

- 构建、安装、回归与原图：`test-runs/MATH-PYPI-batch-20261106T010610Z-054fd721`
- 交付与完整性归档：`test-runs/MATH-PYPI-delivery-20261106T010903Z-4dd7a953`
- [机器摘要](../references/math-published-integration.json)
- [发行身份与文件锁](../references/math-release-lock.json)
- [变更回执](changes/20261106-published-math-integration.json)

```shell
python tools/workflow.py batch --scope MATH-PYPI --plan tools/plans/math-published-integration.json
```

`tools/verify_published_math.py` 保存 pip 安装报告、真实模块路径、每条命令原始输出和实际图像 SHA。测试不注入源码目录；Pillow 仅为验证工具依赖，不是产品运行依赖。

本次是 Windows 上受影响依赖的 wheel/sdist 安装验证；不能据此新增 py-mermaid 的 Linux/no-loader 验收。旧数学 alpha、完整核心及历史流程图记录保留原始候选和实际范围。

当前开发解释器也已安装正式数学发行包，运行 `test-runs/MATH-PYPI-batch-20261106T011025Z-597cb94c` 核对版本和实际 site-packages 路径；原 Canvas/ELK 依赖锁未变。最终完整性归档：`test-runs/MATH-PYPI-final-audit-20261106T011056Z-5cf4c16a`。
