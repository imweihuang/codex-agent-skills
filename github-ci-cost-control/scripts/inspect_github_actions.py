#!/usr/bin/env python3
"""Inventory GitHub Actions workflows and likely CI cost-control opportunities."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPENSIVE_HINTS = {
    "pytest": r"\bpytest\b",
    "npm-ci": r"\bnpm ci\b",
    "npm-build": r"\bnpm run build\b",
    "audit": r"\b(pip[-_]?audit|npm audit|pnpm audit|yarn audit)\b",
    "docker": r"\bdocker\b|services:",
    "playwright": r"\bplaywright\b",
    "matrix": r"strategy:[\s\S]{0,500}matrix:",
    "migrations": r"\b(alembic|migrate|migrations?)\b",
}

EVENT_TRIGGERS = ("pull_request", "pull_request_target", "push", "schedule", "workflow_dispatch")

CHANGE_FILTER_HINT = (
    r"pulls\.listFiles|"
    r"dorny/paths-filter|"
    r"tj-actions/changed-files|"
    r"changed-files|"
    r"paths-filter|"
    r"needs\.[A-Za-z0-9_-]+\.outputs\."
)

DRAFT_GUARD_HINT = (
    r"github\.event\.pull_request\.draft|"
    r"pull_request\.draft|"
    r"\bdraft\s*==\s*false|"
    r"\bdraft\s*!=\s*true"
)

DEPLOY_HINT = (
    r"^\s*name:\s*.*\b(deploy|deployment|publish|release)\b|"
    r"^\s*[A-Za-z0-9_-]+:\s*(?:#.*)?\n\s*(?:name:\s*.*\b(deploy|deployment|publish|release)\b)|"
    r"\b(docker push|npm publish|pnpm publish|yarn npm publish|twine upload|gh release|gcloud run deploy|"
    r"kubectl apply|helm upgrade|terraform apply|rsync|scp)\b|"
    r"\b(peter-evans/create-pull-request|softprops/action-gh-release|docker/build-push-action)\b"
)


def bool_re(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None


def trigger_summary(text: str) -> dict[str, bool]:
    triggers = {name: False for name in EVENT_TRIGGERS}
    lines = text.splitlines()
    on_line = re.compile(r"^(?P<indent>\s*)['\"]?on['\"]?\s*:\s*(?P<value>.*)$", re.IGNORECASE)

    for index, line in enumerate(lines):
        match = on_line.match(line)
        if not match:
            continue
        base_indent = len(match.group("indent"))
        value = match.group("value").split("#", 1)[0].strip()
        if value:
            for event in EVENT_TRIGGERS:
                if re.search(rf"\b{re.escape(event)}\b", value):
                    triggers[event] = True
            return triggers

        for child in lines[index + 1:]:
            stripped = child.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(child) - len(child.lstrip())
            if indent <= base_indent:
                break
            if stripped.startswith("-"):
                token = stripped[1:].strip().split("#", 1)[0].strip().rstrip(":")
            else:
                token = stripped.split(":", 1)[0].strip().strip("'\"")
            if token in triggers:
                triggers[token] = True
        return triggers

    return triggers


def workflow_summary(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    triggers = trigger_summary(text)
    triggers["concurrency"] = bool_re(r"(?m)^\s*concurrency\s*:", text)
    triggers["permissions"] = bool_re(r"(?m)^\s*permissions\s*:", text)
    summary = {
        "path": str(path),
        "triggers": triggers,
        "expensive_hints": [name for name, pattern in EXPENSIVE_HINTS.items() if bool_re(pattern, text)],
        "uses_actions": sorted(set(re.findall(r"uses:\s*([^\s#]+)", text))),
        "has_draft_guard": bool_re(DRAFT_GUARD_HINT, text),
        "has_change_filter": bool_re(CHANGE_FILTER_HINT, text),
        "has_paths_filter": bool_re(r"\b(paths|paths-ignore)\s*:", text),
        "has_job_level_if": bool_re(r"(?m)^\s+if\s*:", text),
        "has_timeout_minutes": bool_re(r"(?m)^\s*timeout-minutes\s*:", text),
        "looks_like_deploy_or_release": bool_re(DEPLOY_HINT, text),
    }
    summary["recommendations"] = workflow_recommendations(summary)
    return summary


def repo_shape(root: Path) -> dict[str, object]:
    candidates = {
        "python": ["pyproject.toml", "requirements.txt", "requirements-dev.txt", "backend/pyproject.toml"],
        "node": ["package.json", "frontend/package.json", "web/package.json"],
        "docker": ["Dockerfile", "docker-compose.yml", "compose.yml", "compose.prod.yml"],
        "deploy": ["deploy", "deployment", "release"],
        "docs": ["docs", "README.md"],
    }
    return {
        key: [item for item in items if (root / item).exists()]
        for key, items in candidates.items()
    }


def workflow_recommendations(workflow: dict[str, object]) -> list[str]:
    recs: list[str] = []
    triggers = workflow["triggers"]
    pr_like = bool(triggers.get("pull_request") or triggers.get("pull_request_target"))
    expensive = bool(workflow["expensive_hints"])
    if not triggers.get("concurrency"):
        recs.append("Candidate: add workflow concurrency; use cancel-in-progress only for PR/test lanes, not deploy/release lanes.")
    if triggers.get("concurrency") and workflow["looks_like_deploy_or_release"]:
        recs.append("Check existing concurrency; avoid cancelling in-progress deployments or releases.")
    if not triggers.get("permissions"):
        recs.append("Candidate: derive minimal permissions for this workflow; preserve deploy/release/security/package/OIDC scopes when needed.")
    if "matrix" in workflow["expensive_hints"]:
        recs.append("Consider moving non-blocking matrix breadth to nightly/manual CI.")
    if expensive and pr_like and not workflow["has_draft_guard"]:
        recs.append("Candidate: gate expensive PR jobs on non-draft PRs; ensure ready_for_review retriggers them.")
    if expensive and pr_like and not workflow["has_paths_filter"] and not workflow["has_change_filter"]:
        recs.append("Candidate: add PR file-change filtering before heavyweight jobs; over-include paths and verify required-check behavior.")
    if expensive and not workflow["has_timeout_minutes"]:
        recs.append("Candidate: add timeout-minutes to expensive jobs to avoid paying for hung runs.")
    return recs


def recommendations(workflows: list[dict[str, object]]) -> list[str]:
    recs: list[str] = []
    if not workflows:
        return ["No GitHub Actions workflows found."]
    for workflow in workflows:
        for rec in workflow["recommendations"]:
            recs.append(f"{workflow['path']}: {rec}")
    if not any(wf["triggers"].get("schedule") for wf in workflows):
        recs.append("Optional: add a nightly workflow for slow non-blocking coverage.")
    return recs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="Repository root, default: current directory")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    workflow_dir = root / ".github" / "workflows"
    workflows = []
    if workflow_dir.exists():
        workflows = [
            workflow_summary(path)
            for pattern in ("*.yml", "*.yaml")
            for path in sorted(workflow_dir.glob(pattern))
        ]

    print(json.dumps({
        "repo": str(root),
        "repo_shape": repo_shape(root),
        "required_checks_note": "This helper cannot see branch protection or rulesets. Inspect required check names before making jobs conditional, renaming jobs, or changing required gates.",
        "workflows": workflows,
        "recommendations": recommendations(workflows),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
