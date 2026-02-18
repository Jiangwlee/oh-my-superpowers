#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""
report_to_image.py - 将 Markdown 复盘报告转为手机友好的 PNG 图片（适合 Telegram 推送）

用法：
    uv run scripts/report_to_image.py <input.md> <output.png> [--width 750]

首次使用需安装浏览器（只需一次）：
    uv run playwright install chromium
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


# ── 手机适配的 CSS 样式 ──────────────────────────────────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, 'PingFang SC', 'Hiragino Sans GB',
                 'Microsoft YaHei', sans-serif;
    font-size: 15px;
    line-height: 1.7;
    color: #1a1a1a;
    background: #ffffff;
    padding: 20px 18px 32px;
    max-width: 750px;
}
h1 {
    font-size: 19px;
    color: #0d47a1;
    border-bottom: 2px solid #0d47a1;
    padding-bottom: 6px;
    margin: 16px 0 10px;
}
h2 {
    font-size: 16px;
    color: #1565c0;
    margin: 18px 0 8px;
    padding-left: 8px;
    border-left: 3px solid #42a5f5;
}
h3 {
    font-size: 15px;
    color: #333;
    margin: 12px 0 6px;
}
p { margin: 6px 0; }
ul, ol { padding-left: 18px; margin: 6px 0; }
li { margin: 3px 0; }
strong { color: #c62828; }
em { color: #5c6bc0; font-style: normal; font-weight: 500; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 13px;
}
th {
    background: #e3f2fd;
    color: #0d47a1;
    padding: 6px 8px;
    text-align: left;
    border: 1px solid #bbdefb;
}
td {
    padding: 5px 8px;
    border: 1px solid #e0e0e0;
    vertical-align: top;
}
tr:nth-child(even) td { background: #fafafa; }
code {
    background: #f3f3f3;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 13px;
    font-family: 'SF Mono', Menlo, Consolas, monospace;
}
pre {
    background: #f3f3f3;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    overflow-x: auto;
    margin: 8px 0;
}
pre code { background: none; padding: 0; }
blockquote {
    border-left: 3px solid #90caf9;
    padding-left: 12px;
    color: #555;
    margin: 8px 0;
}
hr {
    border: none;
    border-top: 1px solid #e8e8e8;
    margin: 14px 0;
}
"""


def markdown_to_html_body(md_path: Path) -> str:
    """用 pandoc 将 Markdown 转为 HTML body 片段。"""
    result = subprocess.run(
        ["pandoc", "--from=markdown", "--to=html5", str(md_path)],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style>
</head>
<body>{body}</body>
</html>"""


def html_to_png(html_path: Path, output_path: Path, width: int) -> None:
    """用 playwright headless chromium 截全页图。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.goto(f"file://{html_path.absolute()}", wait_until="load")
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 复盘报告转为手机友好 PNG（适合 Telegram）"
    )
    parser.add_argument("input",  help="输入 Markdown 文件路径")
    parser.add_argument("output", help="输出 PNG 文件路径")
    parser.add_argument(
        "--width", type=int, default=750,
        help="图片宽度（像素），默认 750（Telegram 手机推荐）"
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"错误：找不到输入文件：{input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"转换中：{input_path} → {output_path}（宽度 {args.width}px）...")

    html_body = markdown_to_html_body(input_path)
    full_html = wrap_html(html_body)

    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(full_html)
        tmp_html = Path(f.name)

    try:
        html_to_png(tmp_html, output_path, args.width)
    finally:
        tmp_html.unlink(missing_ok=True)

    size_kb = output_path.stat().st_size // 1024
    print(f"完成：{output_path}（{size_kb} KB）")


if __name__ == "__main__":
    main()
