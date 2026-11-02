# 第三方来源与许可

本项目沿用根 [MIT LICENSE](LICENSE)。

- Mermaid：固定 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`，MIT；版权原文保留于 [references/licenses/mermaid-LICENSE](references/licenses/mermaid-LICENSE)。当前只提交来源元数据与索引，完整参考 checkout 不进入发行包。
- py-skia-canvas：依赖 0.1.0a18，使用其公开 Python API。其 wheel 内含自身及 Rust/Skia 等第三方许可；本项目不复制其核心或原生库。
- Mermaid 的 Dagre/ELK/D3/RoughJS/KaTeX/Iconify/ZenUML 等依赖：锁定源码中的包/lock 只提供来源起点，实际移植/打包前逐项审计版本、传递依赖和许可。不能从 Mermaid 主仓库 MIT 推断所有依赖或资源均为 MIT。
- 系统/用户字体、图标及图片：不随本骨架复制，后续共享 fixture 资源须附独立许可、来源与 SHA。

任何后续源码移植需要同步来源映射和本说明。发布前检查最终 wheel 实际携带的代码、资源、NOTICE 和许可证。
