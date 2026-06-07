# Ad SOP

Judge: marketing, promotion, newsletter, or subscription noise with no
personal or business value. An unsubscribe link alone does not make a
message an ad — service notifications carry them too.

## Steps

1. Confirm from subject and snippet (or `show`) that the content is purely
   promotional.

2. Move it to trash with the judgment you actually made (example shape;
   write your own reason from the message content). Batch same-judgment
   messages into ONE call with repeated `--uid` — one IMAP connection
   handles them all:

   ```bash
   omp mail-pipeline mailbox move --account qq --uid 2001 --uid 2002 --uid 2003 --to trash --reason '同一发件人的系列营销邮件，无个人事务价值'
   ```

Done when: the message is out of the inbox and the audit event records the
reason.
