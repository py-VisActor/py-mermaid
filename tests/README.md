# 测试目录

用户最新 [执行顺序](../docs/FULL_MIGRATION_PLAN.md)要求先写完全部功能源码 P1，再在 P2 根据原实现建立正式用例和单测，P3 分组运行/统一排查修复，P4 最终全量。现有 bootstrap/依赖/计划工具控制只检查资料，不作为 P1 的 Mermaid 功能测试。完整测试设计见 [来源验证方案](../docs/SOURCE_BASED_VERIFICATION.md)。

交接任务图可用 `python scripts/validate_migration_plan.py --check` 检查阶段屏障、任务引用和功能分母；该命令不运行产品。

通用 [像素工具控制](pixel_compare/test_pixel_compare.py)独立执行 `python -m unittest discover -s tests/pixel_compare -v`，先安装 [开发专用依赖](../tools/pixel_compare_requirements.txt)。这些检查验证通道/alpha/尺寸/tile/模式与报告安全性，不是提前执行 Mermaid 的 P2/P3 业务测试；使用方法见 [PIXEL_COMPARE](../tools/PIXEL_COMPARE.md)。

当前 [bootstrap](bootstrap/test_bootstrap.py) 测试开发资料、覆盖分母和来源锁的负控制，不加载 Canvas，不称为 Mermaid spec 通过。

```shell
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py check
```

[fixtures](fixtures/README.md)放共享文本及 case 元数据；后续按 parser、layout、render、exports、lifecycle、deployment 分组增加真实断言。不要批量创建成功的空测试，也不要把 CI 的 bootstrap 成功换成渲染状态。

Canvas 依赖真实检查见 [examples](../examples/README.md)，官方 JS oracle 要求见 [tools/oracle](../tools/oracle/README.md)。完整门禁见 [TEST_AND_RELEASE](../docs/TEST_AND_RELEASE.md)。

[依赖审计控制](dependencies/test_dependency_audit.py)仅验证固定 pnpm 结构的读取边界、peer/patch 上下文、重复键和来源身份拒绝路径。独立执行 `python -m unittest discover -s tests/dependencies -v`；真实锁定源码的清单比较另执行 `python scripts/audit_dependencies.py --check`。详情见 [第三方依赖盘点](../docs/THIRD_PARTY_DEPENDENCIES.md)，不运行 Mermaid 或 Canvas。

[完整树控制](dependencies/test_dependency_tree.py)补查原始锁 snapshot 分母、全部边目标、工作区/alias 解析、可选边、共享/循环回指、额外源码根和 SCC 的依赖优先层号。同一目录命令一起运行；生成物一致性另执行 `python scripts/build_dependency_tree.py --check`。选型范围见 [迁移方案](../docs/DEPENDENCY_MIGRATION.md)。
# 当前 F01.1 基础流程图

日志/报告工具的独立回归位于 `tests/tooling/`，覆盖退出码与原始流、超时/启动失败、不可覆盖、指纹损坏、配置/候选错配、单profile报告及本地服务日志。使用 `python tools/workflow.py record --scope tooling --name evidence-tests -- python -m unittest discover -s tests/tooling -v` 保存标准证据。功能测试批次可用 `python tools/workflow.py batch --plan tools/plans/f011-tests.json`；完整规范见 [RUNS_AND_REPORTS](../tools/RUNS_AND_REPORTS.md)。

当前范围以 [F01.1计划](../docs/F01_1_EXECUTION_PLAN.md)为准。`tests/f011/` 包含来源独立的语言/配置、真实布局、Canvas/PNG/生命周期和公开API用例；源码先完成，再设计测试，再保存首轮失败并按根因修复。独立期望与来源SHA见 `references/f011-*-assertions.json`。多重边/自环等额外边界检查不代表后续图种或全部语法已支持。

```shell
python -m unittest discover -s tests/f011 -v
```

先安装本地包，或开发时显式设置PYTHONPATH=src。真实ELK测试需要正常脚本main入口和py-visactor-elk0.1.0，图像检查使用开发依赖Pillow12.3.0。GPU-required测试在缺设备环境明确失败，不用CPU或skip替代。官方对照及比较器入口见 [工具说明](../tools/oracle/README.md)。
