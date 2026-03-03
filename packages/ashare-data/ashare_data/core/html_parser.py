"""HTML 解析工具。

提供 HTMLParser 基类和通用工具函数。
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any


def class_contains(attrs: list[tuple[str, str | None]], cls: str) -> bool:
    """检查属性列表中是否包含指定 class。

    Args:
        attrs: HTML 标签属性列表。
        cls: 要查找的 class 名称。

    Returns:
        如果找到返回 True，否则返回 False。
    """
    for name, val in attrs:
        if name == "class" and val and cls in val:
            return True
    return False


def get_attr(attrs: list[tuple[str, str | None]], key: str) -> str:
    """从属性列表中获取指定键的值。

    Args:
        attrs: HTML 标签属性列表。
        key: 要查找的键名。

    Returns:
        找到返回对应值（空字符串 if None），未找到返回空字符串。
    """
    for name, val in attrs:
        if name == key:
            return val or ""
    return ""


class TextExtractor(HTMLParser):
    """提取 HTML 中的纯文本内容。

    递归处理嵌套标签，收集所有文本节点。
    """

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.text.append(data)

    def get_text(self) -> str:
        return "".join(self.text).strip()
