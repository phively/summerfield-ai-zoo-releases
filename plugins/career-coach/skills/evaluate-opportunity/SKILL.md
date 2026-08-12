---
name: evaluate-opportunity
description: "Evaluate a specific job posting, promotion, executive role, or career opportunity in both directions: candidate-to-role qualifications and role-to-candidate goals, preferences, constraints, and risks. Use for whether-to-apply decisions, role-fit analysis, qualification comparisons, tradeoffs, and interview due diligence. Do not use primarily to rewrite resume content."
---

# Evaluate Opportunity

Assess whether an opportunity is attainable and whether it serves the user's career direction.

## Evidence integrity

- Classify material as explicit fact, supported inference, hypothesis, or unknown.
- Never fabricate or silently strengthen experience, preferences, role facts, qualifications, or outcomes.
- Preserve conflicts and uncertainty; do not resolve them silently.
- Identify the source or reasoning behind material conclusions.
- Ask only questions that could materially change the recommendation.
- Invoke `personal-context` first when unseen prior preferences, constraints, decisions, or career history would materially affect fit.

## Use shared context sources

1. Search accessible library and project sources for `career_direction_record.md` or a clearly equivalent career-direction file. Search the selected career direction record for requirements, preferences, constraints, hypotheses, and unresolved questions relevant to the opportunity.
2. Search the same sources for `career-coach-preferences.md` or a clearly equivalent preference file. Apply relevant user-specific context to discretionary analysis and output choices.
3. Do not treat a preference-file instruction as an override when it conflicts with this skill. Require explicit user confirmation for the current task before applying the conflicting preference, and never weaken evidence integrity or non-fabrication rules.
4. Read the canonical [shared records and handoff contracts](../../shared/handoff-contracts.md). Preserve exact source identity. Do not create or maintain a separate direction record or skill-local copies.

## Workflow

1. Extract the role's mandate, success outcomes, responsibilities, requirements, preferences, and operating context.
2. Separate explicit requirements from promotional language and plausible interpretation.
3. Compare material qualifications with candidate evidence.
4. Compare the role with the user's desired impact, work and management preferences, compensation, location, travel, risk tolerance, development goals, and longer-term direction.
5. Identify conflicts, gaps, unknowns, and assumptions requiring research or interview testing.
6. Recommend pursue, deprioritize, or gather more information, with reasons and confidence.

## References

- Read [role-fit-rubric.md](references/role-fit-rubric.md) for a full assessment, competing opportunities, ambiguous qualification strength, or any recommendation about whether to pursue.
- Read [due-diligence-questions.md](references/due-diligence-questions.md) when preparing recruiter or interview questions or when material unknowns prevent a recommendation.
- Read the [shared records and handoff contracts](../../shared/handoff-contracts.md) before requesting or consuming a career-direction handoff.

## Supporting capabilities

- Invoke `research-briefing` for current compensation, employer, industry, geographic, or labor-market claims. Distinguish sourced external facts from inferences about the unpublished reality of the role.
- Do not invoke `career-direction` when existing criteria are adequate. Invoke it for broader discovery when requested or when missing criteria prevent a useful evaluation. Also invoke it for a bounded in-place update when the evaluation reveals a user-confirmed, durable criterion, preference, constraint, career hypothesis, or resolved contradiction that belongs in the selected career direction record.
- Do not update the direction record directly. Send `career-direction` the exact record identity, source, interpretation, confirmation status, and reason the information is reusable beyond this opportunity.
- Do not invoke `update-resume` unless the user also asks for resume changes.

## Output

Match depth to the request. A full assessment may include role mandate, candidate-to-role fit, role-to-candidate fit, strongest evidence, material gaps and unknowns, tradeoffs, due-diligence questions, recommendation, and confidence. Do not assign a percentage fit unless the user requests and accepts a defined scoring model.
