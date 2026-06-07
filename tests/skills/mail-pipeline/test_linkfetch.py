"""Unit tests for linkfetch URL extraction and provider matching (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "mail-pipeline" / "scripts"))

import linkfetch  # noqa: E402
from linkfetch import extract_urls, fetch_link_attachments, load_provider_registry, match_provider, unmatched_link_hosts  # noqa: E402


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

    def test_match_provider_jd(self) -> None:
        self.assertEqual("jd", match_provider("https://storage.jd.com/blink.invoice.jd.com/x.pdf?token=1", ["jd"]))
        self.assertEqual("jd", match_provider("http://oss.cn-north-1.jcloudcs.com/pop-einvoice/x.pdf?token=1", ["jd"]))
        self.assertEqual("jd", match_provider("https://eicore-invoice-26.s3.cn-north-1.jdcloud-oss.com/digital-invoice/x.pdf?token=1", ["jd"]))
        self.assertIsNone(match_provider("https://tr.jd.com/jump/transfer?jump_to=x", ["jd"]))

    def test_fetch_link_attachments_jd_pdf_only(self) -> None:
        original_get = linkfetch._get
        try:
            linkfetch._get = lambda url: b"%PDF-1.4\nmock" if url.endswith(".pdf?ok=1") else b"not-pdf"
            message = {
                "html": (
                    '<a href="https://storage.jd.com/blink.invoice.jd.com/invoice.pdf?ok=1">pdf</a>'
                    '<a href="https://storage.jd.com/blink.invoice.jd.com/invoice.xml?ok=1">xml</a>'
                    '<a href="https://tr.jd.com/jump/transfer?jump_to=x">jump</a>'
                ),
                "text": "",
            }
            attachments, provider_meta = fetch_link_attachments(message, ["jd"])
        finally:
            linkfetch._get = original_get
        self.assertEqual({}, provider_meta)
        self.assertEqual(1, len(attachments))
        self.assertEqual("invoice.pdf", attachments[0]["filename"])
        self.assertEqual("link", attachments[0]["origin"])


class TestProviderRegistry(unittest.TestCase):
    def test_builtin_registry_without_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            registry = load_provider_registry(Path(tmp))
        self.assertEqual({"nuonuo", "xforceplus", "keruyun", "jd"}, set(registry))
        self.assertEqual("nuonuo", registry["nuonuo"]["strategy"])

    def test_config_extends_and_overrides_builtins(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config"
            config.mkdir()
            (config / "providers.yaml").write_text(
                "providers:\n"
                "  - name: acme\n"
                "    strategy: direct_pdf\n"
                "    hosts:\n"
                "      - invoice.acme.example.com\n"
                "  - name: jd\n"
                "    strategy: direct_pdf\n"
                "    hosts:\n"
                "      - storage.jd.com\n"
                "      - new-bucket.jdcloud-oss.com\n",
                encoding="utf-8",
            )
            registry = load_provider_registry(Path(tmp))
        self.assertIn("acme", registry)
        self.assertEqual("acme", match_provider("https://invoice.acme.example.com/dl/1.pdf", ["acme"], registry))
        self.assertIn("new-bucket.jdcloud-oss.com", registry["jd"]["hosts"])

    def test_config_rejects_unknown_strategy(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config"
            config.mkdir()
            (config / "providers.yaml").write_text(
                "providers:\n  - name: bad\n    strategy: scrape_js\n    hosts:\n      - x.example.com\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_provider_registry(Path(tmp))

    def test_unmatched_link_hosts_reports_unknown_providers(self) -> None:
        message = {"html": '<a href="https://invoice.unknown-corp.example.com/dl/1.pdf">下载发票</a>', "text": ""}
        hosts = unmatched_link_hosts(message, ["nuonuo", "jd"])
        self.assertEqual(["invoice.unknown-corp.example.com"], hosts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
