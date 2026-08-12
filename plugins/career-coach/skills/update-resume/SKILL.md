---
name: update-resume
description: Review and tailor a resume, executive profile, skills section, or accomplishment bullets for a specific position using only user-provided facts and traceable supporting evidence. Use with a target posting and resume or source materials, including reviews, project summaries, promotion packets, or prior job descriptions. Do not use for open-ended career discovery or primarily deciding whether an opportunity is desirable.
---

# Update Resume

Create accurate, targeted resume content without rewriting the candidate's history.

## Evidence integrity

- Never invent or silently strengthen employers, titles, dates, responsibilities, authority, accomplishments, outcomes, metrics, scale, technologies, certifications, education, or domain experience.
- Classify candidate information as explicit fact, supported inference, hypothesis, or unknown.
- Use only explicit facts as unqualified resume claims. Use a supported inference only when the evidence logically establishes the claim; otherwise require confirmation.
- Preserve traceability from each material proposed claim to supplied evidence.
- Report source conflicts and uncertainty rather than resolving them silently.
- Treat a material value disputed by explicit sources as unresolved unless one source clearly supersedes or validates the other. Do not choose a value merely because one source seems newer, more formal, or more detailed; omit the disputed detail or ask for clarification.
- Ask only questions whose answers could materially improve accuracy or relevance.
- Invoke `personal-context` first when unseen prior career history or decisions would materially affect the work, but treat recalled context as evidence requiring the same scrutiny as supplied sources.

## Use shared context sources

1. Search accessible library and project sources for `career_direction_record.md` or a clearly equivalent career-direction file. Search the selected career direction record for relevant target direction, desired impact, positioning, strengths, constraints, and development priorities.
2. Use career direction context to guide emphasis only. Do not treat it as evidence of candidate experience, scope, ownership, outcomes, metrics, or credentials unless an underlying supplied source independently supports the claim.
3. Search the same sources for `career-coach-preferences.md` or a clearly equivalent preference file. Apply relevant user-specific context to discretionary writing, formatting, and output choices.
4. Do not treat a preference-file instruction as an override when it conflicts with this skill. Require explicit user confirmation for the current task before applying the conflicting preference, and never weaken evidence integrity or non-fabrication rules.
5. Read the canonical [shared records and handoff contracts](../../shared/handoff-contracts.md). Preserve exact source identity. Do not create or maintain a separate direction record or skill-local copies.

## Workflow

1. Establish the requested deliverable and preserve the existing resume's voice and factual history unless broader redesign is requested.
2. Analyze the target posting's mandate, requirements, central responsibilities, competencies, terminology, and ambiguities.
3. Map important requirements to candidate evidence and current resume coverage.
4. Mine relevant sources for scope, actions, methods, outcomes, and supported scale.
5. Prioritize strongly supported evidence that matters to the role.
6. Draft concise, accurate, ATS-readable revisions.
7. Verify every new or materially changed claim before presenting it as ready to use.

## References

- Read [evidence-standard.md](references/evidence-standard.md) whenever multiple sources, conflicts, inferred claims, missing provenance, or substantial new wording are involved.
- Read [posting-analysis.md](references/posting-analysis.md) before a full job-to-resume comparison or when the posting is long, ambiguous, or jargon-heavy.
- Read [resume-writing.md](references/resume-writing.md) before drafting substantial revised content or changing structure, seniority positioning, or ATS formatting.
- Read [output-templates.md](references/output-templates.md) when choosing a proportional deliverable, building an evidence map, or separating ready-to-use language from confirmation-required language.
- Read the [shared records and handoff contracts](../../shared/handoff-contracts.md) before requesting or consuming a career-direction handoff.

## Supporting capabilities

- Invoke `research-briefing` only when current external facts about the employer, industry, location, compensation, or labor market are requested or materially needed. Never use external research as evidence of the candidate's experience.
- Invoke `documents` when creating or modifying a Word document and follow its render-and-verify workflow.
- Do not invoke `evaluate-opportunity` unless the user also requests that distinct outcome. Invoke `career-direction` for broader discovery only when requested, or for a bounded in-place update when resume work reveals a user-confirmed, durable criterion, preference, constraint, career hypothesis, or resolved contradiction that belongs in the selected career direction record.
- Do not update the direction record directly. Send `career-direction` the exact record identity, source, interpretation, confirmation status, and reason the information is reusable beyond this resume task.

## Output

Match the response to the request. Distinguish ready-to-use wording, wording requiring confirmation, and unsupported proposals. For a full review, provide role priorities, an evidence map, recommended positioning, proposed revisions, material gaps, confirmation questions, and concise claim-verification notes. For a narrow request, return only the requested section plus necessary caveats.
