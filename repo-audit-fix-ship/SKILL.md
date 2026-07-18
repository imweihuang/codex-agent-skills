---
name: repo-audit-fix-ship
description: Use when the user explicitly asks for an end-to-end repository quality pass that may include audit, bug fixes, documentation sync, repository hygiene, commit, and push. Do not use for read-only audits, repo readiness/setup checks, debugging-only tasks, frontend/writing audits, or commit-only requests.
metadata:
  short-description: Audit, fix, docs, commit, push
---

# Repo Audit Fix Ship

This is an orchestration skill for full repository cleanup and delivery. Use it to coordinate sharper local skills, not to replace them.

## Activation Guard

Use only when the request clearly includes the full lifecycle: repository audit or quality pass, accepted fixes, documentation or hygiene review, verification, and git delivery.

Do not use for:
- Read-only code review, audit, or risk assessment.
- Repo setup/readiness checks, `AGENTS.md` scaffolding, or agent-readiness scorecards.
- Debugging a specific bug or failed test without a broader repo-quality pass.
- Frontend-only, writing-only, or commit-only requests.
- Deployment or runtime operations where a project-specific deployment skill applies.

If the user says "audit my repo" without asking for fixes and shipping, default to read-only review and use a narrower audit skill instead.

## Delegate First

Load and follow the relevant specialized skill when its trigger applies:

| Situation | Use |
| --- | --- |
| AI-shaped backend/general code audit or cleanup | `audit-ai-code` |
| Frontend/UI/design-system audit or cleanup | `audit-ai-frontend` |
| Documentation, Markdown, prose, citation, or AI-writing cleanup | `audit-ai-writing` |
| Bug, failing test, build failure, or unexpected behavior | Root-cause diagnosis with a minimal reproduction |
| Feature/bugfix implementation after diagnosis | Behavior-first implementation with regression tests |
| Before claiming completion or committing | Explicit local verification with observed evidence |
| Staging and semantic commit grouping | `gh-commit` |
| Branch merge/PR/cleanup decision after implementation | Shared Git delivery and hard-stop rules |

## Workflow

1. Establish scope and git safety first:
- Confirm current repository root and active branch.
- Run `git status --short --branch` and `git remote -v`.
- Respect existing uncommitted changes; never reset or discard user work.
- If commit/push target is unclear, create or recommend a new branch prefixed with `codex/`; do not commit to `main` or `master` unless the user explicitly asked for that.
- If the worktree contains unrelated tracked changes, keep them out of scope and do not stage them.

2. Build a review baseline:
- Inventory project structure and key configs (`package.json`, `pyproject.toml`, `go.mod`, CI configs, docs files).
- Run fast health checks that fit the stack (lint, typecheck, unit tests).
- Capture failures and prioritize by severity: correctness, security, data loss, crashes, regressions.

3. Perform comprehensive code review and audit:
- Use `audit-ai-code`, `audit-ai-frontend`, or `audit-ai-writing` for the relevant surface instead of inventing a separate rubric here.
- Review high-risk areas first: auth, persistence, concurrency, external I/O, error handling.
- Look for bug patterns: null/undefined handling, off-by-one, race conditions, stale state, incorrect async flow, unchecked errors.
- Audit dependency and config risks where tooling exists (for example `npm audit`, `pip-audit`, `go list -m -u all`).
- Record findings with file paths and concrete impact.

4. Fix issues pragmatically:
- Reproduce and diagnose failures before changing behavior.
- Capture a failing test or reproducible characterization before meaningful
  behavior changes when practical.
- Apply minimal, targeted code changes that resolve root causes.
- Add or update tests for each meaningful bug fix.
- Keep backward compatibility unless user requested breaking changes.

5. Synchronize documentation:
- Update docs impacted by code changes (for example `README.md`, architecture notes, runbooks, changelog, API docs, `AGENTS.md`).
- Ensure commands, environment variables, and behavioral notes match the new code.
- Remove stale or contradictory docs.
- If source/config/workflow changed but docs do not need updates, report why instead of touching docs just to satisfy a checklist.

6. Verify end-to-end:
- Run the strongest relevant local verification and inspect its output before
  making success claims, committing, pushing, or opening a PR.
- Re-run lint/typecheck/tests and any relevant build command.
- Re-check git diff for accidental changes, debug logs, generated artifacts, misplaced files, or secrets.
- Summarize what was fixed, what was not fixed, and residual risk.

7. Commit and push:
- Use `gh-commit` for staging and semantic commit grouping when there is any non-trivial diff.
- Stage intentional changes only; prefer explicit paths over broad staging.
- Commit with a scoped message that reflects audit + fixes + docs.
- Push only when the user asked for delivery through git push or the current task clearly includes shipping.
- Report the exact branch, commit hash, verification commands, and remaining risks.

## Required Behavior

- Do not claim checks ran if they did not run.
- If a tool is missing, state it and continue with best available checks.
- Never use destructive git commands to clean state unless user explicitly asks.
- Prefer non-interactive git commands.
- If push fails due to auth/protection, report exact failure and stop.
- Do not stage unrelated files just to make documentation or hygiene checks pass.
- Do not force push or create a new remote repository unless the user explicitly requests it.
- Do not read secret file contents. Use filename, tracked-file, ignore-pattern, and scanner evidence instead.
- Do not run deploy, migration, cloud, paid API, or state-mutating production commands unless the user explicitly approved that specific action.

## Repository Hygiene

- Keep generated/vendor artifacts out of commits: `node_modules/`, `dist/`, `build/`, `coverage/`, caches, logs, temporary files, and local databases.
- Keep new source files in stable project folders such as `src/`, `app/`, `lib/`, `scripts/`, `tests/`, or `docs/` unless root placement is intentional.
- Treat root-level source/config additions as a warning to inspect, not an automatic blocker; document the reason when root placement is intentional.
- Verify setup, run, deploy, environment variable, and troubleshooting docs still match current commands and paths.
- Stage explicit intended paths. Use broad staging only when the whole worktree is confirmed in scope.

## When Not To Use

- Use GitHub publish/PR workflows when the user only wants to stage, commit, push, and open a pull request.
- Use `gh-commit` when the user only wants commits or commit cleanup.
- Use `agent-readiness` or a future repo-readiness skill when the user wants repository setup, `AGENTS.md`, verification-harness, CI, secrets-hygiene, or agent-readiness scoring without code fixes and shipping.
- Use project-specific deployment skills when the task is primarily deployment or runtime verification.
- Use project documentation scaffolding only when starting a new under-documented repository from scratch.

## Commit Template

Use a commit message like:

```text
fix: audit codebase, resolve high-risk bugs, and sync docs
```

Or, when appropriate:

```text
chore: repository audit, bug fixes, and documentation refresh
```

## Reference

- `references/review-checklist.md`: quick checklist for audit/fix/doc/ship steps.
