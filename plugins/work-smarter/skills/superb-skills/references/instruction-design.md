# Prompt and instruction design

Use this reference for one-time prompts, project or custom instructions, and direct review of supplied instruction text.

## Workflow

1. Identify the requested outcome, intended user, execution environment, supplied inputs, required output, and consequential failure modes.
2. Preserve the user's meaning, scope, voice, and level of formality. Do not turn a narrow request into a generalized system.
3. Separate one-time task facts from reusable behavior. Keep one-time facts in the current prompt; recommend project or custom instructions only for behavior relevant to most conversations in that scope.
4. State observable requirements. For conditional behavior, define the trigger, action, exceptions, priority, and fallback.
5. Remove redundancy, contradictions, ambiguous referents, unattainable guarantees, and instructions that merely restate higher-priority behavior without adding precision.
6. Add structure only when it improves execution or verification. Do not prescribe a format that conflicts with the user's requested output.
7. Check that the revision does not silently change authority, introduce unsupported facts, require unavailable tools, or expand the task.

## Output behavior

Return the revised text and explain only material changes or placement recommendations. For a short one-time prompt, do not propose files, skills, plugins, tests, or durable memory unless the user asks or a concrete failure risk warrants them.

When a supplied instruction set mixes project-wide behavior with a reusable specialized workflow, separate the components and explain the boundary. Invoke `skill-creator` only if the user wants the specialized workflow implemented as a skill.
