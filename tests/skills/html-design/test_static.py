from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "html-serve-design"


class HtmlServeDesignStaticTest(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            "SKILL.md",
            "references/publishing-contract.md",
            "references/page-patterns.md",
            "references/prototype-loop.md",
            "references/visual-system.md",
            "references/quality-checklist.md",
            "assets/prototype-workbench.html",
            "assets/report-template.html",
            "assets/brief-template.html",
            "assets/review-template.html",
            "assets/index-template.html",
        ]

        for relpath in required:
            self.assertTrue((SKILL / relpath).is_file(), relpath)

    def test_frontmatter_name_and_description(self):
        text = (SKILL / "SKILL.md").read_text()

        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: html-serve-design\n", text)
        self.assertIn("description: >-\n", text)
        self.assertIn("routine execution of an existing skill template", text)

    def test_no_machine_specific_paths_or_addresses(self):
        text = "\n".join(path.read_text() for path in SKILL.rglob("*") if path.is_file())

        self.assertNotIn("/home/bruce", text)
        self.assertNotIn("~/Dockers", text)
        self.assertIsNone(re.search(r"\b(?:100|192)\.\d+\.\d+\.\d+\b", text))

    def test_workbench_has_plain_http_copy_fallback(self):
        text = (SKILL / "assets" / "prototype-workbench.html").read_text()

        self.assertIn("navigator.clipboard", text)
        self.assertIn('document.execCommand("copy")', text)
        self.assertIn("Copy export", text)

    def test_page_patterns_reference_all_starter_templates(self):
        text = (SKILL / "references" / "page-patterns.md").read_text()

        for asset in [
            "assets/report-template.html",
            "assets/brief-template.html",
            "assets/review-template.html",
            "assets/index-template.html",
            "assets/prototype-workbench.html",
        ]:
            self.assertIn(asset, text)

    def test_visual_system_defines_multiple_style_families(self):
        text = (SKILL / "references" / "visual-system.md").read_text()

        for family in [
            "editorial-report",
            "operational-brief",
            "digest-magazine",
            "review-console",
            "index-catalog",
            "prototype-lab",
        ]:
            self.assertIn(family, text)
