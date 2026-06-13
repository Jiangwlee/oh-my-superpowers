# Prototype Loop

Use html-serve as the browser review surface before selecting the final page
direction.

## Loop

1. Copy `assets/prototype-workbench.html` to a temporary output file under the
   html-serve prototype path.
2. Replace the sample preview with a representative page preview for the
   current scenario.
3. Keep controls focused on decisions that matter for this page: information
   organization, density, navigation, section rhythm, emphasis, and reference
   style.
4. Publish the workbench to html-serve and give the user the preferred URL from
   `HTML_SERVE_BASE_URL` when configured; otherwise give the localhost URL.
5. Ask the user to adjust the browser controls or describe what feels wrong.
6. Apply feedback, republish, and repeat until the user accepts the direction.
7. Save the accepted HTML prototype and matching `DESIGN.md` in the temporary
   workspace.

## Required Workbench Controls

Every prototype workbench should expose:

- Information organization model.
- Page pattern.
- Density: compact, standard, spacious.
- Reading width or layout width.
- Navigation mode: none, inline, sticky, sidebar, tabs.
- Source or metadata visibility: hidden, compact, expanded.
- Emphasis mode: neutral, editorial, operational.

Add task-specific controls only when they change a reusable design decision.
Do not expose every CSS variable as a control.

## Export Contract

The browser export should produce a JSON-like block with:

```json
{
  "scenario": "<page scenario>",
  "informationModel": "priority-pyramid",
  "pagePattern": "report",
  "density": "standard",
  "readingWidth": "66ch",
  "navigation": "sticky",
  "metadata": "compact",
  "emphasis": "editorial",
  "referenceDesign": "<DESIGN.md path>",
  "notes": []
}
```

Use the export as user feedback, not as executable config. The final prototype
still needs a readable `DESIGN.md` explaining the decisions.

## Browser Check

Before asking for approval, inspect the prototype in a browser or with a
screenshot-capable tool when available. Check:

- First viewport shows the page's actual subject, not generic instructions.
- Desktop and mobile layouts do not overlap.
- Controls update the preview and export.
- Copy works over plain HTTP using an `execCommand('copy')` fallback.
- The shared URL uses the configured public base, preferably Tailscale on this
  host, without hardcoding the address in committed files.
