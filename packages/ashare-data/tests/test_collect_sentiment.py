"""Tests for collect_sentiment after deep-research removal.

Verify the module can still be imported and collect() signature
no longer accepts deep_research parameters.
"""

from __future__ import annotations

import inspect
import unittest


class CollectSentimentCleanupTest(unittest.TestCase):
    """验证 collect_sentiment 中深研代码已移除。"""

    def test_no_deep_research_import(self):
        import ashare_data.collect_sentiment as mod
        source = inspect.getsource(mod)
        self.assertNotIn("deep_research_batch", source)
        self.assertNotIn("_run_llm_brief", source)

    def test_collect_signature_no_deep_research_params(self):
        from ashare_data.collect_sentiment import collect
        sig = inspect.signature(collect)
        param_names = set(sig.parameters.keys())
        self.assertNotIn("run_deep_research", param_names)
        self.assertNotIn("deep_research_min_star", param_names)
        self.assertNotIn("deep_research_max_workers", param_names)


if __name__ == "__main__":
    unittest.main()
