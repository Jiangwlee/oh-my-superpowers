# Notification SOP

Judge: service-generated notices — security alerts, billing reminders,
account or system notifications — that inform the user but deliver no
formal invoice.

## Steps

1. Read the content and decide whether the user must act (security warning,
   payment due, account risk).

2. If user action is needed → keep the message unread and put it at the top
   of the report with the required action.

   Otherwise → mark it read:

   ```bash
   omp mail-pipeline mailbox mark-read --account qq --uid 1582 --reason 'Google 安全提醒副本，无需行动'
   ```

Done when: the message is either marked read or reported as
action-required.
