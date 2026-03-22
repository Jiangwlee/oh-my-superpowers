"""Tests for architecture doc alignment."""

from __future__ import annotations

import unittest
from pathlib import Path


class TestReadmeCommands(unittest.TestCase):
    """Doc alignment tests."""

    def test_skill_readme_references_platform_backend_paths(self) -> None:
        content = Path("skills/ashare-assistant/README.md").read_text(encoding="utf-8")
        self.assertIn("apps/ashare-platform/backend", content)

    def test_backend_readme_contains_local_and_docker_run(self) -> None:
        content = Path("apps/ashare-platform/backend/README.md").read_text(encoding="utf-8")
        self.assertIn("uvicorn app.main:app", content)
        self.assertIn("docker compose -f deployment/docker/ashare-platform/docker-compose.yml build", content)
        self.assertIn("docker compose -f deployment/docker/ashare-platform/docker-compose.yml up -d", content)


if __name__ == "__main__":
    unittest.main()
