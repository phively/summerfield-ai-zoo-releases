---
name: update-resume
description: Review and tailor a resume, executive profile, skills section, or accomplishment bullets for a specific position using only user-provided facts and traceable supporting evidence. Use with a target posting and resume or source materials, including reviews, project summaries, promotion packets, or prior job descriptions. Do not use for interview preparation, open-ended career discovery, or primarily deciding whether an opportunity is desirable.
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
- Consult `remember-me`, when available, only for narrow stable personal context that is not owned by Career Coach and would materially affect the work. Treat recalled context as evidence requiring the same scrutiny as supplied sources, and continue with neutral defaults if it is unavailable.

## Boundaries

- Do not own interview preparation. If the user wants answers, question-family mapping, rehearsal, or a preparation sheet, route that distinct outcome to `prepare-interview`.
- Professional-development plans may inform future positioning and identify completed evidence to verify, but they do not establish current qualifications by themselves.
- Planned or intended certifications, courses, capabilities, or experience are not completed candidate evidence. Require traceable support before presenting them as current claims.

## Use shared context sources

Follow [shared source discovery and authority](../../shared/handoff-contracts.md#shared-source-discovery) when stored context could materially affect the requested revisions. A narrow edit with sufficient supplied evidence needs no career-record search. For broader tailoring, retrieve only relevant current positioning, the tracked opportunity and its captured posting, or development context needed to identify completed evidence to verify. Retrieve history only under the shared conditions.

Read [preferences and storage](../../shared/preferences-and-storage.md) when discretionary writing, formatting, output choices, artifact destinations, or an authorized settings change matters. Preserve exact source identities; this skill remains read-only for direction, development, and opportunity records. Those records guide emphasis and never establish candidate experience, scope, ownership, outcomes, metrics, or credentials without independently supported underlying evidence.

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
- Read [career-direction record management](../../shared/career-direction-records.md) before historical retrieval, following a pointer, handling duplicate or inaccessible records, or requesting restoration or another material record change.
- Read [opportunity record management](../../shared/opportunity-records.md) before targeted opportunity-history retrieval or requesting an opportunity lifecycle change.
- Read [persistent-record lifecycle and audits](../../shared/record-audits.md) only when a trigger is due or a requested handoff would cause structural maintenance; `update-resume` remains read-only for Career Coach memory records.

## Supporting capabilities

- When available, invoke `research-briefing` only when current external facts about the employer, industry, location, compensation, or labor market are requested or materially needed. If it is unavailable, label affected external claims unverified or unknown. Never use external research as evidence of the candidate's experience.
- Invoke `documents` when creating or modifying a Word document and follow its render-and-verify workflow.
- Do not invoke `evaluate-opportunity` unless the user also requests that distinct outcome. Invoke `career-direction` for broader discovery only when requested, or for a bounded in-place update when resume work reveals a user-confirmed, durable criterion, preference, constraint, career hypothesis, or resolved contradiction that belongs in the selected career direction record.
- Do not update either direction record directly. Send `career-direction` the exact working and historical record identities when visible, source, interpretation, effective date if confirmed, confirmation status, and reason the information is reusable beyond this resume task.
- Do not create or update opportunity records directly. When resume work reveals a material change to a tracked opportunity, send `evaluate-opportunity` the exact record identities and opportunity identifier when visible, source, evidence classification, proposed state, effective date if known, confirmation status, and lifecycle intent. Resume completion alone does not prove application submission or advancement.

## Output

Match the response to the request. Distinguish ready-to-use wording, wording requiring confirmation, and unsupported proposals. For a full review, provide role priorities, an evidence map, recommended positioning, proposed revisions, material gaps, confirmation questions, and concise claim-verification notes. For a narrow request, return only the requested section plus necessary caveats.
