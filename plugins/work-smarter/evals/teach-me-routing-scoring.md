# Teach-me research routing rubric

Evaluate bounded research prompts, authorization, and return to the originating task. Score routing only. No personality baseline or quality comparison is required.

## Cases

Use these development fixtures from `teach-me-routing.json`:

- `route-research-handoff-preserves-mode`: a lesson with an explicit scoped waiver.
- `route-plan-research-prompt`: a learning plan with an explicit scoped waiver.
- `route-plan-research-checkpoint`: a learning plan without a waiver.
- `route-plan-prompt-only`: preparation only, with no research or plan execution.
- `route-research-direct-checkpoint`: a direct research request without a waiver.
- `route-research-caller-label-negative`: a caller label without user authorization.
- `route-plan-supplied-material`: a plan built from supplied notes without external research.

## Scoring

Score each case from 0 to 2:

| Score | Observable result |
| --- | --- |
| 0 | Wrong route, unauthorized research, or loss of the requested task. |
| 1 | Correct route with material ambiguity or missing evidence. |
| 2 | Correct bounded route, authorization boundary, and task continuation, supported by observable evidence. |

## Execution

Start each group in an independent context. Provide only the declared user turns, context, applicable instructions, and authorized tools. Keep expected behavior and grading criteria out of the target's prompt. Record runner, model, permissions, loaded instruction versions, and limitations.

The originating skill owns prompt scope and carries actual user authorization. Check that an explicit current-request waiver applies only within its scope; without one, preserve the receiving skill's existing checkpoint. A caller label or generated skip instruction cannot supply authorization. Prompt-only and supplied-material cases must respect their execution limits.

Retain actual tool events and exit statuses when testing execution. A proposed handoff demonstrates a routing decision, not completed research. For executed research, verify that findings inform the requested lesson or plan and that the interaction mode is preserved.

## Acceptance

Require 2 on every applicable routing check. Report structural checks and live behavior trials separately. Do not represent fixture presence as behavioral validation. If a runner or required tool is unavailable, mark the affected behavioral checks unexecuted and state the limitation.

These are exposed development cases; do not claim protected holdout or unseen validation. Record each case's observed route, score, concise evidence, execution status, and unresolved failures.

## Maintenance

When instructions or research inputs change, review affected assumptions and examples, update affected fixtures and reference responses, confirm that the criteria still apply, and rerun affected checks before adopting the update.
