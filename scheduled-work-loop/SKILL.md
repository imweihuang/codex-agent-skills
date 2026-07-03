---
name: scheduled-work-loop
description: Use when the user asks Codex to create, design, update, or clarify a recurring scheduled workflow, loop, monitor, follow-up, scheduled task, scheduled message, heartbeat, cron automation, reminder, or repeated check.
---

# Scheduled Work Loop

## Overview

Turn recurring work requests into the right Codex scheduler object. First decide whether each run can start fresh or whether the next check needs this thread's context; then create the scheduled workflow with a short durable prompt.

## Scheduler Choice

| Use | When | Automation kind |
|---|---|---|
| Scheduled Task | Each run can start from the repo, files, web, tools, inbox, database, or another durable source without relying on this thread's conversation history. Long-running monitors should usually be here, with state stored outside the thread if comparison is needed. | `cron` |
| Scheduled Message | The next check must continue this exact thread: unresolved discussion, active checkpoint, pending answer, current investigation state, or "check back later here." Prefer this for short follow-ups, especially under one hour. | `heartbeat` |

If the task needs prior-run state, ask where that state should live unless the request already implies it. Use a Scheduled Task if the state can be stored in a durable artifact, label, file, database, issue, report, or existing system. Use a Scheduled Message only when the thread itself is the necessary state.

## Workflow

1. Infer the recurring job from the current request and conversation.
2. Decide Scheduled Task versus Scheduled Message before asking questions.
3. Ask only for missing answers that materially change the workflow:
   - What should Codex do each time?
   - How often should it run?
   - What change is important enough to report?
   - When should it stop?
   - When should it ask the user for input?
4. Search for and use the `automation_update` tool if it is not already available. Never hand-write raw scheduler directives or show raw recurrence strings to the user.
5. Prefer updating a matching existing automation over creating a duplicate. Inspect existing automations when the request sounds like an update or replacement.
6. Create the automation after the material fields are known. Use the scheduler tool's `suggested_create` or `suggested_update` mode when it requires user review for worktree setup, high-risk changes, or unclear local environment setup.
7. Report the created or updated workflow in plain language: Scheduled Task or Scheduled Message, schedule in local-time terms, what it will report, stop condition, and input gates.

## Inference Defaults

- `What to do`: Use the user's stated action. Preserve project/repo names, paths, source systems, and safety constraints from the conversation.
- `How often`: Use explicit timing from the user. If absent, ask. Convert relative dates into concrete local dates before scheduling.
- `Report threshold`: For monitors, default to reporting important changes, failures, blockers, or user-actionable deltas, not "no change" noise. For work runs, report completion status, blockers, and any created artifacts.
- `Stop condition`: If the user clearly wants an ongoing monitor, encode "continue until disabled." If there is a natural finish line, encode it. Ask when stopping changes cost, risk, or noise.
- `Ask for input`: Default to asking before destructive actions, spending money, changing DNS, modifying shared/prod infrastructure, touching capital-sensitive systems, using secrets, sending external messages, merging, deploying, or choosing between materially different options.

## Prompt Requirements

The scheduled prompt must be short, durable, and self-contained:

- State the job, sources to inspect, reporting threshold, stop condition, and input gates.
- Use exact project names, paths, repos, labels, inbox queries, or URLs when known.
- Include timezone for user-facing schedules.
- Avoid "today," "tomorrow," "this thread above," and other references that decay unless creating a Scheduled Message whose purpose is explicitly to continue the current thread.
- Preserve safety rules from the current thread or repo instructions when they affect the run.
- Avoid long transcripts. Summarize only the facts the future run needs.

## Tool Mapping

For a Scheduled Task, create a `cron` automation with workspace fields such as `cwds`, `executionEnvironment`, model, reasoning effort, recurrence, and status.

For a Scheduled Message, create a `heartbeat` automation attached to the current thread when available. The prompt should say what to continue and what answer or check to produce.

Do not create a cron workaround for a thread heartbeat unless the user explicitly asks for a standalone task.

## Examples

User: "Every morning, check GitHub for unresolved review comments and fix what is safe."

Decision: Scheduled Task. Each run can start fresh from GitHub and the repo. Ask only for schedule/report/stop/input fields that are missing, then create a cron automation with guardrails.

User: "In 30 minutes, check whether this deploy we just started finished and tell me here."

Decision: Scheduled Message. The check depends on this thread's active deploy context and should continue here.

User: "Watch this website hourly and tell me if pricing changes."

Decision: Usually Scheduled Task. If no durable comparison state exists, ask where to record the last seen price, or create a task that writes a small state file/report before comparing later runs.

## Common Mistakes

- Asking all five questions even when the conversation already answers some of them.
- Treating every recurring request as a thread follow-up. Use Scheduled Task when fresh runs are enough.
- Treating a thread-dependent checkpoint as a standalone cron job.
- Creating duplicate automations without checking for an existing matching job.
- Writing a long prompt that only makes sense in the original conversation.
- Claiming the scheduled workflow exists before the scheduler tool confirms it.
