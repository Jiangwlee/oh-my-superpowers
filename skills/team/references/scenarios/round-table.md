# Round Table (轻量版)

> pattern: discussion
> 多 agent 多轮讨论。用 omp-team run 原语搭建，无 session 管理。

## 与 round-table skill 的区别

| 维度 | round-table skill | team round-table |
|------|------------------|-----------------|
| Session 生命周期 | 完整管理（init/end/status） | 无 |
| 角色 prompt 库 | 内置 roles.md | 无，用 role-activation.md 临时定义 |
| 历史消息持久化 | SQLite + post-message | 无，靠 output-file 文件传递 |
| 讨论流程 | 结构化 SOP（spawn/collect/watch） | Orchestrator 自由编排 |
| 适合场景 | 正式讨论、需要完整记录 | 快速临时讨论、不需要完整记录 |

## 参与者配置

- 2-5 个参与者，每个用 `prompts/role-activation.md` 定义角色
- 建议使用不同 runtime 增加视角多样性
- 每个参与者的 prompt 应包含：角色定义 + 讨论话题 + 前一轮上下文 + Action Tag 要求

## 编排流程

### 每轮

1. **构造 prompt**: Orchestrator 为每个参与者构造本轮 prompt：
   - 话题/引导问题
   - 前一轮所有参与者的输出作为上下文
   - 要求使用 Action Tag 标注发言类型
   - 要求以 `简言之:` 一句话结尾

2. **并行执行**:

```bash
omp-team run claude --prompt-file round-1-participant-A.md --output-file r1-A.txt &
omp-team run codex --prompt-file round-1-participant-B.md --output-file r1-B.txt &
omp-team run pi --prompt-file round-1-participant-C.md --output-file r1-C.txt &
wait
```

3. **收集与综述**: Orchestrator 收集所有输出：
   - 提炼本轮核心争议点
   - 生成 ASCII 框架图（矩阵/光谱/因果环路——选最贴合结构的形式）
   - 提出下一轮引导问题

4. **决策**: Orchestrator 决定下一步：
   - **继续** — 用新引导问题进入下一轮
   - **收敛** — 论点已充分，生成最终结论
   - **深入** — 不推进新问题，围绕当前争议深挖
   - **换人** — 引入新参与者（构造新角色 prompt）

### Action Tags (建议在 prompt 中要求使用)

| Tag | 含义 |
|-----|------|
| 陈述 | 阐述新观点 |
| 质疑 | 对他人观点提问 |
| 补充 | 在他人观点上添加 |
| 反驳 | 反对他人观点并给出理由 |
| 综合 | 整合多方观点 |

每条发言格式：

```
【角色名】【Action Tag】：发言内容

简言之: 一句话压缩
```

## 完成判定

- 达成共识（各方立场趋同）
- 达到最大轮次（建议 3-5 轮）
- 用户指示停止
- 超过 5 轮时，orchestrator 应主动提示考虑收敛

## 示例编排序列

```
[Orchestrator] 话题: "AI Agent 是否需要长期记忆？"
  - 参与者 A (claude): 认知科学研究者
  - 参与者 B (codex): 系统架构师
  - 参与者 C (pi): 产品经理

[Round 1] 定义问题 → 并行发言 → 综述 + ASCII 图
[Round 2] 深入核心分歧 → 并行回应 → 综述
[Round 3] 收敛 → 各方修正立场 → 最终结论
```
