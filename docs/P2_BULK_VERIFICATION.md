# 本批 P2 测试设计合同

2026-11-06，P1 门禁已完成，状态仅为 `code_complete_unverified`。
冻结候选：`97b353ebf7e176a750a736a714c85638e0a497b722e451dc77570579a2d36cbb`。
装配 run：`BULK-P1-assembly-20261106T040205Z-6d6594fb`；
冻结 run：`BULK-P1-freeze-20261106T040338Z-8ecb17c2`。

## 当前门禁

P2 只设计与编写来源独立测试、fixture、oracle 与比较工具。
可以编译、导入、检查测试发现与签名；不执行产品 parse/build/layout/render、正式单测、官方图像或截图。
任何产品源码新疑点记录为 P3 待查，保留此 P1 候选供全分组首次运行，不能逐图边测边修。
只有所有保留入口与跨图能力的测试设计收齐，才统一进入 P3。

只读产品模型/公开接口用于绑定断言是允许的；输入与期望必须从固定源 grammar/DB/spec/fixture/styles/renderer 得到，
不能把 Python 输出抄为预期、用当前分支条件反推期望或只检查注册/成功。

## 范围与写 owner

- A：`tests/bulk/a/**`、`tests/bulk/cases-A.json`、`references/bulk-A-assertions.json`、`docs/changes/bulk-A-P2.json`。
  保留 F02 六入口、mindmap/treeView、F08 四入口，共 12 个。
- B：`tests/bulk/b/**`、`tests/bulk/cases-B.json`、`references/bulk-B-assertions.json`、`docs/changes/bulk-B-P2.json`。
  temporal 四入口、business 六入口，共 10 个。
- C：`tests/bulk/c/**`、`tests/bulk/cases-C.json`、`references/bulk-C-assertions.json`、`docs/changes/bulk-C-P2.json`。
  sequence、railroad 四入口、zenuml、info；另外来源独立的泳道路由纯数值断言可置该目录。
- root：`tests/bulk/shared/**`、根 `tests/bulk/__init__.py`、共享 support、`tools/**`、总测试清单/阶段与最终报告。
  13 跨图能力适用部分、原 F01 回归、数学集成及原生设备/导出/线程/离线资源矩阵。

统计图表四入口、treemap、sankey、venn 继续 `deferred_by_user`，不进入本批门禁与计数。
已有历史测试保留，不能将其改写为新源码通过证据。

## 测试要求

1. 按实际源生产 grammar、DB 动作、配置/样式和算法分支逐项建立输入与断言索引；源测试中的参数表、
   helper 生成器、正例、负例、多断言与边界不以文件数代替覆盖率。
2. 正例检查实际语义字段、顺序、标识符/引用/分组、标签与格式、方向、约束和 source span。
   负例检查源码确实拒绝的输入、错误类别/位置；不能将任何异常都当预期语法失败。
3. 专用算法需来源独立的数值/几何/约束断言，特别是 COSE/tidy/fCoSE、日历/DST/远年、
   Git 图、泳道周期/排序/端口/路由/方向/标签；不只检查返回非空。
4. 渲染 fixture 覆盖全部保留语法/形状/样式分支以及默认/显式配置，保留原始 A/B 图。
   像素差仅诊断；内容、连接、包含/排序、可读性、意外裁切、设备策略与静态导出是门禁。
5. 原源异常/未消费元数据列明 `upstream_defect` / `source_unconsumed`，P3 采集官方结果确认；
   不能单凭 Python 当前没有实现就删掉分母或记源不支持。
6. 模块测试使用 `unittest`，每个 owner 目录有 `__init__.py`，便于集中 discover。
   原生异步测试用 `IsolatedAsyncioTestCase`，所有 Canvas 对象留在创建线程。

## 通用渲染 fixture 格式

各组 `cases-*.json`：

```json
{
  "schema": "py-mermaid-bulk-cases/v1",
  "group": "A",
  "cases": [
    {
      "id": "A-kind-source-case-id",
      "kind": "classDiagram",
      "source": "完整原始Mermaid输入",
      "config": {},
      "origin": {
        "path": "packages/mermaid/src/...",
        "sha256": "固定源SHA256",
        "symbol": "源case/production/renderer分支",
        "line": 1
      },
      "expect": "render",
      "features": ["来源功能ID"],
      "expectedText": ["可见文本"],
      "expectedErrorCodes": []
    }
  ]
}
```

`id` 使用 ASCII 字母/数字/`._-`，组内唯一。`expect` 为 `render`、`syntax_error`、
`upstream_defect` 或 `excluded_by_static_scope`；最后一类只登记来源，不计通过或待迁移。
需要 renderer/config 错误时可用 `expect: "error"` 并填写精确 expectedErrorCodes。
`origin.path` 相对固定 Mermaid checkout；ZenUML 外源另加 `origin.repository="zenuml-core"`，
`path` 相对其固定 source checkout；依赖算法同样用明确 repository/version/path。
纯合成边界输入必须注明对应 production/分支，不伪称原测试原文。

资源可用可选 `resources`：`images: {id: {path,mime?,sha256?}}`、
`icons: {id: {path,sha256?}}`、`fonts: [{family,path,sha256?}]`；path 相对仓库根，
仅显式读取本地文件，不自动下载。
`expectedText` 必须是真实可见内容，源 label 有分行/截断/公式时写说明与专用断言，
不要要求字体引擎给出完全相同的 run 切片。

原测试断言索引与 fixture 的数量分别记实；fixture 不是全部单元测试分母。
P2 回执写明设计覆盖、原文件 SHA、已编码的实际用例/断言、剩余疑点与未执行事实。

## P3 已验证的空画面合同扩展

合法空铁路图和全隐藏样式不能被白图负控制误判，也不能放行任意空输出。
仅在原 renderer/样式及官方原始 PNG 均证明空画面时，fixture 填
`expectedEmpty: {"background":"white","reason":"具体来源分支与证据"}`，`expectedText` 必须为空。
源算法固定尺寸时另外填写 `width`/`height`；全部隐藏但字体/宿主自然尺寸可变时省略尺寸。
检查器要求全 RGBA 背景、无实际可见绘制 trace，并用注入非空像素的副本证明会拒绝；
官方比较还必须确认 A 原图也满足同一空画面合同。原始图片不修改。
