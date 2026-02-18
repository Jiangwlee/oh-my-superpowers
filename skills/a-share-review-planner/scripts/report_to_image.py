#!/usr/bin/env python3
"""
report_to_image.py - 将 Markdown 复盘报告转为图片/PDF，不依赖 Openclaw browser relay

用法：
    python3 scripts/report_to_image.py <input.md> [--format png|pdf] [--output path]

默认输出 PNG（与输入文件同目录，扩展名替换）。
PNG 模式：使用 Chrome headless 截图，viewport 宽 750px，自动探测页面高度。
PDF 模式：使用 Chrome headless --print-to-pdf，生成完整分页 PDF。

依赖：系统已安装 Google Chrome（/Applications/Google Chrome.app），无需额外 pip 包。
"""

import argparse
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Chrome 可执行路径（按优先级） ───────────────────────────────────────────
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]

# ── 手机友好 CSS（与 report_to_html.py 保持一致）──────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, 'PingFang SC', 'Hiragino Sans GB',
                 'Microsoft YaHei', sans-serif;
    font-size: 30px;
    line-height: 1.8;
    color: #1a1a1a;
    background: #ffffff;
    padding: 28px 22px 48px;
    max-width: 750px;
}
h1 {
    font-size: 38px;
    color: #0d47a1;
    border-bottom: 2px solid #0d47a1;
    padding-bottom: 8px;
    margin: 20px 0 14px;
}
h2 {
    font-size: 35px;
    color: #1565c0;
    margin: 22px 0 12px;
    padding-left: 10px;
    border-left: 4px solid #42a5f5;
}
h3 { font-size: 30px; color: #333; margin: 16px 0 8px; }
p { margin: 8px 0; }
ul, ol { padding-left: 22px; margin: 8px 0; }
li { margin: 5px 0; }
strong { color: #c62828; }
em { color: #5c6bc0; font-style: normal; font-weight: 500; }
table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 27px; }
th {
    background: #e3f2fd; color: #0d47a1;
    padding: 8px 12px; text-align: left; border: 1px solid #bbdefb;
}
td { padding: 7px 12px; border: 1px solid #e0e0e0; vertical-align: top; }
tr:nth-child(even) td { background: #fafafa; }
code {
    background: #f3f3f3; padding: 2px 6px; border-radius: 3px;
    font-size: 27px; font-family: 'SF Mono', Menlo, Consolas, monospace;
}
pre {
    background: #f3f3f3; padding: 16px; border-radius: 6px;
    font-size: 25px; overflow-x: auto; margin: 12px 0;
    white-space: pre-wrap; word-break: break-all;
}
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #90caf9; padding-left: 16px; color: #555; margin: 12px 0; }
hr { border: none; border-top: 1px solid #e8e8e8; margin: 18px 0; }
"""


def find_chrome() -> str | None:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def markdown_to_html(md_path: Path) -> str:
    """Markdown → 完整 HTML 字符串"""
    if shutil.which("pandoc"):
        try:
            result = subprocess.run(
                ["pandoc", "--from=markdown", "--to=html5", str(md_path)],
                capture_output=True, text=True, check=True
            )
            body = result.stdout
        except subprocess.CalledProcessError:
            body = _md_fallback(md_path)
    else:
        body = _md_fallback(md_path)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style>
</head>
<body>{body}</body>
</html>"""


def _md_fallback(md_path: Path) -> str:
    content = md_path.read_text(encoding="utf-8")
    return f'<pre style="white-space:pre-wrap;font-size:14px;">{html.escape(content)}</pre>'


def screenshot_png(html_file: Path, output: Path, dpr: int = 3, width: int = 750) -> None:
    """
    用 Node.js CDP（screenshot.js）截全页 PNG。
    - 自动探测真实页面高度（无多余空白）
    - DPR=3（iPhone 17 原生 3x Retina），输出宽度 2250px，文字锐利
    - 需要 Node.js 18+ 和系统 Chrome
    """
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 node，无法运行 screenshot.js")

    script = Path(__file__).parent / "screenshot.js"
    if not script.exists():
        raise RuntimeError(f"找不到 screenshot.js: {script}")

    result = subprocess.run(
        [node, str(script), str(html_file.absolute()), str(output.absolute()),
         str(dpr), str(width)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"screenshot.js 失败: {result.stderr.strip()}")
    if result.stdout.strip():
        print(f"  截图尺寸: {result.stdout.strip()}", file=sys.stderr)


def generate_pdf(chrome: str, html_file: Path, output: Path) -> None:
    """用 headless Chrome 生成完整 PDF"""
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={output.absolute()}",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"file://{html_file.absolute()}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 复盘报告转为 PNG 图片或 PDF（不依赖 Openclaw browser）"
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--format", choices=["png", "pdf"], default="png",
                        help="输出格式（默认 png）")
    parser.add_argument("--output", help="输出文件路径（默认与输入同目录）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：找不到输入文件：{input_path}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(f".{fmt}")

    # 先生成 HTML 中间文件（临时）
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        html_path = Path(tmp.name)

    try:
        html_content = markdown_to_html(input_path)
        html_path.write_text(html_content, encoding="utf-8")

        if fmt == "pdf":
            chrome = find_chrome()
            if not chrome:
                print("错误：未找到 Google Chrome", file=sys.stderr)
                sys.exit(1)
            generate_pdf(chrome, html_path, output_path)
        else:
            screenshot_png(html_path, output_path)
    finally:
        html_path.unlink(missing_ok=True)

    if not output_path.exists():
        print(f"错误：输出文件未生成：{output_path}", file=sys.stderr)
        sys.exit(1)

    size_kb = output_path.stat().st_size // 1024
    print(f"完成（{fmt}，{size_kb}KB）：{output_path}")
    print(f"file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
