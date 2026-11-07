> 2026-11-06 已接入正式 `py-visactor-katex==0.1.0`，导入 `py_katex`；wheel/sdist 仓库外安装、22 项既有回归各两环境、8 集成图三后端和五格式均通过。当前入口为 [正式数学接入验收](MATH_RELEASE_INTEGRATION.md)。本轮受影响安装验证已完成，下文旧“相邻源码/数学未发布/安装暂缓”按历史保留；未发布 py-mermaid。

# 完整数学核心静态能力接入验收

2026-11-06：独立 py-katex 已完成固定 KaTeX 0.18.11 核心静态迁移并接入 Mermaid。详见 [完整验收](https://github.com/py-VisActor/py-katex/blob/main/docs/FULL_STATIC_ACCEPTANCE.md) 和 [机器摘要](../references/math-full-verification-summary.json)。

973 个测试方法、684 个注册/宏上下文、1909 个上游功能输入及 217 组等价关系通过；267 个公式和 8 个集成图三后端共 825 视图通过，297 个历史流程图三后端回归通过。五格式导出、人工看图与 HTML QA 已完成。

[查看报告](http://127.0.0.1:8765/MATH-FULL-batch-20261105T172308Z-e0e12af6/index.html)。全部模块只做静态渲染，Dagre 完全剥离；任意宿主 CSS、HTML/MathML 输出后端及独立 contrib 扩展不在核心验收范围。安装验证继续暂缓，未提交推送发布。旧 alpha 及旧“数学延后”说明保留为历史。
