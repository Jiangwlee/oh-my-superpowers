# Chrome CDP 参考（markdown-to-anything）

> 仅记录本 skill 用到的最小 CDP 调用集合。

## 用途

`scripts/screenshot.js` 统一处理三类任务：
- `SVG/HTML -> PNG`（`Page.captureScreenshot`）
- `HTML -> PDF`（`Page.printToPDF`）
- `SVG bbox 校验`（`Runtime.evaluate` + DOM `getBBox()`）

## 启动 Chrome（headless）

关键参数：
- `--headless=new`
- `--remote-debugging-port=<port>`
- `--window-size=<w>,<h>`
- `--no-sandbox`（容器/CI 常用）

## 常用 CDP 方法

### 1. 页面与运行时启用

- `Page.enable`
- `Runtime.enable`

### 2. 等待页面加载

- 监听事件：`Page.loadEventFired`
- 额外等待：`document.fonts.ready`（PDF 路径建议）

### 3. 获取内容尺寸（截图前）

通过 `Runtime.evaluate` 执行 JS：
- `document.documentElement.scrollWidth`
- `document.documentElement.scrollHeight`

## PNG 截图

### 视口/DPR 设置

使用 `Emulation.setDeviceMetricsOverride`：
- `width`
- `height`
- `deviceScaleFactor`（如 `3`）
- `mobile: false`（避免字体 boosting）

### 截图

使用 `Page.captureScreenshot`：
- `format: "png"`
- `captureBeyondViewport: true`
- `clip: {x, y, width, height, scale: 1}`

## PDF 输出（A4）

使用 `Page.printToPDF`：
- `paperWidth: 8.27`
- `paperHeight: 11.69`
- `marginTop/Bottom/Left/Right: 0.4`
- `printBackground: true`
- `transferMode: "ReturnAsBase64"`

## SVG 布局校验（CDP 路径）

思路：在页面内注入 JS，通过 `querySelectorAll('svg text, svg rect, ...')` 遍历元素，调用 `getBBox()` 获取 bbox，然后：
- 检查越界（是否超出画布）
- 计算 bbox 交集（目前主要用于 `text-text` 碰撞）

## 实践建议

- 优先把复杂计算放到页面内 JS（`Runtime.evaluate`）完成，只把 JSON 结果回传给 Node。
- 失败时保留 Python 近似校验兜底，避免 Chrome/Node 缺失时整条链路不可用。
- 生成 PDF 前等待 `document.fonts.ready`，降低 CJK 字体错乱风险。
