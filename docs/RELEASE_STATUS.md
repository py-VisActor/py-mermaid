# 发行状态


## 0.1.4 统一发行

[PyPI 0.1.4](https://pypi.org/project/py-visactor-mermaid/0.1.4/) 与 [GitHub Release](https://github.com/py-VisActor/py-mermaid/releases/tag/py-visactor-mermaid-v0.1.4) 已发布。macOS 安装会选择同版 Canvas、ELK、KaTeX 和 VChart，并已用正式 PyPI 工件在 macOS 13.7.8 全新安装验证。Apple Silicon、Intel、Windows 和 Linux 的 wheel 与 sdist 均通过发行安装检查。

[发行说明](releases/0.1.4.md) · [发行工作流](https://github.com/py-VisActor/py-mermaid/actions/runs/44465489337) · [工件 SHA 和安装记录](../references/mermaid-publication-0.1.4.json)。

## 0.1.2 macOS 发行

[PyPI 0.1.2](https://pypi.org/project/py-visactor-mermaid/0.1.2/) 与 [GitHub Release](https://github.com/py-VisActor/py-mermaid/releases/tag/py-visactor-mermaid-v0.1.2) 已发布。Apple Silicon、Intel、Windows 和 Linux 均通过同一 wheel 与 sdist 的隔离安装和静态渲染验证。macOS 13.7.8 从 PyPI 全新安装后验证了 Canvas、ELK、KaTeX、VChart 与 Mermaid，且 `pip check` 通过。

[发行说明](releases/0.1.2.md) · [发行工作流](https://github.com/py-VisActor/py-mermaid/actions/runs/44458655299) · [工件 SHA 和安装记录](../references/mermaid-publication-0.1.2.json)。

## 0.1.1 文档发行

`py-visactor-mermaid 0.1.1` 已正式发布到 [PyPI](https://pypi.org/project/py-visactor-mermaid/0.1.1/) 和 [GitHub](https://github.com/py-VisActor/py-mermaid/releases/tag/py-visactor-mermaid-v0.1.1)。[版本说明](releases/0.1.1.md) · [固定发行凭据](../references/mermaid-publication-0.1.1.json)。

本版更新用户文档、AI 工作规范与 PyPI 文档入口，渲染实现和依赖约束保持不变。Documentation 已实际回读为 `docs/README.md`。Windows/Linux 的同组 wheel、sdist 安装验证、OIDC 上传、实际 PyPI SHA 核对及公开工件再次安装均成功，见[发行流水线](https://github.com/py-VisActor/py-mermaid/actions/runs/42377962940)。

Python 导入名为 `py_mermaid`，CLI 为 `py-mermaid`。使用方式见[用户文档](README.md)。

- 用户：[安装和使用](README.md)、[版本发布](https://github.com/py-VisActor/py-mermaid/releases)。
- 维护者：[开发入口](development/README.md)、[构建与验证流程](TEST_AND_RELEASE.md)。
- 历史：[0.1.0 发布说明](MERMAID_PYPI_PUBLICATION.md)、[原发行凭据](../references/mermaid-publication-0.1.0.json)。旧版本、tag 与资产完整保留。

发行凭据始终绑定各自的构建提交及精确文件，不能将当前 main 的文档修改重绑到旧发行。

旧状态时间线[原字节归档](development/history/documentation-before-20261107/docs__RELEASE_STATUS.md.txt)。
