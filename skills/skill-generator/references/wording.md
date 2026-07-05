# Wording — 用词

Purpose: 逐句锤炼 skill 文本的用词，使其读起来像一个细致的操作者写的指令，而非一个泛泛的助手在解释话题。第 4 步起草时套用，第 5 步评审时对照。
Sections: 祈使句 | 强动词 | 去解释 | 去空话 | 硬词 | 对照

## 祈使句

用命令式、指示性语气写正文（"运行 X""归入 Y""修掉所有 blocking"）。skill 是给 agent 的指令，不是给读者的说明。

## 强动词

需要动作处就用硬动词，不用被动语态或软语言。

- 弃：`should`、`try to`、`generally`、`if possible`、`recommended`、`尽量`、`建议`。
- 用：`Run`、`Split`、`Reject`、`必须`、`不得`。

一个弱到打不过模型默认行为的词是 no-op（`be thorough` 而 agent 本就大致 thorough）—— 换更强的词（`relentless`），别加更多句子。

## 去解释（去 rationale）

SKILL.md 正文只写**动作/指令**，不解释为什么。原理属于 `philosophy.md` 这类 reference，不属于骨架。

- 弃元评论：`This section explains…`、`It is important to note…`、`本节介绍…`。
- 直接给指令：把"本节介绍如何 X"改成"做 X：……"。

## 去空话

删掉随意、模糊的措辞。

- 弃：`just`、`simply`、`stuff`、`do X nicely`、`as needed`、`where appropriate`、`酌情`、`适当`。
- 弃术语/黑话：内部标签、框架俚语、未解释的缩写、AI 过程词 —— 能用平实任务词的地方别用黑话。
- 隐藏分支要显式化：把"根据情况处理"改成"若 X → Y；否则 → Z"。

## 硬词

硬约束用硬语言：`MUST` / `NEVER` / `Do not` / `必须` / `不得`。软约束才用 `prefer` / `优先`。

## 对照

| 弱（改） | 强（用） |
|---|---|
| You should generally validate the input | Validate the input. Reject when the schema mismatches. |
| Handle errors as appropriate | 若退出码 ≠ 0 → 打印 stderr 前 20 行并停止 |
| This section explains the workflow | （删标题下这句，直接给步骤） |
| Try to keep SKILL.md short | SKILL.md body 必须 < 500 行；逼近就下沉 references |
| 酌情拆分 references | 一句讲得清 → 内联；要展开多段 → 下沉 |
