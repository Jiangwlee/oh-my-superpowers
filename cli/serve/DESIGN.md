# omp serve Design Contract

`omp serve` is a project-local Skill workbench. Its interface must feel like a
dense development surface, not a marketing page, generic file manager, or chat
demo.

This contract is derived from the C5 prototype:

`/oh-my-superpowers/omp-serve-ui-prototypes/prototype-c5-two-message-types.html`

## Information Model

Use a **task-based** primary model with a **hierarchical tree** support model.

The user arrives to complete development tasks: inspect files, preview or edit
content, and work with Pi. The file tree supports navigation, but the product is
not organized around browsing alone.

## Layout

Use a three-column workbench:

| Region | Purpose | Constraint |
|---|---|---|
| Left | Project file tree | Narrow, scannable, lazy-expandable |
| Center | Editor and preview surface | Largest flexible region |
| Right | Pi interaction surface | Chat and terminal modes share the same panel |

Keep the app full viewport height. Use fixed chrome rows for top and bottom
bars, and let the middle work area consume remaining height.

Use stable grid dimensions:

- App shell: `44px 1fr 30px`.
- Main grid: file tree, editor, assistant/terminal.
- Panels: `min-width: 0`, `min-height: 0`, `overflow: hidden`.
- Inner scroll regions own their scrolling; the page body must not scroll.

## Visual Language

Use the C5 visual system:

| Token | Role |
|---|---|
| `--bg` | warm near-black page background |
| `--panel` | warm dark panel surface |
| `--ink` | primary text |
| `--muted` | ordinary readable text |
| `--faint` | secondary metadata |
| `--line` | low-contrast borders |
| `--green` | active, approved, successful state |
| `--amber` | folder, mode, pending patch state |
| `--cyan` | user prompt and secondary accent |
| `--red` | destructive or removed diff state |

Keep neutral pixels dominant. Accent colors signal state and hierarchy; do not
use them as decoration.

## Typography

Use sans-serif for application chrome and body UI. Use the mono stack for file
paths, command labels, metadata, terminal text, code, and compact controls.

Rules:

- Body letter spacing must be `0`.
- Uppercase chrome labels use positive tracking.
- Compact controls use mono text and stable heights.
- Terminal text inherits the mono system and must not introduce a separate
  visual language.

## Panels

Panels are dense work surfaces:

- Use low-contrast translucent dark surfaces.
- Use one-pixel borders with `--line`.
- Keep panel radius near `20px`.
- Use inner tool surfaces with darker backgrounds and smaller radii.
- Do not nest decorative cards.
- Use cards only for repeated assistant turns, tool steps, or comparable
  repeated items.

## Controls

Use compact controls:

- Tab and mode controls stay small and predictable.
- Active states use color plus background, not size changes.
- Buttons must not resize the surrounding toolbar on hover or active state.
- File tabs may truncate, but must not push mode controls off screen.

## Scrollbars

All scrollable regions must use one scrollbar design language. Browser default
scrollbars must not leak through in any workbench surface.

Apply the same scrollbar treatment to:

- File tree scroll containers.
- Markdown preview.
- Diff view.
- Assistant chat stream.
- Editor/code surfaces.
- Terminal/xterm viewport.

Dark theme scrollbar:

```css
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(243, 236, 221, .16);
  border-radius: 999px;
  border: 3px solid transparent;
  background-clip: content-box;
}
```

Light theme scrollbar:

```css
::-webkit-scrollbar-thumb {
  background: rgba(42, 37, 27, .20);
  border: 3px solid transparent;
  background-clip: content-box;
}
```

For xterm.js, target the generated viewport explicitly:

```css
.terminal-surface .xterm-viewport::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.terminal-surface .xterm-viewport::-webkit-scrollbar-thumb {
  background: rgba(243, 236, 221, .16);
  border-radius: 999px;
  border: 3px solid transparent;
  background-clip: content-box;
}
```

Do not rely on parent scrollbar rules to style generated component internals.
When adding a third-party component, inspect its generated scroll element and
bind the workbench scrollbar contract directly.

## Terminal Mode

Terminal mode is a first-class Pi interaction mode, not an embedded external
widget.

Rules:

- The terminal pane must fill the right panel.
- The composer must disappear in terminal mode.
- The terminal surface must use the same border, radius, and dark inner surface
  language as editor surfaces.
- xterm dimensions must be constrained with `width: 100%`, `height: 100%`,
  `min-width: 0`, and parent grid constraints.
- Resize the PTY when the terminal container changes size.
- Terminal scrollbars must match the workbench scrollbar contract.

## Footer (Bottom Bar)

The 30px bottom bar is fixed chrome and splits into two halves:

- Left: the `Project` label, the project tab strip, and the `+` add button. Tabs
  are mono pills; the active project uses color plus background (never a size
  change). The strip scrolls horizontally when crowded and must not leak a
  default scrollbar or push the right strip off screen.
- Right: the session/mode/state info strip.

The bar must keep its 30px height and never let the page body scroll. Adding a
project opens the shared dialog (see below) with a `$HOME`-sandboxed directory
picker; removing a project always goes through a confirm dialog.

## Dialogs

All popups use one reusable dialog component (`web/dialog.ts`, styled under
`.omp-dialog`): a blurred scrim, a titled panel on `--panel` with `--line`
borders and ~16px radius, primary/danger/default pill actions, and scroll
regions bound to the workbench scrollbar contract. Do not hand-roll one-off
modals — extend the component so every dialog shares the same language.

## Responsive Behavior

At medium widths, keep the editor and assistant usable by reducing the file tree
width and pinning the assistant panel when needed.

At narrow mobile widths, hide the file tree and assistant panel. Do not squeeze
the three-column workbench into unusable columns.

## Verification Checklist

Before calling a visual change done:

- Open the workbench in Chrome.
- Check desktop width and a narrow viewport.
- Inspect all scrollable surfaces, including terminal/xterm internals.
- Confirm `document.body.scrollWidth === document.body.clientWidth`.
- Confirm terminal mode shows Pi output and does not overflow the right panel.
- Confirm light and dark theme scrollbar thumbs use matching geometry.
- Confirm hover, active, and focused states do not resize fixed-format controls.
