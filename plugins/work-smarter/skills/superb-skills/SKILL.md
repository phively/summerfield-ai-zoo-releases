---
name: superb-skills
description: Design, refine, review, and test prompts and reusable instruction packages, skills, plugins, contracts, and evaluations. Use when a user wants reusable instructions or asks whether an instruction or assistant is reliable, including domain-specific evaluation plans, test cases, scorecards, and reference responses. Skip one-off content rewrites or ordinary use of fixed instructions.
---

# Superb Skills

Build reliable instruction packages with explicit authority, progressive disclosure, and observable tests.

## Respect the operation boundary

Resolve allowed operations before retrieval. Response-only/no-tool requests exclude reads, commands, tests, and writes; use supplied guidance and disclose missing essentials. Registered-read exceptions permit only the exact source, route, verification, and invocation-only wrappers. Apply these boundaries throughout.

## Route the work

1. Identify the outcome, target, artifacts, preserved behavior, limits, and unknowns. Ask only questions that could change the result.
2. Classify the request before acting: planning produces a plan; review reports findings; implementation edits and validates. Do not implement planning or review requests.
3. Select the smallest applicable workflow:
   - Read [instruction-design.md](references/instruction-design.md) for one-time prompts, project/custom instructions, or instruction review; apply its missing-authority and mutable-dependency rules. Also read [project-instructions-template.md](references/project-instructions-template.md) when drafting project or custom instructions.
   - Read [plugin-architecture.md](references/plugin-architecture.md) for a plugin, multiple coordinated skills, manifests, contracts, shared resources, packaging, or publication readiness.
   - Invoke `skill-creator` when creating, revising, validating, installing, or packaging an individual skill. Do not duplicate its platform-specific implementation procedure here.
   - Read [evaluation.md](references/evaluation.md) for evaluation design or behavior checks, including architecture comparisons. Apply its feasibility, input-maintenance, and protected-validation rules, including planning-only obligations.
   - Read [preferences-and-lessons.md](references/preferences-and-lessons.md) for missing preferences, project settings, task overrides, one observed operational mistake with a potentially reusable remedy, recurring mistakes, verified lessons, or unavailable/partial records. Apply its persistence and evidence rules to reusable preference-dependent targets, including standalone targets.
   - Read [working-memory.md](references/working-memory.md) only when persistent current state must survive extended work or conversation boundaries, multiple workflows need one current authority, history must remain reconstructable, or drift creates material risk. Do not create persistent working-memory files by default or read the reference when this gate fails.
4. Use every applicable workflow for mixed requests, but load no reference merely because it exists.
5. Use `research-briefing` through the canonical [handoff contract](../../shared/handoff-contracts.md) only for material external claims requiring verification; omit it for stylistic edits, deterministic transformations, or supplied-text analysis needing no factual validation.
6. Consult `remember-me` through the same contract only for requested personal context or missing durable context that materially affects a discretionary choice. Never copy its retrieval, storage, or lifecycle procedure into the output or silently change durable memory.
7. Complete only that mode; check its applicable design obligations and report material decisions and limitations. Apply consequential constraints to the delivered target instructions or a bounded handoff, not only commentary.

## Keep one authority

Inventory instruction layers before drafting. Choose the narrowest reliable owner: project/custom instructions for scope-wide behavior; skills for reusable workflows; plugin contracts for shared coordination; references for conditional detail; scripts for repeated deterministic work; the current prompt for one-time facts; or briefing/history only after the working-memory gate passes.

Do not reproduce platform behavior, repository instructions, installed-skill procedures, plugin contracts, or another authoritative rule unless the target needs a narrow, identified local override. A routing sentence is not permission to summarize the receiving skill's workflow.

Consolidate duplicate or conflicting authorities while preserving user intent. Never create a skill, file, or storage tier solely for symmetry.

## Package rules

Write direct, testable rules with triggers, actions, exceptions, priority, and fallback. Put activation conditions in descriptions and conditional detail in references. Preserve meaning, scope, authorization, behavior, and compatibility; document necessary changes. Invent no requirements, preferences, evidence, capabilities, results, or missing content. Match specificity to risk and prefer one owner plus references.

## Validate behavior

For new architectures or material boundary changes, compare baseline and candidates under identical prompts and scoring. Apply routed checks for activation, unavailable dependencies, authority leakage, output limits, and preserved requirements. Prefer simplicity unless measured gains exceed routing and maintenance costs.

Surface blockers at their gate: state observed evidence, unknowns, and the smallest resolving action. Fix safe, authorized issues before dependent work; do not block a whole phase while a remedy remains. Request missing input/authority specifically; preserve completed work and resume at the failed gate.

Lead with the artifact or recommendation; keep explanations outside copy-ready text and report only material changes, validation, and limitations.
