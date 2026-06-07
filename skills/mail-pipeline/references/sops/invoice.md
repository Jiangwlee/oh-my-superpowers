# Invoice SOP

Judge: the message delivers a formal invoice — a pdf/zip invoice attachment,
or a link from an invoice provider (nuonuo, xforceplus, keruyun, jd).

## Steps

1. Stage the message:

   ```bash
   omp mail-pipeline stage --account qq --uid 1581
   ```

   If it fails with `no pdf/zip attachment and no allowlisted invoice link`,
   the provider is not registered — the error lists the candidate link
   hosts. Mark the message read per the notification SOP, and add the
   candidate hosts (with uid and sender) to the report's "needs your
   decision" section so the user can extend `config/providers.yaml`.
   Reporting an unallowlisted invoice provider is mandatory, never silent.

2. Read each staged PDF and extract six fields: `invoice_date` (YYYY-MM-DD),
   `invoice_number`, `amount` (价税合计), `tax_rate` (keep face markers such
   as `*` verbatim), `purchase_content`, `seller`. For foreign-currency
   invoices add `"currency": "USD"` (omitted = CNY).

3. Submit the fields (real example from a processed invoice):

   ```bash
   omp mail-pipeline submit --id 915c524c2d9a --fields '{"invoice_date":"2026-06-04","invoice_number":"26427000000465806619","amount":314.4,"tax_rate":"*","purchase_content":"通信服务费","seller":"中国电信股份有限公司武汉分公司","confidence":0.98}'
   ```

   - Multiple staged files → add `--invoice-file <filename>` so the invoice
     PDF receives the clean rendered name.
   - Rejected as duplicate `invoice_number` → verify it is the same invoice,
     then drop the pending item:
     `omp mail-pipeline submit --id <pending_id> --discard --reason 'duplicate delivery of 26427000000465806619'`
   - Unreadable PDF or uncertain fields → do not submit; leave the item
     pending and report it.

4. Mark the source mail read:

   ```bash
   omp mail-pipeline mailbox mark-read --account qq --uid 1581 --reason 'invoice 26427000000465806619 archived'
   ```

Done when: the pending id is resolved (finalized or discarded), the archived
file is named `{invoice_date}_{invoice_number}_{seller}.pdf`, and the source
mail is read.
