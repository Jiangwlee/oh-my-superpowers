# Extended Review Checklist
#
# 按变更风险加载，与 core checklist 配合使用。
# 加载时机：涉及性能、并发、I/O、公共接口、类/模块设计或其他非平凡结构风险时加载

## Review Standard

- Treat maintainability and design checks as investigation signals, not automatic findings.
- Mark a maintainability issue `BLOCKING` only when it causes a current contract violation or demonstrably wrong behavior and includes complete blocking evidence.
- Keep concrete future maintenance cost as non-blocking `FOLLOW_UP`. Keep wording polish, stylistic alternatives, and unsupported future risk as `ADVISORY`.

## 3. Performance

- [ ] N+1 查询：循环内是否有数据库查询或网络请求？能否批量化？
- [ ] 无界循环/递归：是否有缺少终止条件或上限的循环？
- [ ] 缺失索引：新增的数据库查询是否利用了索引？WHERE 条件是否可能全表扫描？
- [ ] 不必要的内存分配：是否在循环中重复创建大对象？是否可以复用？
- [ ] 阻塞操作：I/O 密集操作是否在主线程/事件循环中同步执行？
- [ ] 缓存缺失：重复计算的结果是否可以缓存？

### Performance 启发式问题

- 如果数据量增长 100 倍，这段代码还能正常工作吗？
- 这个操作的时间复杂度是什么？有没有更优的算法？

## 4. Maintainability

- [ ] 命名清晰度：变量名/函数名是否准确表达其含义？含糊命名是否造成了具体理解或维护风险？
- [ ] 职责边界：函数是否混合了多个职责，导致理解、测试或修改困难？
- [ ] 控制流：嵌套是否遮蔽了主要路径、错误路径或终止条件？
- [ ] 重复代码：相似实现是否已经产生漂移或缺陷风险？抽象能否降低风险而不引入过度设计？
- [ ] 错误处理：异常是否被合理处理？错误信息是否对调试有帮助？
- [ ] 代码异味：God class、feature envy、primitive obsession、long parameter list？

### Maintainability 启发式问题

- 一个新人读这段代码，能否在 5 分钟内理解它的作用？
- 如果需要修改这段代码的行为，改动范围有多大？

## 5. Design Risks

> 仅在 diff 涉及类/模块设计时检查。对小改动（单函数修改、bug fix）跳过本节。

- [ ] **职责耦合：** 类或模块是否混合了独立变化的职责，导致无关行为必须一起修改或测试？
- [ ] **扩展风险：** 变更是否绕过已有扩展点或破坏稳定契约，导致回归、分支复制或调用方迁移？
- [ ] **替换契约：** 子类型或实现是否违反调用方依赖的行为、输入或输出契约？
- [ ] **接口耦合：** 接口是否迫使调用方依赖不使用的能力，并造成具体变更传播？
- [ ] **依赖方向：** 高层策略是否耦合到易变的具体实现，导致测试、替换或演进困难？

> 这些原则只用于定位风险。只有能说明具体影响时才报告 finding；不要为了满足设计原则而过度设计。
