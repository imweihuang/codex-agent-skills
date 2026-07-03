---
name: gpt-peer-review
description: Use when the user explicitly asks Codex to ask GPT, GPT-5.5, OpenAI, Codex, or another GPT reviewer for a peer review, code audit, architecture review, schema review, production-readiness review, red-team critique, candid feedback, or second opinion.
---

# GPT Peer Review

This is a compatibility entry point for GPT-only peer review. Use the unified `peer-review` workflow with the reviewer roster restricted to Codex/GPT.

Default GPT settings:

- CLI: `codex`
- Model: `gpt-5.5`
- Effort: `xhigh`
- Sandbox: read-only
- CWD: temporary empty directory
- Session: ephemeral

Do not silently downgrade to an older GPT model or lower effort. If Codex CLI, GPT-5.5, auth, or xHigh reasoning is unavailable, report that clearly and ask before using a fallback.

Run preflight:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" --reviewers gpt --preflight
```

Run review:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/run_peer_review.py" \
  --reviewers gpt \
  --mode "Diff Critique" \
  --milestone "current milestone" \
  README.md src tests
```

Follow the unified `peer-review` safety model: curate only relevant non-secret context, keep the external reviewer away from the repo filesystem, validate findings against the repo, then report the participant table, accepted/deferred/rejected findings, edits made, and verification results.
