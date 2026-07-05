# Philosophy — Predictability 及其杠杆

Purpose: 解释造 skill 时"为什么这样切"的底层模型。所有决策服务于一个根德性：predictability。术语定义见 `foundation.md`。
Sections: 根德性 | 两种成本 | 信息层级 | 转向（Steering） | 修剪（Pruning）

## 根德性：Predictability

Skill 存在的意义是**从随机系统里榨出确定性**。根德性是 predictability —— agent 每次走相同的**过程**，而非产出相同的文本（一个 brainstorming skill 应当**可预测地**发散）。成本、可维护性都是它的症状，不是对手。下面每个杠杆都服务于它。

## 两种成本（Invocation）

skill 怎样被触达，决定你付哪种成本：

- **Model-invoked**：保留 `description`，agent 能自主触发，其他 skill 也能触达。代价是**context load** —— description 每轮常驻窗口。仅当 agent 必须自主够到它时才选。
- **User-invoked**：`disable-model-invocation: true`，去掉 description。零 context load，但付**cognitive load**（人要记得它存在）。

拆分 skill 就是在花这两种成本之一。**不要为"模块化"而拆**：更多 model-invoked skill = 更多 description 抢注意力；更多 user-invoked skill = 更多要人记。只在有一个**独立引导词**该触发它、或另一个 skill 必须够到它时，才按 invocation 拆。

## 信息层级（Information Hierarchy）

skill 的内容按"agent 多快需要它"排成一把梯子：

1. **In-file step** —— SKILL.md 里的有序动作，主层。每步落在一个 **Done 判据** 上。
2. **In-file reference** —— SKILL.md 里按需查的定义/规则。常是合法的扁平同级集（一场 review 的每条规则同一层），不是坏味道。
3. **Disclosed reference** —— 移出 SKILL.md、藏在 context pointer 后，pointer 触发才加载。

**渐进披露**是往下移的动作，保护顶层可读。判据是**分支**：每条路径都要的内联，只有部分分支够到的下沉。一个指向必读材料却触发不稳的 pointer 是 variance bug —— **先改措辞**，改不动才拉回内联。

**Co-location**：同一时刻要一起读的东西（一个概念的定义、规则、注意事项）放同一标题下，别散落。梯子决定"下沉多深"，co-location 决定"落地后旁边放什么"。

## 转向（Steering）

塑造 agent 运行时行为的杠杆：

- **Leading word（引导词）**：一个预训练已有的紧凑概念（如 _lesson_、_fog of war_、_tracer bullets_），反复作为 token 出现，累积成分布式定义，锚定一整片行为。自造词要先花 token 定义，回报低 —— **优先复用已有词**。同一个词若也活在你的 prompt、文档、代码里，skill 触发更可靠。
- **Completion criterion（Done 判据）**：两个属性使它成为杠杆。**清晰度**（能否分辨 done / not-done）抵抗 premature completion —— 模糊的界（"理解已达成"）让 agent 提前宣布完成、溜向下一步。**要求度**（要求多少）决定 legwork —— "每个改动的 model 都交代"逼出彻底的活，"给个变更清单"不会。最强的判据既可检验又穷尽。
- **Premature completion（提前完成，失败模式）**：在真正做完前结束当前步。两股力拔河：可见的后续步骤（往前拉）与 Done 判据的清晰度（抵抗）。**先锐化判据**（局部、便宜）；只有判据不可避免地模糊、且你真观察到 agent 在赶时，才把后续步骤藏起来（拆到独立上下文 / subagent，内联的 model-invoked 藏不掉）。

## 修剪（Pruning）

保持 skill 精简，每个补救对应一种失败：

- **Single source of truth**：每个含义只在一处。违反即 **Duplication**（改一处要改多处、涨 token、抬高该含义在梯子上的虚假权重）。
- **Relevance**：每行是否还关乎 skill 所做的事。失效有二：从不关乎（纯说明），或变陈旧。
- **No-op（失败模式）**：模型默认就会做、写了也不改变行为的指令。测试：这行相对默认行为改变了什么吗？一个弱到打不过默认的 leading word 就是 no-op，修法是换更强的词，不是换技术。
- 逐句而非逐行地猎杀 no-op；一句没通过就删整句，别只修词。**放胆删** —— 大多数没通过的散文该删而非重写。
