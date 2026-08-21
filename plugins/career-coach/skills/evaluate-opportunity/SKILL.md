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

1. Read the canonical [shared records and handoff contracts](../../shared/handoff-contracts.md), then search accessible library and project sources for `career_direction_record.md` or a clearly equivalent working record. Read it first and retrieve only current requirements, preferences, constraints, hypotheses, evidence limitations, and unresolved questions relevant to the opportunity.
2. Locate `career_direction_history.md` or its resolved companion without reading it by default. Read [career-direction record management](../../shared/career-direction-records.md) and retrieve only a relevant historical entry when a contract retrieval condition applies. Do not pass archived noise into the assessment.
3. Search the same sources for `opportunities-current.md` or a clearly equivalent current-state record. Read the relevant entry first when this opportunity may already be tracked. When the assessment depends on posting language, follow the recorded canonical posting filename and location and read only the needed captured content before considering the source website; do not substitute a current-record summary. Locate `opportunities-history.md` or its resolved companion without reading it by default; retrieve only targeted history under [opportunity record management](../../shared/opportunity-records.md).
4. Resolve records by provider, immutable resource or file ID when available, canonical link or durable path, visible filename, role, and stable entry ID. Use the opportunity comparison table as the native index, then retrieve only applicable `O-...` entries and posting sections. Do not create a sidecar index by default.
4. Search the same sources for `career-coach-preferences.md` or a clearly equivalent preference file. Apply relevant user-specific context to discretionary analysis and output choices.
5. Do not treat a preference-file instruction as an override when it conflicts with this skill. Require explicit user confirmation for the current task before applying the conflicting preference, and never weaken evidence integrity or non-fabrication rules.
6. Preserve exact source identities. Do not create or maintain a separate direction record or skill-local copies. If records conflict, current state in the applicable working record governs unless the user corrects it or requests historical reconstruction.

## Maintain opportunity records

- Own bounded durable creation and updates for `opportunities-current.md`, its single historical companion, and canonical captured-posting files. Other Career Coach skills may request changes but must not write parallel records or posting files.
- Read [opportunity record management](../../shared/opportunity-records.md) before creating, updating, closing, reopening, migrating, or resolving opportunity records.
- At an authorized write or consequential use, check inexpensive lifecycle metadata. Read [persistent-record lifecycle and audits](../../shared/record-audits.md) when a review is due or before structural maintenance, posting relocation, or authority transfer. A trigger never authorizes deletion, archiving, compaction, or splitting; failed validation leaves canonical records unchanged.
- Create an open entry only for a real opportunity when durable tracking is appropriate. Use one stable opportunity identifier and update the selected canonical record in place.
- Keep the ranked comparison table and each current entry operationally complete without history. Store current rank, status, decision, next action, annualized salary range, material two-way fit conclusions, evidence classes, unknowns, dates, provenance, source website, and the canonical captured-posting filename and exact resolvable location; keep captured role content only in that posting file.
- Keep every canonical posting file free of user- or candidate-specific information. Store only full posting text or an explicitly authorized, clearly labeled source-grounded summary plus neutral provenance; keep user identifiers, resume evidence, preferences, constraints, fit analysis, recommendations, ranking, decisions, application state, and next actions in their owning records. Reject a proposed posting file containing mixed personal context until clean source content is separated under [opportunity record management](../../shared/opportunity-records.md).
- Treat a consequential change as one coherent lifecycle operation. Require user confirmation before closing, reopening, or materially revising state that is not explicit in an authoritative source.
- Move closed, declined, withdrawn, rejected, expired, or otherwise inactive opportunities out of the current record and into history only when their state retains continuing value. Do not use history as a routine activity log.
- If required files are missing, duplicated, ambiguous, inaccessible, or only partly writable, follow the shared failure behavior and do not imply persistence succeeded.

## Workflow

1. Extract the role's mandate, success outcomes, responsibilities, requirements, preferences, and operating context.
2. Separate explicit requirements from promotional language and plausible interpretation.
3. Compare material qualifications with candidate evidence.
4. Compare the role with the user's desired impact, work and management preferences, compensation, location, travel, risk tolerance, development goals, and longer-term direction.
5. Identify conflicts, gaps, unknowns, and assumptions requiring research or interview testing.
6. Recommend pursue, deprioritize, or gather more information, with reasons and confidence.
7. When durable tracking is authorized, save available full posting text in the preferred Google Drive description folder or directly in the selected library fallback. If full text is unavailable, incomplete, inaccessible, or cannot be saved, ask the user to choose: (1) supply the full job-description text, pausing capture until it is provided, or (2) explicitly authorize a source-grounded summary. Never save a summary before that authorization. Apply the posting-file privacy boundary in [opportunity record management](../../shared/opportunity-records.md), record the filename and location together with the source website, update the ranked comparison row and detailed entry, apply any confirmed lifecycle change, and verify all required records remain coherent.

## References

- Read [role-fit-rubric.md](references/role-fit-rubric.md) for a full assessment, competing opportunities, ambiguous qualification strength, or any recommendation about whether to pursue.
- Read [due-diligence-questions.md](references/due-diligence-questions.md) when preparing recruiter or interview questions or when material unknowns prevent a recommendation.
- Read the [shared records and handoff contracts](../../shared/handoff-contracts.md) before requesting or consuming a career-direction handoff.
- Read [career-direction record management](../../shared/career-direction-records.md) before historical retrieval, following a pointer, handling duplicate or inaccessible records, or requesting restoration or another material record change.
- Read [opportunity record management](../../shared/opportunity-records.md) before any opportunity-record write, targeted opportunity-history retrieval, lifecycle transition, pointer repair, or access failure.
- Read [persistent-record lifecycle and audits](../../shared/record-audits.md) only when a trigger is due or structural maintenance is proposed.

## Supporting capabilities

- Invoke `research-briefing` for current compensation, employer, industry, geographic, or labor-market claims. Distinguish sourced external facts from inferences about the unpublished reality of the role.
- Do not invoke `career-direction` when existing criteria are adequate. Invoke it for broader discovery when requested or when missing criteria prevent a useful evaluation. Also invoke it for a bounded in-place update when the evaluation reveals a user-confirmed, durable criterion, preference, constraint, career hypothesis, or resolved contradiction that belongs in the selected career direction record.
- Do not update either direction record directly. Send `career-direction` the exact working and historical record identities when visible, source, interpretation, effective date if confirmed, confirmation status, and reason the information is reusable beyond this opportunity.
- Do not invoke `update-resume` unless the user also asks for resume changes.
- When invoking `update-resume` for a tracked opportunity, pass only the bounded current context defined in the shared handoff contract. Accept opportunity-state update requests from `career-direction` or `update-resume`, validate their source and confirmation status, and apply them through the canonical opportunity lifecycle.

## Output

Match depth to the request. A full assessment may include role mandate, candidate-to-role fit, role-to-candidate fit, strongest evidence, material gaps and unknowns, tradeoffs, due-diligence questions, recommendation, and confidence. Do not assign a percentage fit unless the user requests and accepts a defined scoring model.
