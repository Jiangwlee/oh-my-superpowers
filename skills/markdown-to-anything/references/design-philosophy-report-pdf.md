---
name: Meridian Ledger
description: Design philosophy for report PDF typography and layout — precision, density, analytical clarity
type: reference
---

# Meridian Ledger

A design philosophy for analytical documents where information density is the primary virtue.
Inspired by Bloomberg terminal economics and Zurich school typographic discipline.

## The Movement

**Meridian Ledger** treats the printed page as a precision instrument, not a canvas.
Every typographic decision is an act of subordination — the designer disappears so the data speaks.
The document should feel like it was composed by someone who has spent years reading financial research:
meticulous, unhurried, exacting. Not a single pixel wasted on decorative excess.

## Typography as Infrastructure

Body text sits at 14px — the exact weight of a well-calibrated balance sheet.
Line height 1.55 creates breathing room without drift. Headings descend in weight with precision:
H1 at 22px anchors the document; H2 at 17px sections it with quiet authority; H3 at 15px
subdivides without competing. All hierarchy is expressed through weight and color, never through
size inflation. Thin fonts in body; 700-weight only for headings and labels. Every character is
painstakingly chosen for legibility at print resolution.

## Color as Signal

Deep navy (#0d3880) is the document's governing voice — used for H1, strong labels, table headers.
Measured blue (#1565c0) marks H2 section boundaries with a 3px left border, a quiet vertical
accent that costs nothing and gives structure everything. Accent blue (#42a5f5) for the border
itself — lighter, like a watermark from a master hand. Table zebra striping in #f8fbff:
almost imperceptible, yet it transforms readability of dense numeric rows. The background
remains pure white — no warmth, no drift, just the clinical authority of a printed report.

## Density without Chaos

Tables are the primary information vessel. Font 13px, padding compressed to 5–6px vertical,
8px horizontal. Column headers in bold, no-wrap to prevent header text from breaking across lines.
Cell content uses `word-break: break-word` to prevent overflow without forcing ugly line breaks
on short words. The table is a grid, not a decoration — it should feel like the output of a
well-engineered data pipeline. The result of countless calibrations by someone who has built
dozens of such documents.

## Space as Punctuation

Margins are not decorative — they are the silence between movements. H2 carries 18px top margin
to signal a new section's arrival. Paragraphs breathe with 5px separation. Lists compress to
3px item margin — tight enough to scan quickly, open enough to read without fatigue. The page
itself is orchestrated with painstaking restraint: no element shouts, every element is exactly
where it must be, placed by a hand that has learned through deep expertise when to stop.
