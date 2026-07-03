---
name: github-ci-cost-control
description: Audit and safely reduce GitHub Actions cost in an existing repository. Use when the user asks to add CI cost controls, reduce GitHub Actions minutes, tune PR checks, add path filters, skip expensive draft PR runs, add concurrency cancellation, split nightly CI from PR gates, or apply reusable CI savings patterns across repos without disabling necessary verification.
---

# GitHub CI Cost Control

## Purpose

Reduce GitHub Actions spend without turning CI into theater. Keep a fast, relevant gate on PRs and `main`; move only expensive non-blocking coverage to scheduled/manual workflows.

## Workflow

1. Inspect the repo before editing.
   - Read `.github/workflows/*.{yml,yaml}`.
   - Run `python3 <skill-dir>/scripts/inspect_github_actions.py <repo>` for a quick inventory.
   - Treat helper recommendations as branch-protection-blind candidates, not instructions to apply blindly.
   - Identify languages, package managers, app directories, generated files, deploy files, and existing required checks.
   - If GitHub access is available, inspect recent runs and PR required checks before changing workflow names or job names.

2. Preserve safety gates.
   - Do not delete CI, tests, lint, security/audit checks, deploy checks, migrations, or required check names just to save minutes.
   - Do not move all CI to nightly.
   - Do not remove `push` coverage for `main` unless branch protection blocks direct pushes and the user explicitly wants PR-only CI.
   - Do not make repo-wide GitHub account settings changes from this skill.
   - Know the GitHub required-check behavior: a workflow skipped by path/branch filters or commit message can leave required checks pending and block merges, while a job skipped by a job-level `if:` reports success and may allow merge. This makes under-included path filters dangerous.
   - If a required job can become conditional, prefer a stable aggregate gate job as the required check, or keep the old required gate until branch protection behavior is proven.

3. Add low-risk cost controls first.
   - Add workflow-level `concurrency` only after classifying the workflow. Use `cancel-in-progress: true` for PR/test lanes, but do not cancel in-progress deploy, publish, release, or tag workflows unless the repo already proves that is safe.
   - Limit `pull_request` activity types to `opened`, `synchronize`, `reopened`, and `ready_for_review` only after confirming the workflow does not depend on labels, title/body edits, base-branch edits, review events, or other PR metadata changes.
   - Derive minimal workflow `permissions`; preserve scopes needed for deploys, releases, security uploads, package publishing, OIDC, and comments.
   - Gate expensive jobs on draft status only when `ready_for_review` or another final-code trigger will run the gated jobs when the PR becomes ready.
   - Add a cheap file-change detection job for PRs.
   - Run expensive backend/frontend/mobile/docs jobs only when relevant paths change.
   - Keep cheap global checks, such as brand/copy/license checks, separate from heavyweight jobs.
   - Preserve fail-open guard clauses such as `always()`, `needs.changes.result != 'success'`, and non-PR fallbacks. Removing them can turn filter failures into under-running gates.
   - Add `timeout-minutes` to expensive jobs so hung jobs cannot spend the default maximum runtime.
   - Avoid duplicate push+PR runs: when safe, run `push` only on `main`/release branches/tags and rely on `pull_request` for feature branches.
   - Use dependency caches where supported by existing setup actions or repo package managers.

4. Use repo-specific path groups.
   - Backend examples: `backend/`, `api/`, `server/`, `services/`, `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `uv.lock`, `alembic/`, `migrations/`, `docker-compose.yml`, `compose*.yml`, `deploy/`, `scripts/`.
   - Frontend examples: `frontend/`, `web/`, `app/`, `src/`, `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `vite.config.*`, `next.config.*`.
   - Docs examples: `docs/`, `README*`, `*.md`.
   - Treat `.github/workflows/` changes as touching every CI lane.
   - Derive actual groups from this repo rather than blindly using these examples.
   - Over-include when unsure. A false run costs minutes; a false skip can merge broken code.
   - Include nested manifests and lockfiles for monorepos, such as `apps/*/package.json`, `packages/*/pyproject.toml`, `poetry.lock`, `uv.lock`, `pnpm-lock.yaml`, `yarn.lock`, and shared config.

5. Split optional depth from merge gates.
   - Keep PR/main gates fast enough to run on every relevant change.
   - Move long-running non-blocking checks to `schedule` plus `workflow_dispatch` when they are not required to decide whether to merge.
   - Good nightly candidates: full matrix builds, exhaustive browser tests, slow security scans, large dependency audits, non-critical integration sweeps.
   - Bad nightly-only candidates: unit tests for touched code, lint/typecheck for touched app, migration smoke checks, required deploy/package checks.

6. Verify before finishing.
   - Parse the edited workflow YAML locally.
   - Run `git diff --check`.
   - Verify gate survival, not only job shape. Conditionalizing a required check can change branch-protection behavior.
   - If possible, open or use a test PR that touches only irrelevant paths and confirm it is mergeable or blocked exactly as intended.
   - Confirm a relevant-path PR still runs the heavyweight jobs.
   - If draft gating changed, confirm draft-to-ready transition runs the final gated jobs.
   - Report whether previously required checks still gate merges.
   - Report exactly what was verified and what was not.

## Implementation Notes

- Prefer existing workflow style and job names.
- Keep required check names stable unless the user approves branch protection updates.
- Prefer `pull_request` over `pull_request_target` unless the repo already needs the latter and handles its security risk.
- For fork-heavy public repos, be careful with secrets and write permissions.
- If a workflow already uses `paths`/`paths-ignore`, decide whether job-level filters are still needed. Job-level filters usually give better visibility because the workflow still reports a cheap check instead of disappearing entirely.
- Treat scheduled CI as additional coverage, not replacement coverage.

## Useful Patterns

Basic PR/test workflow-level concurrency:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

For deploy, publish, release, or tag workflows, scope cancellation to PRs or use `cancel-in-progress: false` so a newer push cannot cancel a live deployment halfway through.

PR event narrowing:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
```

Minimal read permissions for CI:

```yaml
permissions:
  contents: read
  pull-requests: read
```

Use the `pull-requests: read` permission with PR file-filter snippets that call `pulls.listFiles`.

Cheap PR file filter with `actions/github-script`:

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/github-script@v9
        id: filter
        with:
          script: |
            const isPullRequest = context.eventName === "pull_request";
            let files = [];
            if (isPullRequest) {
              const changed = await github.paginate(github.rest.pulls.listFiles, {
                owner: context.repo.owner,
                repo: context.repo.repo,
                pull_number: context.payload.pull_request.number,
                per_page: 100,
              });
              files = changed.map((file) => file.filename);
            }
            const workflow = !isPullRequest || files.some((file) => file.startsWith(".github/workflows/"));
            const touches = (prefixes) => files.some((file) => prefixes.some((prefix) => file === prefix || file.startsWith(prefix)));
            core.setOutput("backend", String(workflow || touches(["backend/", "api/", "server/", "scripts/", "deploy/"])));
            core.setOutput("frontend", String(workflow || touches(["frontend/", "web/", "package.json", "package-lock.json"])));
```

Expensive job guard:

```yaml
needs: changes
if: >-
  always() && (
    needs.changes.result != 'success' ||
    github.event_name != 'pull_request' ||
    (github.event.pull_request.draft == false && needs.changes.outputs.backend == 'true')
  )
steps:
  - name: Verify changes filter
    if: needs.changes.result != 'success'
    run: exit 1
```

Stable aggregate gate for required checks:

```yaml
ci-gate:
  needs: [changes, backend, frontend]
  if: always()
  runs-on: ubuntu-latest
  steps:
    - name: Verify required CI lanes
      run: |
        if [ "${{ needs.changes.result }}" != "success" ]; then
          exit 1
        fi
        if [ "${{ needs.changes.outputs.backend }}" = "true" ] && [ "${{ needs.backend.result }}" != "success" ]; then
          exit 1
        fi
        if [ "${{ needs.changes.outputs.frontend }}" = "true" ] && [ "${{ needs.frontend.result }}" != "success" ]; then
          exit 1
        fi
```

When heavy jobs can skip, make a stable aggregate gate like `ci-gate` the required check instead of requiring skippable heavyweight jobs directly.
