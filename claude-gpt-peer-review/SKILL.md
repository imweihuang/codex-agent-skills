---
name: claude-gpt-peer-review
description: Use when the user asks for both Claude and GPT, dual-model peer review, cross-model review, deciding vote, model council, red-team review, honest feedback from both models, or a higher-confidence second opinion on strategy, architecture, schema, production readiness, code quality, tests, or API contracts.
---

# Claude + GPT Peer Review

This is a compatibility entry point for Claude plus GPT peer review. Use the unified `peer-review` workflow with the reviewer roster restricted to Claude and Codex/GPT.

Default reviewer settings:

| Reviewer | CLI | Model | Effort |
| --- | --- | --- | --- |
| Claude | `claude` | Opus 4.8 via `opus` alias | `xhigh` |
| Codex/GPT | `codex` | `gpt-5.5` | `xhigh` |

Do not silently downgrade either reviewer. If a CLI, model, auth state, or effort is unavailable, report that clearly and ask before using a fallback.

Run preflight:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" --reviewers claude,gpt --preflight
```

Run review:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" \
  --reviewers claude,gpt \
  --mode "Diff Critique" \
  --milestone "current milestone" \
  README.md src tests
```

Follow the unified `peer-review` safety model: use one neutral prompt and one curated context bundle, keep outputs independent until both reviews complete, validate findings against the repo, then report the participant table, agreement, disagreement, accepted/deferred/rejected findings, edits made, and verification results.
