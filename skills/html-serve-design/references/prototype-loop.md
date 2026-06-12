# Prototype Loop

Use html-serve as the browser review surface before packaging a target skill
template.

## Loop

1. Copy `assets/prototype-workbench.html` to a temporary output file under the
   html-serve prototype path.
2. Replace the sample preview with a representative target-skill page preview.
3. Keep controls focused on decisions that matter for this target skill:
   density, navigation, source visibility, section rhythm, and emphasis.
4. Publish the workbench to html-serve and give the user the preferred URL from
   `HTML_SERVE_BASE_URL` when configured; otherwise give the localhost URL.
5. Ask the user to adjust the browser controls or describe what feels wrong.
6. Apply feedback, republish, and repeat until the user accepts the design.
7. Convert the accepted design into the target skill's final template asset.

## Required Workbench Controls

Every prototype workbench should expose:

- Page pattern.
- Density: compact, standard, spacious.
- Reading width.
- TOC mode: none, inline, sticky.
- Source visibility: hidden, compact, expanded.
- Emphasis mode: neutral, editorial, operational.

Add target-specific controls only when they change a reusable template decision.
Do not expose every CSS variable as a control.

## Export Contract

The browser export should produce a JSON-like block with:

```json
{
  "targetSkill": "<skill-name>",
  "pagePattern": "report",
  "density": "standard",
  "readingWidth": "66ch",
  "toc": "sticky",
  "sources": "compact",
  "emphasis": "editorial",
  "notes": []
}
```

Use the export as user feedback, not as executable config. The final template
still belongs in the target skill's `assets/` directory.

## Browser Check

Before asking for approval, inspect the prototype in a browser or with a
screenshot-capable tool when available. Check:

- First viewport shows the page's actual subject, not generic instructions.
- Desktop and mobile layouts do not overlap.
- Controls update the preview and export.
- Copy works over plain HTTP using an `execCommand('copy')` fallback.
- The shared URL uses the configured public base, preferably Tailscale on this
  host, without hardcoding the address in committed files.
