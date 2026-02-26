import json
import unittest
from unittest import mock
from pathlib import Path
import sys

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers import taoguba


class TaogubaFetchersTest(unittest.TestCase):
    def test_now_recommend_includes_content_from_detail_page(self):
        payload = {
            "status": True,
            "dto": {
                "list": [
                    {
                        "newTopicID": "123456",
                        "subject": "题材A爆发",
                        "subinfo": "摘要A",
                        "userName": "alice",
                        "dateTime": 1760000000000,
                        "totalViewNum": 1000,
                        "totalReplyNum": 88,
                        "stockList": [{"stockCode": "000001"}],
                    }
                ]
            },
        }
        raw = json.dumps(payload).encode("utf-8")

        with mock.patch("ashare_data.fetchers.taoguba.http_bytes", return_value=raw):
            with mock.patch(
                "ashare_data.fetchers.taoguba._fetch_detail", return_value="正文A"
            ) as detail_mock:
                rows = taoguba.fetch_taoguba_now_recommend(count=1)

        self.assertEqual(len(rows), 1)
        self.assertIn("content", rows[0])
        self.assertEqual(rows[0]["content"], "正文A")
        detail_mock.assert_called_once_with("https://www.tgb.cn/a/123456")

    def test_hot_discussion_extracts_subject_body_quotecontent(self):
        payload = {
            "status": True,
            "dto": {
                "list": [
                    {
                        "newTopicID": "7788",
                        "subject": "机器人分歧转一致",
                        "body": "<p>正文段落</p>",
                        "quoteContent": "<div>引用观点</div>",
                        "userName": "bob",
                        "dateTime": 1760001000000,
                        "totalViewNum": 7000,
                        "totalReplyNum": 320,
                        "stockList": [{"stockCode": "300024"}],
                    }
                ]
            },
        }

        with mock.patch(
            "ashare_data.fetchers.taoguba._fetch_json_get", return_value=payload
        ):
            rows = taoguba.fetch_taoguba_hot_discussion(page_no=1, count=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subject"], "机器人分歧转一致")
        self.assertEqual(rows[0]["body"], "正文段落")
        self.assertEqual(rows[0]["quotecontent"], "引用观点")
        self.assertEqual(rows[0]["url"], "https://www.tgb.cn/a/7788")


if __name__ == "__main__":
    unittest.main()
