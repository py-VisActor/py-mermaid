# F01.4 静态流程图用法

本轮静态范围已完成本地验收，详见 [验收记录](F01_4_ACCEPTANCE.md)；用法与环境边界以下述说明为准。固定 mermaid@12.2.0，生产只依赖公开 py-skia-canvas 与 pyelk，不执行 JavaScript。数学为独立后续模块，交互和 Dagre 已排除，安装验证暂缓。

```python
from pathlib import Path
from py_mermaid import render, ResourceBundle, ImageResource, IconResource, FontResource, ExportOptions

if __name__ == "__main__":
    diagram = '''flowchart LR
A@{shape: doc, label: "Input"} e1@-->|read| B@{shape: cyl, label: "Storage"}
classDef selected fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
class A selected
linkStyle 0 stroke:#0369a1,stroke-width:3px
'''
    result = render(diagram, backend="auto", format="svg")
    Path("flowchart.svg").write_bytes(result.data)
```

`parse` 只生成不可变语义值；`render` 同步、`arender` 异步；ELK worker 需要脚本 main 保护。支持 png、jpg/jpeg、webp、svg、pdf；ExportOptions 提供 quality、density、matte、outline、downsample。SVG/PDF 通过 Canvas 公开静态编码入口输出，不携带点击、导航、脚本或 DOM 交互行为。

资源必须显式提供。ImageResource(id,data,mime) 使用 bytes；IconResource(id,svg) 使用独立 SVG；FontResource(family,path) 注册调用者指定的字体文件。以 ResourceBundle(images=(...),icons=(...),fonts=(...)) 传给 render/arender 的 resources 参数。网络 URL 只能作为 bundle 的查找 key，不自动抓取。inline SVG 与 data:image;base64 属显式离线资源，仍进行内容与预算校验。资源缺失或不安全明确诊断。未提供 Iconify 图标时保留固定源码的问号回退。legacy Font Awesome 名称须以同名 IconResource 显式映射，不模拟外部 CSS 字体映射。

方向支持 TB/TD、LR、RL、BT 及来源方向别名。`layout` 支持 elk、elk.stress、elk.force、elk.mrtree、elk.sporeOverlap、elk.box、elk.rectpacking；源支持的组 algorithm 与公开 elk 配置见来源映射。算法使用真实 pyelk 实现；不支持项明确拒绝，没有算法回退。非路由算法按来源画中心直线并裁至节点轮廓。

`look="handDrawn"` 与 `handDrawnSeed` 控制纯 Python 手绘路径：非零 seed 可重复；0 保留来源随机语义。边 animate/animation 只影响初始可见线型，没有动画播放器。`@{view: collapsed}` 仅绘制初始折叠状态，没有展开控件行为。
