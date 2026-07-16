#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_peer_review.py"
SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"
CANON_PATH = Path.home() / ".claude" / "skills" / "shared" / "hard-stops.md"
SPEC = importlib.util.spec_from_file_location("run_peer_review", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class DefaultReviewerPolicyTest(unittest.TestCase):
    def test_default_constant_and_empty_selection_are_claude_only(self) -> None:
        self.assertEqual(RUNNER.DEFAULT_REVIEWERS, ("claude",))
        self.assertEqual(RUNNER.parse_reviewers(""), ["claude"])

    def test_default_alias_selects_only_claude(self) -> None:
        self.assertEqual(RUNNER.parse_reviewers("all"), ["claude"])

    def test_gemini_alias_does_not_implicitly_add_grok(self) -> None:
        self.assertEqual(RUNNER.parse_reviewers("all-with-gemini"), ["claude", "gemini"])

    def test_grok_remains_available_when_explicitly_requested(self) -> None:
        self.assertEqual(RUNNER.parse_reviewers("claude,grok"), ["claude", "grok"])

    @unittest.skipUnless(CANON_PATH.exists(), "shared machine canon is not installed")
    def test_skill_and_shared_canon_document_manual_only_codex_review(self) -> None:
        self.assertIn("Grok Build remains supported only as explicit opt-in", SKILL_PATH.read_text())
        self.assertIn("`all` is a legacy alias for the Claude default", SKILL_PATH.read_text())
        canon_text = CANON_PATH.read_text()
        self.assertIn("Cross-model review — manual-only, every lead", canon_text)
        self.assertIn("NO review pass fires automatically", canon_text)

    def test_unspecified_intensity_defaults_to_manual_planning_high(self) -> None:
        intensity = RUNNER.resolve_review_intensity(None)
        self.assertEqual(intensity.name, "planning")
        self.assertEqual(intensity.claude_effort, "high")

    def test_claude_route_matrix(self) -> None:
        cases = {
            ("auto", "planning"): ("judgment", "claude-fable-5", "high", True),
            ("routine", "planning"): ("routine", "opus", "high", False),
            ("judgment", "planning"): ("judgment", "claude-fable-5", "high", False),
            ("load-bearing", "planning"): ("load-bearing", "claude-fable-5", "xhigh", False),
            ("routine", "gate"): ("load-bearing", "claude-fable-5", "xhigh", False),
            ("judgment", "critical"): ("load-bearing", "claude-fable-5", "xhigh", False),
        }
        for (review_class, intensity_name), expected in cases.items():
            with self.subTest(review_class=review_class, intensity=intensity_name):
                with patch.dict("os.environ", {}, clear=True):
                    route = RUNNER.resolve_claude_route(
                        review_class,
                        RUNNER.resolve_review_intensity(intensity_name),
                    )
                self.assertEqual(
                    (route.effective_class, route.model, route.effort, route.defaulted),
                    expected,
                )

    def test_cli_opus_override_keeps_gate_floor(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            route = RUNNER.resolve_claude_route(
                "routine",
                RUNNER.resolve_review_intensity("gate"),
                cli_model="opus",
            )

        self.assertEqual(
            (route.model, route.model_source, route.effort),
            ("opus", "cli", "xhigh"),
        )

    def test_environment_opus_cannot_downgrade_load_bearing(self) -> None:
        with patch.dict(
            "os.environ",
            {"PEER_REVIEW_CLAUDE_MODEL": "opus"},
            clear=True,
        ):
            route = RUNNER.resolve_claude_route(
                "load-bearing",
                RUNNER.resolve_review_intensity("planning"),
            )

        self.assertEqual(
            (route.model, route.model_source),
            ("claude-fable-5", "route"),
        )
        self.assertIn("rejected environment model override", route.note)

    def test_environment_fable_can_strengthen_routine_route(self) -> None:
        with patch.dict(
            "os.environ",
            {"PEER_REVIEW_CLAUDE_MODEL": "claude-fable-5"},
            clear=True,
        ):
            route = RUNNER.resolve_claude_route(
                "routine",
                RUNNER.resolve_review_intensity("planning"),
            )

        self.assertEqual(
            (route.model, route.model_source, route.effort),
            ("claude-fable-5", "environment", "high"),
        )

    def test_default_fable_review_has_no_automatic_fallback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PEER_REVIEW_CLAUDE_MODEL": RUNNER.DEFAULT_CLAUDE_MODEL,
            },
            clear=True,
        ):
            participant = RUNNER.preflight_participant("claude")

        self.assertEqual(participant.requested_effort, "high")
        self.assertIsNone(participant.fallback_model)
        self.assertIsNone(participant.fallback_effort)
        self.assertIn("fallback disabled", participant.effort_status)

    def test_fable_alias_ignores_lower_effort_without_adding_fallback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PEER_REVIEW_CLAUDE_MODEL": "claude-fable-5-20260709",
                "PEER_REVIEW_CLAUDE_EFFORT": "medium",
            },
            clear=True,
        ):
            participant = RUNNER.preflight_participant(
                "claude", RUNNER.resolve_review_intensity("planning")
            )

        self.assertEqual(participant.requested_effort, "high")
        self.assertIsNone(participant.fallback_model)
        self.assertIsNone(participant.fallback_effort)
        self.assertIn("ignored effort override medium", participant.effort_status)

    def test_fable_alias_honors_explicit_xhigh_without_adding_fallback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PEER_REVIEW_CLAUDE_MODEL": "claude-fable-5-20260709",
                "PEER_REVIEW_CLAUDE_EFFORT": "xhigh",
            },
            clear=True,
        ):
            participant = RUNNER.preflight_participant(
                "claude", RUNNER.resolve_review_intensity("planning")
            )

        self.assertEqual(participant.requested_effort, "xhigh")
        self.assertIsNone(participant.fallback_effort)

    def test_explicit_opus_fallback_inherits_resolved_effort(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PEER_REVIEW_CLAUDE_MODEL": RUNNER.DEFAULT_CLAUDE_MODEL,
                "PEER_REVIEW_CLAUDE_FALLBACK_MODEL": "opus",
            },
            clear=True,
        ):
            participant = RUNNER.preflight_participant("claude")

        self.assertEqual(participant.fallback_model, "opus")
        self.assertEqual(participant.fallback_effort, "high")

    def test_invalid_effort_override_is_disclosed_and_uses_planning_floor(self) -> None:
        with patch.dict(
            "os.environ",
            {"PEER_REVIEW_CLAUDE_EFFORT": "banana"},
            clear=True,
        ):
            participant = RUNNER.preflight_participant(
                "claude", RUNNER.resolve_review_intensity("planning")
            )

        self.assertEqual(participant.requested_effort, "high")
        self.assertIsNone(participant.fallback_effort)
        self.assertIn("ignored effort override banana", participant.effort_status)

    def test_rate_limit_and_quota_errors_trigger_fallback(self) -> None:
        self.assertTrue(RUNNER.should_use_claude_fallback("HTTP 429 rate limit exceeded"))
        self.assertTrue(RUNNER.should_use_claude_fallback("quota exhausted for this model"))

    def test_default_fable_timeout_does_not_launch_fallback(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            participant = RUNNER.preflight_participant("claude")
        participant.status = "ready"
        participant.cli_path = "/fake/claude"
        primary_timeout = RUNNER.subprocess.TimeoutExpired(
            cmd=["/fake/claude"], timeout=10, output="", stderr="primary timed out"
        )

        with tempfile.TemporaryDirectory() as output_dir:
            with patch.object(RUNNER.subprocess, "run", side_effect=primary_timeout) as run_mock:
                result = RUNNER.run_participant(
                    participant, "review input", Path(output_dir), timeout_seconds=10
                )

        self.assertFalse(result.used_fallback)
        self.assertEqual(result.status, "timeout")
        self.assertEqual(run_mock.call_count, 1)

    def test_explicit_fallback_runs_after_timeout(self) -> None:
        with patch.dict(
            "os.environ", {"PEER_REVIEW_CLAUDE_FALLBACK_MODEL": "opus"}, clear=True
        ):
            participant = RUNNER.preflight_participant("claude")
        participant.status = "ready"
        participant.cli_path = "/fake/claude"
        primary_timeout = RUNNER.subprocess.TimeoutExpired(
            cmd=["/fake/claude"], timeout=5, output="", stderr="primary timed out"
        )
        fallback_success = RUNNER.subprocess.CompletedProcess(
            args=["/fake/claude"], returncode=0, stdout="review complete", stderr=""
        )

        with tempfile.TemporaryDirectory() as output_dir:
            with patch.object(
                RUNNER.subprocess, "run", side_effect=[primary_timeout, fallback_success]
            ) as run_mock:
                result = RUNNER.run_participant(
                    participant, "review input", Path(output_dir), timeout_seconds=10
                )

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.status, "ran")
        self.assertIn("used fallback opus/high", result.notes or "")
        self.assertEqual(run_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
