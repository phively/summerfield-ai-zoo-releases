# Shared records and handoff contracts

This file is the canonical coordination contract for the career-coach skills. Read it from the plugin-level path; do not copy it into a skill folder.

## Shared source discovery

At the start of each skill workflow, search accessible library and project sources for:

- `career_direction_record.md` or a clearly equivalent file containing the user's reusable career direction; and
- `career-coach-preferences.md` or a clearly equivalent file containing user-specific coaching, analysis, or output preferences.

Preserve the exact source identity and update an existing record in place. Never create skill-local static copies. If several plausible files exist and the choice could change the work, surface the candidates and resolve which is authoritative. Do not claim access to a missing or inaccessible source.

Treat `career-coach-preferences.md` as guidance for discretionary behavior. A stored preference is not an override of a conflicting skill instruction without explicit user confirmation for the current task. Even with confirmation, never weaken factual accuracy, evidence integrity, or non-fabrication requirements.

## Career Direction record ownership

`career-direction` owns creation and updates to `career_direction_record.md`. Structure it using the canonical profile and criteria in its `decision-criteria.md` and the discovery dimensions in its `discovery-framework.md`. Preserve user-stated facts, evidence labels, hypotheses, unresolved questions, source notes, and update dates.

`evaluate-opportunity` and `update-resume` may search and read the record for relevant context. They must not maintain a separate direction record or create local copies. When either skill identifies a durable new preference, constraint, criterion, career hypothesis, or resolved contradiction that should change the record, invoke `career-direction` for a bounded in-place update. Do not invoke it merely because the current task produced role-specific facts or resume wording.

## Career Direction to Evaluate Opportunity

Provide only relevant reusable context, including:

- exact career direction record identity and last-updated date when visible;
- applicable requirements, preferences, desired impact, environment, compensation, location, travel, risk, development goals, and unresolved questions;
- the evidence class and source of each material criterion;
- exact preference-file identity and applicable confirmed preferences;
- conflicts or uncertainties that must remain visible.

## Evaluate Opportunity to Career Direction

When a record update is warranted, send a bounded update request containing:

- the durable criterion, preference, constraint, hypothesis, or contradiction observed;
- the user's exact statement or identified source;
- why the information appears reusable beyond the evaluated opportunity;
- whether the user explicitly confirmed the interpretation;
- the exact career direction record to update.

Keep employer- or role-specific due diligence in the opportunity assessment unless it establishes a reusable criterion.

## Career Direction to Update Resume

Provide only positioning context relevant to the target role, including:

- exact career direction record identity and last-updated date when visible;
- target impact, plausible roles or levels, preferred scope, strengths to emphasize, development priorities, and applicable constraints;
- exact preference-file identity and applicable confirmed preferences;
- evidence labels and unresolved uncertainty.

Career direction context can guide emphasis but cannot establish an unverified resume claim about experience, scope, ownership, outcomes, or credentials.

## Update Resume to Career Direction

When a record update is warranted, send the same bounded update fields defined for `evaluate-opportunity`. Do not add job-posting language, proposed resume wording, or unsupported candidate claims to the career direction record merely because they improve positioning.
