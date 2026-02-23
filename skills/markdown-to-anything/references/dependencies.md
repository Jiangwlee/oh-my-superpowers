# 依赖与降级

## 必需（按输出路径）

- `node` + `Google Chrome/Chromium`
  - 用于 `scripts/screenshot.js`
  - 报告链 PNG/PDF、SVG->PNG、CDP 校验都依赖它

## 可选（报告链 Markdown -> HTML）

- `pandoc`（首选）
  - 可用时优先用于 Markdown -> HTML
- `scripts/vendor/marked.min.js`
  - 无 `pandoc` 时的前端渲染后备
- Python 内置 fallback renderer
  - `marked` 缺失时再降级

## 降级顺序（报告链）

`pandoc` -> `marked` -> Python fallback

调用方应读取 `--stdout-manifest` 中的 `warnings`，不要假设一定使用了 `pandoc`。

## 常见故障

- `node not found`
  - 安装 Node.js，确认 `node` 在 PATH
- `Chrome not found`
  - 安装 Google Chrome 或 Chromium（`screenshot.js` 会按内置路径查找）
- `screenshot.js --png/--pdf failed`
  - 先用 `report_render.py --format html` 生成 HTML，再单独跑 `screenshot.js` 定位问题
