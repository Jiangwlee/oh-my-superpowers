# Evidence Sources

`omp-evolution scan` 输出两段数据：机械信号和 session 样本。

## 机械信号（脚本产出，确定性）

| 信号 | 检测方式 | 含义 |
|------|---------|------|
| `low_usage` | session JSONL 计数，周期内 ≤ 2 次 | 可能价值不足或 description 不准 |
| `high_usage` | session JSONL 计数，周期内 ≥ 10 次 | 核心 skill，优化优先级高 |
| `zero_usage` | session JSONL 计数，周期内 0 次 | 考虑是否仍需要 |
| `skill_md_too_long` | `wc -l SKILL.md` > 500 | 违反渐进式披露，需 simplify |
| `has_feedback` | memory 文件中 type: feedback 记录数 | 用户有过纠正或确认 |

## Session 样本（脚本提取，LLM 分析）

脚本从 session JSONL 中提取与当前项目 skill 相关的调用片段。LLM 负责做以下语义分析：

| 分析项 | 判断依据 |
|--------|---------|
| **误触发** | skill 被调用但 session 上下文与 skill 职责不匹配 |
| **用户重试** | 同一 skill 短时间内被多次调用，暗示首次结果不满意 |
| **方向纠正** | skill 调用后用户立即发出纠正性指令 |
| **规则重复/冲突** | CLAUDE.md 中的规则与 specs 中的规则语义重叠或矛盾 |

## 数据路径

- Claude sessions：`~/.claude/projects/<encoded-path>/*.jsonl`
- Memory files：`~/.claude/projects/<encoded-path>/memory/`
- 当前项目 skills：`<project-root>/skills/`
- 当前项目 CLAUDE.md：`<project-root>/CLAUDE.md`
