# Mutation Operators

每次修复只用一种算子。算子选择由 LLM 推荐、用户确认。

## 6 种算子

| 算子 | 适用场景 | 操作 |
|------|---------|------|
| `remove-redundancy` | 规则/描述与其他位置重复 | 删除重复内容，保留权威位置 |
| `tighten-description` | 触发不精确，误触发或漏触发 | 收紧 description 边界，加 "Do NOT use when" |
| `add-constraint` | 缺少必要的行为约束 | 在 SKILL.md 或 references 中增加约束 |
| `add-boundary` | 与其他 skill 职责边界模糊 | 明确区分，加排他描述 |
| `simplify` | 指令过长或过于复杂 | 精简内容，将细节下沉到 references |
| `restructure` | 流程顺序不合理或缺少检查点 | 重组步骤，调整顺序或加 gate |

## 证据→算��推荐映射

LLM 根据以下映射推荐算子，填入发现表格的"建议算子"列：

| 证据特征 | 推荐算子 |
|---------|---------|
| 同一规则出现在两处以上 | `remove-redundancy` |
| 被其他 skill 的场景误触发 | `add-boundary` |
| 调用频率高但 feedback 中有纠正 | `tighten-description` |
| 调用频率高且无负面反馈 | 跳过（健康） |
| SKILL.md 超 500 行 | `simplify` |
| 用户在 session 中多次重试 | `add-constraint` |
| 流程中途被用户打断/纠正方向 | `restructure` |

## 使用规则

1. 每次修复只用一种算子
2. 算子名记录到 results.tsv 的 operator 列
3. 用户可覆盖 LLM 的推荐
4. 长期积累后可分析 results.tsv，统计各算子的成功率（keep / total）
