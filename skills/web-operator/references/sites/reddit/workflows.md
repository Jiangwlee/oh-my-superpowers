# Reddit Workflows

This file describes the repeatable `reddit.com` workflows bundled with the
skill. Input is either a search query or a single Reddit post URL. Output is
structured JSON from the helper scripts under `../../scripts/sites/reddit/`.
Public entrypoints are `search.sh` and `open-post.sh`.

## Scope

- Search `reddit.com` using the default search results page.
- Return result summaries, not full discussion trees.
- Open one Reddit post URL and return the main post plus visible comments.
- Do not expand more comments or traverse linked posts.

## Script entrypoints

- [../../scripts/sites/reddit/search.sh](../../scripts/sites/reddit/search.sh)
  Inputs: search query, optional result limit, optional target prefix.
  Output: JSON array of up to 10 results with `title`, `subreddit`,
  `time_hint`, `summary`, and `url`.
- [../../scripts/sites/reddit/open-post.sh](../../scripts/sites/reddit/open-post.sh)
  Inputs: one Reddit post URL, optional comment limit, optional target prefix.
  Output: JSON object with `title`, `subreddit`, `author`, `time`, `text`,
  `url`, and `comments`.

## Search SOP

1. Pick a usable `reddit.com` tab with `list_raw`.
2. Navigate to `https://www.reddit.com/search/?q=<query>`.
3. Wait for post links matching `/r/<sub>/comments/<id>/...`.
4. Extract up to 10 unique result cards.
5. Return each result with a short visible summary.

## Open-post SOP

1. Pick a usable `reddit.com` tab with `list_raw`.
2. Navigate to the target post URL.
3. Wait for the post title and comment articles to appear.
4. Extract the main post body from the visible page content.
5. Extract the first visible comments in DOM order without expanding threads.

## Notes

- These workflows reuse an existing Reddit tab and do not open a new tab.
- The post workflow includes comments in the returned JSON; default comment
  limit is 10.
- Reddit's default app shell can keep background requests open, so the scripts
  use fast navigation plus explicit selector waits instead of waiting for the
  full page to become idle.
