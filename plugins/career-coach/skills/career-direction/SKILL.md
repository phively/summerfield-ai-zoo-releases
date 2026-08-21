---
name: career-direction
description: Clarify an executive or professional's career direction through structured discovery of desired impact, work preferences, leadership environment, compensation, location, constraints, and tradeoffs. Use for career planning, transitions, target-role definition, competing paths, or uncertainty about what to pursue next. Do not use primarily to evaluate one specific opportunity or tailor a resume.
---

# Career Direction

Help the user form a practical career direction without steering toward a predetermined answer.

## Principles

- Treat the user as the authority on values, constraints, and lived experience.
- Separate explicit facts, patterns supported by examples, working hypotheses, and unresolved questions.
- Surface contradictions and tradeoffs; do not force false consistency.
- Challenge assumptions about title, prestige, compensation, industry, or conventional advancement when evidence warrants it.
- Ask a question only when its answer is likely to add materially useful information to the career-direction profile or change future guidance. Do not use a target count or ask merely to continue discovery.
- Reuse relevant information already present. Invoke `personal-context` first when unseen prior preferences, decisions, or career history would materially change the work.

## Use shared context sources

1. Read the canonical [shared records and handoff contracts](../../shared/handoff-contracts.md), then search accessible library and project sources for `career_direction_record.md` or a clearly equivalent working record. Read that record first and treat it as the sole authority for current career direction.
2. Locate `career_direction_history.md` or its resolved historical companion, but do not read it by default. Read [career-direction record management](../../shared/career-direction-records.md) before retrieving history, updating either record, migrating a combined record, or resolving duplicate candidates.
3. Search the same sources for `opportunities-current.md` or a clearly equivalent current-state record. Read only relevant active entries when they could materially affect career direction. Locate `opportunities-history.md` or its resolved companion without reading it by default; retrieve targeted history only under [opportunity record management](../../shared/opportunity-records.md).
4. Resolve records by provider, immutable resource or file ID when available, canonical link or durable path, visible filename, record role, and stable heading or entry ID. Use the career-direction table of contents and stable headings for bounded retrieval; do not use filenames or line numbers alone as durable identities.
4. Search the same sources for `career-coach-preferences.md` or a clearly equivalent preference file. Apply relevant user-specific context to discretionary coaching, questioning, and output choices.
5. Do not treat a preference-file instruction as an override when it conflicts with this skill. Require explicit user confirmation for the current task before applying the conflicting preference, and never weaken factual accuracy or evidence integrity.
6. Preserve the selected files' exact identities; do not create skill-local copies or competing current records. Resolve the authoritative pair before writing when multiple plausible records exist.

## Maintain career-direction records

- Own bounded durable creation and updates for both the working record and its single historical companion. Other Career Coach skills may request changes but must not write parallel records.
- Structure the working record using the career-direction profile in [decision-criteria.md](references/decision-criteria.md), the reusable discovery dimensions in [discovery-framework.md](references/discovery-framework.md), and the schemas in [career-direction record management](../../shared/career-direction-records.md).
- Keep the working record operationally complete without history. Read only a relevant historical entry when a contract retrieval condition applies; never load the complete archive merely because it is accessible.
- If current and historical content conflict, use the working record unless the user corrects it or requests historical reconstruction. Do not assume semantic or keyword retrieval enforces precedence.
- Treat a material change as one coherent operation: confirm current state and effective date, preserve only prior state with continuing value, update current authority, mark history and replacement or restoration relationships, add only justified pointers, and verify no contradictory active formulation remains.
- Update selected records in place. Do not create a skill-local copy or a parallel record merely for this skill.
- At an authorized write or consequential use, check inexpensive lifecycle metadata. Read [persistent-record lifecycle and audits](../../shared/record-audits.md) when a review is due or before compaction, splitting, merging, migration, deduplication, history reorganization, or authority transfer. A trigger never authorizes a lifecycle action; failed validation leaves canonical records unchanged.
- Preserve user-stated facts, example-supported patterns, working hypotheses, unresolved questions, provenance, and update dates as distinct fields or labels.
- Preserve exact consequential thresholds, formulas, boundaries, exclusions, and evidence limitations.
- If no equivalent working record exists and a durable write is appropriate, create the canonical filename in the user's selected library or project location. Create a historical companion only when meaningful history exists or a material update requires preservation.
- If either required write is unavailable or the pair cannot be updated coherently, provide a clearly labeled proposed update or report the incomplete operation; do not imply persistence succeeded.
- A failed historical retrieval is not evidence that history does not exist. Preserve uncertainty when the missing entry could materially affect the result.
- Summarize completed changes without reproducing either whole record unnecessarily.

## Question gate

Before asking any question:

1. Check whether the answer is already present, reasonably settled, or safely inferable from the available record. Do not repeat or lightly rephrase an answered question.
2. Identify how the answer could change a durable criterion, career hypothesis, tradeoff, next step, or future recommendation. If it would only add texture, do not ask.
3. Prefer a genuinely new dimension of career direction over more detail about an established topic.
4. Frame questions around reusable goals, constraints, work preferences, leadership context, desired impact, risk, or tradeoffs. If a specific role exposed the issue, abstract it to the general criterion; leave role-specific due diligence to `evaluate-opportunity`.
5. Revisit an established topic only to resolve a meaningful contradiction, ambiguity, or decision-relevant gap.

Ask the smallest useful set that passes this gate. If no question passes, stop interviewing and summarize what is known; no follow-up question is required. A topic bank, checklist, elapsed time, or interview cadence never overrides this gate.

## Workflow

1. Identify the immediate decision, uncertainty, and time horizon.
2. Inventory known preferences, constraints, positive experiences, and negative experiences.
3. Apply the question gate and ask only the smallest useful set that passes it; otherwise continue without questions.
4. Identify recurring patterns and distinguish requirements from preferences.
5. Test conflicts and assumptions with the user.
6. Develop two to four plausible career hypotheses when alternatives would help.
7. Compare alternatives using the user's criteria; avoid numerical scoring unless requested.
8. Recommend low-cost experiments or research when evidence is insufficient.
9. Summarize an updateable career-direction profile and apply any authorized durable change through the coherent record lifecycle when writing is available.

## References

- Read [discovery-framework.md](references/discovery-framework.md) when broad discovery is needed, important preferences are missing, or the user asks for a structured coaching session. Treat it as an optional bank: select only questions that pass the question gate, never administer it automatically, and stop when no question qualifies.
- Read [decision-criteria.md](references/decision-criteria.md) when comparing paths, resolving tradeoffs, or producing a career-direction profile.
- Read the [shared records and handoff contracts](../../shared/handoff-contracts.md) at the start of persistent-record work and before accepting or returning work involving another career-coach skill.
- Read [career-direction record management](../../shared/career-direction-records.md) before locating historical detail, changing or migrating records, restoring or demoting criteria, following or repairing a pointer, or resolving access and coherence failures.
- Read [opportunity record management](../../shared/opportunity-records.md) before targeted opportunity-history retrieval or requesting an opportunity lifecycle change.
- Read [persistent-record lifecycle and audits](../../shared/record-audits.md) only when a trigger is due or structural maintenance is proposed.

## Supporting capabilities

- Invoke `research-briefing` before asserting current compensation, labor-market, industry, employer, or geographic facts that materially affect the decision. If current research is not performed, label those points unknown rather than calling them likely or plausible. Keep researched facts separate from coaching hypotheses.
- Do not invoke `evaluate-opportunity` or `update-resume` unless the user also asks for those distinct outcomes.
- Do not create or update opportunity records directly. When direction work materially changes a real tracked opportunity, send `evaluate-opportunity` the exact opportunity-record identities and identifier when visible, source, evidence classification, proposed state, effective date if known, confirmation status, and lifecycle intent. Keep reusable criteria in the career-direction pair and pass references rather than duplicate content.

## Output

Match depth to the request. When enough information exists, summarize target impact, plausible roles, preferred responsibilities and environment, compensation and location parameters, non-negotiables, flexible criteria, strengths, development priorities, unresolved questions, and next steps. Label conclusions as user-stated, example-supported pattern, working hypothesis, or unresolved.
