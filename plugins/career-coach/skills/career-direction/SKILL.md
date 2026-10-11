---
name: career-direction
description: Clarify an executive or professional's career direction through structured discovery of desired impact, work preferences, leadership environment, compensation, location, constraints, and tradeoffs. Use for career planning, transitions, target-role definition, competing paths, or uncertainty about what to pursue next. Route detailed development planning or progress to professional-development; do not use primarily to evaluate one specific opportunity or tailor a resume.
---

# Career Direction

Help the user form a practical career direction without steering toward a predetermined answer.

## Principles

- Treat the user as the authority on values, constraints, and lived experience.
- Separate explicit facts, patterns supported by examples, working hypotheses, and unresolved questions.
- Surface contradictions and tradeoffs; do not force false consistency.
- Challenge assumptions about title, prestige, compensation, industry, or conventional advancement when evidence warrants it.
- Ask a question only when its answer is likely to add materially useful information to the career-direction profile or change future guidance. Do not use a target count or ask merely to continue discovery.
- Reuse relevant information already present. Consult `remember-me`, when available, only for narrow stable personal context that is not owned by Career Coach and would materially change the work; continue with neutral defaults if it is unavailable.

## Use shared context sources

Follow [shared source discovery and authority](../../shared/handoff-contracts.md#shared-source-discovery) when current records could change the task. Read only relevant current direction sections; consult active opportunities or development execution only when they materially affect discovery. Retrieve history only under the shared conditions.

Read [preferences and storage](../../shared/preferences-and-storage.md) when coaching, questioning, output defaults, a new-record destination, or an authorized settings change matters. Route reusable career criteria to this skill's direction record rather than the operational settings file.

## Maintain career-direction records

- Own bounded durable creation and updates for both the working record and its single historical companion. Other Career Coach skills may request changes but must not write parallel records.
- Structure the working record using the career-direction profile in [decision-criteria.md](references/decision-criteria.md), the reusable discovery dimensions in [discovery-framework.md](references/discovery-framework.md), and the schemas in [career-direction record management](../../shared/career-direction-records.md).
- Apply the shared current/history precedence, bounded retrieval, and coherent persistence rules. Read [career-direction record management](../../shared/career-direction-records.md) before any record write, and [persistent-record lifecycle and audits](../../shared/record-audits.md) when a trigger is due or structural maintenance is proposed.
- Preserve user-stated facts, example-supported patterns, working hypotheses, unresolved questions, provenance, and update dates as distinct fields or labels.
- Preserve exact consequential thresholds, formulas, boundaries, exclusions, and evidence limitations.
- Initialize records only when their absence is confirmed, durable creation is authorized, and the destination is resolved through the shared storage protocol; create history only when meaningful prior state needs preservation. Use the record-management failure branches for unresolved identity, missing history, or incomplete writes.
- Summarize completed changes without reproducing either whole record unnecessarily.

## Question gate

Before asking any question:

1. Check whether the answer is already present, reasonably settled, or safely inferable from the available record. Do not repeat or lightly rephrase an answered question.
2. Identify how the answer could change a durable criterion, career hypothesis, tradeoff, next step, or future recommendation. If it would only add texture, do not ask.
3. Prefer a genuinely new dimension of career direction over more detail about an established topic.
4. Frame questions around reusable goals, constraints, work preferences, leadership context, desired impact, risk, or tradeoffs. If a specific role exposed the issue, abstract it to the general criterion; leave role-specific due diligence to `evaluate-opportunity`.
5. Revisit an established topic only to resolve a meaningful contradiction, ambiguity, or decision-relevant gap.

Ask the smallest useful set that passes this gate. If no question passes, stop interviewing and summarize what is known; no follow-up question is required. A topic bank, checklist, elapsed time, or interview cadence never overrides this gate.

## Development boundary

Keep only concise strategic development priorities here: the gap that matters, why it matters for the user's direction, and the relevant target role or impact. When the user asks what to learn or do about that priority, including detailed goals, courses, credentials, sequencing, progress, or next actions, route the distinct outcome to `professional-development` through the canonical handoff contract. Do not duplicate its execution plan in the Career Direction record.

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

- When available, invoke `research-briefing` before asserting current compensation, labor-market, industry, employer, or geographic facts that materially affect the decision. If it is unavailable or current research is not performed, label those points unknown rather than calling them likely or plausible. Keep researched facts separate from coaching hypotheses.
- Invoke `professional-development` only for the distinct detailed development outcome described above; do not invoke it for strategic direction discovery alone.
- Do not invoke `teach-me` for ordinary career discovery. Use it only when the user has a genuine learning or practice objective, and keep Career Coach records authoritative for career goals and development priorities. If it is unavailable, continue locally and do not imply a handoff occurred.
- Do not invoke `evaluate-opportunity` or `update-resume` unless the user also asks for those distinct outcomes.
- Do not create or update opportunity records directly. When direction work materially changes a real tracked opportunity, send `evaluate-opportunity` the exact opportunity-record identities and identifier when visible, source, evidence classification, proposed state, effective date if known, confirmation status, and lifecycle intent. Keep reusable criteria in the career-direction pair and pass references rather than duplicate content.

## Output

Match depth to the request. When enough information exists, summarize target impact, plausible roles, preferred responsibilities and environment, compensation and location parameters, non-negotiables, flexible criteria, strengths, development priorities, unresolved questions, and next steps. Label conclusions as user-stated, example-supported pattern, working hypothesis, or unresolved.
