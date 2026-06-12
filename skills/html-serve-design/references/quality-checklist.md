# Quality Checklist

Run this checklist before packaging the final template into the target skill.

## Template Ownership

- [ ] Final template is copied into `skills/<target-skill>/assets/`.
- [ ] Target skill has its own reference explaining HTML generation and
      html-serve publishing.
- [ ] Target skill does not depend on `skills/html-serve-design/` at runtime.
- [ ] No test files were placed inside the skill directory.

## Publishing Contract

- [ ] No committed file contains a personal absolute path.
- [ ] No committed file contains a fixed LAN or Tailscale IP.
- [ ] html-serve paths are expressed with `HTML_SERVE_DATA_DIR` and relative
      output paths.
- [ ] URLs are derived from `HTML_SERVE_BASE_URL` or documented as local
      examples.
- [ ] If html-serve is unavailable, target skill still preserves its core
      non-HTML artifacts.

## Page Quality

- [ ] First viewport shows the actual result subject.
- [ ] The page pattern matches the reader task.
- [ ] Source visibility is intentional: hidden, compact, or expanded.
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
- [ ] Placeholder and example content were removed.

## Handoff

- [ ] Final response names the prototype URL.
- [ ] Final response names each target skill file changed.
- [ ] Final response states what validation was run.
