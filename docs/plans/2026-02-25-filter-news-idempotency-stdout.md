# filter_to_markdown 新闻过滤 + run_analysis 幂等 + stdout 重定向 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 减小新闻子代理输入体积（24h 过滤）、支持幂等跳过已完成任务、改用 stdout 重定向代替不可靠的 Write tool。

**Architecture:**
- `filter_to_markdown.py` 新增 `_filter_recent_24h()` 在生成 Markdown 前先过滤，减少输入 token。
- `run_analysis.py` 的 `_run_opencode()` 加 `overwrite` 参数：输出文件已存在且非空时直接返回 True。
- `_run_opencode()` 改为 stdout 重定向模式：prompt 指示 agent 直接输出 Markdown，python 代码将 stdout 写入文件。

**Tech Stack:** Python 3.10+，标准库（datetime、os、subprocess），unittest

---

## 背景说明

**为什么这不是"缓存"？**
幂等跳过（skip-if-exists）和 `cache.py` 的缓存不同：
- 缓存（cache.py）：对网络请求结果做 TTL 缓存，加速相同 key 的重复请求。
- 幂等跳过：如果 LLM 分析产物（报告文件）已存在，直接复用，不重新调用 LLM。这是流水线幂等性，防止重跑时浪费 token。

---

## Task 1: filter_to_markdown.py — 新闻 24h 过滤

**Files:**
- Modify: `skills/ashare-assistant/scripts/filter_to_markdown.py`
- Create: `skills/ashare-assistant/tests/test_filter_to_markdown.py`

### Step 1: 写失败测试

```python
# skills/ashare-assistant/tests/test_filter_to_markdown.py
import sys, os, unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.filter_to_markdown import _filter_recent_24h


class FilterRecent24hTest(unittest.TestCase):

    def _make_items(self, *offsets_hours: int) -> list[dict]:
        """生成距今 N 小时的新闻条目列表。"""
        now = datetime.now()
        return [
            {"title": f"news-{i}", "makeDate": (now - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")}
            for i, h in enumerate(offsets_hours)
        ]

    def test_keeps_items_within_24h(self):
        items = self._make_items(1, 12, 23)  # 全部在 24h 内
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 3)

    def test_drops_items_older_than_24h(self):
        items = self._make_items(1, 25, 48)  # 只有第1条在 24h 内
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "news-0")

    def test_fallback_to_first_item_when_all_filtered(self):
        """全部超过 24h 时，返回最新1条（而不是空列表）。"""
        items = self._make_items(25, 30, 48)
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "news-0")  # 第一条（最新）

    def test_malformed_date_kept(self):
        """makeDate 格式错误时，保留该条目（宽容策略）。"""
        items = [{"title": "bad", "makeDate": "not-a-date"}]
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        self.assertEqual(_filter_recent_24h([], hours=24), [])
```

### Step 2: 运行测试确认失败

```bash
python3 -m unittest skills.ashare-assistant.tests.test_filter_to_markdown -v
```

期望：`AttributeError: module has no attribute '_filter_recent_24h'`

### Step 3: 在 filter_to_markdown.py 添加实现

在 `_escape_md()` 函数之后（约第47行）、`_convert_news()` 之前，插入：

```python
def _filter_recent_24h(data: list, hours: int = 24) -> list:
    """过滤新闻列表，只保留最近 N 小时内的条目。

    使用 makeDate 字段（格式: 'YYYY-MM-DD HH:MM:SS'）做比对。
    解析失败的条目视为有效（宽容策略，防止数据格式变化导致全量丢弃）。
    全部过期时返回列表中的第一条（最新一条）作为兜底。

    Args:
        data: 新闻条目列表，每项含 makeDate 字段。
        hours: 时间窗口（小时），默认24。

    Returns:
        过滤后的列表，至少包含1条（若原列表非空）。
    """
    if not data:
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    result = []
    for item in data:
        raw_date = str(item.get("makeDate") or "").strip()
        if not raw_date:
            result.append(item)
            continue
        try:
            item_time = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            result.append(item)  # 格式异常，宽容保留
            continue
        if item_time >= cutoff:
            result.append(item)
    # 兜底：全部过滤掉时返回第一条（最新一条）
    return result if result else [data[0]]
```

同时在文件顶部 `from datetime import datetime` 改为：
```python
from datetime import datetime, timedelta
```

### Step 4: 把过滤应用到 `_convert_news()` 和 `convert_news_flash()`

`_convert_news()` 函数体开头（第75行 `for i, item in enumerate...` 之前）插入：

```python
data = _filter_recent_24h(data)
```

`convert_news_flash()` 函数体内（第144行 `for item in data:` 之前）插入：

```python
data = _filter_recent_24h(data)
```

### Step 5: 运行测试确认通过

```bash
python3 -m unittest skills.ashare-assistant.tests.test_filter_to_markdown -v
```

期望：5 tests, OK

### Step 6: 运行全量测试确认无回归

```bash
python3 -m unittest discover -s skills/ashare-assistant/tests -v 2>&1 | tail -20
```

### Step 7: 提交

```bash
git add skills/ashare-assistant/scripts/filter_to_markdown.py \
        skills/ashare-assistant/tests/test_filter_to_markdown.py
git commit -m "feat(filter_to_markdown): 新闻 24h 时间窗口过滤，减少 LLM 输入体积"
```

---

## Task 2: run_analysis.py — 幂等跳过（skip-if-exists）

**Files:**
- Modify: `skills/ashare-assistant/scripts/run_analysis.py:186-283`

### Step 1: 写失败测试

在 Task 1 测试文件中追加（或单独建 `test_run_analysis.py`，建议单独建）：

```python
# skills/ashare-assistant/tests/test_run_analysis.py
import sys, os, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.run_analysis import _run_opencode


class RunOpencodeIdempotencyTest(unittest.TestCase):

    def test_skip_if_output_exists_and_non_empty(self):
        """output_path 已存在且非空时，直接返回 True，不启动子进程。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            with open(output_path, "w") as f:
                f.write("# existing report\nsome content")
            # overwrite=False（默认）时应跳过
            result = _run_opencode(
                prompt="irrelevant",
                output_path=output_path,
                title="test",
                overwrite=False,
            )
            self.assertTrue(result)

    def test_no_skip_when_overwrite_true(self):
        """overwrite=True 时即使文件存在也会尝试调用（这里会 FileNotFoundError 因为没有 opencode）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            with open(output_path, "w") as f:
                f.write("# existing")
            result = _run_opencode(
                prompt="irrelevant",
                output_path=output_path,
                title="test",
                overwrite=True,
            )
            # opencode 不存在，返回 False
            self.assertFalse(result)
```

### Step 2: 运行测试确认失败

```bash
python3 -m unittest skills.ashare-assistant.tests.test_run_analysis -v
```

期望：`TypeError: _run_opencode() got an unexpected keyword argument 'overwrite'`

### Step 3: 修改 `_run_opencode()` 函数签名和逻辑

函数签名改为：
```python
def _run_opencode(
    prompt: str,
    output_path: str,
    title: str,
    attached_files: list[str] | None = None,
    model: str | None = None,
    timeout: int = 300,
    overwrite: bool = False,
) -> bool:
```

在函数体最开头（docstring 之后、`full_prompt = ...` 之前）插入：

```python
    # 幂等跳过：输出文件已存在且非空时直接复用
    if not overwrite and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        size_kb = os.path.getsize(output_path) / 1024
        logger.info("跳过（已存在）: %s (%.1f KB)", title, size_kb)
        return True
```

### Step 4: 运行测试确认通过

```bash
python3 -m unittest skills.ashare-assistant.tests.test_run_analysis -v
```

期望：2 tests, OK

### Step 5: 提交

```bash
git add skills/ashare-assistant/scripts/run_analysis.py \
        skills/ashare-assistant/tests/test_run_analysis.py
git commit -m "feat(run_analysis): 幂等跳过——输出文件已存在时不重复调用 LLM"
```

---

## Task 3: run_analysis.py — stdout 重定向替代 Write tool

**Files:**
- Modify: `skills/ashare-assistant/scripts/run_analysis.py:186-310`

### 背景

当前流程：prompt 要求 agent 用 Write tool 写文件 → Write tool 不可靠会失败 → 有 `_try_save_from_stdout()` 作为兜底。

新流程：prompt 要求 agent 直接输出 Markdown 到终端 → python 捕获 stdout → 直接写文件。stdout 比 Write tool 更可靠，因为 opencode 的 stdout 就是 agent 的文字输出流。

### Step 1: 在 test_run_analysis.py 追加测试

```python
    def test_stdout_written_to_output_path(self):
        """当 opencode 返回 Markdown stdout 时，内容应被写入 output_path。"""
        # 此测试 mock subprocess.run
        import unittest.mock as mock

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            fake_stdout = "# 新闻情绪分析\n\n## 结论\n内容"

            mock_result = mock.Mock()
            mock_result.returncode = 0
            mock_result.stdout = fake_stdout
            mock_result.stderr = ""

            with mock.patch("subprocess.run", return_value=mock_result):
                result = _run_opencode(
                    prompt="test",
                    output_path=output_path,
                    title="test-stdout",
                    overwrite=True,
                )

            self.assertTrue(result)
            with open(output_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("# 新闻情绪分析", content)
```

### Step 2: 运行测试确认失败

```bash
python3 -m unittest skills.ashare-assistant.tests.test_run_analysis.RunOpencodeIdempotencyTest.test_stdout_written_to_output_path -v
```

期望：FAIL（当前实现 stdout 只是 fallback，primary 路径是 Write tool 写文件）

### Step 3: 修改 `_run_opencode()` 的 prompt 和输出逻辑

**3a. 修改 full_prompt 组装（第208-213行）：**

原来：
```python
full_prompt = (
    f"{prompt}\n\n"
    f"---\n\n"
    f"请将分析结果写入文件: `{output_path}`\n"
    f"使用 Write 工具直接写入上述路径，不要输出到终端。"
)
```

改为：
```python
full_prompt = (
    f"{prompt}\n\n"
    f"---\n\n"
    f"请将完整的 Markdown 分析结果直接输出到终端（stdout）。\n"
    f"不要使用 Write 工具写文件，直接输出文本即可。\n"
    f"输出必须以 `#` 开头的一级标题开始，之后是完整的分析内容。"
)
```

**3b. 修改成功路径（第253-273行），用 stdout 直接写文件替代文件存在性检查：**

删除：
```python
        # 检查输出文件是否生成
        if os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            logger.info(
                "子代理完成: %s (%.1f秒, 输出 %.1f KB)",
                title,
                elapsed,
                size_kb,
            )
            return True
        else:
            logger.error("子代理完成但未生成输出文件: %s (%.1f秒)", title, elapsed)
            # 如果 stdout 有内容，可能是子代理没有使用 Write 工具
            if result.stdout:
                logger.info("子代理 stdout 长度: %d 字符", len(result.stdout))
                # 尝试从 stdout 提取并保存
                _try_save_from_stdout(result.stdout, output_path)
                if os.path.exists(output_path):
                    logger.info("从 stdout 提取内容并保存到: %s", output_path)
                    return True
            return False
```

改为：
```python
        # 从 stdout 提取 Markdown 并写入输出文件
        stdout = result.stdout or ""
        if not stdout.strip():
            logger.error("子代理完成但 stdout 为空: %s (%.1f秒)", title, elapsed)
            return False

        content = _extract_markdown_from_stdout(stdout)
        if not content:
            logger.error(
                "子代理 stdout 无 Markdown 内容（未找到 # 标题）: %s (%.1f秒)",
                title,
                elapsed,
            )
            logger.debug("stdout 前500字符: %s", stdout[:500])
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        size_kb = len(content) / 1024
        logger.info("子代理完成: %s (%.1f秒, 输出 %.1f KB)", title, elapsed, size_kb)
        return True
```

**3c. 将 `_try_save_from_stdout` 重命名为 `_extract_markdown_from_stdout` 并改为返回值函数：**

删除原来的 `_try_save_from_stdout`（第286-305行），替换为：

```python
def _extract_markdown_from_stdout(stdout: str) -> str:
    """从 stdout 提取 Markdown 内容（从第一个 # 标题开始）。

    Returns:
        提取的 Markdown 文本，未找到时返回空字符串。
    """
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            content = "\n".join(lines[i:])
            if len(content) > 100:
                return content
    return ""
```

### Step 4: 运行所有测试

```bash
python3 -m unittest skills.ashare-assistant.tests.test_run_analysis -v
```

期望：3 tests, OK

### Step 5: 全量测试

```bash
python3 -m unittest discover -s skills/ashare-assistant/tests -v 2>&1 | tail -20
```

### Step 6: 提交

```bash
git add skills/ashare-assistant/scripts/run_analysis.py \
        skills/ashare-assistant/tests/test_run_analysis.py
git commit -m "feat(run_analysis): stdout 重定向替代不可靠的 Write tool"
```

---

## Task 4: 部署到测试机

```bash
# 本机同步源码到部署目录
cp -r skills/ashare-assistant/ .claude/skills/ashare-assistant/
cp -r skills/ashare-assistant/ .agents/skills/ashare-assistant/

# 上传到测试机
scp -r skills/ashare-assistant/scripts/filter_to_markdown.py root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/ashare-assistant/scripts/
scp -r skills/ashare-assistant/scripts/run_analysis.py root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/ashare-assistant/scripts/
```

验证：
```bash
ssh root@tencent-vps "cd /root/.openclaw/workspace-smartrader/skills/ashare-assistant && python3 -m py_compile scripts/filter_to_markdown.py scripts/run_analysis.py && echo OK"
```

---

## 总结

| 任务 | 效果 |
|------|------|
| Task 1 24h 过滤 | news_headline: 20条→1条（240KB→~12KB），其他新闻同比大幅缩减 |
| Task 2 幂等跳过 | 重跑时已完成任务直接复用，不消耗 token |
| Task 3 stdout 重定向 | Write tool 失败不再导致任务失败 |
