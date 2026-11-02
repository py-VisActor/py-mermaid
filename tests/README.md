# 测试目录

当前 [bootstrap](bootstrap/test_bootstrap.py) 测试开发资料、覆盖分母和来源锁的负控制，不加载 Canvas，不称为 Mermaid spec 通过。

```shell
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py check
```

[fixtures](fixtures/README.md)放共享文本及 case 元数据；后续按 parser、layout、render、exports、lifecycle、deployment 分组增加真实断言。不要批量创建成功的空测试，也不要把 CI 的 bootstrap 成功换成渲染状态。

Canvas 依赖真实检查见 [examples](../examples/README.md)，官方 JS oracle 要求见 [tools/oracle](../tools/oracle/README.md)。完整门禁见 [TEST_AND_RELEASE](../docs/TEST_AND_RELEASE.md)。
