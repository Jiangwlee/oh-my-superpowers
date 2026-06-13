# Quality Checklist

Run this checklist before calling the page design ready.

## Workspace Artifacts

- [ ] Temporary workspace was created with `omp html-design init`.
- [ ] Five relevant `DESIGN.md` references were copied or their absence was
      explained.
- [ ] Final `DESIGN.md` names the selected information organization model.
- [ ] Final HTML prototype and `DESIGN.md` are in the workspace.
- [ ] No test files were placed inside the skill directory.

## Publishing Contract

- [ ] No committed file contains a personal absolute path.
- [ ] No committed file contains a fixed LAN or Tailscale IP.
- [ ] html-serve paths are expressed with `HTML_SERVE_DATA_DIR` and relative
      output paths.
- [ ] User-facing URLs prefer `HTML_SERVE_BASE_URL`; on this host that should
      be configured as the Tailscale base URL.
- [ ] Localhost URLs are used only as fallback, service checks, or secondary
      troubleshooting links.

## Page Quality

- [ ] First viewport shows the actual subject.
- [ ] The information organization model matches the reader task.
- [ ] The page pattern matches the reader task.
- [ ] Source and metadata visibility are intentional: hidden, compact, or
      expanded.
- [ ] Mobile and desktop layouts do not overlap.
- [ ] Body line length stays in the readable range.
- [ ] Text fits inside buttons, labels, and cards.
- [ ] Copy/export interaction works over plain HTTP.

## Visual Quality

- [ ] No hardcoded AI-default indigo colors.
- [ ] No decorative gradient blob or generic SVG background.
- [ ] No emoji icons in UI chrome.
- [ ] Accent color is used sparingly.
- [ ] Cards are not nested.
- [ ] Placeholder and example content were removed from final artifacts.

## Handoff

- [ ] Final response names the prototype URL.
- [ ] Final response names the workspace path.
- [ ] Final response names the chosen `DESIGN.md` reference.
- [ ] Final response states what validation was run.
