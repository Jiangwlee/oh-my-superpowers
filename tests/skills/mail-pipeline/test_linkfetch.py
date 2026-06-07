"""Unit tests for linkfetch URL extraction and provider matching (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "mail-pipeline" / "scripts"))

from linkfetch import extract_urls, match_provider  # noqa: E402


class TestLinkfetch(unittest.TestCase):
    def test_extract_urls_from_html_hrefs(self) -> None:
        message = {
            "html": '<a href="https://nnfp.jss.com.cn/abc">查看发票</a> <img src="https://cdn.example.com/x.png">',
            "text": "",
        }
        urls = extract_urls(message)
        self.assertIn("https://nnfp.jss.com.cn/abc", urls)
        self.assertIn("https://cdn.example.com/x.png", urls)

    def test_extract_urls_dedupes_and_falls_back_to_text(self) -> None:
        message = {"html": "", "text": "see https://saas.xforceplus.com/api/x?token=1 and https://saas.xforceplus.com/api/x?token=1"}
        self.assertEqual(["https://saas.xforceplus.com/api/x?token=1"], extract_urls(message))

    def test_match_provider_respects_allowlist(self) -> None:
        self.assertEqual("nuonuo", match_provider("https://nnfp.jss.com.cn/abc", ["nuonuo", "xforceplus"]))
        self.assertEqual("xforceplus", match_provider("https://saas.xforceplus.com/api/x", ["xforceplus"]))
        self.assertIsNone(match_provider("https://nnfp.jss.com.cn/abc", ["xforceplus"]))
        self.assertIsNone(match_provider("https://evil.example.com/nnfp.jss.com.cn", ["nuonuo"]))

    def test_match_provider_ignores_lookalike_hosts(self) -> None:
        self.assertIsNone(match_provider("https://nnfp.jss.com.cn.evil.com/abc", ["nuonuo"]))

    def test_extract_bare_url_inside_html_body(self) -> None:
        message = {"html": "你收到一张发票，点击「 https://invoice.keruyun.com/s/Bc0yM_ 」即可下载使用", "text": ""}
        self.assertEqual(["https://invoice.keruyun.com/s/Bc0yM_"], extract_urls(message))

    def test_match_provider_keruyun(self) -> None:
        self.assertEqual("keruyun", match_provider("https://invoice.keruyun.com/s/Bc0yM_", ["keruyun"]))
        self.assertIsNone(match_provider("https://invoice.keruyun.com/s/Bc0yM_", ["nuonuo", "xforceplus"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
