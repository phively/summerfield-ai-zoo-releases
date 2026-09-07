# Prompt and instruction design

Use this reference for one-time prompts, project or custom instructions, and direct review of supplied instruction text.

## Establish the artifact contract

Identify the requested outcome, intended user, execution environment, supplied inputs, required output, applicable instruction layers, hard character limit, and consequential failure modes.

If the target has a hard limit, treat it as a delivery requirement. For an 8,000-character limit, use 7,600 characters as the default working target unless the user specifies another amount of headroom. Count the complete copy-ready artifact, including headings, whitespace, and examples. Revise any artifact above the hard limit before delivery; do not merely warn that it is too long. Keep commentary, rationale, and placement recommendations outside the artifact.

When file tools are available, validate a saved artifact with `../scripts/check_instruction_length.py`. The script counts Unicode code points as physically stored, including line-ending characters. If exact validation is unavailable, draft conservatively below the working target and label any reported count as an estimate.

## Separate authority before drafting

Inventory the supplied and accessible instruction layers. Classify every proposed rule:

| Rule type | Placement |
| --- | --- |
| Behavior needed for most work in this project or custom-instruction scope | Project or custom instructions |
| One-time fact, input, or requirement | Current prompt |
| Recognizable reusable specialist workflow | Skill |
| Existing platform, repository, plugin, contract, or installed-skill behavior | Omit, unless a narrow local override is required |
| Detailed conditional procedure, schema, rubric, or example | Reference |
| Repeated deterministic transformation or check | Script |

Do not copy the procedures of `research-briefing`, `remember-me`, `skill-creator`, or another installed skill into project instructions. Invoke or reference an existing capability only when the project needs explicit routing; state only the local trigger or override, not the receiving capability's internal workflow. Do not add fallback copies "in case" a skill does not activate. If a required capability is unavailable, report that outside the artifact and design only a user-authorized replacement.

When a supplied instruction set mixes project-wide behavior with a specialized repeatable workflow, separate the components and explain the boundary. Invoke `skill-creator` only if the user wants the specialized workflow implemented as a skill.

## Draft and reduce

1. Preserve the user's meaning, scope, voice, authorization boundaries, and level of formality. Do not turn a narrow request into a generalized system.
2. State observable requirements. For conditional behavior, define the trigger, action, material exceptions, priority, and fallback.
3. Include only project-specific context and behavior that changes execution. Remove generic advice and rules already enforced elsewhere.
4. Consolidate repeated rules under one formulation. Remove contradictions, ambiguous referents, unattainable guarantees, unnecessary examples, and speculative edge cases.
5. Add structure only when it improves execution or verification. Omit empty template sections and avoid headings that merely restate the prose beneath them.
6. Check every factual or evaluative explicit or implicit comparison. Require a stated comparison set and supporting evidence, or rewrite it as the supported absolute property and reasons. Preserve clearly labeled subjective guidance and aesthetic opinion as opinion.
7. Verify that the revision does not silently change authority, introduce unsupported facts, require unavailable tools, or expand the task.
8. Measure the artifact. When reduction is needed, remove duplication and misplaced content before compressing consequential rules. Never meet the limit by dropping an active constraint without reporting the conflict.

## Output behavior

For creation, return the copy-ready artifact first, followed by its validated character count and only material placement notes. For review, diagnose concrete defects before presenting a revision. For a short one-time prompt, do not propose files, skills, plugins, tests, or durable memory unless the user asks or a concrete failure risk warrants them.

Read [project-instructions-template.md](project-instructions-template.md) only when drafting project or custom instructions. Treat it as a selection guide, not a form whose every section must appear.
