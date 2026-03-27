# 讨论流程详细 SOP
#
# 用途：补充 SKILL.md 高层 SOP 的执行细节
# 加载时机：进入每轮循环前

## Phase 0: 初始化

### Step 1: 创建 Session

```bash
export ROUND_TABLE_SESSION=$(omp-round-table start "<topic>")
```

### Step 2: 选择参与者

从 `references/roles.md` 选取 3-5 人：
1. 根据议题关联度排序
2. 确保至少一对对立视角
3. 确保至少一个"意外视角"
4. 用户可指定或调整

### Step 3: 生成角色 Prompt

为每个参与者生成 `participants/<role-id>.md`：
- 使用 `assets/participant-prompt.md` 模板
- 填充角色档案（来自 roles.md）
- 写入 session 目录

### Step 4: 写入背景

编辑 session 目录的 `context.md`：
- 议题
- 讨论目标
- 约束条件（技术栈、时间、团队规模等）
- 用户提供的额外背景

### Step 5: 展示并确认

向用户展示：
- 议题
- 参会者列表（姓名、角色、runtime/model）
- 等待用户确认开始

## Phase 1: 每轮循环

### Step 1: 确定引导问题

- **第 1 轮**：定义性问题——"我们应当如何定义 [核心概念]？"
- **后续轮**：从上轮核心争议中生长出的更深问题
- **用户选"深入"**：围绕当前争议点构造更聚焦的问题
- **用户给了具体意见**：将用户观点融入引导问题

### Step 2: 构建 Prompt

按 `references/prompt-templates.md` 的四层结构拼接。

将每个参与者的完整 prompt 写入临时文件，用于 spawn。

### Step 3: 启动参与者

```bash
omp-round-table spawn <round-number>
```

spawn 会：
1. 在 tmux 中并行启动所有参与者
2. 等待所有进程完成（超时 5 分钟）
3. 返回 JSON 结果（completed/failed 列表）

### Step 4: 收集回复

对每个完成的参与者：

```bash
omp-round-table post-message <role-id> <response-file> \
  --round N --name "人物名" --action "行动标签" --summary "一句话"
```

注意：orchestrator 需要阅读每个 response 文件，提取行动标签和摘要，然后调用 post-message。

### Step 5: 综述

Orchestrator 作为主持人：

1. **提炼核心争议点**：不是面面俱到，找最深的裂缝
2. **生成 ASCII 框架图**：
   - 形式不固定：2x2 矩阵、光谱轴、因果环路、层级树
   - 选最见骨的形式
   - 标出正/负反馈环、因果链、张力维度
3. **提出下一轮引导问题**：从核心争议中生长出来的更深问题

将综述写入文件并 post：

```bash
omp-round-table post-message moderator <summary-file> \
  --round N --name "主持人" --action "综合" --summary "本轮一句话摘要"
```

### Step 6: 用户参与

展示给用户：
- 本轮各参与者发言摘要
- 核心争议点
- ASCII 框架图
- 下一轮引导问题

等待用户输入，处理指令：

| 指令 | 动作 |
|------|------|
| 继续 / 可 | 接受引导问题，进入下一轮 |
| 结束 / 止 | 进入 Phase 2 |
| 深入 / 深入此节 | 不推进新问题，围绕当前争议深挖 |
| 换人 / 引入新人物 | 询问用户要引入谁，更新 participants |

将用户回复 post 到 session：

```bash
omp-round-table post-message user <user-input-file> \
  --round N --name "用户" --action "指令" --summary "用户意图"
```

### 轮次软提醒

超过 5 轮时，在综述末尾添加：

> 提示：讨论已进行 N 轮。如果核心议题已充分展开，建议考虑收敛。你可以说"结束"进入总结阶段。

不阻断，只提醒。

## Phase 2: 结束

### Step 1: 全局总结

Orchestrator 做最终综述：
- 回顾所有轮次的核心争议演变
- 提炼最终结论（共识点 + 分歧点）
- 列出未解决的开放问题
- 给出行动建议

### Step 2: 生成文档

```bash
omp-round-table end --output-dir "$(pwd)/docs/round-table"
```

`end` 命令生成基础文档框架，但 orchestrator 应该补充：
- 最终结论（替换占位符）
- 未解决问题
- 行动建议

### Step 3: 展示结果

向用户报告：
- 文档路径
- 关键结论摘要
- 建议的下一步行动

## 主持人行为准则

- **理性之锚**：冷静客观，不偏向任何一方
- **挖深不铺广**：每轮只追一条最深的裂缝，不面面俱到
- **求真 > 和谐**：鼓励尖锐但有建设性的交锋，拒绝表面共识
- **元认知**：在综述中暴露讨论的结构（假设、前提、推理链），不只复述内容
