# WPS 365 (365.kdocs.cn) Workflows

This file describes the repeatable `365.kdocs.cn` workflows bundled with the skill.
Input is either a search query or a file key from a previous search. Output is
structured JSON from the helper scripts under `../../scripts/sites/kdocs/`.
Public entrypoints are `search.sh`, `open-doc.sh`, `find-in-doc.sh`,
`ask-ai.sh`, and `close-doc.sh`.

## Scope

- Search WPS 365 documents using the site's Full Text Search panel.
- Return result summaries with text snippets and version ranking.
- Open one document by file key and read its outline and first visible page.
- Search within an open document using the WPS Find dialog.
- Ask WPS AI Docs Chat a question directly from the main page and extract the
  rendered answer plus referenced documents.
- Close the document tab when done, preserving the main `365.kdocs.cn/latest` tab.
- Not in scope: writing, editing, uploading, or navigating team spaces.

## Script entrypoints

- [../../scripts/sites/kdocs/search.sh](../../scripts/sites/kdocs/search.sh)
  Inputs: search query, optional result limit (default 10), optional target prefix.
  Output: JSON array with `file_key`, `title`, `last_opened`, `location`,
  `creator`, `snippet`, and `is_latest` fields.

- [../../scripts/sites/kdocs/open-doc.sh](../../scripts/sites/kdocs/open-doc.sh)
  Inputs: file key (e.g. `file_503025782506`), optional main tab prefix.
  Output: JSON object with `title`, `url`, `doc_target`, `word_count`, and
  `visible_text` (the first screen of accessible document text).

- [../../scripts/sites/kdocs/find-in-doc.sh](../../scripts/sites/kdocs/find-in-doc.sh)
  Inputs: keyword to find, optional doc tab prefix.
  Output: JSON object with `keyword`, `match_count`, and `context` (visible
  text lines after navigating to the first match).

- [../../scripts/sites/kdocs/ask-ai.sh](../../scripts/sites/kdocs/ask-ai.sh)
  Inputs: natural-language question, optional main tab prefix.
  Output: JSON object with `question`, `scope`, `answer`, `references`, and
  `main_target`.

- [../../scripts/sites/kdocs/close-doc.sh](../../scripts/sites/kdocs/close-doc.sh)
  Inputs: optional doc tab prefix.
  Output: JSON object with `closed_target`, `closed_url`, and `main_tab_alive`.

## Search SOP

1. Find or reuse the `365.kdocs.cn` main tab. If none is open, create one at
   `https://365.kdocs.cn/`.
2. Navigate to `https://365.kdocs.cn/latest` to ensure clean state.
3. Click the search bar to open the search panel (modal overlay, no URL change).
4. Type the query; the panel shows results under Document Name and Full Text tabs.
5. Wait for `.item-container` elements to appear.
6. Extract results from the Full Text section (has snippets) then the File Name
   section (no snippets), deduplicating by `data-key`.
7. Rank versions: group docs by base name (strip `-vN-` and `-YYYYMMDD` suffixes),
   sort by version number then date, mark the top entry `is_latest: true`.

## Open-doc SOP

1. Find the `365.kdocs.cn` main tab. If none is open, create one at
   `https://365.kdocs.cn/`.
2. Derive the document URL from the file key: strip the `file_` prefix to get
   the numeric id, then form `https://365.kdocs.cn/l/<id>`.
3. Call `window.open(url, '_blank')` on the main tab. A new doc tab opens.
4. Poll `cdp list_raw` until a new `365.kdocs.cn/l/` tab appears.
5. Wait until `document.title` changes from `WPS 365` to the document name.
6. Extract the visible document text via the accessibility tree (`snap`),
   filtering out toolbar and UI labels.
7. Return `title`, `url`, `doc_target` (targetId prefix), `word_count`, and
   `visible_text`.

## Find-in-doc SOP

1. Find a `365.kdocs.cn/l/` doc tab.
2. Click the magnifier button (`[class*="kd-icon-magnifier"]` parent button) to
   show the Find/Replace dropdown.
3. Click the Find item (`.component-find-dropdown-item` whose text includes
   `Find` but not `Replace`).
4. Focus `.component-find-input` and type the keyword.
5. Click the Next button to jump to the first match.
6. Read `.find-result` innerText for the match count (format `N/M`).
7. Read visible text from the accessibility tree to get context around the match.

## Ask-ai SOP

1. Find or reuse the `365.kdocs.cn` main tab. If none is open, create one at
   `https://365.kdocs.cn/`.
2. Navigate to `https://365.kdocs.cn/latest` to reset into the stable home page.
3. Ensure the `Docs Chat` panel is open; if the QA textarea is absent, click
   the `Docs Chat` button in the main page toolbar.
4. Capture the current answer count and latest rendered answer text.
5. Fill the textarea whose placeholder contains
   `supports @ to specify files for Q&A`.
6. Click the Send button (`button[aria-label="Send"]`).
7. Wait until either a new `.qa-group` appears or the latest answer text
   changes, then wait for the Stop button to disappear so the answer is done.
8. Extract the latest answer from `.gpt-chat-block-msg-printer`.
9. Extract referenced document titles from `.gpt-chat-list-card`.

## Close-doc SOP

1. Find the `365.kdocs.cn/l/` doc tab.
2. If a target prefix was passed explicitly, resolve its current URL and require
   it to match `https://365.kdocs.cn/l/`.
3. Send `Page.close` CDP command to close the tab.
4. Verify the main `365.kdocs.cn/latest` tab is still open.

## Notes

- The search panel is a modal overlay; the URL stays at `365.kdocs.cn/latest`.
  There is no direct search URL to navigate to.
- Main-tab discovery accepts existing `365.kdocs.cn/ent/...` workspace pages.
  If no WPS tab exists, the helper opens `https://365.kdocs.cn/` automatically.
- `ask-ai.sh` currently scopes to `All parsed files`, matching the default Docs
  Chat textarea placeholder. It does not yet automate `@`-mentioning specific
  files.
- Document content is canvas-rendered; text is only readable via the
  accessibility tree (`cdp snap`).
- Version detection parses filenames only. Documents without `-vN` or date
  suffixes will not be version-ranked.
- `open-doc.sh` depends on the target document appearing in the DOM (either via
  an open search panel or the recent-file list). Run `search.sh` first to ensure
  the item is visible.
