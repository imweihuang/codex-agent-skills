#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone


DEFAULTS = {
    "claude": {
        "model": "opus",
        "effort": "high",
        "reserved_model": "claude-fable-5",
        "reserved_efforts": ("high", "xhigh"),
        "fallback_model": None,
        "fallback_effort": None,
    },
    "codex": {"model": "gpt-5.5", "effort": "xhigh"},
    "gemini": {"model": "cli-default", "effort": "not-cli-exposed"},
    "grok": {"model": "grok-4.5", "effort": "reasoning_effort=high"},
}


@dataclass
class CliReport:
    key: str
    label: str
    cli: str
    package_manager: str
    package_name: str
    path: str | None
    current_version: str | None
    latest_version: str | None
    update_command: str
    status: str
    note: str


@dataclass
class ModelReport:
    key: str
    label: str
    current_model: str
    current_effort: str
    suggested_model: str
    suggested_effort: str
    status: str
    evidence: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually check/update peer-review CLIs and propose model-default changes.",
    )
    parser.add_argument("--no-online", action="store_true", help="Skip npm/Homebrew latest-version queries.")
    parser.add_argument("--update", action="store_true", help="Run known update commands, then print a fresh report.")
    parser.add_argument(
        "--install-missing",
        action="store_true",
        help="With --update, install missing npm/Homebrew-managed CLIs where a safe package is known.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    if args.update:
        run_updates(install_missing=args.install_missing)

    cli_reports = collect_cli_reports(online=not args.no_online)
    model_reports = collect_model_reports()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "online_checks": not args.no_online,
        "updated_before_report": args.update,
        "cli_reports": [report.__dict__ for report in cli_reports],
        "model_reports": [report.__dict__ for report in model_reports],
        "default_files_changed": False,
    }

    if args.json:
        print(json.dumps(payload, indent=2) + "\n")
    else:
        print_markdown(cli_reports, model_reports, online=not args.no_online, updated=args.update)

    return 0 if all(report.status not in {"missing", "update_failed"} for report in cli_reports) else 2


def collect_cli_reports(online: bool) -> list[CliReport]:
    return [
        claude_report(online),
        codex_report(online),
        gemini_report(online),
        grok_report(online),
    ]


def claude_report(online: bool) -> CliReport:
    path = shutil.which("claude")
    current = command_version(["claude", "--version"]) if path else None
    return CliReport(
        key="claude",
        label="Claude",
        cli="claude",
        package_manager="Claude native updater",
        package_name="Claude Code",
        path=path,
        current_version=current,
        latest_version=None if online else "skipped",
        update_command="claude update",
        status="ready" if path else "missing",
        note="Latest version is checked by the native updater; run --update to invoke it.",
    )


def codex_report(online: bool) -> CliReport:
    path = shutil.which("codex")
    current = normalize_codex_version(command_version(["codex", "--version"])) if path else None
    latest = npm_view_version("@openai/codex") if online else "skipped"
    return CliReport(
        key="codex",
        label="Codex/GPT",
        cli="codex",
        package_manager="npm",
        package_name="@openai/codex",
        path=path,
        current_version=current,
        latest_version=latest,
        update_command="npm install -g @openai/codex@latest",
        status=version_status(current, latest, path),
        note="Model defaults are checked with `codex debug models`.",
    )


def gemini_report(online: bool) -> CliReport:
    path = shutil.which("gemini")
    current = command_version(["gemini", "--version"]) if path else None
    latest = brew_formula_version("gemini-cli") if online else "skipped"
    return CliReport(
        key="gemini",
        label="Gemini",
        cli="gemini",
        package_manager="Homebrew",
        package_name="gemini-cli",
        path=path,
        current_version=current,
        latest_version=latest,
        update_command="brew upgrade gemini-cli",
        status=version_status(current, latest, path),
        note="Gemini CLI model catalogs and thinking effort are not reliably exposed by local help output.",
    )


def grok_report(online: bool) -> CliReport:
    path = shutil.which("grok")
    current = normalize_grok_version(command_version(["grok", "--version"])) if path else None
    latest = npm_view_version("@xai-official/grok") if online else "skipped"
    return CliReport(
        key="grok",
        label="Grok Build",
        cli="grok",
        package_manager="npm",
        package_name="@xai-official/grok",
        path=path,
        current_version=current,
        latest_version=latest,
        update_command="npm install -g @xai-official/grok@latest",
        status=version_status(current, latest, path),
        note="Model defaults are checked with `grok models`.",
    )


def collect_model_reports() -> list[ModelReport]:
    return [
        claude_model_report(),
        codex_model_report(),
        gemini_model_report(),
        grok_model_report(),
    ]


def claude_model_report() -> ModelReport:
    help_text = command_output(["claude", "--help"])
    effort_ok = all(value in help_text for value in ("--effort", "xhigh"))
    model_ok = all(value in help_text for value in ("claude-fable-5", "opus"))
    policy_flags_ok = all(
        value in help_text for value in ("--tools", "--no-session-persistence", 'Use "" to disable all')
    )
    status = "confirmed" if effort_ok and model_ok and policy_flags_ok else "needs_manual_check"
    evidence = (
        "`claude --help` confirms Opus/high for routine routing plus Fable 5 high/xhigh reserved routing, policy-critical flags, and empty --tools disable semantics"
        if status == "confirmed"
        else "`claude --help` did not confirm all model, effort, and policy-critical tool/session controls"
    )
    return model_report("claude", "Claude", DEFAULTS["claude"]["model"], DEFAULTS["claude"]["effort"], status, evidence)


def codex_model_report() -> ModelReport:
    raw = command_output(["codex", "debug", "models"], timeout=30)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return model_report("codex", "Codex/GPT", DEFAULTS["codex"]["model"], DEFAULTS["codex"]["effort"], "unknown", "`codex debug models` was not parseable")

    models = data.get("models", [])
    default_model = DEFAULTS["codex"]["model"]
    default_effort = DEFAULTS["codex"]["effort"]
    default_ok = model_supports(models, default_model, default_effort)
    best = best_codex_model(models)
    suggested_model = default_model if default_ok else (best[0] if best else default_model)
    suggested_effort = default_effort if (default_ok or not best) else best[1]
    if default_ok:
        status = "confirmed"
        evidence = f"`codex debug models` lists {default_model} with {default_effort}"
    elif best:
        status = "proposal"
        evidence = f"default unavailable; highest-priority local xhigh model appears to be {best[0]}"
    else:
        status = "needs_manual_check"
        evidence = "`codex debug models` did not expose a usable xhigh model"
    return ModelReport("codex", "Codex/GPT", default_model, default_effort, suggested_model, suggested_effort, status, evidence)


def gemini_model_report() -> ModelReport:
    help_text = command_output(["gemini", "--help"])
    model_ok = "--model" in help_text
    effort_exposed = "thinking" in help_text.lower() or "effort" in help_text.lower()
    if model_ok and not effort_exposed:
        status = "confirmed_with_caveat"
        evidence = "`gemini --help` exposes --model but no thinking-effort flag; CLI default is used unless overridden"
    elif model_ok:
        status = "needs_manual_check"
        evidence = "`gemini --help` may expose effort-related text; inspect before claiming"
    else:
        status = "needs_manual_check"
        evidence = "`gemini --help` did not confirm --model"
    return model_report("gemini", "Gemini", DEFAULTS["gemini"]["model"], DEFAULTS["gemini"]["effort"], status, evidence)


def grok_model_report() -> ModelReport:
    raw_models = command_output(["grok", "models"], timeout=30)
    help_text = command_output(["grok", "--help"])
    models = parse_grok_models(raw_models)
    default_model = DEFAULTS["grok"]["model"]
    suggested_model = default_model
    if models and default_model not in models:
        suggested_model = next(iter(models))
    policy_flags_ok = all(
        value in help_text
        for value in ("--reasoning-effort", "--disable-web-search", "--tools", "--no-subagents", "--prompt-file")
    )
    if "you are logged in" not in raw_models.lower():
        status = "auth_required"
        evidence = "`grok models` did not confirm login"
    elif suggested_model != default_model:
        status = "proposal"
        evidence = f"`grok models` lists {suggested_model}, not {default_model}"
    elif policy_flags_ok:
        status = "confirmed"
        evidence = "`grok models` confirms model and `grok --help` exposes the policy-critical reasoning, web, tool, subagent, and prompt flags"
    else:
        status = "needs_manual_check"
        evidence = "`grok --help` did not confirm all policy-critical reasoning, web, tool, subagent, and prompt flags"
    return ModelReport(
        "grok",
        "Grok Build",
        default_model,
        DEFAULTS["grok"]["effort"],
        suggested_model,
        DEFAULTS["grok"]["effort"],
        status,
        evidence,
    )


def model_report(key: str, label: str, model: str, effort: str, status: str, evidence: str) -> ModelReport:
    return ModelReport(key, label, model, effort, model, effort, status, evidence)


def run_updates(install_missing: bool) -> None:
    commands = [
        ("claude", ["claude", "update"], None),
        ("codex", ["npm", "install", "-g", "@openai/codex@latest"], ["npm"]),
        ("gemini", ["brew", "upgrade", "gemini-cli"], ["brew"]),
        ("grok", ["npm", "install", "-g", "@xai-official/grok@latest"], ["npm"]),
    ]
    for cli, command, prerequisites in commands:
        if shutil.which(cli) is None and not install_missing:
            print(f"[refresh] skipped {cli}: missing; pass --install-missing with --update to install when supported", file=sys.stderr)
            continue
        if prerequisites and any(shutil.which(item) is None for item in prerequisites):
            print(f"[refresh] skipped {cli}: missing prerequisite {'/'.join(prerequisites)}", file=sys.stderr)
            continue
        if cli == "claude" and shutil.which(cli) is None:
            print("[refresh] skipped claude: no safe automatic install path configured", file=sys.stderr)
            continue
        if cli == "gemini" and shutil.which(cli) is None:
            command = ["brew", "install", "gemini-cli"]
        print(f"[refresh] running: {' '.join(command)}", file=sys.stderr)
        subprocess.run(command, check=False)


def command_version(command: list[str]) -> str | None:
    output = command_output(command, timeout=20)
    return " ".join(output.strip().split()) or None


def command_output(command: list[str], timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout or ""


def npm_view_version(package: str) -> str | None:
    output = command_output(["npm", "view", package, "version"], timeout=30)
    return output.strip().splitlines()[-1].strip() if output.strip() else None


def brew_formula_version(formula: str) -> str | None:
    output = command_output(["brew", "info", "--json=v2", formula], timeout=60)
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None
    formulae = data.get("formulae", [])
    if not formulae:
        return None
    return formulae[0].get("versions", {}).get("stable")


def normalize_codex_version(raw: str | None) -> str | None:
    if raw is None:
        return None
    return raw.removeprefix("codex-cli ").strip()


def normalize_grok_version(raw: str | None) -> str | None:
    if raw is None:
        return None
    match = re.search(r"grok\s+([^\s]+)", raw)
    return match.group(1) if match else raw


def version_status(current: str | None, latest: str | None, path: str | None) -> str:
    if path is None:
        return "missing"
    if latest in {None, "", "skipped"}:
        return "ready"
    if current == latest:
        return "current"
    return "update_available"


def model_supports(models: list[dict], slug: str, effort: str) -> bool:
    for item in models:
        if item.get("slug") != slug:
            continue
        efforts = {entry.get("effort") for entry in item.get("supported_reasoning_levels", [])}
        return effort in efforts
    return False


def best_codex_model(models: list[dict]) -> tuple[str, str] | None:
    candidates = []
    for item in models:
        slug = item.get("slug")
        if not slug:
            continue
        efforts = {entry.get("effort") for entry in item.get("supported_reasoning_levels", [])}
        if "xhigh" not in efforts:
            continue
        candidates.append((item.get("priority", 0), slug, "xhigh"))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, slug, effort = candidates[0]
    return slug, effort


def parse_grok_models(raw: str) -> set[str]:
    models: set[str] = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(("* ", "- ")):
            models.add(stripped[2:].split()[0])
    return models


def print_markdown(cli_reports: list[CliReport], model_reports: list[ModelReport], online: bool, updated: bool) -> None:
    print("# Peer Review CLI Refresh")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"Online package checks: {'enabled' if online else 'skipped'}")
    print(f"Ran updater first: {'yes' if updated else 'no'}")
    print("\n## CLI Versions")
    print("| Reviewer | CLI | Current | Latest | Status | Update command |")
    print("| --- | --- | --- | --- | --- | --- |")
    for report in cli_reports:
        print(
            "| "
            + " | ".join(
                [
                    report.label,
                    f"`{report.cli}`",
                    report.current_version or "missing",
                    report.latest_version or "native updater/manual",
                    report.status,
                    f"`{report.update_command}`",
                ]
            )
            + " |"
        )
    print("\n## Model Defaults")
    print("| Reviewer | Current default | Suggested default | Status | Evidence |")
    print("| --- | --- | --- | --- | --- |")
    for report in model_reports:
        current = f"`{report.current_model}` / `{report.current_effort}`"
        suggested = f"`{report.suggested_model}` / `{report.suggested_effort}`"
        print(f"| {report.label} | {current} | {suggested} | {report.status} | {report.evidence} |")

    proposals = [report for report in model_reports if report.status == "proposal"]
    if proposals:
        print("\n## Proposed Default Changes")
        for report in proposals:
            print(
                f"- {report.label}: consider changing `{report.current_model}` / `{report.current_effort}` "
                f"to `{report.suggested_model}` / `{report.suggested_effort}`."
            )
    else:
        print("\n## Proposed Default Changes")
        print("- None. No skill default files were changed.")

    print("\n## Notes")
    for report in cli_reports:
        print(f"- {report.label}: {report.note}")
    print("- Run with `--update` to update installed CLIs. Add `--install-missing` to install supported missing npm/Homebrew CLIs.")
    print("- This script does not rewrite `SKILL.md` or `run_peer_review.py`; default changes remain a manual code review decision.")


if __name__ == "__main__":
    raise SystemExit(main())
