---
name: supervised-dev-dispatch
description: Use when the user explicitly asks for supervised parallel development, a goal loop, nonstop or continuous development dispatch, dispatcher/monitor coordination, autopilot-like development with human approval gates, recursive task discovery, or coordinated work across multiple branches/worktrees.
---

# Supervised Dev Dispatch

## Overview

Run a supervised parallel development campaign, not an unrestricted autonomous swarm. The lead owns human communication, task selection, recursive task discovery, worker launch, monitoring, audit, merge readiness, and repo organization; workers own only scoped implementation or audit tasks.

Use this skill only when the user explicitly asks for a coordinated multi-session run, a goal loop, an autopilot-like development loop, continuous dispatch, or parallel work across branches/worktrees.

This is a Codex-native campaign skill. It does not invoke Claude-specific day
skills, goal commands, hooks, Workflows, external-model subagents, or Codex CLI
self-delegation. An external model participates only when the user explicitly
requests that model or peer review in the active task.

Default objective for goal-loop or nonstop prompts: keep making safe, reviewable progress until no useful task candidates remain or the user directs a stop. The default is continuous dispatch with draft PRs, local verification, and ledgered outcomes; it is not automatic peer review, merge, deploy, live-data mutation, or destructive cleanup.

## Operating Model

Default: the current user-facing thread where this skill is invoked is the lead thread. The lead combines communicator, dispatcher, reviewer, and repo organizer responsibilities. Do not create a separate communicator or dispatcher by default. Record the lead thread ID in `RUN.md` when available.

For goal-loop, nonstop, overnight, or long-running unattended runs, keep the current user-facing thread as the lead by default and launch worker lanes from it. Use a separate visible dispatcher/monitor only when the user explicitly asks for split-lead mode, names another dispatcher thread, or a non-interactive automation needs a separate background runner while a user-facing lead path remains clear. Record the reason when split-lead mode is used.

Lead bootstrap: the lead creates the run ledger, records the user-facing lead path, surveys or records defaults, then launches workers from the current thread. Record `Lead mode: single` by default. If split-lead mode is explicitly requested or required, record `Lead mode: split`, the separate dispatcher thread ID/link, and the reason.

If invoked from a non-interactive automation or background context, create a lead handoff note and do not launch workers until a user-facing approval/status path is clear.

Worker execution is separate from lead visibility. The default requirement is an inspectable, isolated worker lane, not necessarily a normal user-owned sidebar session. When the host routes subtasks through delegated Codex worker threads, that is acceptable if each worker has a thread ID or report, an isolated worktree/branch, and ledgered evidence. If the user explicitly asks for sidebar-visible worker sessions, create user-owned/sidebar-visible worker threads when tools and host policy allow; if not, record the fallback before launch.

Record each worker's execution mode in `ACTIVE_WORKERS.md` and outcome summaries:

- `sidebar-visible thread`: a normal user-owned thread visible in the sidebar.
- `delegated worker thread`: an inspectable Codex delegation/subtask thread with an ID, but not necessarily shown as a normal sidebar session.
- `local/subagent fallback`: a non-sidebar local worker or subagent path. Use only when thread creation is unavailable or explicitly allowed, keep it scoped, and record the fallback reason.
- `lead-direct`: the lead did the work in an assigned worktree because launching a worker was unsafe or unnecessary.

Do not say "worker sessions were created" unless they are actually sidebar-visible or user-owned threads. Otherwise say "delegated worker threads" or "worker lanes" and provide IDs/report paths.

| Role | Authority | Must Not Do |
| --- | --- | --- |
| Lead | Talk with the user, maintain queue, launch workers, monitor, review diffs, organize PRs, ask batched questions, record decisions, merge if allowed, clean completed work | Approve from memory, bypass the ledger, touch hard-stop actions without approval, let review debt outrun verification |
| Optional split dispatcher | In explicitly recorded split-lead mode, maintain queue and monitor workers through the ledger | Replace the user-facing lead, ask the user directly unless instructed, touch hard-stop actions without approval |
| Worker | Complete one scoped task in its assigned worktree/branch and report evidence | Spawn sessions, merge, deploy, touch primary checkout, self-approve scope expansion |

The run ledger is the lead-owned durable record for status, decisions, worker evidence, and resume safety. In single-lead mode it is not a shared-memory bridge between lead sessions. In split-lead mode, the lead and optional dispatcher communicate through the ledger. Do not rely on chat memory as the source of truth.

## Start Survey

Ask briefly before dispatching unless the user already answered or the prompt clearly says `use defaults`, `goal loop`, `nonstop`, `overnight`, or `stop when no more tasks to work on`. In those cases, record defaults in `RUN.md` and start.

1. Focus: general highest-priority progress, backend only, performance only, bug fixes, docs, audits, frontend, or another scope.
2. Sources: GitHub issues, open PR debt, repo TODOs, docs/LESSONS, failing tests, agent-proposed tasks, or all of these.
3. Autonomy: open PRs only, merge after lead audit, deploy allowed only with explicit approval, or another level.
4. Restrictions: forbidden paths/actions beyond the defaults.
5. WIP: default maximum 3 useful active worker lanes total. Suggested mix is `2 implementers + 1 auditor/reviewer`; use 3 implementers only when tasks are low-risk, disjoint, and review debt is under control. Running fewer than 3 is correct when only fewer safe, useful, disjoint tasks exist, but record the hold reason.
6. Run style: interactive or continuous/unattended. Use one lead thread by default and `CI-soft draft PR` mode.
7. Standing authorizations, up front: while the user is still present, identify
   the hard-stop approvals this run's plan will predictably need. Resolve
   `.delegate/command-center/CURRENT`, read the active registry's `DECISIONS.md`,
   and record every relied-on standing authorization by central decision ID in
   the run's `DECISIONS.md`. The command-center registry is the sole source of
   standing authorization; a supervised-run decision is run-scoped and cannot
   create one. The lever for more autonomy is more written authorizations,
   never looser gates.

If the user asks for minimal restrictions, keep reversible repo work allowed but preserve the hard stops below.

Default run settings when survey is skipped:

- focus: highest-priority progress toward the repo/project goal
- sources: open PR debt, issues, repo TODOs, source-of-truth docs, lessons, failing tests, worker findings, and any explicitly requested peer-review results
- autonomy: isolated worktrees/branches and draft PRs allowed; merge, deploy, live mutation, destructive cleanup, dependency/lockfile/CI/workflow changes, secrets/auth, and remote branch deletion require explicit approval
- WIP: maximum 3 useful active worker lanes total; suggested mix `2 implementers + 1 auditor/reviewer`; if below cap while ready queued work exists, launch the next safe worker or record the hold reason
- run style: continuous/unattended for goal-loop, nonstop, overnight, or "stop when no more tasks" prompts
- lead mode: single current thread by default; split-lead/separate dispatcher only when explicitly requested or required by non-interactive automation
- CI: CI-soft draft PR mode
- stop condition: no safe useful candidates remain, the user directs stop, tools/auth/environment prevent meaningful progress, or all remaining useful work is blocked by hard-stop approvals
- recursive task discovery: enabled from repo and worker evidence; peer review is manual-only
- effort policy: three classes only: `routine`, `complex`, `critical`; Codex implementer high is the default, lead planning defaults complex/high, and xhigh is reserved for critical work and reviewers

## Hard Stops

These hard stops are minimum dispatch safety rules. They override looser repo-local instructions unless the active command-center registry's `DECISIONS.md` contains a standing exception for the exact case or the user explicitly approves the action in the current thread. A supervised-run decision never creates or expands a standing exception. The machine-wide canonical list lives in the global AGENTS/shared-canon hard-stops block; if this list and that block disagree, the STRICTER rule wins.

Require explicit user approval before:

- production/shared-VM deploys, restarts, scheduler changes, DNS changes, or cloud resource deletion
- secrets, credentials, `.env*`, private keys, or auth setup
- live DB writes, migrations on deployed data, re-extraction/imports, or bulk live-data mutation
- dependency additions, lockfile changes, CI/workflow edits, or supply-chain/auth configuration changes
- bulk deletion, destructive cleanup, force pushes except updating an owned unmerged worker branch
- remote branch deletion, git history rewrite, or cleanup outside run-owned artifacts
- merges or pushes to shared branches
- capital-sensitive or trading/fund-moving systems
- expanding a worker from a narrow task into a new product direction

Any role that hits a hard stop reports it to the lead immediately. The lead records it in `QUESTIONS.md`, links any applicable central decision ID in the run's `DECISIONS.md`, and relays a concise, one-reply request to the user without waiting for other lanes. Resume the affected lane only after the user decides or an exact central decision applies. Do not infer, defer, absorb, or self-approve hard stops.

While a hard-stop question is open, block only the affected lane, branch, deployment, cleanup, or task family. Continue unrelated safe work when it can be isolated cleanly. Do not merge, deploy, clean affected branches, approve affected continuations, or infer approval for the blocked action.

## Command-center authority

When `.delegate/command-center/CURRENT` exists, it contains the absolute path of the active registry directory. That registry's `DECISIONS.md` is the sole authority for standing authorizations and hard-stop exceptions. `HANDOFF.md` indexes active tracks; local track ledgers under `.delegate/ledgers/` reference central decision IDs but never copy their text as authority.

Only the active lead writes the track ledger. Workers report evidence to the lead but must not edit the track ledger. Before a new lead writes, record the leadership handoff in the ledger.

Whenever status, lead, next action, or closeout changes, update `HANDOFF.md` and the track ledger in the same lead operation. If either write fails, treat state as ambiguous and repair both before handoff or resume.

Supervised-run `DECISIONS.md` files remain run-scoped. They may record a current-run choice or cite a central decision ID, but they cannot establish standing authorization.

## Run-ledger authority

The lead owns writes to the central run ledger. In explicitly recorded split-lead mode, the optional dispatcher may also write run-ledger updates. Workers report hard stops, findings, and completion evidence in their assigned thread or an explicitly assigned worker report path; narrow worker permission to edit a run file never permits edits to the command-center registry or track ledger.

## Ledger

Create a run ledger before launching workers. Prefer repo-local scratch paths such as:

```text
.delegate/supervised-runs/YYYY-MM-DD-slug/
```

Use `references/ledger-templates.md` for file templates. Minimum files:

- `RUN.md`: objective, focus, rules, WIP limits, autonomy, hard stops, active registry path, and central decision references
- `TASK_QUEUE.md`: candidates, priority, status, branch, risk class
- `TASK_DISCOVERY.md`: accepted/rejected task ideas from repo scans, workers, and peer-review planning
- `BRIEFS/Txxx.md`: durable worker brief with cwd, branch, allowed paths, forbidden paths, tests, and return format
- `ACTIVE_WORKERS.md`: thread IDs, worktrees, branches, base SHA, current state
- `PROGRESS.md`: concise operator-readable updates
- `QUESTIONS.md`: unanswered user decisions and approvals
- `DECISIONS.md`: user answers with date/time and source session
- `PR_REVIEW.md`: audit, peer-review, verification, merge decision
- `OUTCOMES.md`: business-readable run results, why each task mattered, evidence, remaining gates
- `CLEANUP.md`: worktrees/branches/PRs removed or intentionally kept
- `LESSON_CANDIDATES.md`: durable lessons to consider appending after wrap-up
- `state.json`: optional machine-readable status; markdown files remain authoritative

Treat `docs/LESSONS.md` as durable memory after a run, not the live coordination surface.

Canonical task statuses for ledger tables: `candidate`, `queued`, `planning`, `running`, `blocked-question`, `ready-review`, `needs-fix`, `pr-open`, `completed`, `completed-noop`, `merged`, `cleaned`, `abandoned`. Use `blocked-by` to link a task, lane, or PR to a question ID.

Ledger root guard: before writing briefs, progress updates, or review records, verify the central ledger root is the intended run path under the lead-owned worktree or explicitly approved location. Do not let central ledger writes land in the primary checkout by accident when the lead is operating from another worktree. Use absolute paths for ledger writes when there is any ambiguity, and record the verified ledger root in `RUN.md`.

## Dispatch Rules

Before launching any worker:

1. Read repo instructions and relevant source docs.
2. Inspect current checkout, open PRs, branches, worktrees, and dirty state.
3. Record primary checkout path, branch, and HEAD in `RUN.md`; workers must treat this path as forbidden unless it is their assigned worktree.
4. Record target base SHA and branch in the ledger.
5. Verify the central ledger root is the intended run path. If the lead is in a separate worktree, confirm ledger writes will not land in the primary checkout by accident.
6. Create or verify an isolated worker worktree/branch, preferably with `git worktree add <absolute-worktree-path> -b codex/<task> <base-sha>`.
7. Write a durable `BRIEFS/Txxx.md` with absolute worker cwd, branch, base SHA, primary checkout path, allowed paths, forbidden paths/actions, tests, return format, and hard stops. The brief must name one **primary verifier**: the strongest independent check closest to the surface where the outcome actually matters. Builds and lint are supporting evidence unless they are the real contract under test.
8. Pre-launch brief check: verify the exact `BRIEFS/Txxx.md` path exists, is readable, and is the same absolute path that will be given to the worker.
9. Select and record the worker execution mode before launch: `sidebar-visible thread`, `delegated worker thread`, `local/subagent fallback`, or `lead-direct`.
10. Require the worker to verify its cwd equals the assigned worktree path and branch before any write.
11. Prefer disjoint tasks. If two active workers would touch the same high-conflict file family, queue one instead.

Default worker classes:

- `implementer`: may edit code/docs in assigned scope.
- `auditor`: read-only unless the lead logs a narrow follow-up branch authorization and rechecks hard stops.
- `reviewer`: peer-review/diff critique only; never mutates repo.

Every implementation brief must include this anti-cheating clause: do not
weaken or skip tests, narrow the scope, hide failures, or swap in mocks/stubs
to satisfy the done-when; surface the blocker instead, report exact verification
commands with key output, and disclose any mocks/stubs touched.

Launch replacements continuously while there are safe, useful task candidates and active worker capacity. If active workers are below the WIP limit and a queued ready task exists, the lead must either launch it or record a hold reason in `TASK_QUEUE.md` and `PROGRESS.md` before the next checkpoint.

Default `CI-soft draft PR` mode:

- continue launching only disjoint, conflict-aware tasks that can open draft PRs or produce read-only audit results
- require local verification before opening code PRs; require peer-review evidence only when the user explicitly requested peer review in the active task
- record hosted CI as `not executed` or `external blocker` rather than treating it as passed
- do not merge, deploy, clean up merged branches, edit CI/workflows, or override hard stops without explicit user approval
- do not stop solely because of draft PR count, hosted CI failure/unavailability, or an unanswered question that affects only one isolated lane

Default stop condition: stop only when no safe useful task candidates remain, the user directs a stop, tools/auth/environment prevent meaningful progress, or all remaining useful work is blocked by hard-stop approvals. If the user wants PR-count, CI, conflict, time, or risk caps, record those run-specific guardrails in `RUN.md`.

Docs-only exact-sync or read-only audit outputs count in `OUTCOMES.md`.

## Effort And Review Intensity

Use three effort classes. Do not create a larger taxonomy during a run.

| Class | Default Effort | Peer-Review Intensity | Use For |
| --- | --- | --- | --- |
| `routine` | implementer high | none unless explicitly requested | scoped implementation, docs, focused bugfixes with clear tests |
| `complex` | lead/implementer high | manual only | task selection, ambiguous implementation, shared behavior, multi-file changes |
| `critical` | lead xhigh | manual only | schema, migrations, auth, security, privacy, public or rights-sensitive surfaces, deploy, shared infrastructure, scheduler, CI/workflows, extraction/import, provenance, point-in-time correctness, broad refactors, API contracts, merge/readiness decisions, weak or conflicting verification |

Before launching each worker, record `Effort class`, `Requested effort`, and `Reason` in the worker brief. If the host does not expose a mechanical effort control for worker threads, treat the recorded effort as a prompt-level instruction and record that caveat.

Do not invoke `peer-review` based on these effort classes. If the user explicitly requests peer review, default to `planning`/`high`; use `gate`, `critical`, `xhigh`, or `max` only when the request explicitly names it.

## Recursive Task Discovery

The lead should keep the queue replenished from current state, not from a stale initial plan. Use these sources in priority order:

1. explicit user focus and current run decisions
2. blocking findings from completed workers and PR reviews
3. repo instructions, current source-of-truth docs, `docs/LESSONS.md`, open issues/PRs, failing tests, TODOs, and recent diffs
4. suggestions from any peer review the user explicitly requested
5. lead-proposed tasks from gaps found while auditing

Do not run a planning council automatically. When the user explicitly requests a planning peer review, use the named reviewer and effort. If the request does not name either, use the configured default reviewer at planning effort with no fallback. Otherwise no reviewer is selected or invoked. The lead validates, ranks, accepts, rejects, or defers suggestions before adding them to `TASK_QUEUE.md`; reviewers never assign workers directly. Record the inputs and decisions in `TASK_DISCOVERY.md` only for a review that actually ran.

## Skill Routing Policy

The lead owns skill selection. Each worker brief should name required, optional-trigger, and forbidden skills when skill use matters.

- `Required`: skills the worker must read and follow before task action.
- `Optional triggers`: skills the worker may use only if their trigger condition appears during the scoped task.
- `Forbidden`: skills or tools the worker must not use.

Workers must not use `supervised-dev-dispatch` or any skill/tool that launches additional sessions unless the user explicitly authorizes nested dispatch in `DECISIONS.md`. Workers do not broaden scope just because a skill suggests more work; they report findings or candidate tasks back to the lead.

Default routing guidance:

- implementation or bugfix: capture a failing test or reproducible characterization when practical; diagnose unexplained failures before editing
- isolated branches/worktrees: follow the shared Git isolation and ownership rules
- ambiguous scoped work: write a bounded plan with explicit verification and stop conditions
- before claiming completion: run the strongest relevant verification and report the observed evidence
- branch finalization or cleanup: follow the shared Git delivery and hard-stop rules
- frontend visual or behavioral changes: `build-web-apps:frontend-testing-debugging`, `playwright`, and/or `web-design-guidelines`
- security-sensitive changes: `codex-security:security-diff-scan` or `codex-security:security-scan`
- GitHub PR comments, PR hygiene, or CI failures: relevant `github:*` skills
- auditing AI-shaped code, writing, or UI: `audit-ai-code`, `audit-ai-writing`, or `audit-ai-frontend`

## Peer Review Policy

`peer-review` is manual-only for the lead and every worker. A worker brief cannot authorize it unless the user's explicit request is quoted or referenced from the active decision registry. Risk, readiness, merge intent, queue depth, weak verification, or a reviewer role does not trigger it. When the user requests review, use only the named reviewer, mode, intensity, and fallback; unspecified manual reviews use the configured planning default with no fallback. Reviewer sessions remain read-only, and the lead validates their findings against repository evidence.

## Worker Continuation

The lead may approve a worker to continue with next steps in the same session only when all are true:

- same branch and worktree
- same product area and risk class
- same verification path
- no new hard-stop action
- no forbidden path expansion
- update recorded in `ACTIVE_WORKERS.md` and `PROGRESS.md`

Otherwise create a new task in `TASK_QUEUE.md`.

## Worker Lifecycle And Replacement

The lead should keep up to the active worker limit running while safe useful work remains. This means "up to 3 useful workers" by default, not exactly 3 workers at all times.

Active worker count includes lanes in `planning`, `running`, or approved same-session continuation. A worker that has returned a final report no longer counts as active after the lead updates the ledger to `ready-review`, `completed`, `completed-noop`, `pr-open`, `abandoned`, or `blocked-question`.

When a worker finishes, the lead must update `ACTIVE_WORKERS.md`, `TASK_QUEUE.md`, `PROGRESS.md`, and `OUTCOMES.md` before launching a replacement worker, opening a PR, or making review/merge decisions. If the finished worker produced a code branch, also update `PR_REVIEW.md` before packaging or merging.

Replacement launch rule: after ledger update, the lead may launch a new worker if active workers remain below the WIP limit, the new task is disjoint from unreviewed code branches, and no hard-stop or user question blocks that lane. If active workers are below the cap but a ready task is not launched, record the reason.

Review-debt throttle: completed code branches waiting for lead review count as review debt, not active workers. Do not launch more implementation workers when more than one code branch is awaiting lead review unless the remaining workers are read-only auditors/reviewers or the user explicitly relaxes the throttle in `DECISIONS.md`.

## Monitoring Loop

Poll workers on a steady cadence. Each poll should update the ledger with:

- current status: `queued`, `planning`, `running`, `blocked-question`, `ready-review`, `needs-fix`, `merged`, `cleaned`, `abandoned`
- execution mode and visibility/fallback when it changes or was missing
- branch/worktree cleanliness
- tests run and key result
- PR URL, if opened
- blockers and next action

If a worker edits the primary checkout, wrong branch, wrong ledger root, or a missing/wrong brief path is discovered, stop the affected lane, preserve user work, move or discard only run-created changes after inspection, and record the incident in `PROGRESS.md` and `LESSON_CANDIDATES.md`. The incident note should say what happened, whether the primary checkout stayed clean, what correction was made, and what remains blocked.

## Review, Merge, Cleanup

Workers' claims are not final. The lead must independently review before merge:

1. Read the final worker report and final candidate diff.
2. Verify branch freshness against target base.
3. Run relevant tests. If verification is not possible, mark `needs user decision`; do not auto-merge.
4. If the user explicitly requested peer review, run it against the final candidate diff and verification evidence according to the Peer Review Policy above; otherwise continue with the lead's own diff audit.
5. Classify findings: fix, defer, reject, or needs user decision.
6. Merge only if `RUN.md` specifies the target branch, merge method, required approval level, and cleanup permission, and all gates are satisfied. Default merge permission is `approval required` unless the user approves it in the current thread and the run records that decision, or an exact active-registry decision ID grants it and the run cites that ID.
7. After merging, run an integration check on the target branch when the merge changes code or shared contracts.
8. Remove only completed local worker worktrees/branches after merge containment is proven and `RUN.md` allows local run-owned cleanup. Remote branch deletion, destructive cleanup, and cleanup outside run-owned artifacts require explicit approval.
9. Preserve unrelated dirty state and abandoned branches unless the user approves cleanup.

Merge containment is proven when the target branch contains the merged PR/commit, the worker branch has no unique intended changes left outside the merge, required post-merge checks passed or were explicitly user-waived, and `PR_REVIEW.md` records the evidence.

For repo cleanup, restrict cleanup to work produced by the run unless the user explicitly expands scope.

## Outcome Documentation

Update `OUTCOMES.md` whenever a task reaches `completed-noop`, `completed`, `pr-open`, `merged`, `abandoned`, or `blocked-question`. This file is for the operator, not for internal traces. It should answer:

- what was done
- why the task was chosen
- how the repo/product is better off
- what evidence proves the result
- what remains blocked or risky

Use concise tables. Prefer links to PRs, branches, files, tests, peer-review outputs, and ledger entries over raw logs.

At each checkpoint and final response, the lead should print a compact outcome summary in this shape:

```markdown
## Supervised Run Checkpoint

Net result: <one sentence>
Current gate: <none | question | CI | review | merge | deploy>

| Output | Why it mattered | Evidence | Next gate |
| --- | --- | --- | --- |
| <task/PR> | <business/product/repo value> | <tests/PR/review> | <next> |

Questions needing you:
- <question or none>

Next lead move:
- <one next action>
```

## Communication

The human-facing lead should answer from `OUTCOMES.md`, `PROGRESS.md`, `QUESTIONS.md`, `DECISIONS.md`, and `PR_REVIEW.md`, not from worker chat summaries alone.

When the user asks for status, lead with:

- active workers and states
- completed/merged work
- why the completed work matters
- questions needing user decision
- risks or blocked items
- next lead action

## Common Failure Modes

| Failure | Prevention |
| --- | --- |
| Worker edits primary checkout | Isolated worktree check before launch; monitor branch cleanliness |
| Brief path missing or unreadable | Pre-launch brief check verifies the exact absolute path before worker start |
| Ledger writes land in wrong checkout | Ledger root guard verifies the intended run path before any central ledger write |
| Active workers stay below cap without explanation | Launch queued ready work or record a hold reason in `TASK_QUEUE.md` and `PROGRESS.md` |
| Many workers create review debt | Keep opening draft PRs only with local verification and OUTCOMES entries; include peer review only when explicitly requested; do not merge or clean up without approval |
| More code branches finish than the lead can review | Review-debt throttle allows only one unreviewed code branch before new implementers pause; use read-only auditors/reviewers instead |
| Worker keeps expanding scope | Same-scope continuation rule; otherwise queue new task |
| Hard-stop approval buried in chat | `QUESTIONS.md` and `DECISIONS.md` only; continue unrelated lanes when safe |
| Green worker tests hide bad diff | Lead diff audit and rerun tests; add peer review only when the user explicitly requests it |
| Cleanup removes user work | Cleanup only run-owned worktrees/branches; preserve unrelated dirty state |
| Continuous run stops too early | Use recursive task discovery and continue until no safe useful candidates remain or the user directs stop |
| User cannot tell why work mattered | Maintain `OUTCOMES.md` and print checkpoint summaries from it |

## Wrap-Up

At the end of a campaign:

1. Ensure all workers are merged, queued, abandoned, or explicitly parked.
2. Clean run-owned merged branches and worktrees.
3. Update `CLEANUP.md`, `PROGRESS.md`, and `OUTCOMES.md`.
4. Move durable lessons from `LESSON_CANDIDATES.md` into the repo lesson ledger only when appropriate and allowed by repo rules.
5. Report final status to the user with outcome value, merged/open PRs, verification, cleanup, remaining risks, and unanswered questions.
