import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.cdp_debug import _build_parser, _dispatch


class CdpDebugCliTest(unittest.TestCase):
    @patch("ashare_data.cdp_debug.fetch_indexflash_via_cdp")
    def test_dispatch_ths_indexflash(self, mock_fetch_indexflash_via_cdp):
        mock_fetch_indexflash_via_cdp.return_value = {"zdfb_data": {"znum": 1}}
        parser = _build_parser()
        args = parser.parse_args(["ths-indexflash"])

        result = _dispatch(args)

        self.assertEqual(result["zdfb_data"]["znum"], 1)

    @patch("ashare_data.cdp_debug.CdpClient")
    def test_dispatch_fetch_json(self, mock_client_cls):
        mock_session = MagicMock()
        mock_session.fetch_json.return_value = {"ok": True}
        mock_client = MagicMock()
        mock_client.open_page.return_value = mock_session
        mock_client_cls.return_value = mock_client

        parser = _build_parser()
        args = parser.parse_args(
            [
                "fetch-json",
                "--page-url",
                "https://q.10jqka.com.cn/",
                "--url",
                "/api.php?t=indexflash",
                "--headers",
                json.dumps({"Accept": "*/*"}),
            ]
        )

        result = _dispatch(args)

        self.assertEqual(result, {"ok": True})
        mock_client.open_page.assert_called_once_with("https://q.10jqka.com.cn/")
        mock_session.fetch_json.assert_called_once_with("/api.php?t=indexflash", headers={"Accept": "*/*"})
        mock_session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
