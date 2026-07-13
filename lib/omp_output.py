"""omp 统一输出层 — 把 CLI 输出契约（docs/specs/02_framework/cli-development-guide.md）编码成单一边界。

契约（2026-04-07 圆桌决议）：
- 结构化数据走 stdout，JSON 单行（不 pretty），保管道可组合（`omp X | jq`）。
- 错误/诊断/进度走 stderr。
- 退出码：0 成功 / 1 业务失败 / 2 用法错误 / 4 权限·环境缺失。

Public API:
    EXIT_OK / EXIT_FAIL / EXIT_USAGE / EXIT_ENV  退出码常量
    emit(data)                                   数据 → stdout（JSON 单行）
    emit_error(msg, code, hint=None, exit_code)  错误 → stderr（结构化），并 raise typer.Exit
"""

import json
import sys

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_ENV = 4


def emit(data) -> None:
    """数据 → stdout，JSON 单行（管道友好）。"""
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def emit_error(msg: str, code: str, hint: str | None = None, *, exit_code: int = EXIT_FAIL):
    """结构化错误 → stderr，并以给定退出码退出。

    供 agent-facing 命令统一错误格式使用；人类向命令可继续用自有文案，只需对齐退出码。
    """
    import typer

    payload = {"error": msg, "code": code}
    if hint:
        payload["hint"] = hint
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
    raise typer.Exit(exit_code)
