# CLI 参数（主入口）

主入口：

```bash
python scripts/convert.py <input.md> [options]
```

参数说明：

- `--mode auto|report`
  - `auto`：默认按程序化报告路径处理（无触发词信息时默认 PDF）
  - `report`：使用 HTML 渲染链（推荐）
- `--format png|pdf|both`
  - `png/pdf/both` 均走 HTML -> Chrome CDP
- `--theme dark|blue|light`
  - `report+png` 默认 `light`
  - `report+pdf` 默认 `blue`
- `--font-size small|medium|large`
- `--output <path>`
  - 单输出可给完整文件名
  - `both` 建议给不带后缀的基路径
- `--engine auto|pandoc|marked|fallback`
  - 仅 `report` 渲染链使用
- `--stdout-manifest`
  - 输出 JSON manifest（推荐给调用方）

Manifest 关键字段：

- `mode`
- `format`
- `files`
- `warnings`
- `errors`
