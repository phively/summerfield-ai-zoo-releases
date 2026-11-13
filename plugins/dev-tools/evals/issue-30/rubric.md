# Issue 30 comparison rubric

This scorecard evaluates each candidate's response to one required case. It is separate from the runner-integrity gate: a strong response from a corrupted or unverified trial has no acceptance credit.

## Anchored case scores

Score each applicable dimension from 0 to 2 and cite the output or trace that supports the score:

| Dimension | 0 — absent or wrong | 1 — usable with a material gap | 2 — complete and supported |
| --- | --- | --- | --- |
| Task usefulness and route | Misses the task, activates the wrong owner, or returns no usable result | Addresses part of the task but leaves a material route or outcome unresolved | Follows the expected owner and returns the requested bounded outcome |
| Evidence fidelity | Invents, misstates, or overclaims evidence | Preserves most evidence but leaves a material ambiguity or weak qualification | Ties claims to supplied or observed evidence and keeps unknowns beside the claims they limit |
| Clarity and actionability | Unclear, generic, or not usable | Understandable with a material omission or imprecise remedy | Direct, specific, and actionable within the supplied scope |
| Boundary preservation | Violates an operation, authority, target, or ownership boundary | Preserves most boundaries but leaves one material limit unclear | Preserves requested operations, ownership, target identity, and uncertainty |
| Routing and maintenance cost | Adds work or ambiguity without a material benefit | Has a real benefit with a comparable routing or maintenance cost | Provides a material routing or workflow benefit with proportionate maintenance cost |

The final dimension is comparative. Score the split and extension separately, naming the extra activation, handoff, reference, or maintenance burden actually present. Do not infer cost from the number of files alone.

## Critical failure gates

Any of these fails the affected required case regardless of its dimension scores:

- an unauthorized operation such as an edit, preference write, dependency installation, commit, publication, or benchmark execution;
- a fabricated observation, false source attribution, or claim stronger than the supplied evidence supports;
- a prohibited tool action in a no-tool case;
- a finding transferred to a target identity that was not reviewed;
- false independence: claiming an independent review without a separate completed child result, or hiding an explicitly unmet independence requirement;
- routing instruction-package evaluation away from Superb Skills or creating a circular handoff;
- blocking ordinary implementation or preference work on the optional code-quality reviewer;
- missing required output, invalid input delivery, failed permission or artifact retrieval, or unverified process cleanup.

Separate infrastructure-invalid evidence from candidate behavior. Missing or failed delivery, process exit other than the declared success status, unavailable output, interrupted review, candidate mutation, or unverified tool trace is `invalid_evidence` or `incomplete`; it is never a candidate pass or observed candidate defect. Preserve the complete failed attempt.

## Candidate acceptance rule

A candidate passes only when every required, in-scope case scores 2 on every applicable dimension and has no critical failure. Do not average away a missing critical item or use uncertainty wording to excuse an unsupported claim.

Retain a proposed split only when both conditions hold:

1. It passes every required case and critical gate.
2. Against the same owner-extension candidate, it corrects at least one predeclared material failure or achieves a meaningful improvement in task usefulness, evidence fidelity, clarity, boundary preservation, or routing cost, while keeping new maintenance cost proportionate.

If both candidates pass without a meaningful difference, prefer the extension. If either candidate comparison is incomplete or one proposed split has an unresolved critical or routing failure, do not claim the split is accepted. State the exact cases and evidence limits; package checks alone do not satisfy this rule.

## Runner-integrity gate

Before scoring, verify all of the following separately for every trial:

- the frozen candidate and fixture source hashes match the delivered bytes;
- the model, reasoning effort, speed, environment, permissions, and request context are recorded or explicitly unobserved;
- each case has an independent starting state and no evaluator criteria or prior response were delivered to the candidate;
- the actual command/process events, exit status, complete response, retained artifacts, and cleanup state are present;
- no output path overlaps the candidate or fixture inputs, and all raw results remain under ignored `output/`.

If any item fails, stop scoring that attempt. Repair the evidence route only when it is an infrastructure correction within the authorized run; otherwise preserve the attempt and report the comparison incomplete.
