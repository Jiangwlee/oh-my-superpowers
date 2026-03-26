# Xueqiu Workflows

This file describes the repeatable `xueqiu.com` workflows bundled with the
skill. Input is either a search query, a single post URL, or a request for the
home-page hot timeline. Output is structured JSON from the helper scripts under
`../../scripts/sites/xueqiu/`. Public entrypoints are `search.sh`,
`open-post.sh`, `hot.sh`, and `stock-info.sh`.

## Scope

- Search `xueqiu.com` and return discussion-post summaries.
- Open one post URL and return the main article plus visible top comments.
- Extract the current visible "热门" home timeline post list.
- Open one stock page and return the latest announcements and discussions.
- Return visible DOM data only; do not force hidden replies to expand.

## Script entrypoints

- [../../scripts/sites/xueqiu/search.sh](../../scripts/sites/xueqiu/search.sh)
  Inputs: search query, optional result limit, optional target prefix.
  Output: JSON array of up to 10 discussion results with `author`,
  `time_hint`, `title`, `summary`, and `url`.
- [../../scripts/sites/xueqiu/open-post.sh](../../scripts/sites/xueqiu/open-post.sh)
  Inputs: one `xueqiu.com/<user>/<post>` URL, optional comment limit, optional
  target prefix.
  Output: JSON object with `author`, `time`, `source`, `title`, `text`, `url`,
  and `comments`.
- [../../scripts/sites/xueqiu/hot.sh](../../scripts/sites/xueqiu/hot.sh)
  Inputs: optional result limit and optional target prefix.
  Output: JSON array of up to 10 hot timeline posts with `author`, `time_hint`,
  `title`, `summary`, and `url`.
- [../../scripts/sites/xueqiu/stock-info.sh](../../scripts/sites/xueqiu/stock-info.sh)
  Inputs: stock symbol or stock URL, optional result limit, optional target prefix.
  Output: JSON object with `stock_url`, `announcements`, and `discussions`.
  Each item includes `title`, `time`, `summary`, and `link`.

## Search SOP

1. Pick a usable `xueqiu.com` tab with `list_raw`.
2. Navigate to `https://xueqiu.com/k?q=<query>`.
3. Wait for the discussion timeline items to appear.
4. Extract up to 10 unique post links under `https://xueqiu.com/<user>/<post>`.
5. Ignore stock rows and other non-post search blocks.

## Open-post SOP

1. Pick a usable `xueqiu.com` tab with `list_raw`.
2. Navigate to the target post URL.
3. Wait for `.article__page` and the article body to appear.
4. Extract the main article metadata and normalized body text.
5. Extract visible top comments from `.comment__list` without expanding more replies.

## Hot-post SOP

1. Pick a usable `xueqiu.com` tab with `list_raw`.
2. Navigate to `https://xueqiu.com/`.
3. Click the visible `热门` tab when present.
4. Wait for `.timeline__item` cards to appear.
5. Extract up to 10 unique post links and summaries from the visible timeline.

## Stock-info SOP

1. Pick a usable `xueqiu.com` tab with `list_raw`.
2. Navigate to `https://xueqiu.com/S/<symbol>`.
3. Wait for `.stock-timeline-tabs` to appear.
4. Click `公告` and extract the latest visible announcement items.
5. Click `讨论` and extract the latest visible discussion items.
6. Return both arrays in one JSON object.

## Notes

- These scripts prefer direct URL navigation over click paths when a stable URL exists.
- The search workflow reads the visible page and does not call private APIs.
- The hot-post workflow assumes the signed-in home page exposes the "热门" feed.
- Comment extraction returns only the comments currently visible in the DOM.
- The stock-info workflow uses the stock page's own tabs instead of the global search page.
- Announcement links prefer the underlying PDF/source document when present.
