import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers.sohu_zdt import fetch_sohu_zdt_history, parse_sohu_zdt_history_html


_HTML = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>日期</th>
          <th>涨停只数</th>
          <th>跌停只数</th>
          <th>停牌</th>
          <th>成交额(亿)</th>
          <th>沪市</th>
          <th>深市</th>
          <th>京市</th>
        </tr>
        <tr>
          <th>上涨只数</th>
          <th>平盘只数</th>
          <th>下跌只数</th>
          <th>上涨只数</th>
          <th>平盘只数</th>
          <th>下跌只数</th>
          <th>上涨只数</th>
          <th>平盘只数</th>
          <th>下跌只数</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>03/20</td>
          <td>40</td>
          <td>26</td>
          <td>11</td>
          <td>23030.89</td>
          <td>308</td>
          <td>21</td>
          <td>1978</td>
          <td>312</td>
          <td>21</td>
          <td>2553</td>
          <td>42</td>
          <td>3</td>
          <td>255</td>
        </tr>
        <tr>
          <td>01/02</td>
          <td>30</td>
          <td>10</td>
          <td>5</td>
          <td>12000.50</td>
          <td>100</td>
          <td>2</td>
          <td>900</td>
          <td>200</td>
          <td>3</td>
          <td>1800</td>
          <td>10</td>
          <td>1</td>
          <td>120</td>
        </tr>
        <tr>
          <td>12/31</td>
          <td>20</td>
          <td>8</td>
          <td>4</td>
          <td>11000.00</td>
          <td>90</td>
          <td>1</td>
          <td>910</td>
          <td>180</td>
          <td>2</td>
          <td>1820</td>
          <td>9</td>
          <td>1</td>
          <td>121</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class SohuZdtTest(unittest.TestCase):
    def test_parse_sohu_zdt_history_html(self):
        rows = parse_sohu_zdt_history_html(_HTML, anchor_date=date(2026, 3, 22))

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["trade_date"], "2026-03-20")
        self.assertEqual(rows[0]["limit_up_count"], 40)
        self.assertEqual(rows[0]["turnover_billion"], 23030.89)
        self.assertEqual(rows[0]["shanghai"]["advance_count"], 308)
        self.assertEqual(rows[0]["beijing"]["decline_count"], 255)
        self.assertEqual(rows[2]["trade_date"], "2025-12-31")

    @patch("ashare_data.fetchers.sohu_zdt.http_bytes")
    def test_fetch_sohu_zdt_history_decodes_gbk_bytes(self, mock_http_bytes):
        mock_http_bytes.return_value = _HTML.encode("gbk", errors="ignore")

        rows = fetch_sohu_zdt_history(anchor_date=date(2026, 3, 22))

        self.assertEqual(rows[0]["trade_date"], "2026-03-20")
        self.assertEqual(rows[1]["shenzhen"]["flat_count"], 3)
        self.assertEqual(mock_http_bytes.call_args.args[0], "https://q.stock.sohu.com/cn/zdt.shtml")


if __name__ == "__main__":
    unittest.main()
