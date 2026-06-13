# Visual System

Use a restrained, readable style for HTML page prototypes. Favor durable
reading surfaces over decorative app chrome.

The system defines shared craft rules, not one fixed visual style. Each page
chooses a page pattern and style family from `page-patterns.md`.

## Base Tokens

Use semantic tokens:

```css
:root {
  --bg: #fafafa;
  --surface: #ffffff;
  --fg: #111111;
  --muted: #666666;
  --border: #dddddd;
  --soft: #f5f5f3;
  --accent: #1a1a1a;
  --success: #166534;
  --warn: #92400e;
  --danger: #b91c1c;
  --font-display: "Source Serif 4", Georgia, "Noto Serif SC", serif;
  --font-body: Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;
}
```

## Typography

- Body text: `15px` to `18px`, line-height `1.5` to `1.7`.
- Long-form reading width: `60ch` to `70ch`.
- Display headings may use serif; body should use a readable sans-serif unless
  the page has an editorial reason to use serif body.
- Use at most three visible weights in one page.
- Body letter spacing must be `0`.
- ALL CAPS labels need positive tracking.
- Every first viewport needs one dominant entry point. Use at least two
  hierarchy vectors on it: scale, weight, spacing, tracking, or alignment.
- Avoid flat hierarchy: adjacent levels must not share the same scale, weight,
  and spacing.

## Color Discipline

- Neutral pixels should dominate the page.
- Use one accent color and at most two visible accent moments per viewport.
- Do not use hardcoded Tailwind indigo defaults such as `#6366f1`, `#4f46e5`,
  or `#7c3aed`.
- Avoid purple-blue gradients, decorative glow blobs, and generic hero effects.
- Semantic colors are for status only: success, warning, danger.

## Style Family Rules

| Family | Typography | Layout | Accent behavior |
|---|---|---|---|
| `editorial-report` | Serif display, large title/deck contrast, generous section rhythm | Reading column plus optional TOC | Accent is rare; sources stay quiet |
| `operational-brief` | Sans-first, smaller title, stronger labels | Action lanes, compact tables/lists | Semantic status colors allowed for urgency |
| `digest-magazine` | Serif or mixed display, strong story tiers | One lead item, grouped picks, radar list | One distinctive visual move, not a gradient |
| `review-console` | Sans-first with mono metadata | Severity lanes and file/path anchors | Severity color is functional, never decorative |
| `index-catalog` | Quiet sans, low hierarchy | Search/filter plus grouped artifact rows | Accent only for active filter or latest item |
| `prototype-lab` | Utility typography around preview | Split preview/control workspace | Controls stay neutral so preview carries style |

If a template feels like the same card grid with different labels, redesign
the information architecture before changing colors.

## Layout

- Put the result's real subject in the first viewport.
- Reports should start with conclusion or executive summary, not methodology.
- Keep source lists compact unless source inspection is the page's main task.
- Prefer full-width page bands and constrained inner reading columns.
- Use cards only for repeated comparable items or decision units.
- Do not nest cards inside cards.
- Page sections should create rhythm. Uniform gaps across every section read as
  template output.

## Components

Use consistent primitives:

- Header: title, scenario, generated time, output type.
- Summary block: strongest conclusions or action items.
- Section: heading, body, optional evidence/source links.
- Source list: title, platform, URL, one-line reason it matters.
- Decision item: severity/status, impact, recommended action.
- Footer: local artifact paths and audit note when useful.

## Motion

- Use motion only to confirm state changes: control selection, row expansion,
  copy success, or navigation orientation.
- Keep common transitions around `150ms`; hover and press feedback should feel
  immediate.
- Do not use decorative ambient motion in result pages.
- Any transform-based motion must respect `prefers-reduced-motion`.
- Copy/export feedback must also work without motion.

## State Design

Design empty, error, and edge states when the page can produce them.
Static generated pages usually need:

- Empty source list or empty findings list.
- Partial result notice when some upstream fetches failed.
- Long title and missing metadata behavior.
- Mobile layout at narrow viewport.

## Anti-Patterns

- Generic placeholder copy, sample content, or invented metrics.
- Emoji as icons in headings, buttons, or feature lists.
- Decorative SVG waves, blobs, or bokeh.
- Colored left-border callout cards with rounded corners.
- Page text that explains how the page is designed rather than presenting the
  result.
- Personal filesystem paths or network addresses in committed templates.
