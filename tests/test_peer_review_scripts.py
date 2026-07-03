from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_SCRIPT = REPO_ROOT / "peer-review" / "scripts" / "build_review_context.py"
RUNNER_SCRIPT = REPO_ROOT / "peer-review" / "scripts" / "run_peer_review.py"
REFRESH_SCRIPT = REPO_ROOT / "peer-review" / "scripts" / "refresh_peer_review_clis.py"
CHATGPT_PRO_SKILL = REPO_ROOT / "chatgpt-pro-peer-review" / "SKILL.md"
CHATGPT_PRO_METADATA = REPO_ROOT / "chatgpt-pro-peer-review" / "agents" / "openai.yaml"
PEER_REVIEW_SKILL = REPO_ROOT / "peer-review" / "SKILL.md"
PEER_REVIEW_METADATA = REPO_ROOT / "peer-review" / "agents" / "openai.yaml"
README = REPO_ROOT / "README.md"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ContextBuilderTests(unittest.TestCase):
    def run_context(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(CONTEXT_SCRIPT), "--root", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def init_repo(self, root: Path, files: dict[str, str]) -> None:
        subprocess.run(["git", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def test_total_limit_omission_is_visible_in_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root, {"a.txt": "a" * 50, "b.txt": "b" * 50})

            result = self.run_context(root, "--max-total-bytes", "20", "a.txt", "b.txt")

            self.assertEqual(result.returncode, 0)
            self.assertIn("CONTEXT OMITTED", result.stdout)

    def test_symlink_to_outside_root_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            outside = Path(tmp) / "outside-secret.txt"
            root.mkdir()
            outside.write_text("SECRET_TOKEN=abc123", encoding="utf-8")
            (root / "safe-link.md").symlink_to(outside)
            subprocess.run(["git", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "safe-link.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            result = self.run_context(root, "safe-link.md")

            self.assertEqual(result.returncode, 0)
            self.assertNotIn("SECRET_TOKEN", result.stdout)
            self.assertIn("skipped", result.stderr)

    def test_secret_like_content_blocks_context_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root, {"config.yaml": "api_key: sk-proj-" + "a" * 48})

            result = self.run_context(root, "config.yaml")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("possible secret", result.stderr)

    def test_non_git_root_fails_closed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.md").write_text("hello", encoding="utf-8")

            result = self.run_context(root, "notes.md")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("git ls-files unavailable", result.stderr)


class RunnerTests(unittest.TestCase):
    def test_planning_intensity_lowers_claude_and_codex_to_high(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        intensity = runner.resolve_review_intensity("planning")
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(runner.shutil, "which", return_value="/bin/reviewer"),
            mock.patch.object(runner, "get_version", return_value="test"),
            mock.patch.object(runner, "codex_model_supports", return_value=True),
        ):
            claude = runner.preflight_participant("claude", intensity)
            codex = runner.preflight_participant("codex", intensity)

        self.assertEqual(claude.requested_effort, "high")
        self.assertEqual(codex.requested_effort, "high")
        self.assertIn("planning", claude.effort_status)
        self.assertIn("planning", codex.effort_status)

    def test_gate_intensity_keeps_claude_and_codex_xhigh(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        intensity = runner.resolve_review_intensity("gate")
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(runner.shutil, "which", return_value="/bin/reviewer"),
            mock.patch.object(runner, "get_version", return_value="test"),
            mock.patch.object(runner, "codex_model_supports", return_value=True),
        ):
            claude = runner.preflight_participant("claude", intensity)
            codex = runner.preflight_participant("codex", intensity)

        self.assertEqual(claude.requested_effort, "xhigh")
        self.assertEqual(codex.requested_effort, "xhigh")
        self.assertIn("gate", claude.effort_status)
        self.assertIn("gate", codex.effort_status)

    def test_claude_defaults_use_opus_48_xhigh_effort(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(runner.shutil, "which", return_value="/bin/claude"),
            mock.patch.object(runner, "get_version", return_value="test"),
        ):
            participant = runner.preflight_participant("claude")

        self.assertEqual(participant.requested_model, "opus")
        self.assertEqual(participant.requested_effort, "xhigh")
        self.assertIn("xhigh", participant.effort_status)

    def test_grok_defaults_use_composer_25_fast_model(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(runner.shutil, "which", return_value="/bin/grok"),
            mock.patch.object(runner, "get_version", return_value="test"),
            mock.patch.object(runner, "grok_model_status", return_value="ready"),
        ):
            participant = runner.preflight_participant("grok")

        self.assertEqual(participant.requested_model, "grok-composer-2.5-fast")
        self.assertEqual(participant.requested_effort, "max; reasoning_effort=high")

    def test_refresh_defaults_use_composer_25_fast_model(self) -> None:
        refresh = load_module(REFRESH_SCRIPT, "refresh_peer_review_clis")

        self.assertEqual(refresh.DEFAULTS["grok"]["model"], "grok-composer-2.5-fast")

    def test_claude_command_has_no_default_budget_cap(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant(
            key="claude",
            label="Claude",
            cli="claude",
            cli_path="/bin/claude",
            cli_version="test",
            requested_model="opus",
            requested_effort="xhigh",
            effort_status="test",
            status="ready",
        )
        with mock.patch.dict("os.environ", {}, clear=True):
            cmd, stdin_text = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertNotIn("--max-budget-usd", cmd)
        self.assertEqual(stdin_text, "prompt")

    def test_claude_command_uses_explicit_budget_override(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant(
            key="claude",
            label="Claude",
            cli="claude",
            cli_path="/bin/claude",
            cli_version="test",
            requested_model="opus",
            requested_effort="xhigh",
            effort_status="test",
            status="ready",
        )
        with mock.patch.dict("os.environ", {"PEER_REVIEW_CLAUDE_MAX_BUDGET_USD": "12"}, clear=True):
            cmd, _ = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertIn("--max-budget-usd", cmd)
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "12")

    def test_gemini_command_skips_trust_for_headless_run(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant(
            key="gemini",
            label="Gemini",
            cli="gemini",
            cli_path="/bin/gemini",
            cli_version="test",
            requested_model="gemini-test",
            requested_effort="not-cli-exposed",
            effort_status="test",
            status="ready",
        )

        cmd, stdin_text = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertIn("--skip-trust", cmd)
        self.assertEqual(stdin_text, "prompt")

    def test_gemini_cli_default_omits_unverified_model_flag(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant(
            key="gemini",
            label="Gemini",
            cli="gemini",
            cli_path="/bin/gemini",
            cli_version="test",
            requested_model="cli-default",
            requested_effort="not-cli-exposed",
            effort_status="test",
            status="ready",
        )

        cmd, _ = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertNotIn("--model", cmd)

    def test_default_reviewer_roster_excludes_gemini_but_keeps_opt_in_alias(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")

        self.assertEqual(runner.parse_reviewers("all"), ["claude", "codex", "grok"])
        self.assertEqual(runner.parse_reviewers("all-with-gemini"), ["claude", "codex", "gemini", "grok"])

    def test_review_scope_auto_fails_closed_to_strict(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")

        policy = runner.resolve_review_policy("auto")

        self.assertEqual(policy.requested_scope, "auto")
        self.assertEqual(policy.effective_scope, "strict")
        self.assertFalse(policy.web_search_requested)
        self.assertIn("defaults to strict", policy.note)

    def test_review_scope_manifest_discloses_policy(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")

        policy = runner.resolve_review_policy("web-research")
        manifest = runner.review_policy_manifest(policy)

        self.assertEqual(manifest["requested_scope"], "web-research")
        self.assertEqual(manifest["effective_scope"], "web-research")
        self.assertTrue(manifest["web_search_requested"])
        self.assertEqual(manifest["external_research"], "allowed_if_supported")

    def test_apply_review_policy_records_per_participant_web_support(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participants = [
            runner.Participant("claude", "Claude", "claude", "/bin/claude", "test", "m", "e", "s", "ready"),
            runner.Participant("codex", "Codex", "codex", "/bin/codex", "test", "m", "e", "s", "ready"),
            runner.Participant("grok", "Grok Build", "grok", "/bin/grok", "test", "m", "e", "s", "ready"),
        ]

        with mock.patch.dict("os.environ", {}, clear=True):
            runner.apply_review_policy(participants, runner.resolve_review_policy("web-research"))

        by_key = {item.key: item for item in participants}
        self.assertEqual(by_key["grok"].review_scope_effective, "web-research")
        self.assertTrue(by_key["grok"].web_search_enabled)
        self.assertFalse(by_key["codex"].web_search_enabled)
        self.assertFalse(by_key["claude"].tools_enabled)
        self.assertIn("no verified", by_key["codex"].notes)

    def test_context_only_tool_policy_ignores_claude_tool_env(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant("claude", "Claude", "claude", "/bin/claude", "test", "opus", "xhigh", "s", "ready")

        with mock.patch.dict("os.environ", {"PEER_REVIEW_CLAUDE_TOOLS": "WebFetch"}, clear=True):
            policy = runner.resolve_review_policy("strict")
            tool_policy = runner.resolve_tool_policy(policy)
            runner.apply_review_policy([participant], policy, tool_policy)
            cmd, _ = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertEqual(tool_policy.name, "context-only")
        self.assertFalse(tool_policy.web_research_allowed)
        self.assertFalse(tool_policy.write_action_tools_allowed)
        self.assertFalse(participant.tools_enabled)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")

    def test_web_allowed_tool_policy_enables_only_verified_paths(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participants = [
            runner.Participant("claude", "Claude", "claude", "/bin/claude", "test", "opus", "xhigh", "s", "ready"),
            runner.Participant("codex", "Codex", "codex", "/bin/codex", "test", "gpt-5.5", "xhigh", "s", "ready"),
            runner.Participant("grok", "Grok Build", "grok", "/bin/grok", "test", "grok-build", "max; reasoning_effort=high", "s", "ready"),
        ]

        with mock.patch.dict("os.environ", {"PEER_REVIEW_CLAUDE_TOOLS": "WebFetch"}, clear=True):
            policy = runner.resolve_review_policy("web-research")
            tool_policy = runner.resolve_tool_policy(policy)
            runner.apply_review_policy(participants, policy, tool_policy)
            claude_cmd, _ = runner.command_for(participants[0], "prompt", Path("/tmp"))

        by_key = {item.key: item for item in participants}
        self.assertEqual(tool_policy.name, "web-allowed")
        self.assertTrue(tool_policy.web_research_allowed)
        self.assertFalse(tool_policy.local_repo_browsing_allowed)
        self.assertFalse(tool_policy.write_action_tools_allowed)
        self.assertTrue(by_key["claude"].tools_enabled)
        self.assertEqual(claude_cmd[claude_cmd.index("--tools") + 1], "WebFetch")
        self.assertFalse(by_key["codex"].web_search_enabled)
        self.assertTrue(by_key["grok"].web_search_enabled)

    def test_tool_policy_manifest_discloses_fail_closed_rules(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")

        manifest = runner.tool_policy_manifest(runner.resolve_tool_policy(runner.resolve_review_policy("strict")))

        self.assertEqual(manifest["name"], "context-only")
        self.assertFalse(manifest["web_research_allowed"])
        self.assertFalse(manifest["local_repo_browsing_allowed"])
        self.assertFalse(manifest["write_action_tools_allowed"])

    def test_grok_command_allows_more_than_one_turn(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with tempfile.TemporaryDirectory() as tmp:
            participant = runner.Participant(
                key="grok",
                label="Grok Build",
                cli="grok",
                cli_path="/bin/grok",
                cli_version="test",
                requested_model="grok-build",
                requested_effort="max; reasoning_effort=high",
                effort_status="test",
                status="ready",
            )

            cmd, _ = runner.command_for(participant, "prompt", Path(tmp))

        self.assertIn("--max-turns", cmd)
        turns = int(cmd[cmd.index("--max-turns") + 1])
        self.assertGreaterEqual(turns, 32)

    def test_grok_command_disables_web_search_by_default(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with tempfile.TemporaryDirectory() as tmp:
            participant = runner.Participant(
                key="grok",
                label="Grok Build",
                cli="grok",
                cli_path="/bin/grok",
                cli_version="test",
                requested_model="grok-build",
                requested_effort="max; reasoning_effort=high",
                effort_status="test",
                status="ready",
            )

            cmd, _ = runner.command_for(participant, "prompt", Path(tmp))

        self.assertIn("--disable-web-search", cmd)

    def test_grok_web_research_scope_omits_disable_web_search_and_raises_default_turns(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with tempfile.TemporaryDirectory() as tmp:
            participant = runner.Participant(
                key="grok",
                label="Grok Build",
                cli="grok",
                cli_path="/bin/grok",
                cli_version="test",
                requested_model="grok-build",
                requested_effort="max; reasoning_effort=high",
                effort_status="test",
                status="ready",
                review_scope_effective="web-research",
                web_search_enabled=True,
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                cmd, _ = runner.command_for(participant, "prompt", Path(tmp))

        self.assertNotIn("--disable-web-search", cmd)
        self.assertGreater(int(cmd[cmd.index("--max-turns") + 1]), 32)

    def test_grok_command_honors_explicit_turn_budget_override(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with tempfile.TemporaryDirectory() as tmp:
            participant = runner.Participant(
                key="grok",
                label="Grok Build",
                cli="grok",
                cli_path="/bin/grok",
                cli_version="test",
                requested_model="grok-build",
                requested_effort="max; reasoning_effort=high",
                effort_status="test",
                status="ready",
            )
            with mock.patch.dict("os.environ", {"PEER_REVIEW_GROK_MAX_TURNS": "8"}, clear=True):
                cmd, _ = runner.command_for(participant, "prompt", Path(tmp))

        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "8")

    def test_grok_command_disables_plan_mode_for_headless_review(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        with tempfile.TemporaryDirectory() as tmp:
            participant = runner.Participant(
                key="grok",
                label="Grok Build",
                cli="grok",
                cli_path="/bin/grok",
                cli_version="test",
                requested_model="grok-build",
                requested_effort="max; reasoning_effort=high",
                effort_status="test",
                status="ready",
            )

            cmd, _ = runner.command_for(participant, "prompt", Path(tmp))

        self.assertIn("--no-plan", cmd)
        self.assertNotIn("--permission-mode", cmd)

    def test_web_research_does_not_relax_codex_read_only_sandbox(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participant = runner.Participant(
            key="codex",
            label="Codex",
            cli="codex",
            cli_path="/bin/codex",
            cli_version="test",
            requested_model="gpt-5.5",
            requested_effort="xhigh",
            effort_status="test",
            status="ready",
            review_scope_effective="web-research",
            web_search_enabled=False,
        )

        cmd, stdin_text = runner.command_for(participant, "prompt", Path("/tmp"))

        self.assertEqual(stdin_text, "prompt")
        self.assertIn("--sandbox", cmd)
        self.assertEqual(cmd[cmd.index("--sandbox") + 1], "read-only")
        self.assertNotIn("workspace-write", cmd)
        self.assertNotIn("danger-full-access", cmd)

    def test_build_prompt_strict_requires_supplied_context_only_and_evidence_basis(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        args = runner.argparse.Namespace(
            focus=[],
            prompt_file=None,
            project=None,
            milestone="current milestone",
            mode="Diff Critique",
            review_scope="strict",
        )

        prompt = runner.build_prompt(args, Path("/tmp/repo"), runner.resolve_review_policy("strict"))

        self.assertIn("Use only the supplied context", prompt)
        self.assertIn("Do not use web search", prompt)
        self.assertIn("Evidence basis", prompt)

    def test_build_prompt_web_research_allows_external_sources_with_citations(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        args = runner.argparse.Namespace(
            focus=["current vendor/API facts"],
            prompt_file=None,
            project=None,
            milestone="current milestone",
            mode="Strategy Review",
            review_scope="web-research",
        )

        prompt = runner.build_prompt(args, Path("/tmp/repo"), runner.resolve_review_policy("web-research"))

        self.assertIn("external web/source research", prompt)
        self.assertIn("Cite every external source", prompt)
        self.assertIn("external-source-grounded", prompt)

    def test_short_note_prefers_terminal_error_over_startup_warnings(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        stderr = "\n".join(
            [
                "\x1b[2m2026-06-23T23:25:40Z\x1b[0m \x1b[33m WARN\x1b[0m plugin name collision resolved",
                "\x1b[2m2026-06-23T23:26:14Z\x1b[0m \x1b[33m WARN\x1b[0m session registry update failed",
                "Max turns reached",
                "Error: max turns reached",
            ]
        )

        self.assertEqual(runner.short_note(stderr), "Error: max turns reached")

    def test_run_exit_code_requires_all_reviewers_unless_partial_allowed(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        results = [
            runner.Participant("claude", "Claude", "claude", "/bin/claude", "test", "m", "e", "s", "ran"),
            runner.Participant("gemini", "Gemini", "gemini", "/bin/gemini", "test", "m", "e", "s", "error"),
        ]

        self.assertEqual(runner.run_exit_code(results, allow_partial=False), 1)
        self.assertEqual(runner.run_exit_code(results, allow_partial=True), 0)

    def test_ready_reviewers_run_concurrently_when_jobs_allows(self) -> None:
        runner = load_module(RUNNER_SCRIPT, "run_peer_review")
        participants = [
            runner.Participant("claude", "Claude", "claude", "/bin/claude", "test", "m", "e", "s", "ready"),
            runner.Participant("gemini", "Gemini", "gemini", "/bin/gemini", "test", "m", "e", "s", "ready"),
        ]
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_runner(participant, review_input, output_dir, timeout_seconds):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.1)
            with lock:
                active -= 1
            participant.status = "ran"
            return participant

        results = runner.run_participants(participants, "prompt", Path("/tmp"), timeout_seconds=5, jobs=2, runner=fake_runner)

        self.assertEqual([item.key for item in results], ["claude", "gemini"])
        self.assertTrue(all(item.status == "ran" for item in results))
        self.assertEqual(max_active, 2)


class SkillDocumentationTests(unittest.TestCase):
    def test_chatgpt_pro_skill_is_discoverable_and_guarded(self) -> None:
        text = CHATGPT_PRO_SKILL.read_text(encoding="utf-8")

        self.assertIn("name: chatgpt-pro-peer-review", text)
        self.assertIn("Use when", text)
        self.assertIn("GPT-5.5 Pro", text)
        self.assertIn("Extended Pro", text)
        self.assertIn("Chrome", text)
        self.assertIn("Do not submit", text)
        self.assertIn("context helper", text)
        self.assertIn("manual browser", text)
        self.assertIn("45 minutes", text)
        self.assertIn("CHATGPT_PRO_BROWSER_TIMEOUT_SECONDS", text)
        self.assertIn("poll", text)
        self.assertIn("handoff", text)

    def test_chatgpt_pro_skill_has_ui_metadata(self) -> None:
        text = CHATGPT_PRO_METADATA.read_text(encoding="utf-8")

        self.assertIn("display_name: \"ChatGPT Pro Peer Review\"", text)
        self.assertIn("$chatgpt-pro-peer-review", text)

    def test_peer_review_docs_use_composer_25_fast_default(self) -> None:
        skill_text = PEER_REVIEW_SKILL.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")

        self.assertIn("grok-composer-2.5-fast", skill_text)
        self.assertIn("PEER_REVIEW_GROK_MODEL=grok-composer-2.5-fast", skill_text)
        self.assertIn("grok-composer-2.5-fast", readme_text)

    def test_peer_review_docs_define_intensity_policy(self) -> None:
        skill_text = PEER_REVIEW_SKILL.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")
        metadata_text = PEER_REVIEW_METADATA.read_text(encoding="utf-8")

        for text in (skill_text, readme_text):
            self.assertIn("`planning`", text)
            self.assertIn("`gate`", text)
            self.assertIn("`critical`", text)
            self.assertIn("--intensity gate", text)
            self.assertIn("Humans do not need to specify", text)
        self.assertIn("infer the review intensity", metadata_text)
        self.assertIn("default to gate", metadata_text)
        self.assertIn("Gemini opt-in", metadata_text)

    def test_peer_review_docs_define_fail_closed_tool_policy(self) -> None:
        skill_text = PEER_REVIEW_SKILL.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")

        for text in (skill_text, readme_text):
            self.assertIn("`context-only`", text)
            self.assertIn("`web-allowed`", text)
            self.assertIn("write/action tools", text)
            self.assertIn("Humans do not need to specify tool flags", text)


if __name__ == "__main__":
    unittest.main()
