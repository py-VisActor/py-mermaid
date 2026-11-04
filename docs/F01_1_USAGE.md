# F01.1 使用与支持边界

当前只交付基础流程图，尚未发布。Python 3.13，Canvas0.1.0a18，py-visactor-elk0.1.0。目标与进度见[计划](F01_1_EXECUTION_PLAN.md)、[账本](execution-state.json)。

## 接口

`parse(text, *, config=None) -> Flowchart` 返回不可变原文、方向、有序节点/边、配置和源位置，不创建Canvas/ELK。`MermaidError` 含code及适用span：原文Python字符偏移、UTF-16偏移、1-based行/0-based UTF-16列，span半开。

`render(text, *, config=None, format="png", backend="auto") -> RenderResult` 返回data bytes、实际width/height、image/png、纯值模型/测量/布局/绘制trace及backend状态。`arender`参数相同，适合已有事件循环；sync render在活动loop内明确提示使用arender。

```python
import asyncio
from pathlib import Path
from py_mermaid import arender

async def main():
    result = await arender("graph LR; A[Start] --> B[End]", backend="cpu")
    Path("result.png").write_bytes(result.data)

if __name__ == "__main__":
    asyncio.run(main())
```

脚本需要main保护以满足ELK进程spawn。Canvas创建/测量/绘制/编码留在调用线程；每次请求独立解析和ELK worker生命周期。GPU-required不隐式退CPU。backend只记录状态，不替代完整native追踪。

## 语法

支持入口flowchart/graph、方向TD/LR、普通矩形A[Label]、裸引用A、双引号普通标签、有向边A --> B、多段链、分支/合流、分号/换行分隔及整行%%注释。重复显式标签更新文字，保留首次插入顺序。Unicode实际字形取决于系统字体。

同行节点/边之后的%%不是固定上游的合法注释，明确拒绝。非法/不完整输入给诊断，不截断后假成功。其他方向、边标签、子图、其他形状、样式语句、frontmatter/directive、HTML/Markdown/math/图标与实体语法留待后续。

## 默认配置

layout=elk，有效theme=redux-color/look=neo。不能从全局default/classic推断图种外观。默认有效字体14px、`"Recursive Variable", arial, sans-serif`；白节点、#28253D边框/文字、黑边、2px描边；标签最小宽120、换行宽120、padding16/12、4px透明黑影。

仅接受已实现配置键，未知配置拒绝。htmlLabels控制普通文本排版含义，不创建HTML/DOM；富标签仍拒绝。maxTextSize按UTF-16计数，maxEdges限制边数。flowchart.diagramPadding控制留白；minNodeWidth/wrappingWidth影响测量。

root fontFamily按源码桥接到主题字体；root fontSize保留站点值，不能等同主题有效字号。flowchart.padding/nodeSpacing/rankSpacing保留配置值，但默认neo矩形采用16/12 padding，固定ELK adapter采用base spacing40；这些站点值不被错误映射为实际几何变化。其他主题/look和布局选项后续实现。

## 运行与限制

`python examples/basic_flowchart.py --out NEW.png` 调用真实ELK和Canvas，已有文件拒绝覆盖。auto保留默认，cpu显式请求CPU，gpu要求实际GPU。字体不打包，CJK/emoji/fallback结合真实PNG审阅。

Windows本地结果与Linux/no-loader未验项分别记录。输出为静态PNG和诊断数据；没有浏览器事件或HTML accessibility tree。完整功能分母保留在长期清单，不因本轮局部验证提升为完整兼容。
