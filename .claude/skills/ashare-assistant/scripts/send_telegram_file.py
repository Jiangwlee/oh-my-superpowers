#!/usr/bin/env python3
"""
send_telegram_file.py - 通过 Telegram Bot API 发送文件/图片

用法：
    python3 send_telegram_file.py <file_path> [--caption TEXT] [--chat-id ID] [--method photo|document]

自动从 ~/.openclaw/openclaw.json 读取 botToken、allowFrom（默认收件人）、proxy。

--method photo    （默认）用 sendPhoto 发送，图片直接显示在聊天中，无需点击，无缩略图变形问题。
                  每张图片宽+高必须 ≤ 10000px（分页后每页约 2250+6000=8250，满足要求）。
--method document 用 sendDocument 发送，保留原始文件，但在聊天中显示为文件附件（需点击查看）。
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
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


def send_file(
    file_path: Path,
    bot_token: str,
    chat_id: str,
    caption: str = "",
    proxy: str = "",
    method: str = "photo",
) -> dict:
    """
    发送文件到 Telegram（使用标准库 urllib，无 curl 依赖）。
    method="photo"    → sendPhoto（图片直接显示，无需点击，无缩略图压扁）
    method="document" → sendDocument（原始质量，但显示为文件附件）
    """
    api_method = "sendPhoto" if method == "photo" else "sendDocument"
    field_name = "photo" if method == "photo" else "document"
    url = f"https://api.telegram.org/bot{bot_token}/{api_method}"

    # 构建 multipart/form-data
    boundary = "----TelegramBotBoundary" + os.urandom(8).hex()

    def _field(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    def _file_field(name: str, filename: str, data: bytes, mime: str) -> bytes:
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        return header + data + b"\r\n"

    parts: list[bytes] = [_field("chat_id", chat_id)]
    if caption:
        parts.append(_field("caption", caption))
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts.append(_file_field(field_name, file_path.name, file_path.read_bytes(), mime))
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"https": proxy, "http": proxy})
        )
    else:
        opener = urllib.request.build_opener()

    try:
        with opener.open(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body_text}") from e


def main() -> None:
    parser = argparse.ArgumentParser(
        description="通过 Telegram Bot 发送图片或文件"
    )
    parser.add_argument("file", help="要发送的文件路径（PNG/PDF 等）")
    parser.add_argument("--caption", default="", help="文件说明（可选）")
    parser.add_argument("--chat-id", dest="chat_id", default="", help="目标 chat_id（默认读配置）")
    parser.add_argument("--method", choices=["photo", "document"], default="photo",
                        help="发送方式：photo=图片直接显示（默认），document=文件附件")
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

    print(f"发送图片（{args.method}）：{file_path.name}（{file_path.stat().st_size // 1024}KB）→ {chat_id}")

    resp = send_file(file_path, bot_token, chat_id, args.caption, proxy, method=args.method)

    if resp.get("ok"):
        print("发送成功")
    else:
        print(f"发送失败：{resp.get('description', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
