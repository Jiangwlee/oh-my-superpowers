import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.sentiment_preprocess import run_sentiment_preprocess


class SentimentPreprocessTest(unittest.TestCase):
    @patch("ashare_data.sentiment_preprocess.which", return_value=None)
    def test_skip_when_opencode_missing(self, _mock_which):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            (data_dir / "filtered").mkdir(parents=True, exist_ok=True)
            result = run_sentiment_preprocess(data_dir=data_dir)

        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["news"]["message"], "skipped_opencode_not_found")
        self.assertEqual(result["social"]["message"], "skipped_opencode_not_found")


if __name__ == "__main__":
    unittest.main()
