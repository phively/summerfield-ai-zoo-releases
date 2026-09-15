# Career Coach

Career Coach coordinates five bounded capabilities for evidence-grounded career decisions and materials. The [handoff contract](shared/handoff-contracts.md) is authoritative for ownership, routing, and persistence; this file is only an overview.

## Capabilities

| Skill | Owns | Does not own |
| --- | --- | --- |
| [Career Direction](skills/career-direction/SKILL.md) | Reusable goals, preferences, constraints, positioning, target-role hypotheses, and strategic priorities | Detailed development execution, specific opportunity evaluation, interview preparation, or resume production |
| [Professional Development](skills/professional-development/SKILL.md) | Capability and credential gaps, development goals, learning investments, sequencing, progress, evidence, and next actions | Career discovery, one-time learning answers, opportunity fit, interview preparation, or resume claims |
| [Evaluate Opportunity](skills/evaluate-opportunity/SKILL.md) | Bidirectional role fit, pursuit decisions, due diligence, captured postings, and durable opportunity state | Candidate interview responses or resume rewriting |
| [Prepare Interview](skills/prepare-interview/SKILL.md) | Transient preparation for what the candidate should communicate, demonstrate, explain, and practice | Opportunity records, employer due diligence as its primary task, or a persistent interview/story-bank layer |
| [Update Resume](skills/update-resume/SKILL.md) | Evidence-grounded resume, profile, and accomplishment-bullet tailoring | Career discovery, opportunity decisions, interview preparation, or unsupported future claims |

## Persistent records

| Record authority | Canonical owner | Scope |
| --- | --- | --- |
| [Career-direction records](shared/career-direction-records.md) | `career-direction` | Current direction and material historical direction state |
| [Professional-development records](shared/professional-development-records.md) | `professional-development` | Current development execution plan and completed evidence |
| [Opportunity records](shared/opportunity-records.md) | `evaluate-opportunity` | Active and historical opportunity state, captured postings, and concise actual interview facts |
| Interview preparation | None | Preparation remains task-scoped; it does not create an interview history, transcript, or story-bank record |

All lifecycle audits use [record-audits.md](shared/record-audits.md). Skills may read bounded context from another authority or request a bounded update through that owner; they do not create competing copies.

## Choose a skill

- Clarify what to pursue next: [Career Direction](skills/career-direction/SKILL.md).
- Turn a confirmed priority into a development plan: [Professional Development](skills/professional-development/SKILL.md).
- Decide whether a specific role or opportunity is worth pursuing: [Evaluate Opportunity](skills/evaluate-opportunity/SKILL.md).
- Prepare for a specific interview: [Prepare Interview](skills/prepare-interview/SKILL.md).
- Tailor a resume or profile using supported evidence: [Update Resume](skills/update-resume/SKILL.md).

## Coordination

The contract defines the complete handoff surface, including:

- Career Direction ↔ Professional Development for strategic priorities and execution updates.
- Evaluate Opportunity ↔ Prepare Interview for opportunity context and concise actual interview facts.
- Career Direction or Professional Development → Prepare Interview for relevant priorities, completed evidence, and known gaps.
- Any Career Coach skill → Update Resume for supported source evidence and bounded context.
- Optional handoffs to Work Smarter’s `teach-me`, `research-briefing`, and `remember-me` when those capabilities are available and genuinely needed.

When an optional supporting capability is unavailable, the invoking skill follows its documented fallback and does not invent persistence or external research.

## Evidence boundary

Keep user-stated facts, source facts, supported inferences, hypotheses, and unknowns explicitly distinct. Opportunity conclusions do not become candidate evidence; planned development does not become completed qualification or experience. Resume outputs use only traceable supporting evidence, and interview preparation remains task-scoped unless a concise actual interview fact belongs in the opportunity record.
