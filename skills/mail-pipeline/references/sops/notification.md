# Notification SOP

Judge: service-generated notices — security alerts, billing reminders,
account or system notifications — that inform the user but deliver no
formal invoice.

## Steps

1. Read the content and decide whether the user must act (security warning,
   payment due, account risk).

2. If user action is needed → keep the message unread and put it at the top
   of the report with the required action. It stays in the work queue on
   purpose; on a later run, re-report it briefly until the user handles it.

   Otherwise → mark it read with the judgment you actually made (example
   shape; never copy a reason without reading the message):

   ```bash
   omp mail-pipeline mailbox mark-read --account qq --uid 2042 --reason '服务条款更新通知，已阅，无需行动'
   ```

Done when: the message is either marked read or reported as
action-required.
