# py-vchart 0.1.1 PyPI 正式发布

2026-11-07，账户完成 Trusted Publisher 配置后，重跑此前失败的 publish/verify；[工作流 42337813981 第2次尝试](https://github.com/py-VisActor/py-vchart/actions/runs/42337813981) 的四组既有验证、publish 和 verify 共6个 job 全部成功。

正式项目：[py-visactor-vchart 0.1.1](https://pypi.org/project/py-visactor-vchart/0.1.1/)。CPython 3.13 安装：

```sh
python -m pip install py-visactor-vchart==0.1.1
```

使用此前已通过 Windows/Linux × Canvas a18/a19 验证的同组文件，没有重建、覆盖 tag 或替换资产。实际 PyPI 元数据、下载文件与原 manifest 三方一致：wheel SHA-256 `45b66f82d0c74a8d15306b117d93ad2d88c26d2997719306336bcc92b7ce49e2`；sdist `fee51a35d75b7f8572e76b0028d63c833f6e01c670c7ea41dc412386b3bcef7f`。

CI 的 PyPI 核验资产 ZIP 已回读并按 GitHub API digest 验证：`17d3174cf896e54893bae789f759fb610d379c08929eb4bddec3737573e49f21`。其中 wheel/sdist 各在全新仓库外环境完成225例、68类型与36项原生/负控方法。归档：相邻供应方 `test-runs/vchart-pypi-ci-42337813981-attempt2/`；首次失败资产保持不变。

## py-mermaid 正式依赖

`pyproject.toml` 与依赖清单已改为 `py-visactor-vchart==0.1.1`，由正常 PyPI 解析器安装，不再依赖 GitHub wheel URL。新 wheel、sdist 两个全新消费方环境均成功：

- `VCHART-INSTALL-wheel-20261107T061840Z-c4a0291f`
- `VCHART-INSTALL-sdist-20261107T061940Z-cd8458f2`

未预装 VChart，pip report 的 files.pythonhosted.org URL和SHA与正式元数据一致；index安装没有 direct_url.json。实际68类型CPU绘制、SVG/PDF、数学glyph与真实ELK 3节点2边均通过，无相邻源码或Skia-Python导入。

补充检查 `VCHART-PYPI-CHECKS-batch-20261107T062014Z-ed55e3d4` 通过：14 bootstrap、14依赖、156接入方法，合计184；含拒绝未发布状态/错误文件主机的两个负控。首次安装证明脚本的变量重名导致JSON序列化失败已保留并修复，没有修改任何图表产品代码或放宽绘制门禁。

[机器补充汇总](../references/vchart-pypi-verification.json) 严格核对当前与原同候选P4的全部产品文件：仅 `README.md` 与 `pyproject.toml` 改变，渲染源码逐字节不变。原2283方法、三后端和30实际看图继续对应其原候选，新补证仅验证发布和依赖渠道，不冒称重新完成整轮视觉验收。

[此前分页图表报告](http://127.0.0.1:8765/VCHART-P5-delivery-20261107T045848Z-3903b480/index.html) 已在发布前闭合，页面的 PyPI blocked 是当时历史状态；其图片、附件、原始失败与哈希不重写。当前发布状态以本页及补充汇总为准。68二维静态类型/七语法范围、Venn/Treemap限制、22条旧分支缺口和静态排除均不变。py-mermaid当前改动仍留本地，未发布py-mermaid包。
