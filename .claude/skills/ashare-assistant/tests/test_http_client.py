import sys
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.core.http_client as http_client


class HttpClientTest(unittest.TestCase):
    def test_get_payload_rejected(self) -> None:
        with self.assertRaises(ValueError):
            http_client.http_text("https://example.com", method="GET", payload={"a": 1})

    @mock.patch("scripts.core.http_client._NO_PROXY_OPENER")
    def test_http_json_parses_dict(self, mock_opener: mock.Mock) -> None:
        resp = mock.Mock()
        resp.read.return_value = b'{"ok": true}'
        mock_opener.open.return_value.__enter__ = mock.Mock(return_value=resp)
        mock_opener.open.return_value.__exit__ = mock.Mock(return_value=False)

        result = http_client.http_json("https://example.com")

        self.assertEqual(result["ok"], True)

    @mock.patch("scripts.core.http_client.time.sleep")
    @mock.patch("scripts.core.http_client._NO_PROXY_OPENER")
    def test_http_text_retries_then_succeeds(
        self, mock_opener: mock.Mock, mock_sleep: mock.Mock
    ) -> None:
        resp = mock.Mock()
        resp.read.return_value = b"ok"
        ctx = mock.Mock(
            __enter__=mock.Mock(return_value=resp),
            __exit__=mock.Mock(return_value=False),
        )
        mock_opener.open.side_effect = [OSError("boom"), ctx]

        out = http_client.http_text("https://example.com", retries=2, sleep_sec=0)

        self.assertEqual(out, "ok")
        mock_sleep.assert_called_once()

    @mock.patch("scripts.core.http_client._NO_PROXY_OPENER")
    def test_http_bytes_returns_raw_bytes(self, mock_opener: mock.Mock) -> None:
        resp = mock.Mock()
        resp.read.return_value = b"\x1f\x8braw"
        mock_opener.open.return_value.__enter__ = mock.Mock(return_value=resp)
        mock_opener.open.return_value.__exit__ = mock.Mock(return_value=False)

        out = http_client.http_bytes("https://example.com/bin")

        self.assertEqual(out, b"\x1f\x8braw")


if __name__ == "__main__":
    unittest.main()
