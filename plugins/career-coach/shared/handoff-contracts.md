# Shared records and handoff contracts

This file is the canonical authority, ownership, and coordination contract for the career-coach skills. Read it from the plugin-level path; do not copy it into a skill folder. Read [career-direction-records.md](career-direction-records.md) for career-direction record procedures, [opportunity-records.md](opportunity-records.md) for opportunity record procedures, and [record-audits.md](record-audits.md) only when a lifecycle trigger is due or structural maintenance is proposed.

## Shared source discovery

At the start of each skill workflow, search accessible library and project sources for:

- `career_direction_record.md` or a clearly equivalent working file containing the user's current reusable career direction;
- `career_direction_history.md` or a clearly equivalent historical companion, but do not read its contents by default; and
- `opportunities-current.md` or a clearly equivalent working file containing active opportunities and their current state;
- `opportunities-history.md` or a clearly equivalent historical companion, but do not read its contents by default; and
- an accessible Google Drive folder named `opportunity descriptions`, `job descriptions`, or a clearly equivalent name, containing canonical captured postings when available; otherwise canonical captured postings stored directly in the selected library location; and
- `career-coach-preferences.md` or a clearly equivalent file containing user-specific coaching, analysis, or output preferences.

Preserve exact source identities and update existing records in place. Resolve a canonical Markdown record by storage provider, immutable resource or file ID when available, canonical link or durable path, visible filename, selected library or folder identity, record role, and stable entry or heading when applicable. A filename, line number, organization name, or vague folder location alone is not a durable identity. Preserve the existing working record's identity wherever possible and introduce only one clearly named historical companion. Never create skill-local static copies or competing current records. If several plausible files or pairs exist and the choice could change the work, surface the candidates and resolve the authoritative pair before writing. Do not claim access to a missing or inaccessible source.

Treat `career-coach-preferences.md` as guidance for discretionary behavior. A stored preference is not an override of a conflicting skill instruction without explicit user confirmation for the current task. Even with confirmation, never weaken factual accuracy, evidence integrity, or non-fabrication requirements.

## Opportunity record authority and ownership

`opportunities-current.md` is the working record and sole authority for active opportunities and their current state. `opportunities-history.md` is authoritative only about inactive or prior opportunity state and material changes. If they conflict about an active opportunity, the current record governs unless the user corrects it or requests historical reconstruction. Semantic or keyword retrieval does not enforce this precedence.

The ranked comparison table in `opportunities-current.md` is the sole authority for current opportunity ranking. A canonical captured-posting file is authoritative only for full posting text or an explicitly authorized, clearly labeled source-grounded summary and its neutral provenance. Never place resume evidence, personal experience, preferences, constraints, fit conclusions, recommendations, rankings, decisions, application state, next actions, or other user- or candidate-specific context in that file. Both opportunity records must preserve its filename and exact resolvable location together with the source website. Use the captured file, not the live website, as the first source when clarifying posting language; consult the website only when the file is missing or broken, the user requests a current-source check, or the task requires refreshing provenance. Posting content cannot silently establish lifecycle state, ranking, candidate evidence, or user preferences.

`evaluate-opportunity` owns creation and bounded durable updates to both opportunity records and canonical posting files under [opportunity-records.md](opportunity-records.md). All Career Coach skills may read relevant current entries and the smallest posting portion needed for their task. `career-direction` and `update-resume` must request changes through `evaluate-opportunity`; they must not create, update, or keep parallel opportunity records or posting files.

Read the current record first only when an active opportunity could affect the task. Read the smallest relevant historical entry only when the current record points to it, the user asks about inactive or prior state, history is needed to resolve a material contradiction, or an opportunity may be reopened. Do not load the complete history merely because it is accessible. A retrieval miss is not evidence that history does not exist.

Treat a consequential opportunity change as one operation. Confirm current state, status, source, ranking, and effective date; preserve only materially useful prior state; update or remove the comparison row and open entry; write any required canonical posting or historical file and relationships; and verify that no conflicting active entry remains. If required writes cannot complete coherently, report the incomplete operation and do not claim persistence.

## Career Direction record authority and ownership

`career_direction_record.md` is the working record and sole authority for current career direction. `career_direction_history.md` is authoritative only about historical state. If they conflict, the working record governs unless the user explicitly corrects it or requests historical reconstruction. Semantic or keyword retrieval does not enforce this authority or precedence; every skill must apply it explicitly.

`career-direction` owns creation and bounded durable updates to both records. Structure and maintain them under [career-direction-records.md](career-direction-records.md), using the canonical current profile in its `decision-criteria.md` and the discovery dimensions in its `discovery-framework.md`. Preserve user-stated facts, evidence labels, hypotheses, unresolved questions, source notes, dates, and consequential numerical rules exactly.

`evaluate-opportunity` and `update-resume` may read applicable current context but must not create or maintain parallel career-direction records or update history. When either skill identifies a durable new preference, constraint, criterion, career hypothesis, or resolved contradiction that should change current state, invoke `career-direction` for one bounded coherent update. Do not invoke it merely because the current task produced role-specific facts or resume wording.

## Cross-record authority boundary

Career direction defines reusable goals, criteria, constraints, preferences, hypotheses, and unresolved questions; it is not an opportunity tracker. Opportunity records apply or reference those criteria for specific roles; they cannot establish general career direction. Store opportunity-specific status, rank, fit conclusions, risks, next actions, and due diligence only in `opportunities-current.md`. Store a reusable change to career direction only in `career_direction_record.md` after confirmation through `career-direction`.

Reference, rather than duplicate, the applicable direction record by exact canonical resource identity, stable heading or criterion identifier when present, and last-verified or effective date. A direction change does not silently rewrite an existing opportunity conclusion, and opportunity evidence does not silently become a reusable preference. When the records appear inconsistent, preserve both authorities, surface the conflict, and route a bounded proposed update to the owning skill.

Canonical resume artifacts and supporting evidence remain authoritative for resume claims. Neither a career-direction preference nor an opportunity-fit conclusion can establish experience, scope, ownership, metrics, credentials, or outcomes.

## Retrieval precedence

Every skill reads the working record first. Read only the relevant historical entry or section when the working record points to it, the user asks about prior state or change over time, history is needed to resolve a material contradiction, an archived subject becomes relevant again, a superseded criterion may need restoration, or intentionally omitted provenance is necessary. Do not load the complete archive merely because it is accessible.

Historical entries must have a stable identifier such as `H-YYYY-MM-DD-NN`, an explicit `superseded`, `archived`, `rejected`, or `restored` status, relevant dates, and replacement or restoration references when applicable. A retrieval miss is not evidence that history does not exist; preserve uncertainty when missing history could materially change the result.

## Coherent persistence

Treat a material current-state change as one operation across both records when history must be retained. Confirm current state and its effective date, preserve only materially useful prior state, update the working authority, mark history and replacement relationships, add only justified pointers, and verify no contradictory active formulation remains. If both required records cannot be updated coherently, report the incomplete update and do not claim persistence succeeded.

At an authorized write or consequential use, check the inexpensive lifecycle metadata defined in [record-audits.md](record-audits.md). A due threshold triggers review only. Before compaction, splitting, merging, migration, deduplication, history reorganization, or authority transfer, stage and validate the complete affected record set under that shared protocol. On failed validation, inaccessible dependencies, or partial writes, keep every canonical authority unchanged.

## Career Direction to Evaluate Opportunity

Provide only relevant current reusable context; exclude irrelevant history. Include:

- exact working-record identity and last-updated date when visible;
- applicable requirements, preferences, desired impact, environment, compensation, location, travel, risk, development goals, and unresolved questions;
- the evidence class and source of each material criterion;
- exact preference-file identity and applicable confirmed preferences;
- conflicts or uncertainties that must remain visible.

Include a historical entry only when one of the retrieval conditions applies, and identify its canonical file, entry identifier, subject, and relevance.

## Evaluate Opportunity to Career Direction

When a record update is warranted, send a bounded update request containing:

- the durable criterion, preference, constraint, hypothesis, or contradiction observed;
- the user's exact statement or identified source;
- why the information appears reusable beyond the evaluated opportunity;
- whether the user explicitly confirmed the interpretation;
- the exact working record and historical companion identities to update when visible.

Keep employer- or role-specific due diligence in the opportunity assessment unless it establishes a reusable criterion.

## Career Direction to Update Resume

Provide only current positioning context relevant to the target role; exclude irrelevant history. Include:

- exact working-record identity and last-updated date when visible;
- target impact, plausible roles or levels, preferred scope, strengths to emphasize, development priorities, and applicable constraints;
- exact preference-file identity and applicable confirmed preferences;
- evidence labels and unresolved uncertainty.

Include historical context only when one of the retrieval conditions applies and it materially affects positioning; identify the canonical entry rather than passing the archive.

Career direction context can guide emphasis but cannot establish an unverified resume claim about experience, scope, ownership, outcomes, or credentials.

## Update Resume to Career Direction

When a record update is warranted, send the same bounded update fields defined for `evaluate-opportunity`. Do not add job-posting language, proposed resume wording, or unsupported candidate claims to the career direction record merely because they improve positioning.

## Evaluate Opportunity to Update Resume

When the user requests resume work for a tracked opportunity, provide only relevant current opportunity context: exact current-record and opportunity identities, canonical captured-posting filename and location, the smallest posting content needed, role mandate and requirements, current pursue decision, material qualification evidence and gaps, evidence classifications, unresolved conflicts, and target positioning. Include targeted history only when it materially affects the requested resume work. Opportunity conclusions and posting claims guide emphasis but cannot establish an unverified resume claim.

## Update Resume to Evaluate Opportunity

When resume work reveals a material opportunity-state change, send a bounded request containing the exact opportunity-record identities when visible, opportunity identifier, source, evidence classification, proposed current-state change, confirmation status, effective date if known, and lifecycle intent. Do not treat draft wording, unsupported claims, or completion of a resume artifact as proof that an application was submitted or an opportunity advanced.

## Career Direction to Evaluate Opportunity Records

When career-direction work reveals a material change to a real tracked opportunity, send the same bounded opportunity-update fields. Keep reusable goals, preferences, constraints, and hypotheses in the career-direction pair; pass only their canonical identity and relevant current interpretation to the opportunity record rather than duplicating them.

## Evaluate Opportunity Records to Career Direction

Provide only opportunity evidence that could establish or test a reusable career criterion, preserving exact opportunity identity, source, evidence classification, confirmation state, and uncertainty. Employer- or role-specific facts remain in the opportunity pair unless the user confirms a broader interpretation through `career-direction`.
