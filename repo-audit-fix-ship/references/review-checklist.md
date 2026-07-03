# Review Checklist

## Audit
- Confirm branch, remotes, and local changes.
- Run stack-appropriate lint, typecheck, tests.
- Identify high-severity defects first.
- Check dependency/configuration security risks.
- Delegate the detailed rubric to `audit-ai-code`, `audit-ai-frontend`, or `audit-ai-writing` when they apply.

## Fix
- Use `systematic-debugging` for failures and root-cause work.
- Use `test-driven-development` for behavior changes unless explicitly exempted.
- Implement smallest safe fix for each accepted finding.
- Add or update tests for bug fixes.
- Avoid unrelated refactors unless requested.

## Docs
- Update user-facing and developer-facing docs changed by behavior.
- Verify setup, run, deploy, and troubleshooting instructions.
- Keep AGENTS/tasks/decisions aligned with implementation.
- If source/config changed but no docs changed, record the reason.

## Repository hygiene
- Keep generated artifacts out of commits (`node_modules/`, `dist/`, `build/`, `coverage/`, caches, logs, temp files, local DBs).
- Keep new implementation files under stable folders (`src/`, `app/`, `lib/`, `scripts/`, `tests/`, `docs/`) unless root placement is intentional.
- Inspect root-level source/config additions and document why they belong there.
- Confirm staged files are intentional and minimal.

## Ship
- Re-run validation checks.
- Use `verification-before-completion` before success claims or delivery.
- Use `gh-commit` for non-trivial staging and semantic commit grouping.
- Stage only intended files.
- Commit with clear scope and push to a `codex/*` branch.
- Report commit hash, branch, checks run, and remaining risks.
