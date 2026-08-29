---
name: superb-skills
description: Design, refine, review, and test ChatGPT prompts, project or custom instructions, individual skills, multi-skill plugins, inter-skill contracts, and supporting references, scripts, assets, and evaluations. Use when creating or improving these instruction packages, deciding where behavior or durable state belongs, reducing context cost or duplicated authority, validating triggers and failure behavior, or designing working-memory records. Do not use for ordinary content editing or software packaging unrelated to ChatGPT instructions, skills, or plugins.
---

# Superb Skills

Build reliable instruction packages with explicit authority, progressive disclosure, and observable tests.

## Route the work

1. Define the requested outcome, target platform, supplied artifacts, existing behavior to preserve, and consequential unknowns. Ask only questions whose answers could materially change the design; otherwise state limited assumptions.
2. Select the smallest applicable workflow:
   - Read [instruction-design.md](references/instruction-design.md) for one-time prompts, project instructions, custom instructions, or direct review of supplied instruction text.
   - Read [plugin-architecture.md](references/plugin-architecture.md) for a plugin, multiple coordinated skills, manifests, inter-skill contracts, shared resources, packaging, or publication readiness.
   - Invoke `skill-creator` and follow its current conventions whenever creating, revising, validating, installing, or packaging an individual skill. Do not duplicate its platform-specific implementation procedure here.
   - Read [evaluation.md](references/evaluation.md) when designing tests, comparing architectures, validating implicit activation, diagnosing an observed failure, or deciding whether a revision improved behavior.
   - Apply the working-memory gate below. Read [working-memory.md](references/working-memory.md) only if the gate passes.
3. Use every applicable workflow for mixed requests, but load no reference merely because it exists. Preserve one authority for rules shared across workflows.
4. Identify factual or current claims requiring verification. Use `research-briefing` only through the canonical [research handoff contract](../../shared/handoff-contracts.md) when research could materially affect the package. Do not use it for stylistic editing, deterministic transformation, or direct analysis of supplied text that needs no factual validation.
5. Implement the smallest complete change. Preserve useful behavior and backward compatibility unless the user requests otherwise or a genuine conflict requires a change.
6. Validate the affected structure and behavior. Report the artifact inventory, material decisions, results, and unresolved limitations; add concise usage guidance for a new package.

## Use relevant personal context

When stable goals, constraints, collaboration preferences, or output preferences could materially affect package design or review, search accessible library and project sources for `remember-me/index.md` or a clearly equivalent index. Read the index first and retrieve the smallest sufficient set of relevant current context from its summary or identified current source. Expand retrieval when the bounded context is incomplete, stale, ambiguous, conflicting, or lacks consequential detail. Read the canonical [handoff contracts](../../shared/handoff-contracts.md) before accepting personal context or proposing a durable update.

Apply current instructions to the current task without silently changing durable memory. Stored preferences may guide discretionary choices but cannot override factual accuracy, evidence integrity, supported platform conventions, or non-fabrication. If the index is missing or inaccessible, continue with neutral defaults and report the limitation only when material.

## Placement model

Put each behavior or resource in its narrowest reliable home:

- project or custom instructions for behavior relevant to most conversations in that scope;
- a skill for a reusable specialized workflow with a recognizable user goal;
- a plugin-level contract for canonical coordination among bundled capabilities;
- a reference for conditional detail, schemas, rubrics, examples, templates, or source material;
- a script for fragile or repeated deterministic work;
- an asset for output resources not intended as instructions;
- the current prompt for one-time facts and requirements;
- a working briefing for reusable authoritative current state; and
- a historical record for superseded state with continuing explanatory, evidentiary, audit, or restoration value.

Explain a placement decision only when alternatives have material tradeoffs. Never create a new skill or storage tier solely for conceptual symmetry.

## Shared rules

- Write concise, direct, imperative, testable rules.
- Define the trigger, action, important exceptions, priority, and fallback for conditional behavior.
- Put activation conditions in skill descriptions and detailed procedure in the body or conditional references.
- Consolidate overlap; remove contradictions, ambiguity, unsupported requirements, unnecessary edge cases, and uncontrolled duplicate authority.
- Match specificity to operational risk. Preserve judgment for variable work; use strict procedures or scripts for fragile repetition.
- Distinguish user-provided facts, verified facts, source claims, reasonable inferences, hypotheses, unknowns, and recommendations when material.
- For a factual or evaluative explicit or implicit comparison, identify the relevant comparison set and require evidence that supports the comparison. If either is missing, state only the supported absolute property and its reasons. Clearly labeled subjective guidance or aesthetic opinion may use comparative language without empirical comparative evidence.
- Never invent requirements, preferences, evidence, platform capabilities, tool results, or missing content.
- For persistent memory, optimize in strict order: reliable recall of relevant information; fewer tokens to read and update context; then retrieval speed. Never trade a higher-ranked objective for a lower-ranked one.
- Optimize other design concerns jointly for output quality, reliability, context efficiency, maintainability, and execution speed—not token count or modularity alone.

## Working-memory gate

Do not create persistent working-memory files by default. The gate passes only when current state must survive extended or multi-phase work, conversation boundaries or compaction; multiple skills need one authoritative state; reusable decisions or unresolved issues must persist; meaningful history must remain reconstructable; or state drift would create material risk.

Use one current-state file while the record is small and predominantly current. Add history only when separating active from inactive information materially improves retrieval, maintenance, auditability, or reliability. Designate one current authority, read it first, and treat history as subordinate unless the task concerns history.

Protect recall by keeping all decision-relevant current state discoverable and by expanding beyond an index or summary when it is incomplete, stale, ambiguous, conflicting, or lacks consequential detail. Once recall is protected, reduce routine read and update tokens through concise current records, conditional references, and narrow coherent updates. Only then improve retrieval speed with stable headings, identifiers, metadata, or search patterns. Do not load irrelevant context merely to improve recall.

Read [working-memory.md](references/working-memory.md) in full before designing, splitting, updating, auditing, or handing off persistent records. Do not read it when the gate fails.

When creating a persistent-memory system, define measurable lifecycle-review triggers covering thresholds, lifecycle events, integrity failures, and retrieval failures, plus a staged before/after audit that fails closed on unexplained information loss. Treat elapsed time, file size, or change count as a reason to inspect the record, never as sufficient reason to delete, summarize, or split it.

## Long-running work

For extended or multi-phase work, maintain a compact current brief containing the objective, authoritative decisions, active constraints and preferences, unresolved questions, and next action. Refresh it after material decisions, phase changes, long detours, detected drift, or conversation-context compaction, then recheck exact consequential constraints against their authoritative source. Conversation-context compaction does not by itself make a persistent-record audit due; run that audit only when a record trigger is met. Restate exact consequential constraints before an output when older context creates meaningful risk. Skill invocation does not replace current task state.

## Communication

Lead with the answer or recommended action. Be concise and proportional. Avoid routine praise, filler, repeated conclusions, and generic closing offers. Challenge unsupported assumptions with concise reasoning. Apologize only for an actual error or inconvenience, then focus on the correction.
