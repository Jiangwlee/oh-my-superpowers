#!/usr/bin/env python3
"""
generate_daily_report.py - 生成 GitHub Trending 综合日报

用法：
    python3 scripts/generate_daily_report.py --memory-root .memory --date 2026-02-22

整合 Trending 数据和 Watchlist 更新，生成详细 Markdown 报告。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_trending_data(memory_root: str, date_str: str) -> list[dict[str, Any]]:
    """加载 Trending 数据"""
    trending_file = (
        Path(memory_root) / "github-tracker" / "trending" / "raw" / f"{date_str}.json"
    )
    if trending_file.exists():
        return json.loads(trending_file.read_text(encoding="utf-8"))
    return []


def load_watchlist_updates(memory_root: str) -> list[dict[str, Any]]:
    """加载 Watchlist 更新"""
    watchlist_dir = Path(memory_root) / "github-tracker" / "projects"
    updates = []

    if not watchlist_dir.exists():
        return updates

    today = datetime.now(timezone.utc).date().isoformat()

    for project_dir in watchlist_dir.iterdir():
        if project_dir.is_dir():
            update_file = project_dir / "updates" / f"{today}.md"
            if update_file.exists():
                # 解析更新文件获取关键信息
                content = update_file.read_text(encoding="utf-8")
                repo = project_dir.name.replace("__", "/")

                # 提取关键指标变化
                stars_change = "0"
                if "stars:" in content:
                    for line in content.split("\n"):
                        if "stars:" in line and "->" in line:
                            parts = line.split("->")
                            if len(parts) == 2:
                                try:
                                    old = int(parts[0].split()[-1])
                                    new = int(parts[1].split()[0])
                                    stars_change = (
                                        f"+{new - old}" if new > old else str(new - old)
                                    )
                                except:
                                    pass
                            break

                # 检查是否有新版本
                has_release = "Release changed:" in content

                updates.append(
                    {
                        "repo": repo,
                        "stars_change": stars_change,
                        "has_release": has_release,
                        "update_file": str(update_file),
                    }
                )

    return updates


def analyze_trends(trending_data: list[dict[str, Any]]) -> dict[str, Any]:
    """分析趋势数据"""
    if not trending_data:
        return {}

    # 语言统计
    lang_count = {}
    total_stars_today = 0

    for item in trending_data:
        lang = item.get("language", "Unknown")
        lang_count[lang] = lang_count.get(lang, 0) + 1

        stars_today = item.get("stars_today", "0")
        if isinstance(stars_today, str):
            stars_today = int(stars_today.replace(",", ""))
        total_stars_today += stars_today

    # Top 语言
    top_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_repos": len(trending_data),
        "total_stars_today": total_stars_today,
        "top_languages": top_langs,
        "language_count": len(lang_count),
    }


def generate_report(
    date_str: str,
    trending_data: list[dict[str, Any]],
    watchlist_updates: list[dict[str, Any]],
    trends: dict[str, Any],
) -> str:
    """生成 Markdown 报告"""

    lines = [
        f"# 📊 GitHub Trending 日报 - {date_str}",
        "",
        "## 📈 今日概览",
        "",
        f"- **热门项目数**: {trends.get('total_repos', 0)}",
        f"- **总新增 Star**: {trends.get('total_stars_today', 0):,}",
        f"- **编程语言种类**: {trends.get('language_count', 0)}",
        "",
        "### 语言分布 Top 5",
    ]

    for lang, count in trends.get("top_languages", []):
        lines.append(f"- {lang}: {count} 个项目")

    lines.extend(["", "## 🔥 热门项目详解", ""])

    # 生成每个项目的详细信息
    for i, item in enumerate(trending_data, 1):
        repo = item.get("repo", "unknown/unknown")
        what_it_does = item.get("what_it_does", "暂无描述")
        tech_stack = item.get("tech_stack", "")
        stars = item.get("stars", "")
        stars_today = item.get("stars_today", "")

        lines.append(f"### #{i} {repo}")
        lines.append("")
        lines.append(f"**功能描述**: {what_it_does}")

        if tech_stack:
            lines.append(f"**技术栈**: {tech_stack}")

        stars_line = f"**Star 数**: {stars}"
        if stars_today:
            stars_line += f" (今日 +{stars_today} ⬆️)"
        lines.append(stars_line)

        # 添加简单趋势分析
        if stars_today:
            try:
                st = int(str(stars_today).replace(",", ""))
                if st > 100:
                    lines.append("**🔥 热度**: 极高，今日增长超过100星")
                elif st > 50:
                    lines.append("**📈 热度**: 很高，今日增长超过50星")
                elif st > 20:
                    lines.append("**📊 热度**: 中等，稳定增长中")
                else:
                    lines.append("**📌 热度**: 平稳")
            except:
                pass

        lines.append("")

    # Watchlist 更新部分
    if watchlist_updates:
        lines.extend(["", "## 📌 我的关注列表更新", ""])

        for update in watchlist_updates:
            repo = update.get("repo", "")
            stars_change = update.get("stars_change", "0")
            has_release = update.get("has_release", False)

            lines.append(f"### {repo}")
            lines.append(f"- **Star 变化**: {stars_change}")
            if has_release:
                lines.append("- **🎉 新版本发布**: 有重要更新")
            lines.append("")
    else:
        lines.extend(["", "## 📌 我的关注列表", "", "今日无重要更新", ""])

    # 洞察总结
    lines.extend(["", "## 💡 今日洞察", ""])

    # 基于数据生成洞察
    if trends.get("top_languages"):
        top_lang = trends["top_languages"][0][0]
        lines.append(f"1. **{top_lang} 持续主导**: 今日热门项目中 {top_lang} 占比最高")

    # 检查是否有特别热门的项目
    hot_projects = []
    for item in trending_data:
        stars_today = item.get("stars_today", "0")
        try:
            if int(str(stars_today).replace(",", "")) > 100:
                hot_projects.append(item.get("repo", ""))
        except:
            pass

    if hot_projects:
        lines.append(
            f"2. **超级热门项目**: {', '.join(hot_projects[:3])} 今日增长超过100星"
        )

    lines.append(
        "3. **建议关注**: 建议查看技术栈与你相关的项目，加入 watchlist 持续跟踪"
    )

    lines.extend(
        [
            "",
            "---",
            f"",
            f"*📅 报告生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
            f"*🌐 数据来源: github.com/trending*",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 GitHub Trending 综合日报")
    parser.add_argument(
        "--memory-root", default=".memory", help="Memory root directory"
    )
    parser.add_argument("--date", help="Date string (YYYY-MM-DD), defaults to today")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).date().isoformat()

    # 加载数据
    trending_data = load_trending_data(args.memory_root, date_str)
    watchlist_updates = load_watchlist_updates(args.memory_root)

    # 分析趋势
    trends = analyze_trends(trending_data)

    # 生成报告
    report = generate_report(date_str, trending_data, watchlist_updates, trends)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = (
            Path(args.memory_root)
            / "github-tracker"
            / "briefs"
            / "daily"
            / f"{date_str}.md"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"✅ 报告已生成: {output_path}")
    print(f"📊 包含 {len(trending_data)} 个热门项目")
    print(f"📌 {len(watchlist_updates)} 个关注项目有更新")


if __name__ == "__main__":
    main()
