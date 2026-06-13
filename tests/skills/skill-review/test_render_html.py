from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "skill-review" / "scripts" / "render_html.py"


FILLED_REPORT = """# skill-review: demo-skill

审查路径：`/tmp/demo-skill`
审查范围：`SKILL.md`, `references/rubric.md`
机械检查：完成
机械检查原始计数：1 CRITICAL · 2 WARNING · 0 SUGGESTION

---

## 审查结果

### A1. Frontmatter and Directory Spec — FINDING

- [✓] `SKILL.md` 存在，有有效的开闭 `---` 界定符 → consistency_check 无 frontmatter 错误
- [✗] `description` 非空，≤ 1024 字符 → 实际 1287 字符
  - **标签**：SPEC
  - **影响**：description 超长可能被截断，影响触发命中
  - **修复**：删除 description 中的冗余工作流摘要
  - **验证**：`omp skill-review check --skill-dir skills/demo-skill`

### B5. Script Interface Design — PASS

- [✓] `cli/<skill-name>/main.py` 存在且是唯一 CLI 入口 → cli/demo-skill/main.py exists
- [—] CLI 前置条件有说明 → 无额外 runtime 要求
"""


def test_render_html_to_output_file(tmp_path: Path) -> None:
    report = tmp_path / "review-demo-skill.md"
    output = tmp_path / "review-demo-skill.html"
    report.write_text(FILLED_REPORT, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    metadata = json.loads(result.stdout)
    assert metadata["html_path"] == str(output)
    html = output.read_text(encoding="utf-8")
    assert "skill-review: demo-skill" in html
    assert "Spec" in html
    assert "description 超长可能被截断" in html
    assert "Readiness score" in html
    assert "default html artifact" in html


def test_publish_writes_under_html_serve_data_dir(tmp_path: Path) -> None:
    report = tmp_path / "review-demo-skill.md"
    data_dir = tmp_path / "html-serve"
    report.write_text(FILLED_REPORT, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(report),
            "--publish",
            "--project",
            "my-project",
            "--data-dir",
            str(data_dir),
            "--base-url",
            "http://example.test:8888",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    metadata = json.loads(result.stdout)
    html_path = Path(metadata["html_path"])
    assert html_path.is_file()
    assert html_path.parent == data_dir / "my-project" / "skill-review"
    assert metadata["url"].startswith("http://example.test:8888/my-project/skill-review/")


def test_rejects_unvalidated_report(tmp_path: Path) -> None:
    report = tmp_path / "review-demo-skill.md"
    output = tmp_path / "review-demo-skill.html"
    report.write_text(
        """# skill-review: demo-skill

### A1. Frontmatter and Directory Spec — __STATE__

- [ ] `SKILL.md` 存在，有有效的开闭 `---` 界定符 → __STATE__ · __EVIDENCE__
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report), "--output", str(output)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "report failed validation" in result.stderr
    assert not output.exists()
