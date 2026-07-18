# Ledger Templates

Use these as compact starting points. Keep run files concise and update them as facts change.

## RUN.md

```markdown
# Supervised Dev Run: <slug>

Date: <YYYY-MM-DD>
Repo: <absolute path>
Lead thread: <current invoking thread id by default, or user-named override>
Lead mode: <single by default | split if explicitly requested/required>
Optional dispatcher thread: <none by default | id/link in split-lead mode>
Optional dispatcher reason: <none | user requested | automation/background runner | other recorded reason>
Worker execution policy: <delegated worker threads by default | sidebar-visible worker sessions requested | local/subagent fallback allowed only when recorded | other>
Ledger root: <absolute path to this run ledger>
Ledger root guard: verified; central ledger writes must use this path and must not land in the primary checkout by accident
Central ledger writers: lead only by default; optional dispatcher may write only in split-lead mode; workers only with narrow brief permission
Active command-center registry: <absolute path resolved through .delegate/command-center/CURRENT or none>
Standing authorization source: active registry DECISIONS.md only
Central decision refs: <D-YYYYMMDD-HHMMSS IDs or none>
Run style: <interactive | continuous/unattended>
Single-lead default: yes; separate dispatcher only when explicitly requested or required by automation
Target branch/base: <branch> @ <sha>
Primary checkout path: <absolute path>
Primary branch/head at start: <branch> @ <sha>
Primary checkout rule: workers must not edit this path unless it is their assigned worktree

## Focus
- <scope or "highest-priority progress toward project goal">

## Autonomy
- Branch/worktree creation: allowed
- Worker launch: allowed
- PR creation: allowed
- Merge target: <branch>
- Merge method: <approval required by default | GitHub squash/rebase/merge if explicitly granted>
- Merge allowed: approval required unless explicitly granted by an exact active-registry decision ID referenced in run DECISIONS.md
- Local run-owned worktree cleanup: <allowed after containment | approval required>
- Remote branch deletion/destructive cleanup: approval required
- Deploy/live mutation: approval required
- Hosted CI policy: CI-soft draft PR mode by default; local verification plus peer review may open draft PRs; merge requires run policy plus explicit approval when required

## WIP Limits
- Implementers: <default 2, or 3 only when low-risk/disjoint and review debt is controlled>
- Auditors/reviewers: <default 1>
- Max active worker lanes: <default up to 3 useful active lanes total; lead thread is not counted>
- Under-cap rule: if active workers are below cap and a ready queued task exists, launch it or record a hold reason in TASK_QUEUE.md and PROGRESS.md
- Review-debt throttle: no more than one unreviewed code branch before pausing new implementers; read-only auditors/reviewers may continue
- Replacement policy: when a worker returns a final report, update ledger status before launching a replacement. Completed branches waiting for lead review are review debt, not active workers.
- Stop condition: <default: no safe useful task candidates remain, user directs stop, tools/auth/environment prevent meaningful progress, or all remaining useful work is blocked by hard-stop approvals>
- Extra user-requested guardrails: <none or PR-count/conflict/time/risk caps>

## Recursive Task Discovery
- Peer-review planning: enabled by default.
- Planning mode/scope/intensity: <Strategy Review or Deciding Vote / broad-repo / planning unless stricter scope or critical trigger is required>
- Re-run planning when: <queue has fewer ready tasks than worker capacity, meaningful state changes, or task families are exhausted>
- Task suggestions must be validated by the lead before entering TASK_QUEUE.md.

## Effort Policy
- Effort classes: routine, complex, critical.
- Codex implementer default: routine / high; do not lower mid-sized or large implementation below high.
- Lead planning default: complex / high.
- Peer-review planning intensity: planning.
- Peer-review merge/readiness intensity: gate.
- Critical triggers use xhigh / peer-review critical: schema, migrations, auth, security, privacy, public or rights-sensitive surfaces, deploy, shared VM, scheduler, CI/workflows, extraction/import, provenance, point-in-time correctness, broad refactors, API contracts, merge/readiness gates with weak or conflicting verification.

## Status Values
- candidate
- queued
- planning
- running
- blocked-question
- ready-review
- needs-fix
- pr-open
- completed
- completed-noop
- merged
- cleaned
- abandoned

## Worker Lifecycle
- Active worker states: planning, running, approved same-session continuation.
- Retired from active count after ledger update: ready-review, completed, completed-noop, pr-open, abandoned, blocked-question.
- Before launching a replacement worker, update ACTIVE_WORKERS.md, TASK_QUEUE.md, PROGRESS.md, OUTCOMES.md, and PR_REVIEW.md when code review is pending.
- Pre-launch brief check: verify the exact BRIEFS/Txxx.md path exists and is readable before sending it to a worker.
- Placement incident protocol: record wrong-checkout, wrong-branch, wrong-ledger-root, and missing-brief incidents in PROGRESS.md and LESSON_CANDIDATES.md with cleanup status.

## Hard Stops
- Secrets/.env/credentials
- Production/shared-VM/DNS/cloud mutation
- Live DB writes/migrations/re-extraction/import
- Dependencies/lockfiles/CI workflow changes
- Bulk deletion/destructive cleanup
- Force push except owned unmerged worker branch
- Remote branch deletion or history rewrite: approval required; cleanup outside run-owned artifacts: approval required
- Capital-sensitive systems
- Expanding a worker from a narrow task into a new product direction

## Peer Review
- Planning review: <required for consequential planning/data/architecture decisions | not required>
- Pre-merge code review: required unless RUN.md records a user-approved trivial exception
- Launch/readiness review: required for deploy, shared-VM, scheduler, public launch, or live-readiness decisions
- Worker peer-review authority: <none by default | allowed only as specified in each brief>

## Skill Routing
- Lead selects required, optional-trigger, and forbidden skills per worker brief.
- Workers must not use agent-spawning or dispatching skills unless the user explicitly authorizes nested dispatch in DECISIONS.md.
```

## TASK_QUEUE.md

```markdown
# Task Queue

| ID | Priority | Class | Status | Lane | Branch | Scope | Risk | Blocked By | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T001 | P1 | implementer | queued | <lane> | codex/<branch> | <scope> | <low/med/high> | <Q-ID or none> | <notes, including hold reason if ready but not launched> |
```

## TASK_DISCOVERY.md

```markdown
# Task Discovery

## Current Sources Reviewed
- <repo docs/issues/PRs/tests/lessons/worker outputs reviewed>

## Peer-Review Planning

| Time | Mode | Scope | Intensity | Context | Output Path | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| <time> | Strategy Review | broad-repo | planning | <files/state> | <path> | <accepted/deferred/rejected summary> |

## Accepted Candidates

| Task | Source | Why It Matters | Conflict Risk | Verification Path | Queue Status |
| --- | --- | --- | --- | --- | --- |
| T001 | peer-review / worker / issue | <value> | <low/med/high> | <tests/checks> | queued |

## Rejected Or Deferred Candidates

| Candidate | Source | Decision | Reason |
| --- | --- | --- | --- |
| <task idea> | <source> | rejected/deferred | <reason> |
```

## ACTIVE_WORKERS.md

```markdown
# Active Workers

| Task | Worker | Execution Mode | Visibility | Class | Worktree | Branch | Base SHA | State | Last Check | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T001 | <name/thread-id/report path> | <sidebar-visible thread/delegated worker thread/local-subagent fallback/lead-direct> | <sidebar/readable-by-id/report-only/local> | implementer | <path> | <branch> | <sha> | running | <time> | <next> |

## Steering Log
- <time> T001: <instruction or correction sent>
```

## BRIEFS/T001.md

```markdown
# Worker Brief T001

Thread: <thread id after launch>
Execution mode: <sidebar-visible thread/delegated worker thread/local-subagent fallback/lead-direct>
Visibility/fallback: <sidebar/readable-by-id/report-only/local and reason if not sidebar-visible>
Class: <implementer/auditor/reviewer>
Effort class: <routine/complex/critical>
Requested effort: <medium/high/xhigh or prompt-level if host control unavailable>
Effort reason: <one sentence>
Assigned cwd/worktree: <absolute path>
Branch: <branch>
Base SHA: <sha>
Primary checkout forbidden path: <absolute path>
Worker report path: <thread final report by default, or absolute path if lead assigns one>
Central ledger write permission: <none by default | narrow files/sections allowed>

## Goal
- <one scoped task>

## Allowed Paths
- <paths>

## Forbidden Paths and Actions
- Do not edit the primary checkout.
- Do not spawn sessions or subagents.
- Do not merge, deploy, change secrets, run live writes, or expand scope.
- Do not edit the central run ledger unless this brief explicitly grants narrow ledger write permission.
- <task-specific forbidden paths/actions>

## Skills
Required:
- <skill name and why, or none>

Optional Triggers:
- <skill name>: use only if <condition>

Forbidden:
- supervised-dev-dispatch
- dispatching-parallel-agents
- subagent-driven-development
- any skill/tool that launches additional sessions

## Required First Checks
- Verify `pwd` equals assigned cwd/worktree.
- Verify branch equals assigned branch.
- Verify worktree is clean before edits.

## Verification
- <focused tests/checks>

## Return Format
- completed yes/no
- branch/PR
- files changed
- commands run with key outputs
- risks/blockers
- lesson candidates
```

## PROGRESS.md

```markdown
# Progress

## Current Summary
- Active: <n>
- Active worker limit: 3
- Under-cap hold reason: <none | why a ready queued worker was not launched>
- Ready for review: <n>
- Unreviewed code branches: <n>
- Blocked questions: <n>
- Merged this run: <n>

## Timeline
- <time>: <concise update>

## Placement Incidents
- <time>: <none | wrong checkout/branch/ledger/brief path, primary checkout cleanliness, correction, remaining gate>
```

## OUTCOMES.md

```markdown
# Outcome Summary

## TL;DR
- Net result: <one sentence>
- Current gate: <none | question | CI | review | merge | deploy>
- Operator action needed: <none or concise decision>

## Why This Run Was Useful

| Work | Why We Did It | How The Repo/Product Is Better Off | Evidence | Next Gate |
| --- | --- | --- | --- | --- |
| T001 / PR #123 | <reason chosen> | <operator/product/repo benefit> | <tests/review/PR/link> | <next> |

## Session Outputs

| Task | Worker | Branch/PR | Result | Verification | Remaining Risk |
| --- | --- | --- | --- | --- | --- |
| T001 | <thread id/name plus execution mode> | <branch or PR> | <completed-noop/completed/pr-open/etc.> | <commands/review> | <risk/gate> |

## Decisions Needed

| ID | Decision | Recommended Option | Risk |
| --- | --- | --- | --- |
| Q001 | <decision> | <recommendation> | <risk> |

## Next Best Actions

1. <next action>
2. <next action>
3. <next action>
```

## QUESTIONS.md

```markdown
# Questions For User

Questions are lane-scoped by default. `Blocking Scope` controls what must pause; unrelated lanes may continue when safe.

| ID | Task/Lane | Priority | Question | Options | Blocking Scope | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q001 | T001 / <lane> | high | <question> | <options> | <task/lane/run> | open |
```

## DECISIONS.md

```markdown
# Decisions

Run decisions are run-scoped and cannot create standing authorization. When relying on a standing authorization, cite its central command-center decision ID instead of copying its text as authority.

| Question | Scope | Authority Class | Approved Action | Limits | Central Decision Ref / User Quote | Time | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q001 | <task/lane/run> | <run-scoped/current-thread/central-ref> | <decision/action> | <limits> | <D-ID or quote> | <time> | <notes> |
```

## PR_REVIEW.md

```markdown
# PR Review

| Task | PR | Final Candidate SHA | Diff Reviewed | Verification Evidence Reviewed | Hosted CI | Peer Review | Intensity | Decision | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T001 | <url> | <sha> | yes/no | <commands/results> | <ci-not-run/ci-unavailable/ci-external-blocker/ci-failed-needs-triage/ci-passed> | <mode/result/reused> | gate/critical | merge/defer/fix | <notes> |

Merge requires review of the final candidate diff and its verification evidence, peer review for code changes unless explicitly waived in RUN.md, run-policy approval, and target-branch containment evidence before cleanup. Earlier strategy or architecture advice does not satisfy this review.
```

## CLEANUP.md

```markdown
# Cleanup

## Removed
- <worktree/branch/PR cleanup evidence>

## Preserved
- <dirty/unmerged/unrelated state intentionally left alone>

## Remaining
- <follow-up cleanup or parked work>
```

## LESSON_CANDIDATES.md

```markdown
# Lesson Candidates

- <durable fact/failure/fix future runs can act on>
```
