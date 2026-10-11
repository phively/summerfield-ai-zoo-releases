---
name: evaluate-opportunity
description: "Evaluate a specific job posting, promotion, executive role, or career opportunity in both directions: candidate-to-role qualifications and role-to-candidate goals, preferences, constraints, and risks. Use for whether-to-apply decisions, role-fit analysis, qualification comparisons, tradeoffs, and interview due diligence. Do not use primarily for candidate interview preparation or to rewrite resume content."
---

# Evaluate Opportunity

Assess whether an opportunity is attainable and whether it serves the user's career direction.

## Evidence integrity

- Classify material as explicit fact, supported inference, hypothesis, or unknown.
- Never fabricate or silently strengthen experience, preferences, role facts, qualifications, or outcomes.
- Preserve conflicts and uncertainty; do not resolve them silently.
- Identify the source or reasoning behind material conclusions.
- Ask only questions that could materially change the recommendation.
- Consult `remember-me`, when available, only for narrow stable personal context that is not owned by Career Coach and would materially affect fit; continue with neutral defaults if it is unavailable.

`evaluate-opportunity` also owns durable opportunity-specific interview facts and due diligence: current round or stage, scheduled timing, known interviewers, questions actually asked, advancement or rejection state, and material role-specific unknowns. Keep speculative likely questions in `prepare-interview` outputs, not in opportunity records.

## Use shared context sources

Follow [shared source discovery and authority](../../shared/handoff-contracts.md#shared-source-discovery). Retrieve the relevant current career criteria and, when this opportunity is tracked, its current entry and canonical captured posting. Use the comparison table for discovery/comparison and exact posting pointers for role language. Retrieve history only under the shared conditions; do not create a sidecar index or duplicate direction records.

Read [preferences and storage](../../shared/preferences-and-storage.md) when analysis/output defaults, a posting or tracker destination, or an authorized settings change matters. Request reusable career-criterion changes through `career-direction`; operational defaults use the common settings protocol.

## Maintain opportunity records

- Own bounded durable creation and updates for `opportunities-current.md`, its single historical companion, and canonical captured-posting files. Other Career Coach skills may request changes but must not write parallel records or posting files.
- Read [opportunity record management](../../shared/opportunity-records.md) before creating, updating, closing, reopening, migrating, or resolving opportunity records.
- Apply shared coherent persistence and lifecycle triggers; read [persistent-record lifecycle and audits](../../shared/record-audits.md) when a review is due or structural maintenance, posting relocation, or authority transfer is proposed.
- Create an open entry only for a real opportunity when durable tracking is appropriate. Use one stable opportunity identifier and update the selected canonical record in place.
- Keep the ranked comparison table and each current entry operationally complete without history. Store current rank, status, decision, next action, annualized salary range, material two-way fit conclusions, evidence classes, unknowns, dates, provenance, source website, and the canonical captured-posting filename and exact resolvable location; keep captured role content only in that posting file.
- Apply the posting-content boundary, metadata template, and publication rules in [opportunity record management](../../shared/opportunity-records.md); reject mixed candidate/source content before saving.
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
7. When durable tracking is authorized, resolve the destination through [preferences and storage](../../shared/preferences-and-storage.md), then save under the metadata, content, publication-message, and failure rules in [opportunity record management](../../shared/opportunity-records.md). If full text is unavailable, incomplete, inaccessible, or cannot be saved, apply that reference's full-text-or-authorized-summary choice. Record the exact posting identity and source in the tracker, update the comparison row and detailed entry, apply confirmed lifecycle changes, and report only verified persistence.

## Interview boundary

Keep role- and employer-side due diligence here: what the candidate needs to learn about the opportunity, including material unknowns and questions to ask. When the user asks what the candidate should communicate, demonstrate, explain, or practice, route that distinct outcome to `prepare-interview`; do not turn due-diligence questions into candidate-preparation claims. `prepare-interview` may request bounded updates to this skill for actual interview facts, but it never writes opportunity records directly.

## References

- Read [role-fit-rubric.md](references/role-fit-rubric.md) for a full assessment, competing opportunities, ambiguous qualification strength, or any recommendation about whether to pursue.
- Read [due-diligence-questions.md](references/due-diligence-questions.md) when preparing recruiter or interview questions or when material unknowns prevent a recommendation.
- Read the [shared records and handoff contracts](../../shared/handoff-contracts.md) before requesting or consuming a career-direction handoff.
- Read [career-direction record management](../../shared/career-direction-records.md) before historical retrieval, following a pointer, handling duplicate or inaccessible records, or requesting restoration or another material record change.
- Read [opportunity record management](../../shared/opportunity-records.md) before any opportunity-record write, targeted opportunity-history retrieval, lifecycle transition, pointer repair, or access failure.
- Read [persistent-record lifecycle and audits](../../shared/record-audits.md) only when a trigger is due or structural maintenance is proposed.

## Supporting capabilities

- When available, invoke `research-briefing` for current compensation, employer, industry, geographic, or labor-market claims. If it is unavailable, label affected claims unverified or unknown. Distinguish sourced external facts from inferences about the unpublished reality of the role.
- Do not invoke `teach-me` for opportunity evaluation or due diligence. Use it only when the user separately requests genuine interview or capability practice, with the relevant receiving skill retaining its own workflow. If it is unavailable, continue locally and do not imply a handoff occurred.
- Invoke `prepare-interview` only when candidate preparation is a distinct requested outcome; do not invoke it merely because the opportunity is in an interview stage.
- Do not invoke `career-direction` when existing criteria are adequate. Invoke it for broader discovery when requested or when missing criteria prevent a useful evaluation. Also invoke it for a bounded in-place update when the evaluation reveals a user-confirmed, durable criterion, preference, constraint, career hypothesis, or resolved contradiction that belongs in the selected career direction record.
- Do not update either direction record directly. Send `career-direction` the exact working and historical record identities when visible, source, interpretation, effective date if confirmed, confirmation status, and reason the information is reusable beyond this opportunity.
- Do not invoke `update-resume` unless the user also asks for resume changes.
- When invoking `update-resume` for a tracked opportunity, pass only the bounded current context defined in the shared handoff contract. Accept opportunity-state update requests from `career-direction` or `update-resume`, validate their source and confirmation status, and apply them through the canonical opportunity lifecycle.

## Output

Match depth to the request. A full assessment may include role mandate, candidate-to-role fit, role-to-candidate fit, strongest evidence, material gaps and unknowns, tradeoffs, due-diligence questions, recommendation, and confidence. Do not assign a percentage fit unless the user requests and accepts a defined scoring model.
