from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "supervised-dev-dispatch"
SKILL = SKILL_ROOT / "SKILL.md"
METADATA = SKILL_ROOT / "agents" / "openai.yaml"
LEDGER_TEMPLATE = SKILL_ROOT / "references" / "ledger-templates.md"


class SupervisedDispatchPolicyTests(unittest.TestCase):
    def test_external_review_is_manual_only(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        metadata = METADATA.read_text(encoding="utf-8")

        self.assertIn("it is not automatic peer review", skill)
        self.assertIn("Otherwise no reviewer is selected or invoked.", skill)
        self.assertIn("`peer-review` is manual-only", skill)
        self.assertIn("External-model peer review is manual-only", metadata)

        for stale_phrase in (
            "peer-review planning by default",
            "Run `peer-review` as a planning council",
            "any code change that will be merged",
            "require local verification and peer-review evidence",
        ):
            self.assertNotIn(stale_phrase, skill)

    def test_hard_stops_and_registry_authority_are_preserved(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        ledger = LEDGER_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("merges or pushes to shared branches", skill)
        self.assertIn("command-center registry is the sole source", skill)
        self.assertIn("active registry DECISIONS.md only", ledger)
        self.assertIn("Remote branch deletion or history rewrite", ledger)

    def test_public_variant_is_generic(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (SKILL, METADATA, LEDGER_TEMPLATE)
        )

        self.assertNotIn("Wei", combined)
        self.assertNotIn("/Users/", combined)


if __name__ == "__main__":
    unittest.main()
