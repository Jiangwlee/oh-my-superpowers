import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.cdp.client import CdpClient
from ashare_data.cdp.session import CdpPageSession


class CdpClientTest(unittest.TestCase):
    @patch("ashare_data.cdp.client.time.sleep")
    @patch("ashare_data.cdp.client.urllib.request.urlopen")
    def test_open_page_returns_session(self, mock_urlopen, _mock_sleep):
        response = MagicMock()
        response.read.return_value = b'{"id":"TAB123"}'
        context = MagicMock()
        context.__enter__.return_value = response
        context.__exit__.return_value = False
        mock_urlopen.return_value = context

        client = CdpClient(base_url="http://127.0.0.1:9222", script_path="/tmp/cdp.mjs", timeout=1)
        session = client.open_page("https://example.com")

        self.assertIsInstance(session, CdpPageSession)
        self.assertEqual(session.target_id, "TAB123")
        requested = mock_urlopen.call_args.args[0]
        self.assertEqual(requested.method, "PUT")


if __name__ == "__main__":
    unittest.main()
