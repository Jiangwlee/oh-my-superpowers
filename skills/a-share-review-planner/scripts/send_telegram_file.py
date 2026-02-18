#!/usr/bin/env python3
"""
send_telegram_file.py - 通过 Telegram Bot API sendDocument 发送文件（无压缩）

用法：
    python3 send_telegram_file.py <file_path> [--caption TEXT] [--chat-id ID]

自动从 ~/.openclaw/openclaw.json 读取 botToken、allowFrom（默认收件人）、proxy。
使用 sendDocument（而非 sendPhoto），Telegram 不会压缩图片，手机端可看到原始质量。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"


def load_openclaw_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def get_telegram_settings(cfg: dict) -> tuple[str, str, str]:
    """返回 (bot_token, chat_id, proxy_url)"""
    tg = cfg.get("channels", {}).get("telegram", {})

    bot_token = tg.get("botToken", "")
    if not bot_token:
        raise ValueError(f"未找到 botToken，请检查 {CONFIG_PATH}")

    allow_from = tg.get("allowFrom", [])
    chat_id = str(allow_from[0]) if allow_from else ""

    proxy = tg.get("proxy", "") or cfg.get("env", {}).get("vars", {}).get("https_proxy", "")

    return bot_token, chat_id, proxy


def send_document(
    file_path: Path,
    bot_token: str,
    chat_id: str,
    caption: str = "",
    proxy: str = "",
) -> dict:
    """用 curl 调 sendDocument API，不压缩文件"""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    cmd = ["curl", "-s", "--max-time", "60"]

    if proxy:
        cmd += ["--proxy", proxy]

    cmd += ["-F", f"chat_id={chat_id}"]
    cmd += ["-F", f"document=@{file_path.absolute()}"]
    if caption:
        cmd += ["-F", f"caption={caption}"]

    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise RuntimeError(f"curl 失败: {result.stderr.strip()}")

    resp = json.loads(result.stdout)
    return resp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="通过 Telegram Bot sendDocument 发送文件（无压缩）"
    )
    parser.add_argument("file", help="要发送的文件路径（PNG/PDF 等）")
    parser.add_argument("--caption", default="", help="文件说明（可选）")
    parser.add_argument("--chat-id", dest="chat_id", default="", help="目标 chat_id（默认读配置）")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误：文件不存在：{file_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_openclaw_config()
    bot_token, default_chat_id, proxy = get_telegram_settings(cfg)
    chat_id = args.chat_id or default_chat_id

    if not chat_id:
        print("错误：未指定 chat_id 且配置中无 allowFrom", file=sys.stderr)
        sys.exit(1)

    print(f"发送文件：{file_path.name}（{file_path.stat().st_size // 1024}KB）→ {chat_id}")

    resp = send_document(file_path, bot_token, chat_id, args.caption, proxy)

    if resp.get("ok"):
        print("发送成功")
    else:
        print(f"发送失败：{resp.get('description', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
