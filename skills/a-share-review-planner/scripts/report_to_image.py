#!/usr/bin/env python3
"""
report_to_image.py - 将 Markdown 复盘报告转为图片/PDF，不依赖 Openclaw browser relay

用法：
    python3 scripts/report_to_image.py <input.md> [--format png|pdf] [--output path]

默认输出到 ~/.openclaw/media/a-share-review/...，确保可被 Openclaw Telegram 通道发送。
PNG 模式：使用 Chrome headless 截图，viewport 宽 750px，自动探测页面高度。
PDF 模式：使用 Chrome headless --print-to-pdf，生成完整分页 PDF。

依赖：系统已安装 Google Chrome（/Applications/Google Chrome.app），无需额外 pip 包。
"""

import argparse
import html
import platform
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

OPENCLAW_MEDIA_ROOT = Path.home() / ".openclaw" / "media"

# ── 手机友好 CSS（与 report_to_html.py 保持一致）──────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0;
    -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
body {
    font-family: 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB',
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


def _font_css() -> str:
    """
    生成字体加载 CSS/HTML 片段。
    - macOS：优先使用 Google Fonts CDN（Noto Sans SC），fallback 到系统 PingFang SC
    - Linux：优先使用本地安装的 Noto CJK（fonts-noto-cjk 包），无需 CDN
    """
    is_linux = platform.system() == "Linux"

    # 检查本地 Noto CJK 是否已安装（Linux apt 安装后字体名为 "Noto Sans CJK SC"）
    has_local_noto = False
    if is_linux:
        try:
            result = subprocess.run(
                ["fc-list", ":lang=zh"],
                capture_output=True, text=True, timeout=5
            )
            has_local_noto = "Noto" in result.stdout
        except Exception:
            pass

    if is_linux and has_local_noto:
        # Linux：本地字体，无需 CDN
        return '<style>/* 使用本地 Noto CJK 字体 */</style>'
    else:
        # macOS 或 Linux 未安装本地字体：使用 Google Fonts CDN
        return """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">"""


def _font_family() -> str:
    """根据平台返回 font-family 字符串（含 emoji 字体，确保 PDF 中 emoji 正常显示）"""
    is_linux = platform.system() == "Linux"
    emoji = "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji'"
    if is_linux:
        return f"'Noto Sans CJK SC', 'Noto Sans SC', 'WenQuanYi Micro Hei', {emoji}, sans-serif"
    return f"'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', {emoji}, sans-serif"


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

    css = CSS.replace(
        "'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB',\n                 'Microsoft YaHei', sans-serif",
        _font_family()
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{_font_css()}
<style>{css}</style>
</head>
<body>{body}</body>
</html>"""


def _md_fallback(md_path: Path) -> str:
    content = md_path.read_text(encoding="utf-8")
    return f'<pre style="white-space:pre-wrap;font-size:14px;">{html.escape(content)}</pre>'


def screenshot_png(
    html_file: Path,
    output: Path,
    dpr: int = 3,
    width: int = 750,
    max_page_height: int = 2000,
) -> list[Path]:
    """
    用 Node.js CDP（screenshot.js）截全页 PNG，支持分页。

    max_page_height: CSS 像素。>0 时启用分页模式，生成 output_1.png output_2.png ...
    返回: 生成的文件路径列表（分页时为多个，单图时为一个）
    """
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 node，无法运行 screenshot.js")

    script = Path(__file__).parent / "screenshot.js"
    if not script.exists():
        raise RuntimeError(f"找不到 screenshot.js: {script}")

    result = subprocess.run(
        [node, str(script), str(html_file.absolute()), str(output.absolute()),
         str(dpr), str(width), str(max_page_height)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"screenshot.js 失败: {result.stderr.strip()}")

    # 解析输出，收集生成的文件路径
    generated: list[Path] = []
    for line in result.stdout.strip().splitlines():
        if line.startswith("page"):
            # 分页模式: "page1:/path/to/file.png:2250x6000"
            parts = line.split(":", 2)
            if len(parts) >= 2:
                generated.append(Path(parts[1]))
                print(f"  {parts[0]}: {parts[2] if len(parts) > 2 else ''}", file=sys.stderr)
        else:
            # 单图模式: "2250x25689px (...)"
            print(f"  截图尺寸: {line}", file=sys.stderr)
            generated.append(output)

    return generated if generated else [output]


def generate_pdf(html_file: Path, output: Path) -> None:
    """
    用 Node.js CDP（screenshot.js --pdf）生成 PDF。
    等待 document.fonts.ready，确保 Noto Sans SC 字体嵌入，中文正常显示。
    """
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 node，无法运行 screenshot.js")

    script = Path(__file__).parent / "screenshot.js"
    if not script.exists():
        raise RuntimeError(f"找不到 screenshot.js: {script}")

    result = subprocess.run(
        [node, str(script), "--pdf",
         str(html_file.absolute()), str(output.absolute())],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"screenshot.js --pdf 失败: {result.stderr.strip()}")


def _default_output_path(input_path: Path, fmt: str) -> Path:
    """
    默认输出到 Openclaw 允许目录（~/.openclaw/media）。
    若输入为 /tmp/a-share-review/{DATE}/report.md，则输出到
    ~/.openclaw/media/a-share-review/{DATE}/report.{fmt}。
    """
    parts = input_path.resolve().parts
    if len(parts) >= 4 and parts[-4] == "tmp" and parts[-3] == "a-share-review":
        date_part = parts[-2]
        return OPENCLAW_MEDIA_ROOT / "a-share-review" / date_part / f"{input_path.stem}.{fmt}"
    return OPENCLAW_MEDIA_ROOT / "a-share-review" / f"{input_path.stem}.{fmt}"


def _is_under_dir(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 复盘报告转为 PNG 图片或 PDF（不依赖 Openclaw browser）"
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--format", choices=["png", "pdf"], default="png",
                        help="输出格式（默认 png）")
    parser.add_argument("--output", help="输出文件路径（默认写入 ~/.openclaw/media/a-share-review）")
    parser.add_argument("--max-height", type=int, default=2000,
                        help="分页高度(CSS px)，0=单图模式，默认2000")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"错误：找不到输入文件：{input_path}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        output_path = _default_output_path(input_path, fmt)

    if not _is_under_dir(output_path, OPENCLAW_MEDIA_ROOT):
        print(
            f"警告：输出路径不在 Openclaw 建议目录下，Telegram 通道可能拒绝该文件：{output_path}",
            file=sys.stderr,
        )

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 先生成 HTML 中间文件（临时）
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        html_path = Path(tmp.name)

    try:
        html_content = markdown_to_html(input_path)
        html_path.write_text(html_content, encoding="utf-8")

        if fmt == "pdf":
            generate_pdf(html_path, output_path)
            output_files = [output_path]
        else:
            output_files = screenshot_png(html_path, output_path,
                                          max_page_height=args.max_height)
    finally:
        html_path.unlink(missing_ok=True)

    # 输出所有生成的文件
    for f in output_files:
        if not f.exists():
            print(f"错误：输出文件未生成：{f}", file=sys.stderr)
            sys.exit(1)
        size_kb = f.stat().st_size // 1024
        print(f"完成（{fmt}，{size_kb}KB）：{f}")
        print(f"file://{f.absolute()}")


if __name__ == "__main__":
    main()
