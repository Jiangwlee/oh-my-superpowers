# Chrome DevTools MCP Command Reference

Complete reference for all chrome-devtools tools accessible via mcp-cli.

## Command Format

```bash
mcp-cli call chrome-devtools <tool> '<json-args>'
```

Both formats work: `<server> <tool>` or `<server>/<tool>`

```bash
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com"}'
mcp-cli call chrome-devtools/navigate_page '{"url": "https://example.com"}'
```

---

## Navigation

### navigate_page

Go to a URL, or back, forward, or reload.

```bash
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com"}'
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com", "timeout": 10000}'
mcp-cli call chrome-devtools navigate_page '{"type": "reload", "ignoreCache": true}'
mcp-cli call chrome-devtools navigate_page '{"type": "back"}'
mcp-cli call chrome-devtools navigate_page '{"type": "forward"}'
mcp-cli call chrome-devtools navigate_page '{"handleBeforeUnload": "accept"}'
```

**Parameters:**
- `type`: "url" | "back" | "forward" | "reload"
- `url`: Target URL (only for type=url)
- `ignoreCache`: Whether to ignore cache on reload
- `handleBeforeUnload`: "accept" | "decline"
- `timeout`: Maximum wait time in milliseconds

### list_pages

Get a list of pages open in the browser.

```bash
mcp-cli call chrome-devtools list_pages
```

### select_page

Select a page as context for future tool calls.

```bash
mcp-cli call chrome-devtools select_page '{"pageId": 1}'
mcp-cli call chrome-devtools select_page '{"pageId": 1, "bringToFront": true}'
```

**Parameters:**
- `pageId`: The ID of the page to select
- `bringToFront`: Whether to focus the page

### new_page

Open a new tab and load a URL.

```bash
mcp-cli call chrome-devtools new_page '{"url": "https://example.com"}'
mcp-cli call chrome-devtools new_page '{"url": "https://example.com", "background": true}'
mcp-cli call chrome-devtools new_page '{"url": "https://example.com", "isolatedContext": "ctx"}'
```

**Parameters:**
- `url`: URL to load (required)
- `background`: Open in background without bringing to front
- `isolatedContext`: Create isolated browser context
- `timeout`: Maximum wait time in milliseconds

### close_page

Close a page by its index. The last open page cannot be closed.

```bash
mcp-cli call chrome-devtools close_page '{"pageId": 1}'
```

---

## Page Content

### take_snapshot

Take a text snapshot of the page based on the accessibility tree. Lists elements with unique `uid`s.

```bash
mcp-cli call chrome-devtools take_snapshot
mcp-cli call chrome-devtools take_snapshot '{"verbose": true}'
mcp-cli call chrome-devtools take_snapshot '{"filePath": "/tmp/snapshot.txt"}'
```

**Parameters:**
- `verbose`: Include all possible information from a11y tree
- `filePath`: Save snapshot to file instead of returning inline

### take_screenshot

Take a screenshot of the page or element.

```bash
mcp-cli call chrome-devtools take_screenshot
mcp-cli call chrome-devtools take_screenshot '{"fullPage": true}'
mcp-cli call chrome-devtools take_screenshot '{"format": "jpeg", "quality": 80}'
mcp-cli call chrome-devtools take_screenshot '{"uid": "1_5"}'
mcp-cli call chrome-devtools take_screenshot '{"filePath": "/tmp/screenshot.png"}'
```

**Parameters:**
- `format`: "png" | "jpeg" | "webp" (default: png)
- `quality`: Compression quality 0-100 for JPEG/WebP
- `uid`: Screenshot specific element
- `fullPage`: Screenshot full page instead of viewport
- `filePath`: Save to file

### evaluate_script

Execute JavaScript in the page context. Returns JSON-serializable values.

```bash
mcp-cli call chrome-devtools evaluate_script '{"function": "() => document.title"}'
mcp-cli call chrome-devtools evaluate_script '{"function": "() => window.location.href"}'
mcp-cli call chrome-devtools evaluate_script '{"function": "(el) => el.innerText", "args": ["1_5"]}'
```

**Parameters:**
- `function`: JavaScript function declaration (required)
- `args`: Array of element uids to pass as arguments

---

## User Interaction

### click

Click on an element.

```bash
mcp-cli call chrome-devtools click '{"uid": "1_5"}'
mcp-cli call chrome-devtools click '{"uid": "1_5", "dblClick": true}'
mcp-cli call chrome-devtools click '{"uid": "1_5", "includeSnapshot": true}'
```

**Parameters:**
- `uid`: Element uid from snapshot (required)
- `dblClick`: Double click instead of single click
- `includeSnapshot`: Include updated snapshot in response

### fill

Type text into an input, textarea, or select option.

```bash
mcp-cli call chrome-devtools fill '{"uid": "1_2", "value": "search text"}'
mcp-cli call chrome-devtools fill '{"uid": "1_2", "value": "option value", "includeSnapshot": true}'
```

**Parameters:**
- `uid`: Element uid (required)
- `value`: Text to fill (required)
- `includeSnapshot`: Include updated snapshot

### fill_form

Fill multiple form elements at once.

```bash
mcp-cli call chrome-devtools fill_form '{"elements": [{"uid": "1_2", "value": "username"}, {"uid": "1_3", "value": "password"}]}'
mcp-cli call chrome-devtools fill_form '{"elements": [...], "includeSnapshot": true}'
```

**Parameters:**
- `elements`: Array of {uid, value} objects (required)
- `includeSnapshot`: Include updated snapshot

### press_key

Press a key or key combination.

```bash
mcp-cli call chrome-devtools press_key '{"key": "Enter"}'
mcp-cli call chrome-devtools press_key '{"key": "Control+A"}'
mcp-cli call chrome-devtools press_key '{"key": "Control+Shift+R"}'
mcp-cli call chrome-devtools press_key '{"key": "Tab", "includeSnapshot": true}'
```

**Parameters:**
- `key`: Key or combination (e.g., "Enter", "Control+A", "Alt+Tab")
- `includeSnapshot`: Include updated snapshot

### type_text

Type text using keyboard into a focused input.

```bash
mcp-cli call chrome-devtools type_text '{"text": "hello world"}'
```

**Parameters:**
- `text`: Text to type (required)

### hover

Hover over an element.

```bash
mcp-cli call chrome-devtools hover '{"uid": "1_5"}'
mcp-cli call chrome-devtools hover '{"uid": "1_5", "includeSnapshot": true}'
```

### drag

Drag an element onto another element.

```bash
mcp-cli call chrome-devtools drag '{"from_uid": "1_3", "to_uid": "1_8"}'
mcp-cli call chrome-devtools drag '{"from_uid": "1_3", "to_uid": "1_8", "includeSnapshot": true}'
```

**Parameters:**
- `from_uid`: Element to drag (required)
- `to_uid`: Element to drop onto (required)
- `includeSnapshot`: Include updated snapshot

### upload_file

Upload a file through a file input element.

```bash
mcp-cli call chrome-devtools upload_file '{"uid": "1_5", "filePath": "/path/to/file.pdf"}'
mcp-cli call chrome-devtools upload_file '{"uid": "1_5", "filePath": "/path/to/file.pdf", "includeSnapshot": true}'
```

**Parameters:**
- `uid`: File input element uid (required)
- `filePath`: Local path of file to upload (required)
- `includeSnapshot`: Include updated snapshot

---

## Waiting and Dialogs

### wait_for

Wait for specified text to appear on the page.

```bash
mcp-cli call chrome-devtools wait_for '{"text": ["Login successful"]}'
mcp-cli call chrome-devtools wait_for '{"text": ["Loading...", "Complete"], "timeout": 15000}'
```

**Parameters:**
- `text`: Non-empty array of texts (resolves when any appears)
- `timeout`: Maximum wait time in milliseconds

### handle_dialog

Handle a browser dialog (alert, confirm, prompt).

```bash
mcp-cli call chrome-devtools handle_dialog '{"action": "accept"}'
mcp-cli call chrome-devtools handle_dialog '{"action": "dismiss"}'
mcp-cli call chrome-devtools handle_dialog '{"action": "accept", "promptText": "custom value"}'
```

**Parameters:**
- `action`: "accept" | "dismiss" (required)
- `promptText`: Text to enter for prompt dialogs

---

## Emulation

### emulate

Emulate various features on the selected page.

```bash
mcp-cli call chrome-devtools emulate '{"viewport": "375x667x2,mobile,touch"}'
mcp-cli call chrome-devtools emulate '{"networkConditions": "Slow 3G"}'
mcp-cli call chrome-devtools emulate '{"cpuThrottlingRate": 4}'
mcp-cli call chrome-devtools emulate '{"geolocation": "37.7749,-122.4194"}'
mcp-cli call chrome-devtools emulate '{"colorScheme": "dark"}'
mcp-cli call chrome-devtools emulate '{"userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"}'
```

**Parameters:**
- `viewport`: Device viewport format: `<width>x<height>x<devicePixelRatio>[,mobile][,touch][,landscape]`
- `networkConditions`: "Offline" | "Slow 3G" | "Fast 3G" | "Slow 4G" | "Fast 4G"
- `cpuThrottlingRate`: CPU slowdown factor (1-20)
- `geolocation`: `<latitude>x<longitude>`
- `colorScheme`: "dark" | "light" | "auto"
- `userAgent`: Custom user agent string

### resize_page

Resize the selected page's window.

```bash
mcp-cli call chrome-devtools resize_page '{"width": 1920, "height": 1080}'
```

**Parameters:**
- `width`: Page width in pixels (required)
- `height`: Page height in pixels (required)

---

## Debugging

### list_console_messages

List all console messages for the current page.

```bash
mcp-cli call chrome-devtools list_console_messages
mcp-cli call chrome-devtools list_console_messages '{"types": ["error"]}'
mcp-cli call chrome-devtools list_console_messages '{"pageSize": 20, "pageIdx": 0}'
mcp-cli call chrome-devtools list_console_messages '{"types": ["error", "issue"], "includePreservedMessages": true}'
```

**Parameters:**
- `types`: Filter by message types (log, debug, info, error, warn, issue, etc.)
- `pageSize`: Maximum messages to return
- `pageIdx`: Page number (0-based)
- `includePreservedMessages`: Include messages from last 3 navigations

### get_console_message

Get a specific console message by ID.

```bash
mcp-cli call chrome-devtools get_console_message '{"msgid": 5}'
```

**Parameters:**
- `msgid`: Message ID (required)

### list_network_requests

List all network requests for the current page.

```bash
mcp-cli call chrome-devtools list_network_requests
mcp-cli call chrome-devtools list_network_requests '{"resourceTypes": ["xhr", "fetch"]}'
mcp-cli call chrome-devtools list_network_requests '{"pageSize": 50, "pageIdx": 0}'
mcp-cli call chrome-devtools list_network_requests '{"includePreservedRequests": true}'
```

**Parameters:**
- `resourceTypes`: Filter by resource types (document, stylesheet, image, script, xhr, fetch, etc.)
- `pageSize`: Maximum requests to return
- `pageIdx`: Page number (0-based)
- `includePreservedRequests`: Include requests from last 3 navigations

### get_network_request

Get details of a specific network request.

```bash
mcp-cli call chrome-devtools get_network_request '{"reqid": 123}'
mcp-cli call chrome-devtools get_network_request '{"reqid": 123, "responseFilePath": "/tmp/response.json"}'
mcp-cli call chrome-devtools get_network_request '{"requestFilePath": "/tmp/request.txt", "responseFilePath": "/tmp/response.json"}'
```

**Parameters:**
- `reqid`: Request ID (optional, returns currently selected if omitted)
- `requestFilePath`: Save request body to file
- `responseFilePath`: Save response body to file

---

## Performance

### lighthouse_audit

Run Lighthouse audit for accessibility, SEO, and best practices.

```bash
mcp-cli call chrome-devtools lighthouse_audit '{"mode": "navigation"}'
mcp-cli call chrome-devtools lighthouse_audit '{"mode": "snapshot", "device": "mobile"}'
mcp-cli call chrome-devtools lighthouse_audit '{"outputDirPath": "/tmp/lighthouse"}'
```

**Parameters:**
- `mode`: "navigation" (reload & audit) | "snapshot" (analyze current state)
- `device`: "desktop" | "mobile"
- `outputDirPath`: Directory to save reports

### performance_start_trace

Start a performance trace recording.

```bash
mcp-cli call chrome-devtools performance_start_trace '{"reload": true, "autoStop": true}'
mcp-cli call chrome-devtools performance_start_trace '{"reload": true, "autoStop": true, "filePath": "/tmp/trace.json.gz"}'
```

**Parameters:**
- `reload`: Automatically reload page after starting trace
- `autoStop`: Automatically stop trace when complete
- `filePath`: Save raw trace data to file

### performance_stop_trace

Stop the active performance trace.

```bash
mcp-cli call chrome-devtools performance_stop_trace
mcp-cli call chrome-devtools performance_stop_trace '{"filePath": "/tmp/trace.json"}'
```

**Parameters:**
- `filePath`: Save trace data to file

### performance_analyze_insight

Get detailed information on a specific performance insight.

```bash
mcp-cli call chrome-devtools performance_analyze_insight '{"insightSetId": "set-1", "insightName": "LCPBreakdown"}'
```

**Parameters:**
- `insightSetId`: ID from trace results (required)
- `insightName`: Insight name (e.g., "LCPBreakdown", "DocumentLatency")

### take_memory_snapshot

Capture a memory heapsnapshot for leak debugging.

```bash
mcp-cli call chrome-devtools take_memory_snapshot '{"filePath": "/tmp/snapshot.heapsnapshot"}'
```

**Parameters:**
- `filePath`: Path to save .heapsnapshot file (required)
