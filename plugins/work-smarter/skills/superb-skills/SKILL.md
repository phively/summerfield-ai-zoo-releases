---
name: superb-skills
description: Design, refine, review, and test prompts, project or custom instructions, skills, multi-skill plugins, inter-skill contracts, and evaluations. Use for instruction-package architecture, placement, concise authoring, trigger design, or observed reliability failures. Do not use for ordinary content editing or software packaging unrelated to instruction systems.
---

# Superb Skills

Build reliable instruction packages with explicit authority, progressive disclosure, and observable tests.

## Route the work

1. Identify the requested outcome, target platform, supplied artifacts, behavior to preserve, applicable limits, and consequential unknowns. Ask only questions whose answers could materially change the result.
2. Select the smallest applicable workflow:
   - Read [instruction-design.md](references/instruction-design.md) for one-time prompts, project or custom instructions, or direct review of supplied instruction text. When drafting project or custom instructions, also read [project-instructions-template.md](references/project-instructions-template.md).
   - Read [plugin-architecture.md](references/plugin-architecture.md) for a plugin, multiple coordinated skills, manifests, inter-skill contracts, shared resources, packaging, or publication readiness.
   - Invoke `skill-creator` and follow its current conventions whenever creating, revising, validating, installing, or packaging an individual skill. Do not duplicate its platform-specific implementation procedure here.
   - Read [evaluation.md](references/evaluation.md) when comparing architectures, testing activation, diagnosing an observed failure, or determining whether a revision improved behavior.
   - Read [working-memory.md](references/working-memory.md) only when persistent current state must survive extended work or conversation boundaries, multiple workflows need one current authority, meaningful history must remain reconstructable, or state drift would create material risk. Do not create persistent working-memory files by default or read the reference when this gate fails.
3. Use every applicable workflow for mixed requests, but load no reference merely because it exists.
4. Identify external claims that could materially affect the package. Use `research-briefing` through the canonical [handoff contract](../../shared/handoff-contracts.md) only when those claims require verification. Do not invoke it for stylistic editing, deterministic transformation, or direct analysis of supplied text that needs no factual validation.
5. Consult `remember-me` through the same contract only when the user asks to apply stored personal context or missing durable context would materially change a discretionary design choice. Never copy its retrieval, storage, or lifecycle procedure into the output, and never silently change durable memory.
6. Implement the smallest complete change, validate the affected structure and behavior, and report material decisions, results, and unresolved limitations.

## Keep one authority

Before drafting, inventory the supplied and accessible instruction layers that govern the result. Classify each candidate rule by its narrowest reliable home:

- project or custom instructions for behavior relevant to most conversations in that scope;
- a skill for a reusable specialized workflow with a recognizable user goal;
- a plugin-level contract for coordination among bundled capabilities;
- a conditional reference for detailed procedures, schemas, rubrics, examples, or source material;
- a script for fragile or repeated deterministic work;
- the current prompt for one-time facts and requirements; and
- a working briefing or historical record only when the working-memory gate passes.

Do not reproduce platform behavior, repository instructions, installed-skill procedures, plugin contracts, or another authoritative rule unless the target needs an explicit local override. State an override narrowly and identify what it changes. A routing sentence is not permission to summarize the receiving skill's workflow.

When a supplied package contains duplicate or conflicting authorities, preserve the user's intended behavior while consolidating the rule into one owner. Never create a new skill, file, or storage tier solely for symmetry.

## Package rules

- Write concise, direct, imperative, testable rules.
- Define the trigger, action, important exceptions, priority, and fallback for conditional behavior.
- Put activation conditions in skill descriptions and conditional detail in the body or routed references.
- Preserve user meaning, scope, authorization boundaries, useful behavior, and backward compatibility unless a genuine conflict requires a documented change.
- Never invent requirements, preferences, evidence, platform capabilities, tool results, or missing content.
- Match specificity to operational risk. Preserve judgment for variable work; use strict procedures or scripts for fragile repetition.
- Prefer one owner plus references over synchronized prose copies.

## Validate behavior

For a new architecture or a material boundary change, establish a baseline and compare candidates with the same prompts and scoring rules. Test direct, indirect, ambiguous, mixed, and negative routes; unavailable dependencies; authority leakage; output limits; and preservation of supplied requirements. Prefer the simpler architecture unless a split produces a clear measurable improvement that exceeds its added routing and maintenance cost.

Lead with the completed artifact or recommendation. Keep explanations outside copy-ready instruction text and limit them to material changes, placement decisions, validation results, and unresolved risks.
