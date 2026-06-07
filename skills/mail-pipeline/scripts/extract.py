"""AI multimodal field extraction for mail-pipeline."""

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import tempfile
from datetime import date
from pathlib import Path

INVOICE_REQUIRED_FIELDS = ["invoice_date", "invoice_number", "amount", "tax_rate", "purchase_content", "seller"]

INVOICE_PROMPT = (
    "这是一张中国电子发票。请从发票图像中提取以下字段，只输出严格 JSON，不要任何其他文字："
    '{"invoice_date": "YYYY-MM-DD", "invoice_number": "发票号码", "amount": 价税合计数字, '
    '"tax_rate": "税率，如 13%；票面为 * 等标记时原样保留", "purchase_content": "购买内容摘要", '
    '"seller": "销售方名称", "confidence": 0到1之间的置信度数字}'
)


def _llm_command(pdf_path: Path, model: str | None) -> list[str]:
    """Build the headless multimodal LLM command.

    `MAIL_PIPELINE_LLM_CMD` overrides the command for tests; the override is
    invoked with the PDF path appended and must print the field JSON.
    """
    override = os.environ.get("MAIL_PIPELINE_LLM_CMD")
    if override:
        return [*shlex.split(override), str(pdf_path)]
    cmd = ["pi", "-p", "--no-session", "--no-tools", "--mode", "text"]
    if model:
        cmd += ["--model", model]
    return [*cmd, f"@{pdf_path}", INVOICE_PROMPT]


def _parse_json(stdout: str) -> dict:
    """Extract the first JSON object from LLM output."""
    text = stdout.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in LLM output")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in LLM output: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM output JSON is not an object")
    return parsed


def extract_invoice(content_b64: str, model: str | None) -> dict:
    """Extract invoice fields from a PDF attachment via a multimodal LLM.

    Raises ValueError when the command fails, output is not valid JSON, or
    required fields are missing/malformed.
    """
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "invoice.pdf"
        pdf_path.write_bytes(base64.b64decode(content_b64))
        try:
            result = subprocess.run(
                _llm_command(pdf_path, model),
                capture_output=True,
                text=True,
                timeout=180,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("invoice extraction timed out") from exc
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise ValueError(f"invoice extraction command failed: {exc}") from exc

    fields = _parse_json(result.stdout)
    missing = [key for key in INVOICE_REQUIRED_FIELDS if not str(fields.get(key) or "").strip()]
    if missing:
        raise ValueError("missing invoice fields: " + ", ".join(missing))
    try:
        date.fromisoformat(str(fields["invoice_date"]))
        float(fields["amount"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"malformed invoice field: {exc}") from exc
    keys = INVOICE_REQUIRED_FIELDS + ["confidence"]
    return {key: fields[key] for key in keys if key in fields}
