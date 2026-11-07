# 验证与发行

本页面向维护者和 AI agent。使用库请阅读[用户文档](README.md)；稳定修改约束见 [AGENTS.md](../AGENTS.md)。旧迁移阶段的发行方案[原字节保留](development/history/test-and-release-before-0.1.1.txt)，不作为当前待办。

## 按影响选择验证

- 纯文档：文档链接、Python 示例语法、公共入口与打包描述检查，不重复绘图或安装矩阵。
- 实现变化：保存修改前证据，执行受影响的来源独立断言、实际绘图、资源及导出检查；按共享影响扩展回归。
- 正式发行：即使仅更新文档，也须构建新版本并验证实际安装包及公开元数据，不覆盖既有版本。

基础检查：

```shell
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
```

来源、像素和图像验证见[来源方案](SOURCE_BASED_VERIFICATION.md)、[渲染判定](RENDER_CONSISTENCY.md)及[日志规范](../tools/RUNS_AND_REPORTS.md)。报告或机械检查通过不替代行为验证。

## 构建审阅文件

使用 CPython 3.13。协调修改项目版本、Python `__version__`、安装示例、发行说明及必要 workflow 默认值；依赖变化必须有单独理由。提交干净候选后构建一次：

```shell
python tools/release_package.py build --out test-runs/NEW-RELEASE
```

输出 wheel、sdist 和固定 SHA manifest，绑定构建提交、产品源文件、独立夹具、验证工具与固定原版观察。正式候选不使用 `--allow-dirty`。

审阅实际 wheel/sdist 中的描述、Documentation URL、版本、依赖、许可及包资源。README 中的链接应能从 PyPI 独立访问；Documentation 必须指向用户入口。

## 验证与上传

创建新的不可变 tag 后，用已有 GitHub 工具保存同一组资产，记录 manifest SHA。`release_github.py create` 不覆盖已有不同字节资产；`dispatch --publish` 启动 `.github/workflows/publish-pypi.yml`。

流水线依次执行：

1. Windows/Linux 各自在仓库外独立安装 wheel、sdist，核查导入来源、API、CLI、静态图种、VChart、资源及合同方法。
2. Linux 实际 IANA 时区检查闭合 Windows 明确跳过的 `tzset` 项，不把跳过写成通过。
3. 两个平台均成功后，OIDC 上传同组已验证文件。
4. 从实际 PyPI 下载 wheel、sdist，核文件集合、字节大小和 SHA，再独立安装并验证。
5. 回读成功后将 GitHub Release 标记为正式版，保存永久发行凭据和当前状态。

工具用法可用 `python tools/release_package.py --help`、`python tools/release_github.py --help` 查询。CI 失败保留原始日志与资产，不移动 tag、不覆盖失败证据，也不更换上传字节绕过验证。

## 元数据和交付

现有 PyPI 版本描述不会随 GitHub 编辑自动更新，需要新版本发行。当前包支持 CPython 3.13、Windows AMD64 和 Linux glibc 2.28+ x86_64；CPU 安装检查不替代另行声明的 GPU 验收。

发行记录分别保存构建提交、tag、manifest、CI、实际索引文件 SHA、隔离安装、已知限制和发布时间。旧证据仍绑定其原始候选，不能换上新版本或新 SHA。最终说明真实发布状态，并更新[当前发行状态](RELEASE_STATUS.md)。
