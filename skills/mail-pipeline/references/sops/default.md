# Default SOP

Judge: the message fits no other scenario, or classification is uncertain.

## Steps

1. Add it to the report's "needs your decision" section with subject,
   sender, and why classification failed; ask the user how to handle it.

2. Mark the message read — the report carries the open question:

   ```bash
   omp mail-pipeline mailbox mark-read --account qq --uid 2077 --reason '无法归类，已转入汇报待用户决定'
   ```

Done when: the message is marked read and appears in the report's "needs
your decision" section.
