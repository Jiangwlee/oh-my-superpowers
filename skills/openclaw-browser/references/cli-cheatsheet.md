# OpenClaw Browser CLI Cheatsheet

Purpose: Provide short command examples for the main `openclaw browser` command families.
Input:   An active `openclaw` CLI plus a browser task such as page reading, interaction,
         debugging, or environment simulation.
Output:  Minimal command snippets that can be adapted in the current session.
Sections: Session | Tabs | Interaction | Waiting | Debugging | Environment

## Session

```bash
openclaw browser status
openclaw browser start
openclaw browser stop
openclaw browser profiles
openclaw browser create-profile qa-mobile
openclaw browser --browser-profile qa-mobile status
```

## Tabs

```bash
openclaw browser open https://example.com
openclaw browser navigate https://example.com/dashboard
openclaw browser tabs
openclaw browser focus abcd1234
openclaw browser close abcd1234
```

## Interaction

Take a snapshot before using any `ref` below.

```bash
openclaw browser snapshot
openclaw browser snapshot --efficient
openclaw browser snapshot --format aria --limit 200
openclaw browser click 12
openclaw browser click 12 --double
openclaw browser hover 23
openclaw browser type 31 "hello"
openclaw browser type 31 "hello" --submit
openclaw browser fill --fields '[{"ref":"8","value":"Ada"},{"ref":"9","value":"Lovelace"}]'
openclaw browser select 17 OptionA OptionB
openclaw browser drag 44 45
openclaw browser press Enter
openclaw browser scrollintoview 51
openclaw browser highlight 51
openclaw browser upload /tmp/example.pdf
openclaw browser dialog --accept
```

## Waiting

Prefer these before `--fn`. Use `--fn` only as a last resort when ordinary wait modes cannot express readiness.

```bash
openclaw browser wait --load networkidle
openclaw browser wait --url '**/dashboard'
openclaw browser wait --text 'Saved'
openclaw browser wait '.toast-success'
openclaw browser wait --time 1000
openclaw browser wait --fn '() => window.appReady === true'
```

## Extraction And Debugging

Use `evaluate --fn` only when snapshot, wait, console, requests, or other browser commands cannot expose the needed state.

```bash
openclaw browser evaluate --fn '() => document.title'
openclaw browser evaluate --fn '(el) => el.textContent' --ref 7
openclaw browser screenshot
openclaw browser screenshot --full-page
openclaw browser screenshot --ref 7
openclaw browser pdf
openclaw browser console --level error
openclaw browser requests
openclaw browser errors
openclaw browser responsebody --url '**/api/search*'
openclaw browser trace
```

## Environment

```bash
openclaw browser resize 1280 720
openclaw browser set viewport 390 844
openclaw browser set device 'iPhone 14'
openclaw browser set timezone Asia/Shanghai
openclaw browser set locale zh-CN
openclaw browser set geo 31.2304 121.4737
openclaw browser set media dark
openclaw browser set headers '{"x-debug":"1"}'
openclaw browser set offline on
openclaw browser set offline off
```

## Notes

- Use `--json` when parsing output programmatically.
- Use `--target-id <id>` when a command must apply to a specific tab.
- Re-run `snapshot` after navigation or major DOM updates.
