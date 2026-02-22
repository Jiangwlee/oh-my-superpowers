#!/usr/bin/env python3
"""
report_to_html.py - 将 Markdown 复盘报告转为手机友好的 HTML 文件

用法：
    python3 scripts/report_to_html.py <input.md> [output.html]

输出 HTML 文件，供 Openclaw browser 工具打开截图后推送给用户。
无需额外依赖：有 pandoc 时渲染富文本，无 pandoc 时自动降级为纯文本展示。
"""

import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path


# ── 手机适配 CSS（750px 宽，适合 Telegram）─────────────────────────────────
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
h3 { font-size: 15px; color: #333; margin: 12px 0 6px; }
p { margin: 6px 0; }
ul, ol { padding-left: 18px; margin: 6px 0; }
li { margin: 3px 0; }
strong { color: #c62828; }
em { color: #5c6bc0; font-style: normal; font-weight: 500; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
th {
    background: #e3f2fd; color: #0d47a1;
    padding: 6px 8px; text-align: left; border: 1px solid #bbdefb;
}
td { padding: 5px 8px; border: 1px solid #e0e0e0; vertical-align: top; }
tr:nth-child(even) td { background: #fafafa; }
code {
    background: #f3f3f3; padding: 1px 5px; border-radius: 3px;
    font-size: 13px; font-family: 'SF Mono', Menlo, Consolas, monospace;
}
pre {
    background: #f3f3f3; padding: 12px; border-radius: 6px;
    font-size: 12px; overflow-x: auto; margin: 8px 0;
    white-space: pre-wrap; word-break: break-all;
}
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #90caf9; padding-left: 12px; color: #555; margin: 8px 0; }
hr { border: none; border-top: 1px solid #e8e8e8; margin: 14px 0; }
"""


def markdown_to_html_body(md_path: Path) -> tuple[str, str]:
    """
    将 Markdown 转为 HTML body 片段。
    返回 (html_body, mode)，mode 为 'pandoc' 或 'fallback'。
    """
    if shutil.which("pandoc"):
        try:
            result = subprocess.run(
                ["pandoc", "--from=markdown", "--to=html5", str(md_path)],
                capture_output=True, text=True, check=True
            )
            return result.stdout, "pandoc"
        except subprocess.CalledProcessError as e:
            print(f"警告：pandoc 转换失败（{e}），降级为纯文本模式", file=sys.stderr)

    # Fallback：将原始 Markdown 转义后用 <pre> 展示，保留可读性
    content = md_path.read_text(encoding="utf-8")
    body = f'<pre style="white-space:pre-wrap;font-size:14px;">{html.escape(content)}</pre>'
    return body, "fallback"


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 复盘报告转为手机友好 HTML（供 Openclaw browser 截图）"
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument(
        "output", nargs="?",
        help="输出 HTML 文件路径（默认与输入同目录，扩展名改为 .html）"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：找不到输入文件：{input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")

    html_body, mode = markdown_to_html_body(input_path)
    if mode == "fallback":
        print("提示：pandoc 未安装，使用纯文本降级模式", file=sys.stderr)

    output_path.write_text(wrap_html(html_body), encoding="utf-8")

    print(f"完成（{mode}）：{output_path}")
    # 输出 file:// URL，方便直接传给 browser 工具
    print(f"file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
