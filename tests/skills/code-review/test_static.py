"""T1 static checks for the code-review skill convergence contract."""

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "code-review"
SKILL_MD = SKILL_DIR / "SKILL.md"
OUTPUT_FORMAT = SKILL_DIR / "references" / "output-format.md"
CORE_CHECKLIST = SKILL_DIR / "references" / "review-checklist-core.md"
EXTENDED_CHECKLIST = SKILL_DIR / "references" / "review-checklist-extended.md"
PROMPT_TEMPLATE = SKILL_DIR / "assets" / "review-prompt-template.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestConvergenceContract(unittest.TestCase):
    """Validate blocker-based review and fix-loop semantics."""

    def test_output_contract_separates_severity_from_disposition(self) -> None:
        content = _read(OUTPUT_FORMAT)
        for term in ["Disposition", "BLOCKING", "FOLLOW_UP", "ADVISORY"]:
            self.assertIn(term, content)
        self.assertIn("APPROVE_WITH_FOLLOWUPS", content)

    def test_blocking_p2_requires_complete_evidence(self) -> None:
        content = _read(OUTPUT_FORMAT)
        for field in ["Contract", "Trigger", "Impact", "Verification"]:
            self.assertIn(field, content)
        self.assertIn("P2", content)
        self.assertIn("BLOCKING", content)

    def test_fix_loop_is_driven_by_blockers_not_all_p0_to_p2_findings(self) -> None:
        content = _read(SKILL_MD)
        self.assertIn("finding ledger", content.lower())
        self.assertIn("include the ledger in `{context}`", content)
        self.assertIn("verified blockers", content.lower())
        self.assertIn("APPROVE_WITH_FOLLOWUPS", content)
        self.assertNotIn("P0-P2 issues", content)

    def test_convergence_keeps_full_coverage_validation_and_round_cap(self) -> None:
        content = _read(SKILL_MD)
        self.assertIn("every changed path is covered", content)
        self.assertIn("validation", content.lower())
        self.assertIn("7 completed review rounds", content)
        self.assertIn("two consecutive", content.lower())

    def test_reviewer_prompt_rejects_subjective_blockers(self) -> None:
        content = _read(PROMPT_TEMPLATE)
        self.assertIn("Disposition", content)
        self.assertIn("more rigorous", content)
        self.assertIn("BLOCKING", content)

    def test_checklists_treat_maintainability_as_investigation_signal(self) -> None:
        core = _read(CORE_CHECKLIST)
        extended = _read(EXTENDED_CHECKLIST)
        self.assertIn("investigation signals", core)
        self.assertIn("non-blocking", extended.lower())


if __name__ == "__main__":
    unittest.main()
