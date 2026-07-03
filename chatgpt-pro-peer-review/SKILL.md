---
name: chatgpt-pro-peer-review
description: Use when the user asks Codex to ask ChatGPT, GPT-5.5 Pro, Extended Pro, ChatGPT Pro, or the ChatGPT browser model for peer review, code audit, architecture review, schema review, production-readiness review, red-team feedback, or a browser-only second opinion.
---

# ChatGPT Pro Peer Review

Use this skill for a browser-backed ChatGPT Pro review. This is not a CLI or API reviewer. It uses the user's logged-in Chrome session and must verify the visible ChatGPT model selector before submitting.

Default reviewer:

- Reviewer: `ChatGPT GPT-5.5 Pro`
- Access path: Chrome browser at `https://chatgpt.com/`
- Required visible selector: `Extended Pro` or `GPT-5.5 Pro`
- Default wait limit: 45 minutes, override with `CHATGPT_PRO_BROWSER_TIMEOUT_SECONDS`
- Report label: `ChatGPT GPT-5.5 Pro (manual browser)`

Do not submit the prompt unless the visible ChatGPT selector confirms `Extended Pro` or `GPT-5.5 Pro`. If the selector is missing, shows a lower model, asks for login, blocks on CAPTCHA, or requires user action, stop and report the exact state.

## Workflow

1. Curate safe context.
   - Use the existing peer-review context helper when repository files are needed:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/peer-review/scripts/build_review_context.py" --list README.md src tests
```

   - Never paste `.env`, secrets, credentials, private keys, runtime logs, local databases, caches, unrelated user files, or uninspected untracked files.
   - If context is large, split by subsystem instead of sending one giant browser prompt.

2. Build a compact review prompt.
   - Include review mode, milestone, focus areas, selected context, and output expectations.
   - Ask for concrete, file-grounded findings with severity, risk, smallest fix, and verification.
   - State that ChatGPT must use only the supplied context unless the user explicitly asks for online research.

3. Use Chrome automation.
   - Use the Chrome browser skill, not the in-app browser, because ChatGPT Pro depends on the user's logged-in browser session.
   - Open `https://chatgpt.com/` in a new or selected Chrome tab.
   - Verify the account is logged in and the model selector reads `Extended Pro` or `GPT-5.5 Pro`.
   - Paste the prompt into the composer and submit only after that selector check passes.
   - Wait until generation completes; a visible `Stop answering` control means the answer is still streaming.
   - Extended Pro can think for a long time. Use repeated short poll calls instead of one long browser call. Default maximum wait is 45 minutes (`2700` seconds), overridable with `CHATGPT_PRO_BROWSER_TIMEOUT_SECONDS`.
   - If the answer is still streaming after the wait limit, keep the ChatGPT tab as a `handoff`, report `manual_action_required`, and include the conversation URL so the user can continue or inspect it.

4. Report honestly.
   - Include the observed model selector, conversation URL, whether the browser run completed, and the full participant label.
   - Treat the browser answer as an external lead, not final truth. Validate major findings against the repo before editing.
   - If the run cannot proceed, report it as `unavailable_browser`, `login_required`, `model_not_selected`, `captcha_required`, or `manual_action_required`.

## Prompt Template

```text
You are ChatGPT GPT-5.5 Pro acting as a candid senior peer reviewer.

Review mode: {mode}
Milestone: {milestone}
Focus areas:
1. {focus}

Rules:
- Use only the supplied repository context unless explicitly told otherwise.
- Do not request or infer secrets.
- Prioritize correctness, regressions, missing tests, security boundaries, and launch risk.
- Return actionable findings only.

For each finding include:
- Severity: P0, P1, or P2
- File or area
- Risk
- Smallest safe fix
- Verification needed

Repository context:
{context}
```

## Browser Automation Shape

Use the Chrome extension-backed browser API. A minimal successful pattern is:

```js
await tab.goto("https://chatgpt.com/");
const composer = tab.playwright.getByRole("textbox", { name: "Chat with ChatGPT" });
await composer.fill(prompt);
await tab.playwright.getByRole("button", { name: "Send prompt" }).click();
```

Before the `fill` and `click`, inspect the page and verify the visible model selector says `Extended Pro` or `GPT-5.5 Pro`. Keep the ChatGPT tab as a deliverable if the user may want to inspect the browser conversation.

Polling pattern after submit:

```js
const maxWaitSeconds = Number(process.env.CHATGPT_PRO_BROWSER_TIMEOUT_SECONDS || 2700);
const started = Date.now();
while (Date.now() - started < maxWaitSeconds * 1000) {
  const text = await tab.playwright.evaluate(() => document.body.innerText || "");
  if (!/Stop answering|Stop generating|Stop streaming/.test(text)) break;
  await new Promise(resolve => setTimeout(resolve, 30000));
}
```

Some browser automation calls have their own shorter execution cap, so for very long Extended Pro answers, run this as repeated 30- to 60-second polling calls from Codex rather than a single monolithic wait.
