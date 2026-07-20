# Core Review Checklist
#
# 所有 diff 规模必检。review 执行者按此清单逐项检查。
# 加载时机：每次 review 都加载

## Review Standard

- Treat checklist items and heuristics as investigation signals, not automatic findings.
- Apply repository-specific instructions and conventions before generic guidance.
- Report an issue only when the change causes a concrete correctness, security, performance, or maintainability impact.

## 1. Correctness

- [ ] 逻辑是否正确？条件判断、循环、递归的终止条件是否成立？
- [ ] 边界条件是否处理？空值、零值、空集合、超大输入、并发访问
- [ ] 是否满足原始需求？对照 diff 上下文中描述的目标逐条验证
- [ ] 错误路径是否正确？异常抛出/捕获是否合理，是否有静默吞错
- [ ] 类型是否匹配？函数参数/返回值类型是否与调用方一致

### Correctness 启发式问题

- 如果输入为 null/undefined/None，这段代码会怎样？
- 如果这个操作执行了两次，结果是否符合预期（幂等性）？
- 是否有 off-by-one 错误？

## 2. Security

- [ ] 注入风险：用户输入是否直接拼入 SQL / shell 命令 / HTML？
- [ ] 硬编码密钥：是否有 API key、password、token 出现在代码中？
- [ ] 认证/授权绕过：权限检查是否可被跳过？是否有未保护的端点？
- [ ] 不安全的反序列化：是否将不可信数据交给 `pickle.loads`、`eval`，或其他会执行代码、实例化任意类型或触发危险钩子的机制？
- [ ] 路径遍历：文件操作是否校验路径，防止 `../` 逃逸？
- [ ] 依赖安全：新引入的依赖是否来自可信来源？是否有已知漏洞？

### Security 启发式问题

- 如果攻击者控制了这个输入，能造成什么损害？
- 这段代码是否信任了不该信任的数据源？

## 反模式检查

### 反 sycophancy 规则

**强制要求：发现问题必须指出。** 禁止以下行为：
- "代码整体很好，只有几个小建议" — 如果有问题就直接列出，不需要先肯定
- "这是个不错的实现，不过..." — 不要用赞美包裹批评
- 无 issue 时直接输出 "No issues found."，不要编造问题凑数

### YAGNI 检查

- [ ] 新增的抽象（接口、基类、工厂）是否解决了当前存在的变化、重复或契约需求？还是只增加了间接层？
- [ ] 新增的配置项是否满足当前需求？还是引入了没有实际使用场景的选择？
- [ ] 新增的参数是否被调用方实际使用？

### Removal Candidates

- [ ] 变更中是否引入了死代码（不可达分支、未调用的函数）？
- [ ] 是否有未使用的 import / require？
- [ ] 是否有遗留的 debug 代码（console.log、print、debugger、TODO/FIXME）？
- [ ] 是否有被注释掉的代码块？
