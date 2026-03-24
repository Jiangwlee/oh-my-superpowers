# CLI 参数（主入口）

主入口：

```bash
python scripts/convert.py <input.md> [options]
```

## 常用命令

标准导出 PDF：

```bash
python scripts/convert.py report.md --format pdf --same-dir --stdout-manifest
```

标准导出 PNG：

```bash
python scripts/convert.py report.md --format png --same-dir --stdout-manifest
```

保留中间文件：

```bash
python scripts/convert.py report.md --format pdf --same-dir --keep-html --keep-clean --stdout-manifest
```

仅导出 HTML：

```bash
python scripts/convert.py report.md --format html --same-dir --stdout-manifest
```

## 参数说明

### 必选
- `input`
  - 本地 Markdown 文件路径

### 路径选择
- `--mode auto|report|card`
  - `auto`：默认走标准 report 路径
  - `report`：强制走标准程序化导出
  - `card`：当前 CLI 未实现，视觉图按 `SKILL.md` 的 SVG/PNG SOP 处理

- `--format pdf|png|html|both`
  - `pdf`：导出 PDF
  - `png`：导出普通报告图
  - `html`：只导出 HTML
  - `both`：同时导出 PDF 和 PNG

### 输出控制
- `--output <path>`
  - 指定输出文件或输出基路径
  - 若传入带后缀路径，会自动去掉后缀作为 base

- `--same-dir`
  - 输出到输入文件同目录
  - 例如 `report.md -> report_report.pdf`

- `--keep-html`
  - 保留中间 HTML

- `--keep-clean`
  - 保留 `normalize_input.py` 生成的 clean markdown

### 渲染控制
- `--theme dark|blue|light`
  - `pdf` 默认 `blue`
  - `png` 默认 `light`

- `--font-size small|medium|large`
  - 控制 HTML 报告渲染字号

- `--engine auto|pandoc|marked|fallback`
  - Markdown -> HTML 引擎优先级
  - `auto` 会优先尝试 `pandoc`

- `--normalize auto|always|never`
  - `auto`：先 inspect，若是 `light_dirty` 则自动清洗
  - `always`：无条件生成 clean markdown 再渲染
  - `never`：跳过脚本清洗

- `--pdf-backend auto|html`
  - 当前 `auto` 与 `html` 等价
  - 表示 PDF 走 `Markdown -> HTML -> Chromium PDF`

### 输出
- `--stdout-manifest`
  - 输出 JSON manifest，推荐给调用方

## Manifest 关键字段

- `ok`
- `input`
- `mode`
- `format`
- `files`
- `intermediate_files`
- `inspection`
- `normalization`
- `engine`
- `warnings`
- `errors`

示例：

```json
{
  "ok": true,
  "mode": "report",
  "format": "pdf",
  "files": ["/path/to/report_report.pdf"],
  "inspection": {
    "cleanliness": "light_dirty",
    "recommended_path": "normalize_then_render"
  },
  "normalization": {
    "performed": true,
    "clean_file": "/path/to/report.clean.md"
  },
  "engine": {
    "markdown_to_html": "pandoc",
    "html_to_pdf": "chromium",
    "html_to_png": "n/a"
  },
  "warnings": [],
  "errors": []
}
```