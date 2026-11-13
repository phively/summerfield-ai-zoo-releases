# Project instruction template

Use this template only for project or custom instructions. Select the smallest set of sections that changes execution; omit unused headings and all bracketed guidance.

```markdown
# [Project or instruction-set name]

## Purpose and scope

[What work these instructions govern and any important boundary.]

## Project-specific context

[Stable facts the assistant cannot reliably infer elsewhere. Exclude one-time task inputs and personal facts already owned by an accessible memory system.]

## Required behavior

[Concise, observable rules that apply to most work in this scope.]

## Conditional behavior

[Only conditions that materially change execution. For each: trigger, action, exception or priority, and fallback.]

## Local capability routing or overrides

[Only project-specific routing or explicit overrides. Name what the override changes; do not reproduce another skill's procedure.]

## Completion checks

[Checks needed to determine that work in this scope is complete.]
```

Before delivery:

- remove any section that is empty, generic, one-time, or already authoritative elsewhere;
- keep explanations and design rationale outside the copy-ready block;
- preserve exact consequential constraints;
- validate the complete artifact against its hard limit; and
- for an 8,000-character limit, prefer no more than 7,600 characters unless the user requests different headroom.
