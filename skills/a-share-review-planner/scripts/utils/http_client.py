"""兼容入口：薄封装 scripts.core.http_client。"""

from scripts.core.http_client import http_json, http_text

__all__ = ["http_json", "http_text"]
