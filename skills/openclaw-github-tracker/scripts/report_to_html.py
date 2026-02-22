#!/usr/bin/env python3
"""
report_to_html.py - 将 GitHub Trending 报告转为手机友好的 HTML/PDF

用法：
    python3 scripts/report_to_html.py <input.md> [output.html]

输出 HTML 文件，供 Openclaw browser 工具打开截图后推送给用户。
"""

import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path


# ── 手机适配 CSS（750px 宽，适合 Telegram/WhatsApp）─────────────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, 'PingFang SC', 'Hiragino Sans GB',
                 'Microsoft YaHei', 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #24292f;
    background: #ffffff;
    padding: 16px 14px 24px;
    max-width: 750px;
}
.header {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
    color: white;
    padding: 20px 16px;
    margin: -16px -14px 20px;
    border-radius: 0 0 12px 12px;
}
.header h1 {
    font-size: 20px;
    margin: 0 0 8px;
}
.header .meta {
    font-size: 12px;
    opacity: 0.9;
}
h1 {
    font-size: 17px;
    color: #0d47a1;
    border-bottom: 2px solid #e3f2fd;
    padding-bottom: 8px;
    margin: 24px 0 12px;
}
h2 {
    font-size: 15px;
    color: #1565c0;
    margin: 18px 0 10px;
    padding-left: 10px;
    border-left: 3px solid #42a5f5;
}
h3 { font-size: 14px; color: #333; margin: 12px 0 6px; }
p { margin: 8px 0; }
ul, ol { padding-left: 20px; margin: 8px 0; }
li { margin: 4px 0; }
strong { color: #d32f2f; }
.highlight { background: #fff3cd; padding: 2px 6px; border-radius: 4px; }
.repo-card {
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    padding: 14px;
    margin: 12px 0;
}
.repo-card h3 {
    margin: 0 0 8px;
    color: #0969da;
    font-size: 15px;
}
.repo-card .meta {
    font-size: 12px;
    color: #57606a;
    margin-bottom: 10px;
}
.repo-card .description {
    color: #24292f;
    margin: 10px 0;
}
.repo-card .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
}
.repo-card .tag {
    background: #ddf4ff;
    color: #0969da;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 12px;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }
th {
    background: #f6f8fa;
    color: #24292f;
    padding: 8px 10px;
    text-align: left;
    border: 1px solid #e1e4e8;
    font-weight: 600;
}
td { padding: 8px 10px; border: 1px solid #e1e4e8; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fa; }
.stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 16px 0;
}
.stat-box {
    background: #f6f8fa;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}
.stat-box .number {
    font-size: 20px;
    font-weight: 600;
    color: #0d47a1;
}
.stat-box .label {
    font-size: 11px;
    color: #57606a;
    margin-top: 4px;
}
.footer {
    margin-top: 30px;
    padding-top: 16px;
    border-top: 1px solid #e1e4e8;
    font-size: 11px;
    color: #57606a;
    text-align: center;
}
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
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout, "pandoc"
        except subprocess.CalledProcessError as e:
            print(f"警告：pandoc 转换失败（{e}），降级为纯文本模式", file=sys.stderr)

    # Fallback：将原始 Markdown 转义后用 <pre> 展示
    content = md_path.read_text(encoding="utf-8")
    body = f'<pre style="white-space:pre-wrap;font-size:13px;">{html.escape(content)}</pre>'
    return body, "fallback"


def wrap_html(body: str, title: str = "GitHub Trending Report") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>{body}</body>
</html>
"""


def generate_html_header(date_str: str, total_repos: int) -> str:
    """生成报告头部"""
    return f"""
<div class="header">
    <h1>📊 GitHub Trending 日报</h1>
    <div class="meta">
        📅 {date_str} | 🌐 github.com/trending | 📈 {total_repos} 个热门项目
    </div>
</div>
"""


def generate_stats_section(language_stats: dict, total_stars: int) -> str:
    """生成统计区域"""
    top_langs = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)[:3]
    lang_text = " | ".join([f"{lang}: {count}" for lang, count in top_langs])

    return f"""
<h1>📈 今日概览</h1>
<div class="stats">
    <div class="stat-box">
        <div class="number">{total_stars:,}</div>
        <div class="label">今日新增 Star</div>
    </div>
    <div class="stat-box">
        <div class="number">{len(language_stats)}</div>
        <div class="label">编程语言</div>
    </div>
    <div class="stat-box">
        <div class="number">🔥</div>
        <div class="label">热门趋势</div>
    </div>
</div>
<p><strong>主要语言分布：</strong> {lang_text}</p>
"""


def generate_repo_card(repo_data: dict, rank: int) -> str:
    """生成单个仓库卡片"""
    repo = repo_data.get("repo", "unknown/unknown")
    what_it_does = repo_data.get("what_it_does", "暂无描述")
    tech_stack = repo_data.get("tech_stack", "")
    stars = repo_data.get("stars", "")
    stars_today = repo_data.get("stars_today", "")

    tags_html = ""
    if tech_stack:
        tags = [t.strip() for t in tech_stack.split(",")[:3]]
        tags_html = (
            '<div class="tags">'
            + "".join([f'<span class="tag">{t}</span>' for t in tags])
            + "</div>"
        )

    stars_html = ""
    if stars:
        stars_html = f"⭐ {stars}"
        if stars_today:
            stars_html += f' <span style="color: #d32f2f;">+{stars_today} today</span>'

    return f"""
<div class="repo-card">
    <h3>#{rank} {repo}</h3>
    <div class="meta">{stars_html}</div>
    <div class="description">{what_it_does}</div>
    {tags_html}
</div>
"""


def generate_watchlist_section(updates: list) -> str:
    """生成关注列表更新区域"""
    if not updates:
        return ""

    html = "<h1>📌 关注列表更新</h1>\n"
    for update in updates:
        repo = update.get("repo", "")
        changes = update.get("changes", "")
        html += f"""
<div class="repo-card">
    <h3>{repo}</h3>
    <div class="description">{changes}</div>
</div>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 GitHub Trending Markdown 报告转为手机友好 HTML"
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument(
        "output",
        nargs="?",
        help="输出 HTML 文件路径（默认与输入同目录，扩展名改为 .html）",
    )
    parser.add_argument("--title", default="GitHub Trending Report", help="报告标题")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：找不到输入文件：{input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")

    html_body, mode = markdown_to_html_body(input_path)
    if mode == "fallback":
        print("提示：pandoc 未安装，使用纯文本降级模式", file=sys.stderr)

    output_path.write_text(wrap_html(html_body, args.title), encoding="utf-8")

    print(f"完成（{mode}）：{output_path}")
    print(f"file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
