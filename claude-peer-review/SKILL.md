---
name: claude-peer-review
description: Use when the user explicitly asks Codex to ask Claude, Claude Opus, or Anthropic for a peer review, code audit, architecture review, schema review, production-readiness review, red-team critique, candid feedback, or second opinion.
---

# Claude Peer Review

This is a compatibility entry point for Claude-only peer review. Use the unified `peer-review` workflow with the reviewer roster restricted to Claude.

Default Claude settings:

- CLI: `claude`
- Model: Opus 4.8 via the Claude CLI `opus` alias
- Effort: `xhigh`
- Tools: empty allowlist by default
- Session persistence: disabled
- Budget: no default cap; set `PEER_REVIEW_CLAUDE_MAX_BUDGET_USD` only when a run needs an explicit `--max-budget-usd` cap

Do not silently downgrade to Sonnet, Fable, an older Opus model, or a lower effort. If Claude CLI, Opus 4.8, auth, or `xhigh` effort is unavailable, report that clearly and ask before using a fallback.

Run preflight:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" --reviewers claude --preflight
```

Run review:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" \
  --reviewers claude \
  --mode "Diff Critique" \
  --milestone "current milestone" \
  README.md src tests
```

Follow the unified `peer-review` safety model: curate only relevant non-secret context, keep Claude tools disabled unless the user explicitly approves otherwise, validate findings against the repo, then report the participant table, accepted/deferred/rejected findings, edits made, and verification results.
