# Journal

<!--
本文件是 story 的过程事件流。所有 task 状态变化、ISSUE 状态变化、关键 NOTE 都按时间序列追加。

追加规则：
  1. 所有 entry 按时间顺序追加（自然时序，不重排）。
  2. 旧 entry 不允许修改 — 状态变化用新 entry 表达。
  3. 当前状态 = 最后一条同 ID（同 task 或同 ISSUE）entry 的状态标记。

Entry 字段约定（详见 references/journal-protocol.md）：

  ## T<n> <短标题> [in_progress] HH:MM
    assumption:  <我以为是什么>
    verify:      <我跑了什么命令（rg / sed / cat 等可重跑命令）>
    fact:        <命令输出告诉我代码实际是什么>
    edit target: <准备改哪些文件 / 哪些函数>

  ## T<n> <短标题> [done] HH:MM
    decision: <关键决策一句话>
    gotcha:   <坑点；可空>
    diff:     <改动文件列表 + 行数>

  ## T<n> [reviewed] HH:MM            （可批量推进多 task）
    verdict:  PASS
    reviewer: <sub-agent | codex | claude tmux session id>
    batch:    T<a>, T<b>, T<c>

  ## T<n> [needs_fix] HH:MM
    verdict:  NEEDS_FIX
    reviewer: <同上>
    batch:    T<n>
    issues:   <CRITICAL/HIGH 列表，必修项；可引用 ISSUE-NNN>

  ## T<n> [dropped] HH:MM
    reason: <为什么不做>

  ## ISSUE-001 open HH:MM
    source: <来源 task / review / 用户 / 自查>
    fact:   <发现的事实，一句话>
    plan:   <当前打算如何处理；可写 "待 T<n> 决定"、"非本 story scope"等>

  ## ISSUE-001 update <fixed | dismissed> HH:MM
    by:     <commit hash 或 task ID 或 reason>
    note:   <可空>

合法 task 状态、合法迁移、禁止迁移、Evidence 检查规则全部定义在 references/state-machine.md（单点定义）。
-->
