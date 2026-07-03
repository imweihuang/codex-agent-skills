---
name: feature-slicing
description: Use when risky or multi-step feature work needs an independently verifiable slice plan, explicit API seams, runnable checkpoints, screenshot gates, reference research, or re-slicing before implementation.
---

# Feature Slicing

Turn a broad feature into a small set of reviewable slices. Each slice should
answer one question, expose one contract, and leave a runnable or inspectable
checkpoint before later slices depend on it.

This skill is for planning or re-planning. Do not treat it as permission to
implement unless the user has asked for implementation in the same task.

## Use When

- A feature has several unknowns, teams, modules, routes, assets, or deployment
  steps.
- A visual, game, dashboard, document, or generated asset needs staged evidence
  instead of one final subjective review.
- A backend or data change needs a stable contract before consumers are ported.
- Implementation starts widening beyond the intended patch and needs to be
  re-sliced before continuing.

Skip this for a small single-file fix where the test, edit, and verification
path are already obvious.

## Principles

1. **Inspect before asking.** Read the repo, existing specs, tests, and runtime
   shape before asking the user questions the code can answer.
2. **Ask only gate-setting questions.** Ask when the answer changes priority,
   risk, approval, product intent, or the first useful checkpoint. Include your
   recommended default so the user can accept or edit it.
3. **Slice at ownership seams.** Each slice should have a named owner: module,
   API, state machine, data contract, route, renderer phase, or test oracle.
4. **Make progress visible.** Each slice should leave something runnable,
   inspectable, or measurable: a test, fixture, route, CLI probe, report,
   screenshot, or workbench.
5. **Research the fog.** If the work depends on a named reference, library,
   public standard, benchmark, or current best practice, research primary
   sources before finalizing the slice graph.
6. **One visual variable per slice.** For visual work, split density, layout,
   silhouette, color, texture, motion, lighting, legibility, and camera framing
   into separate judgment points when they can fail independently.
7. **Keep real approval gates real.** Reversible local taste calls can proceed
   with a documented assumption when the task asks for execution. Destructive,
   production, DNS, shared-infra, secrets, billing, and capital-sensitive gates
   require explicit user approval.

## Workflow

1. **Orient.** Capture the current goal, non-goals, repo constraints, relevant
   files, tests, current failures, and any user-specified approval boundaries.
2. **Clarify.** Ask only the few questions that would materially change the
   plan. If the answer can be safely assumed, state the assumption in the plan.
3. **Research.** Use local docs first. Use current external sources when the
   feature depends on unstable or unfamiliar external behavior.
4. **Draft alternatives.** For a multi-slice feature, compare two or three
   possible slice graphs. Use subagents only when the current environment offers
   them and the work can be split without shared-state risk; otherwise draft the
   alternatives yourself.
5. **Synthesize.** Produce one canonical plan. Record meaningful alternatives
   only when the tradeoff affects risk, cost, timeline, or reviewability.
6. **Fog audit.** Re-read each slice. If it hides multiple variables, broad verbs
   like "make it realistic", unknown external practice, or more than one API
   seam, split it again before implementation.
7. **Materialize if needed.** For multi-slice work, write a spec under
   `specs/feature-slug/` with a README, slice files, assets, and visual evidence
   as appropriate.
8. **Architecture review.** When the plan changes ownership boundaries, use
   `refactor-clean` thinking to confirm the end state has one owner per concept,
   no unnecessary adapters, and explicit removal conditions for temporary seams.
9. **Implement only after the planning gate.** If the user asked for execution,
   proceed slice by slice. If they asked only for a plan, stop with the plan and
   recommended next action.

## Slice Contract

Each slice should state:

- Outcome: what contract or evidence this slice unlocks.
- Owner: the module, route, command, document, or artifact that owns the change.
- Inputs and outputs: data shape, API, UI state, asset, or fixture.
- User-visible checkpoint: what can be run, opened, inspected, or compared.
- Verification: tests, probes, screenshots, metrics, manual checks, or CI.
- Firewalls: files, behaviors, or systems intentionally out of scope.
- Approval gates: anything that must stop for explicit user confirmation.
- Handoff: the next slice that can safely depend on this one.

If a slice cannot be accepted or rejected with one focused artifact, it is still
too broad.

## Spec Folder

Use a single `specs/feature-slug.md` only for a small single-slice plan. Use a
folder for broader work:

- `specs/feature-slug/README.md`: goal, context, slice graph, risks, approval
  gates, current status, and next-agent prompt.
- `specs/feature-slug/slices/NN-short-name.md`: one independently verifiable
  slice per file.
- `specs/feature-slug/assets/`: reference images, fixtures, sample data, and
  captures needed to judge the work.
- `specs/feature-slug/visualizations/`: HTML reports, diagrams, contact sheets,
  harness mockups, and other review artifacts.

The README's next-agent prompt should be direct enough that a fresh agent can
continue without reading the original conversation.

## Visual Gates

For visual or interactive work:

- Define the target in words before comparing images.
- Capture the same viewport, device scale, state, data, route, and camera intent
  when comparing before and after.
- Use `compare-screenshots` when a candidate needs to be judged against a
  baseline, target, reference image, or previous attempt.
- If the target is ambiguous, stop and ask the user. Do not silently treat the
  old screenshot as correct.
- Archive the evidence that decided the slice so later work can tell whether it
  preserved or intentionally changed the visual result.

## Re-Slicing Rule

When implementation starts changing unrelated variables, stop broadening the
patch. Update the spec first: split the slice, freeze inputs, move extra visual
or API variables to later slices, and rewrite the handoff before continuing.
Re-slicing is progress when it prevents a large uncertain patch.

## Done

A sliced plan is done when a fresh agent can start the next slice without the
conversation, the user can review the roadmap without reverse-engineering a wall
of text, and every high-risk gate is explicit.

Adapted from `dzhng/skills` at commit
`2a8e3b8fee57fa401b07e4fe3eae954a187c1a0c`.
