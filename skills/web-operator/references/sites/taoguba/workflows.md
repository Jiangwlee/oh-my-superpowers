# Taoguba Workflows

This file describes the repeatable `tgb.cn` / Taoguba workflows bundled with
the skill. Input is either a time-windowed list task or a single Taoguba post
URL. Output is structured JSON from the helper scripts under
`../../scripts/sites/taoguba/`. Public entrypoints include authenticated
search, `jinghua.sh`, `following.sh`, and `open-post.sh`.

## Scope

- Extract `jinghua` posts from the last 24 hours by default.
- Extract followed-content updates from the last 12 hours by default.
- Open one Taoguba post and return the main post body.
- Sign in using credentials already stored and autofilled by Chrome.
- Search discussions for one explicit year, sorted by hottest by default.
- Search may follow result pagination up to the requested limit; list feeds do
  not expand pagination, and post reading does not follow reply floors.
- Do not read, persist, or print account credentials, cookies, or usernames.

## Script entrypoints

- [../../scripts/sites/taoguba/jinghua.sh](../../scripts/sites/taoguba/jinghua.sh)
  Inputs: optional hour window, optional result limit, optional target prefix.
  Output: JSON array of recent `jinghua` posts with title, author, post time,
  reply time, stats, and URL.
- [../../scripts/sites/taoguba/following.sh](../../scripts/sites/taoguba/following.sh)
  Inputs: optional hour window, optional result limit, optional target prefix.
  Output: JSON array of recent followed-content updates with actor, update
  time, action, text, source post title, and URL.
- [../../scripts/sites/taoguba/open-post.sh](../../scripts/sites/taoguba/open-post.sh)
  Inputs: one Taoguba post URL, optional target prefix.
  Output: JSON object with title, author, publish time, stats, text, and URL.
- [../../scripts/sites/taoguba/login.sh](../../scripts/sites/taoguba/login.sh)
  Inputs: optional timeout and target prefix.
  Output: JSON object with `ok`, `site`, and `status`.
- [../../scripts/sites/taoguba/search.sh](../../scripts/sites/taoguba/search.sh)
  Inputs: query, optional limit, required year, optional hot/latest sort and
  target prefix.
  Output: compact JSON object with requested/applied filters, source and
  timezone metadata, pagination evidence, and result cards.

## Workflow notes

- `jinghua` time strings are month-day plus clock time, so the workflow assumes
  the current year and filters against the current browser time.
- Followed-content updates already expose full timestamps and action labels like
  `跟帖了` or `发布了`.
- Taoguba pages can keep loading after the visible content is ready, so the
  scripts use tolerant navigation plus explicit waits on visible text.
- `login` is idempotent: it returns `already_logged_in` when a signed-in header
  is present. Otherwise it opens the account-login tab, checks only whether
  Chrome autofilled both fields, submits once, and verifies the signed-in
  header. Missing autofill or interactive verification fails closed.
- `search` fails closed unless the signed-in state, discussion content type,
  requested year, and requested sort are all visibly confirmed. It reads only
  `.topic_Item` cards, excluding unrelated sidebar recommendations.
- Search result fields remain compatible with the earlier eastmoney collector:
  title, URL, author, displayed time, abstract, likes, views, comments, rank,
  and normalized `published_at_asia_shanghai`.
