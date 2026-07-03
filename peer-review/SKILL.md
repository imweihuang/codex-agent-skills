---
name: peer-review
description: Use when the user asks for peer review, external review, model council, second opinion, red-team feedback, code audit, architecture review, schema review, production-readiness review, API contract review, coverage audit, or candid feedback from Claude, GPT/Codex, Gemini, Grok, or multiple CLI reviewers.
---

# Peer Review

## Purpose

Use this skill to run independent external CLI reviewers and then have Codex validate the findings. Treat the reviewers as strong second, third, and fourth eyes, not authorities.

Default reviewer roster at `gate` intensity:

| Reviewer | CLI | Default model | Default effort |
| --- | --- | --- | --- |
| Claude | `claude` | Opus 4.8 via `opus` alias | `xhigh` |
| Codex/GPT | `codex` | `gpt-5.5` | `xhigh` |
| Grok Build | `grok` | `grok-composer-2.5-fast` | `max`; `reasoning_effort=high` |

Gemini remains supported but is opt-in. Use `--reviewers all-with-gemini` or include `gemini` explicitly when Gemini's local CLI behavior is acceptable for the task.

If a CLI, model, auth state, or effort setting is unavailable, report it clearly. Do not silently downgrade or present Codex self-review as external peer review.

Humans do not need to specify an intensity flag. The agent must infer review intensity from the request and context, pass the matching `--intensity` value to the runner, and report what it selected. Default review intensity is `gate` when the target is ambiguous or the runner is called directly without a selected intensity. Use lower intensity only through the explicit policy below, not as an unreported fallback.

| Intensity | Use For | Claude/Codex Effort | Grok Effort |
| --- | --- | --- | --- |
| `planning` | Queue discovery, task prioritization, low-risk strategy brainstorms | `high` | `max`; `reasoning_effort=high` |
| `gate` | Pre-merge diff critique, launch/readiness checks, normal blocking reviews | `xhigh` | `max`; `reasoning_effort=high` |
| `critical` | Schema, security, auth, privacy, deploy, live-data, API contract, provenance, point-in-time, weak/conflicting verification | `xhigh` | `max`; `reasoning_effort=high` |

Planning intensity is an approved mode for recursive task discovery and prioritization. It is not a downgrade. Gate and critical reviews remain xhigh for Claude and Codex/GPT.

## Review Modes

Choose one focused mode before building context:

| Mode | Use For | Context Bias |
| --- | --- | --- |
| Strategy Review | Product direction, architecture, schema, roadmap, core tradeoffs | Docs, data models, core modules, representative tests |
| Data/Schema Review | Database design, extraction schemas, event/object semantics, versioning | Models, migrations, schemas, ingestion/extraction/analytics |
| Diff Critique | Recent code changes or PR-like review | `git diff`, touched files, related tests |
| Launch Readiness | Production or deployment readiness | Deployment docs, config templates, health/ops, auth boundaries, tests |
| Coverage Audit | Whether tests prove important behavior | Test files, coverage output if already available, high-risk modules |
| Deciding Vote | Compare plausible designs | Option summary, constraints, files that prove tradeoffs |

Prefer targeted subsystem reviews over one giant whole-repo prompt.

## Evidence Scope

Auto-select evidence scope from the user's request before running reviewers. Always pass the selected scope with `--review-scope`; do not rely on the runner's `auto` default except as a fail-closed fallback.

| Scope | Use For | Reviewer Evidence Policy |
| --- | --- | --- |
| `strict` | Diff critique, implementation correctness, security boundaries, launch readiness, data/schema, coverage audits, secrets-adjacent reviews | Supplied context only; no web/external sources |
| `broad-repo` | Architecture or repo-wide reviews where missing internal context is the main risk | Broader curated repo context; no web/external sources |
| `strategy-open` | Open-ended product, roadmap, architecture tradeoffs, adoption, or planning questions | Supplied context plus external knowledge/source research where a reviewer runtime safely supports it |
| `web-research` | Current facts: vendor/API/library behavior, pricing, regulation, market/news, competitor state, model/CLI capability changes | Supplied context plus external web/source research where a reviewer runtime safely supports it; cite sources |

Force `strict` for security-boundary, secret, deploy, schema-migration, production-readiness, bug/regression, or PR/diff reviews unless the user explicitly asks for external research and the added risk is justified. For strategic/current-info questions, prefer `strategy-open` or `web-research` so independent reviewers can reduce Codex's single-curator blind spot. Label external findings separately from repo-grounded findings.

## Tool Policy

Humans do not need to specify tool flags. The agent infers tool policy from evidence scope and reports what it selected. Tool access is fail-closed.

| Tool Policy | Applies To | Reviewer Tool Access |
| --- | --- | --- |
| `context-only` | `strict`, `broad-repo`, and fallback `auto` | curated context only; no web, no local repo browsing, no write/action tools |
| `web-allowed` | `strategy-open`, `web-research` | web/source research only where a reviewer runtime has a verified safe toggle; no local repo browsing, no write/action tools |

Never allow reviewer write/action tools. Do not let reviewers browse local files beyond the curated context bundle. Claude tools may be enabled only in `web-allowed` scope through an explicitly verified `PEER_REVIEW_CLAUDE_TOOLS` allowlist. Grok web search is enabled only in `web-allowed` scope. Codex/GPT remains read-only in an empty temporary cwd. Gemini remains sandboxed/plan-mode where supported.

## Workflow

1. Define the review target.
   - Identify project goal, milestone, review mode, evidence scope, review intensity, tool policy, and focus areas.
   - If the user does not specify reviewers, use the default roster: Claude, Codex/GPT, and Grok Build.
   - If the user requests a subset, pass it with `--reviewers claude`, `--reviewers gpt`, `--reviewers claude,gpt`, etc.
   - Select intensity yourself. Do not require the user to add flags. Use `--intensity planning` for task discovery and prioritization. Use `--intensity gate` for pre-merge/readiness reviews. Use `--intensity critical` for the critical triggers above.
   - Select tool policy from review scope. Do not require the user to add tool flags.

2. Curate context.
   - Include tracked docs, source files, configs, and tests that directly support the review.
   - Never include `.env`, credentials, private keys, tokens, runtime logs, local DBs, caches, build outputs, or unrelated user files.
   - Inspect selected files first when practical:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/build_review_context.py" --list README.md docs src tests
```

   - If the helper reports `total byte limit reached`, first narrow the selected paths. For a targeted cross-file review, raise limits with `--max-total-bytes 1500000`, `--max-bytes-per-file 150000`, or `PEER_REVIEW_MAX_TOTAL_BYTES` / `PEER_REVIEW_MAX_BYTES_PER_FILE`.
   - Add `--allow-untracked` only for newly created non-secret docs/code that you have inspected.
   - The context helper fails closed outside git by default. Use `--allow-non-git-context` only after inspecting the selected paths.
   - The context helper aborts on common secret/token content patterns. Redact the value or use `--allow-secret-like-content` only after manual inspection.
   - If files are omitted by total byte limits, the helper now emits an in-band `CONTEXT OMITTED` marker that reviewers can see.

3. Preflight the local reviewer roster.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" --preflight
```

   - The response must include all requested participants, selected intensity, CLI versions, requested models, requested efforts, effort-status caveats, and unavailable/auth-failed reviewers.
   - Grok may be installed but unauthenticated. Report that as unavailable for the run until `grok login` or supported xAI auth is configured.
   - Gemini CLI currently exposes `--model` but no clear thinking-effort flag in `gemini --help`; by default use the local CLI default model and report Gemini effort as `not-cli-exposed` unless the installed CLI proves otherwise.
   - Preflight proves local CLI/model metadata, not a full paid review. A run may still fail on provider-specific runtime requirements; report those failures plainly.

4. Refresh reviewer CLIs and default-model evidence only when explicitly asked.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/refresh_peer_review_clis.py"
```

   - This is a manual maintenance command, not part of normal peer-review execution.
   - It checks installed CLI versions, package-manager latest versions where possible, local model catalogs, and current default effort evidence.
   - It prints proposed default changes but does not rewrite `SKILL.md` or `run_peer_review.py`.
   - Run `--update` only when the user explicitly asks to update CLIs. Add `--install-missing` only when the user explicitly asks to install missing supported CLIs.
   - Use `--no-online` when package registry/Homebrew checks are not wanted.

5. Run independent reviewers with one neutral prompt and one shared context bundle.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" \
  --mode "Diff Critique" \
  --review-scope strict \
  --intensity gate \
  --milestone "current milestone" \
  --focus "correctness bugs and behavioral regressions" \
  --focus "missing tests and security boundaries" \
  README.md src tests
```

   - The runner keeps outputs separate and does not show one model's answer to another.
   - The runner runs independent reviewers in parallel by default, up to `--jobs 4` or `PEER_REVIEW_JOBS`. Use `--jobs 1` for sequential debugging.
   - Claude runs with tools disabled and no session persistence unless an explicit `PEER_REVIEW_CLAUDE_TOOLS` override is set after verifying the local CLI tool name.
   - Codex/GPT runs in a temporary empty cwd with read-only sandboxing and ephemeral mode.
   - Gemini runs with `--skip-trust`, plan approval mode, and a sandbox where supported.
   - Grok Build always runs with subagents disabled, interactive plan mode disabled, no tool allowlist, and an initialized empty temp git directory. In `strict` and `broad-repo`, web search is disabled and `PEER_REVIEW_GROK_MAX_TURNS` defaults to `32`; in `strategy-open` and `web-research`, the runner omits the web-disable flag and defaults Grok turns to `64` unless overridden.
   - The manifest and summary disclose requested scope, effective scope, selected tool policy, external research policy, and per-reviewer web/tool status. Some reviewers may remain repo-context-only even when external research is requested because their local CLI does not expose a verified safe web-search toggle.
   - By default the run exits nonzero if any requested reviewer fails. Use `--allow-partial` only when a degraded council is acceptable.

6. Synthesize without outsourcing judgment.
   - Group findings into:
     - agreement across reviewers
     - Claude-only
     - Codex/GPT-only
     - Gemini-only
     - Grok-only
     - direct conflict
     - speculative or unverifiable
   - Validate major findings against the repo before acting.
   - Track evidence basis for important findings: `repo-grounded`, `external-source-grounded`, or `speculative`.
   - Treat external-source-grounded findings as leads until Codex verifies local repo impact.
   - Classify each important finding as `accept and fix`, `accept and defer`, `reject with reason`, or `needs user decision`.

7. Implement only the right scope.
   - If the user asked for review only, do not modify files unless the newest request permits it.
   - If the user asked to proceed, apply small, high-confidence fixes and document strategic deferrals.
   - Keep unrelated refactors out.

8. Report the outcome.
   - Include selected review mode, evidence scope, review intensity, tool policy, context selection, and the participant table from the runner.
   - Include what each model actually participated with: CLI version, model, effort, effort-status caveat, web-search status, and tool status.
   - Include strongest agreement, strongest disagreement, accepted/deferred/rejected findings, edits made, and verification results.
   - Separate repo-grounded findings from external-source-grounded or speculative findings.
   - Never paste secrets or raw `.env` values.

## Overrides

Use these env vars for one run:

```bash
PEER_REVIEW_REVIEWERS=claude,codex,grok
PEER_REVIEW_INTENSITY=gate
PEER_REVIEW_CLAUDE_MODEL=opus
PEER_REVIEW_CLAUDE_EFFORT=xhigh
PEER_REVIEW_CODEX_MODEL=gpt-5.5
PEER_REVIEW_CODEX_EFFORT=xhigh
PEER_REVIEW_GEMINI_MODEL=cli-default
PEER_REVIEW_GROK_MODEL=grok-composer-2.5-fast
PEER_REVIEW_GROK_EFFORT=max
PEER_REVIEW_GROK_REASONING_EFFORT=high
PEER_REVIEW_GROK_MAX_TURNS=32
PEER_REVIEW_JOBS=4
```

Set `PEER_REVIEW_CLAUDE_MAX_BUDGET_USD` only when a Claude run needs an explicit `--max-budget-usd` cap; there is no default budget cap.

Do not use a lower model or lower effort than the selected intensity unless the user explicitly approves the fallback. `planning` intensity is an approved lower-intensity mode for planning reviews, not a fallback.

## Context Selection Guide

- Data/schema review: product docs, data model docs, migrations, ORM models, extraction schemas, ingestion/extraction/analytics services, representative tests.
- Architecture review: README, product docs, deployment docs, service entry points, config, dependency manifests, core modules, tests.
- Production readiness: deployment docs, compose/config files without secrets, health/ops endpoints, tests, CI files, security-sensitive code.
- Frontend/product review: product docs, frontend routes/components/styles, API client types, screenshots if available.
- Diff critique: use `git diff --stat`, `git diff --name-only`, relevant touched files, and tests. Do not blindly include generated files or lockfiles unless dependency behavior is under review.

Keep the bundle small enough for each reviewer to reason over. Split by subsystem when context selection becomes noisy.

## Decision Standard

Give the most weight to feedback that is independently raised, file-grounded, relevant to the milestone, reproducible or logically valid, and scoped to the user's goal. Reject speculative feedback, contradicted claims, and complexity that does not pay for itself.
