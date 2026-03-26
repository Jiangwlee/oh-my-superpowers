# X Workflows

This file describes the repeatable `x.com` workflows bundled with the skill.
Input is either a search query or a single post URL. Output is structured JSON
from the helper scripts under `../../scripts/sites/x/`. Public entrypoints are
`search.sh` and `open-post.sh`.

## Scope

- Search `x.com` using the default search results page.
- Return result summaries, not full threads.
- Open one post URL and return the main post's currently visible text.
- Do not force "Show original" and do not traverse threads.

## Script entrypoints

- [../../scripts/sites/x/search.sh](../../scripts/sites/x/search.sh)
  Inputs: search query, optional result limit, optional target prefix.
  Output: JSON array of up to 10 search results with `author`, `handle`,
  `time_hint`, `summary`, and `url`.
- [../../scripts/sites/x/open-post.sh](../../scripts/sites/x/open-post.sh)
  Inputs: one `x.com/<user>/status/<id>` URL, optional target prefix.
  Output: JSON object with `author`, `handle`, `time`, `text`, and `url`.

## Search SOP

1. Pick a usable `x.com` tab with `list_raw`.
2. Navigate to `https://x.com/search?q=<query>`.
3. Wait for `article` nodes to appear.
4. Extract up to 10 unique post links and summaries.
5. Filter out non-post and `analytics` URLs.

## Open-post SOP

1. Pick a usable `x.com` tab with `list_raw`.
2. Navigate to the target post URL.
3. Wait for the main `article` to appear.
4. Extract the current visible content from that article.
5. Return the visible language version without toggling translation state.

## Notes

- These scripts prefer `nav` over simulated clicks.
- The search script uses the default X search page and does not force `Top` or `Latest`.
- The post script intentionally does not expand replies, threads, or quoted posts.
