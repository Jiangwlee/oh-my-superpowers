from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "html-design"
CLI = ROOT / "cli" / "html-design" / "main.py"


class HtmlDesignStaticTest(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            "SKILL.md",
            "references/publishing-contract.md",
            "references/page-patterns.md",
            "references/prototype-loop.md",
            "references/visual-system.md",
            "references/quality-checklist.md",
            "references/information-organization.md",
            "assets/prototype-workbench.html",
            "assets/report-template.html",
            "assets/brief-template.html",
            "assets/review-template.html",
            "assets/index-template.html",
            "assets/design-index.json",
            "scripts/design_index.py",
            "scripts/workspace.py",
        ]

        for relpath in required:
            self.assertTrue((SKILL / relpath).is_file(), relpath)
        self.assertTrue(CLI.is_file())

    def test_frontmatter_name_and_description(self):
        text = (SKILL / "SKILL.md").read_text()

        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: html-design\n", text)
        self.assertIn("description: >-\n", text)
        self.assertIn("static HTML page prototype", text)
        self.assertIn("omp html-design compile", text)
        self.assertIn("omp html-design search", text)
        self.assertIn("omp html-design init", text)

    def test_no_machine_specific_paths_or_addresses(self):
        text_suffixes = {".md", ".html", ".json", ".py"}
        text = "\n".join(
            path.read_text()
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix in text_suffixes
        )

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

    def test_information_organization_has_at_least_ten_models(self):
        text = (SKILL / "references" / "information-organization.md").read_text()

        models = re.findall(r"^\| [A-Z][^|]+ \|", text, flags=re.MULTILINE)
        self.assertGreaterEqual(len(models), 10)
        for model in [
            "Hierarchical tree",
            "Sequential flow",
            "Database/catalog",
            "Faceted/tagged",
            "Task-based",
        ]:
            self.assertIn(model, text)

    def test_cli_documents_required_commands(self):
        text = CLI.read_text()

        for command in ['@app.command("compile")', '@app.command("search")', '@app.command("init")']:
            self.assertIn(command, text)

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

    def test_publishing_contract_prefers_public_base_url(self):
        text = (SKILL / "references" / "publishing-contract.md").read_text()

        self.assertIn("HTML_SERVE_BASE_URL", text)
        self.assertIn("Tailscale", text)
        self.assertIn("Final responses should lead with the public URL", text)
        self.assertIn("localhost", text)
