# F01.3 配置、主题与富文本

本切片延续 [F01.2 流程图增强](F01_2_USAGE.md)，固定 Mermaid 12.2.0 来源，仅使用真实 pyelk 和公开 py-skia-canvas API。`parse` 返回不可变语义数据，`render` / `arender` 返回 PNG bytes、尺寸、布局、测量及绘制 trace。安装验证仍按用户要求暂缓；下列命令使用已有研发环境。

## 可直接运行的例子

```powershell
$env:PYTHONPATH = 'src'
C:/venvs/pymmd-20261102/Scripts/python.exe examples/rich_flowchart.py --out test-runs/my-rich-flowchart.png --backend auto
```

示例文件拒绝覆盖已有输出；再次执行请换新路径。Windows 的 ELK worker 使用进程，调用入口须放在 `if __name__ == '__main__':` 下；异步程序使用 `await arender(...)`。Canvas 对象始终留在创建线程。

```python
from pathlib import Path
from py_mermaid import render

source = '''---
title: 配置与富文本
config:
  theme: forest
  flowchart:
    wrappingWidth: 180
---
flowchart LR
A["`**开始**与 *Markdown*`"] -->|"`*通过*`"| B["<b>HTML 标签</b><br/>第二行"]
'''

if __name__ == '__main__':
    result = render(source, backend='auto')
    Path('rich-flowchart.png').write_bytes(result.data)
```

## 配置与位置

支持 frontmatter 的 `title`、`config`，以及 `init`、`initialize`、`wrap` 指令；保留 site/frontmatter/directive 等配置层与最终有效配置，按固定上游的合并、secure 项和图种默认规则处理。Python `config=` 是 site 配置入口。不要从配置出现顺序自行推断所有键同一优先级：流程图的默认主题/look、secure 键与主题派生变量各有来源分支。

`SourceDocument` 保留原文、各处理阶段文本和处理后字符边界到原文的映射。错误 span 使用原文位置并包含 UTF-16 偏移，frontmatter、指令、注释、CRLF 和 Unicode 不应让定位漂移。每次请求独立解析配置，不修改全局状态。

主题名称为 `base`、`dark`、`default`、`forest`、`neutral`、`neo`、`neo-dark`、`redux`、`redux-dark`、`redux-color`、`redux-dark-color`，另保留字符串 `"null"` sentinel 的上游语义。默认是流程图级 `redux-color/neo`。`themeVariables` 支持本切片原生字体/颜色/描边/间距等映射，`themeCSS` 支持适用语义目标的字体、颜色、边框、透明度、背景、对齐、声明级联和自定义变量；不创建 DOM 或 CSS 布局引擎。

标题是纯文字，按源锚点、实际字体和墨迹边界进入最终画布；不会把标题内容作为 HTML 执行。显式 `display:none` 产生标题隐藏标志，与缺失测量分开验证。

## 标签与安全

节点、普通边标签和子图标题支持普通文字、HTML 文字格式及反引号界定的 Markdown。粗体、斜体、换行、实体、颜色与适用字体样式使用实测文字 run 绘制；相邻同样式 run 合并测量，保留 shaping 和 kerning。普通块、列表、表格支持其文字内容和本切片可表示的布局意图，不能据此宣称实现了浏览器页面排版或完整 CommonMark。

`htmlLabels=false` 遵循源 SVG 文本路径：普通 HTML 标签可能作为带词间隔的字面文字显示，不是通用去标签。该路径中源 Markdown 忽略的 token 保留 `SOURCE_MARKDOWN_TOKEN_OMISSION:*` 诊断。实体只解释一次，避免把原本的字面标签重新当作 markup。

支持 `strict`、`loose`、`antiscript`、`sandbox` 的文字清洗语义与适用 `dompurifyConfig` 分支。PNG 不创建浏览器 iframe；官方 sandbox 包装仅在研发对照中展开其原始 SVG，并保留包装证据。默认清洗禁止 style 元素，普通 inline style 是否保留按源配置分支处理；`target=_blank` 对应源 `rel=noopener` 钩子。表单控件、外部资源、数学排版、保留的 stylesheet 元素及无法表示的浏览器清洗选项明确诊断。

## 日志、报告与边界

```powershell
C:/venvs/pymmd-20261102/Scripts/python.exe tools/workflow.py batch --scope F01.3 --plan tools/plans/f013-tests.json --keep-going
C:/venvs/pymmd-20261102/Scripts/python.exe tools/workflow.py render --scope F01.3 --fixtures tests/f013/cases.json --profiles cpu auto gpu --default-case rich-overview
```

每次执行创建新 run，保留原始 stdout/stderr、退出码、源指纹及图片哈希。只重新生成已有证据的 HTML 时用 `workflow.py report --spec tools/report_specs/f013-final.json`；不需要重新渲染。细节见 [统一入口](../tools/RUNS_AND_REPORTS.md)。

真实后端 `cpu` 显式禁用 GPU，`auto` 保留默认策略，`gpu` 要求实际 GPU。验收按功能、实际内容/格式、几何关系、可读性和安全判断，像素差保留为诊断。跨字体、浏览器/Canvas、elkjs/Python ELK 的合法尺寸与路由差异不要求消除。

当前根方向 TD/LR、14 种经典形状和 `-->` 等既有范围继续有效；上游 ellipse 渲染缺陷单独报告 `UPSTREAM_SHAPE_MISSING`。style/class/linkStyle 语句、新 shape、其他边类型、手绘、图标图片、数学及非 PNG 导出仍待后续。**F01.4/Dagre 已暂停，等待重新评估。** 本切片不等于完整 flowchart 或全 Mermaid 完成。
