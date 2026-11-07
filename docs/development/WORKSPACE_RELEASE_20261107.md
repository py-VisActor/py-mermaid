# py-VisActor 文档修订发行

本轮将用户说明与维护者、AI agent 工作规则分开，并通过新发行版本更新 PyPI 描述和 Documentation 项目链接。

| 项目 | 新版本 | 发行页面 | 用户文档 |
| --- | --- | --- | --- |
| py-skia-canvas | 0.1.0a20 | [PyPI](https://pypi.org/project/py-skia-canvas/0.1.0a20/) · [GitHub](https://github.com/py-VisActor/py-skia-canvas/releases/tag/v0.1.0a20) | [使用入口](https://github.com/py-VisActor/py-skia-canvas/blob/main/docs/README.md) |
| py-visactor-elk | 0.1.1 | [PyPI](https://pypi.org/project/py-visactor-elk/0.1.1/) · [GitHub](https://github.com/py-VisActor/py-elk/releases/tag/v0.1.1-docs.1) | [使用入口](https://github.com/py-VisActor/py-elk/blob/main/docs/README.md) |
| py-visactor-katex | 0.1.1 | [PyPI](https://pypi.org/project/py-visactor-katex/0.1.1/) · [GitHub](https://github.com/py-VisActor/py-katex/releases/tag/py-visactor-katex-v0.1.1) | [使用入口](https://github.com/py-VisActor/py-katex/blob/main/docs/README.md) |
| py-visactor-vchart | 0.1.2 | [PyPI](https://pypi.org/project/py-visactor-vchart/0.1.2/) · [GitHub](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.2) | [使用入口](https://github.com/py-VisActor/py-vchart/blob/main/docs/README.md) |
| py-visactor-mermaid | 0.1.1 | [PyPI](https://pypi.org/project/py-visactor-mermaid/0.1.1/) · [GitHub](https://github.com/py-VisActor/py-mermaid/releases/tag/py-visactor-mermaid-v0.1.1) | [使用入口](../README.md) |

五个版本的实际 PyPI 元数据已分别与不可变发行标签核对：描述等于该标签中的用户说明文件，Documentation 指向 `docs/README.md`，运行依赖约束保持一致。各自的新工件验证和实际 PyPI 下载后的 Windows/Linux 安装回读均成功；Canvas 的 GPU/CPU 普通、STRICT、实际绘图和生命周期检查也已完成。Canvas 继续使用 alpha 版本号，不据此宣称稳定版本。

[机器汇总](../../references/workspace-documentation-publication-20261107.json)保存实际索引文件名、大小、SHA、发行标签及元数据来源摘要。各项目的安装和平台证据保留在自身发布记录中；元数据检查本身不能代替安装或渲染验收。

各仓的 README 面向使用，`docs/development/README.md` 面向维护者，根 `AGENTS.md` 采用六节稳定规范。旧会话、迁移计划、验收及原始图片按各自来源身份保留。旧 PyPI 版本的元数据不覆盖，旧标签和资产不移动；ELK 的首次 YAML 失败标签也保留，新包绑定实际通过的 `v0.1.1-docs.1`。
