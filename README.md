# Codex Agent Skills

Reusable Codex skills for practical agent-assisted software work.

This repository contains reusable workflow skills that have been useful across
projects. The focus is on safer reviews, cleaner implementation passes, better
delegation, and durable development workflows.

## Install

Install one skill at a time from the folder URL:

```text
Install the Codex skill from https://github.com/imweihuang/agent-skills/tree/main/peer-review
```

For manual installation:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R peer-review "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Replace `peer-review` with any folder in this repository.

## Skills

### Review and Quality Gates

| Skill | Use when |
| --- | --- |
| `peer-review` | You want independent Claude, Codex/GPT, and Grok CLI review with explicit scope, effort, and tool policy. |
| `claude-peer-review` | You specifically want a Claude-only review through the unified runner. |
| `gpt-peer-review` | You specifically want a Codex/GPT-only review through the unified runner. |
| `claude-gpt-peer-review` | You want independent Claude plus Codex/GPT review. |
| `chatgpt-pro-peer-review` | You want a browser-backed ChatGPT Pro review using your logged-in browser session. |
| `audit-ai-code` | You want to remove AI-shaped backend/general code problems such as duplicate helpers, fixture hacks, brittle tests, or over-defensive control flow. |
| `audit-ai-frontend` | You want to de-slop UI code, component APIs, responsive behavior, accessibility, and design-system drift. |
| `audit-ai-writing` | You want to audit prose for generic LLM tells, weak audience modeling, placeholders, markup issues, or citation problems. |
| `compare-screenshots` | You need objective visual comparison and second-order judgment between UI, game, render, chart, or asset screenshots. |
| `repo-audit-fix-ship` | You want an end-to-end repository quality pass that may include audit, fixes, docs, verification, commit, and push. |

### Development Workflow

| Skill | Use when |
| --- | --- |
| `supervised-dev-dispatch` | You want a lead thread to coordinate parallel worker lanes, task selection, review, and run ledgers. |
| `feature-slicing` | You need to turn risky or multi-step work into independently verifiable slices. |
| `refactor-clean` | A change exposes duplicated concepts, compatibility wrappers, or parallel abstractions that should be consolidated. |
| `gh-commit` | You want to inspect a mixed diff and split it into semantic Git commits. |
| `github-ci-cost-control` | You want to reduce GitHub Actions cost while preserving meaningful PR and main checks. |
| `scheduled-work-loop` | You want to design a recurring Codex task, monitor, reminder, heartbeat, or scheduled workflow. |

### Docs and Artifacts

| Skill | Use when |
| --- | --- |
| `write-docs` | You want README or Markdown docs that explain why and where facts live without mirroring code. |
| `simple-html-artifact` | You want a single-file, information-first HTML report, brief, dashboard, explainer, or static page. |
| `find-skills` | You want help discovering or installing a skill for a specific capability. |

## Peer Review Suite

The `peer-review` skill is the most tool-heavy skill in this repository. It
builds a safe context bundle, runs independent reviewers, and asks Codex to
validate the findings instead of accepting model output blindly.

Default reviewer roster:

| Reviewer | CLI | Default model | Default effort |
| --- | --- | --- | --- |
| Claude | `claude` | `opus` alias, documented in the skill as Opus 4.8 | `xhigh` for gate and critical reviews |
| Codex/GPT | `codex` | `gpt-5.5` | `xhigh` for gate and critical reviews |
| Grok Build | `grok` | `grok-composer-2.5-fast` | `max`; `reasoning_effort=high` |

Gemini is supported by the runner but is opt-in.

Humans do not need to specify the review intensity in normal skill use. The
agent should infer it from the task and report what it selected. The runner also
accepts explicit values:

| Intensity | Use for |
| --- | --- |
| `planning` | Queue discovery, task prioritization, and low-risk strategy brainstorming. |
| `gate` | Pre-merge reviews, readiness checks, and normal blocking reviews. |
| `critical` | Security, schema, auth, privacy, deploy, live-data, API contract, provenance, point-in-time, or weak/conflicting verification decisions. |

Humans do not need to specify tool flags either. Tool policy is inferred from
review scope:

| Tool policy | Applies to | Meaning |
| --- | --- | --- |
| `context-only` | `strict`, `broad-repo`, and fallback `auto` | Curated context only; no web, no local repo browsing, no write/action tools. |
| `web-allowed` | `strategy-open` and `web-research` | Web/source research only where the reviewer runtime exposes a verified safe toggle; no local repo browsing and no write/action tools. |

Preflight local reviewer tools:

```bash
python3 peer-review/scripts/run_peer_review.py --preflight
```

Run a targeted review:

```bash
python3 peer-review/scripts/run_peer_review.py \
  --mode "Diff Critique" \
  --review-scope strict \
  --intensity gate \
  --milestone "current milestone" \
  --focus "correctness bugs and behavioral regressions" \
  README.md src tests
```

## Safety Model

These skills are designed to keep high-agency agent work reviewable:

- Context sent to external reviewers should be curated and minimal.
- Secrets, `.env` files, private keys, local databases, logs, caches, and build
  outputs should stay out of review bundles.
- Reviewer write/action tools should remain disabled unless a skill explicitly
  documents a safe path.
- Automation and parallel development skills should create reviewable branches,
  ledgers, and handoffs rather than merging or deploying without approval.

Always inspect a skill before running it in a sensitive repository. Treat these
as workflow instructions, not a substitute for your own security policy.

## Requirements

Most skills only require Codex skill support and normal repo tools such as Git.
Some skills have optional external dependencies:

- `peer-review`: `claude`, `codex`, and `grok` CLIs for the default reviewer roster.
- `chatgpt-pro-peer-review`: Chrome, the Codex browser control path, and a logged-in ChatGPT Pro session.
- `compare-screenshots`: Node.js and image-processing dependencies used by its helper script.
- `github-ci-cost-control`: Python 3 for the workflow inspection helper.

Each skill folder contains its own `SKILL.md` with the actual operating rules.

## Repository Layout

Each top-level folder with a `SKILL.md` is an installable skill. Some skills
include supporting `scripts/`, `references/`, or `agents/openai.yaml` files.

```text
peer-review/
  SKILL.md
  scripts/
  references/
supervised-dev-dispatch/
  SKILL.md
  references/
tests/
  test_peer_review_scripts.py
```

## Validation

Run the bundled peer-review tests:

```bash
python3 -m unittest tests.test_peer_review_scripts
```

Run a quick public-release scan before publishing changes:

```bash
rg -n "(/Users/|\\.env|API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE)" . -g '!*.pyc' -g '!__pycache__/**'
```

Expected matches include deliberate safety rules and test fixtures. Unexpected
matches should be removed before publishing.

## License

MIT. See [LICENSE](LICENSE).
