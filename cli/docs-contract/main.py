#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich", "pyyaml"]
# ///
"""omp docs-contract — Build and lint a documentation skeleton with maintenance contracts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SKILL_DIR = OMP_HOME / "skills" / "docs-contract"
ASSETS_DIR = SKILL_DIR / "assets"

sys.path.insert(0, str(SKILL_DIR))

from scripts.config import load as load_config  # noqa: E402
from scripts.lint import lint_l1  # noqa: E402
from scripts.scaffold import (  # noqa: E402
    ScaffoldPlan,
    apply as apply_scaffold,
    plan as build_plan,
)
from scripts.schema import DocType  # noqa: E402

app = typer.Typer(
    name="docs-contract",
    help="Build a documentation skeleton with maintenance contracts.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _parse_doctype_csv(csv: str) -> list[DocType]:
    if not csv:
        return []
    out: list[DocType] = []
    for name in (s.strip() for s in csv.split(",")):
        if not name:
            continue
        try:
            out.append(DocType(name))
        except ValueError as exc:
            valid = ", ".join(d.value for d in DocType)
            raise typer.BadParameter(
                f"unknown doc-type {name!r}; valid: {valid}"
            ) from exc
    return out


@app.command("scaffold")
def cmd_scaffold(
    root: Path = typer.Option(Path.cwd(), "--root", "-r", help="Project root."),
    apply_changes: bool = typer.Option(
        False, "--apply", help="Write files. Default is dry-run."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing files (default: skip)."
    ),
    include: str = typer.Option(
        "", "--include", help="Comma-separated doc-types to force-include."
    ),
    exclude: str = typer.Option(
        "", "--exclude", help="Comma-separated doc-types to force-exclude."
    ),
) -> None:
    """Predict skeleton candidates and (with --apply) write them from templates."""
    inc = _parse_doctype_csv(include)
    exc = _parse_doctype_csv(exclude)
    plan_obj = build_plan(root, ASSETS_DIR, include=inc, exclude=exc)

    _print_plan(plan_obj)

    if not apply_changes:
        console.print("\n[dim]Dry-run. Re-run with --apply to write files.[/dim]")
        return

    written, skipped = apply_scaffold(plan_obj, force=force)
    console.print()
    if written:
        console.print(f"[green]Wrote {len(written)} file(s):[/green]")
        for p in written:
            console.print(f"  + {p.relative_to(plan_obj.project_root)}")
    if skipped:
        console.print(
            f"[yellow]Skipped {len(skipped)} existing (use --force to overwrite):[/yellow]"
        )
        for p in skipped:
            console.print(f"  - {p.relative_to(plan_obj.project_root)}")


def _print_plan(plan_obj: ScaffoldPlan) -> None:
    table = Table(title=f"Scaffold plan for {plan_obj.project_root}")
    table.add_column("doc-type")
    table.add_column("target")
    table.add_column("suggested")
    table.add_column("exists")
    table.add_column("note")
    for entry in plan_obj.entries:
        rel = entry.target.relative_to(plan_obj.project_root).as_posix()
        suggested_mark = "[green]yes[/green]" if entry.suggested else "[dim]no[/dim]"
        exists_mark = "[yellow]exists[/yellow]" if entry.exists else ""
        if entry.suggested and entry.exists:
            note = "skip (use --force)"
        elif entry.suggested:
            note = "will write"
        else:
            note = ""
        table.add_row(entry.doc_type.value, rel, suggested_mark, exists_mark, note)
    console.print(table)
    f = plan_obj.features
    console.print(
        f"\n[dim]Detected: frontend={f.has_frontend} openapi={f.has_openapi} "
        f"cli={f.has_cli} changelog={f.has_changelog} git_tags={f.git_tag_count} "
        f"src_dirs={f.src_top_level_dirs}[/dim]"
    )


@app.command("lint")
def cmd_lint(
    root: Path = typer.Option(Path.cwd(), "--root", "-r", help="Project root."),
    semantic: bool = typer.Option(
        False, "--semantic", help="Also run L3 semantic lint via LLM (PR4)."
    ),
) -> None:
    """Run L1 structural lint (L2 lands in PR3, L3 in PR4)."""
    cfg = load_config(root)
    for w in cfg.warnings:
        console.print(f"[yellow]config warning:[/yellow] {w}")

    findings = lint_l1(root, exempt_paths=cfg.exempt_paths)

    if semantic:
        console.print("[yellow]--semantic ignored: L3 lands in PR4.[/yellow]")

    if not findings:
        console.print("[green]docs-contract lint: clean.[/green]")
        return

    by_severity: dict[str, list] = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
    }
    for f in findings:
        by_severity[f.severity].append(f)

    color_map = {
        "CRITICAL": "red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "dim",
    }

    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        items = by_severity[severity]
        if not items:
            continue
        color = color_map[severity]
        console.print(f"\n[{color}]{severity}[/{color}] ({len(items)}):")
        for f in items:
            loc_part = ""
            if f.file:
                rel = f.file.relative_to(root).as_posix()
                loc_part = f" {rel}" + (f":{f.line}" if f.line else "")
            console.print(f"  [{f.rule}]{loc_part} — {f.message}")

    blocking = len(by_severity["CRITICAL"]) + len(by_severity["HIGH"])
    if blocking > 0:
        raise typer.Exit(code=1)


@app.command("inventory")
def cmd_inventory(
    root: Path = typer.Option(Path.cwd(), "--root", "-r", help="Project root."),
) -> None:
    """Inventory existing docs (full implementation lands in PR5)."""
    console.print(
        f"[yellow]inventory[/yellow] for {root}: full implementation lands in PR5."
    )


if __name__ == "__main__":
    app()
