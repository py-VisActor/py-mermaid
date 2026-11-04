# F01.1 渲染效果报告

后续推荐使用统一命令 `python tools/workflow.py report --spec tools/report_specs/f011-baseline.json`，自动生成独立日志run和 `reports/<run-id>/index.html`，保留原报告。完整的日志格式、配置、重渲染与HTTP服务命令见 [复用规范](../tools/RUNS_AND_REPORTS.md)。当前服务可通过 `http://127.0.0.1:8765/f011-render-comparison.html` 查看原报告。

打开 [HTML 对比报告](f011-render-comparison.html)。这是单文件离线报告，内嵌原始PNG和已有结果，不需要服务器、安装或网络。

包含12个正例、3个非法输入和CPU/Auto/GPU三个profile，可切换并排、左上角叠加、差异热图、差异掩码，查看输入源码、已保存功能检查、原始尺寸、像素指标和SHA。支持缩放显示、搜索、前后导航及下载原图/输入/本例证据JSON。

报告引用 `test-runs/f011-s5-final-001/` 和 `test-runs/f011-s5-official-001/` 的现有产物。原图和差异图按已有SHA核对；图片未重绘、配准、拉伸或裁切。像素差异仅诊断，功能状态来自已有比较报告。

生成命令（输出路径必须不存在）：

```shell
python tools/build_f011_html_report.py --out reports/new-f011-comparison.html
```

生成器只使用Python标准库读取已有文件，不运行产品渲染、测试或安装验证。输入指纹、生成器/模板SHA及HTML自身SHA见 [manifest](f011-render-comparison.manifest.json)。报告仅代表保存的F01.1候选，系统字体未捆绑，Linux/no-loader及其他图种不在本轮验证结论内。
