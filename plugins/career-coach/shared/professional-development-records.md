# Professional-development record management

Read this reference when locating, reading, creating, updating, or auditing the current professional-development record. Authority and ownership remain defined in [handoff-contracts.md](handoff-contracts.md); lifecycle procedures remain in [record-audits.md](record-audits.md).

## Canonical record

Use `professional-development.md` as the current record and sole authority for detailed development execution unless an existing clearly equivalent record is already authoritative in the user's selected location. Preserve the existing record's identity when one exists. Do not create skill-local copies or competing current records.

## Current development goals

`professional-development` owns bounded durable creation and updates. Other Career Coach skills are read-only consumers of relevant sections and may request a bounded update through the owning skill. If several plausible records exist, resolve the authority before writing; a retrieval miss is not evidence that no record exists.

## Canonical identity and retrieval

Record the provider and library or container scope, immutable resource or file ID when available, canonical link or durable path, visible filename, record role, owner, `Last updated`, `Last audited`, audit byte size, and material-change count since audit. A filename or line number alone is not a durable identity.

Read the current record first and retrieve only the smallest sufficient sections. Use stable headings such as:

- `Current development goals`
- `Capability and credential gaps`
- `Active approaches and sequencing`
- `Progress and completed evidence`
- `Dependencies, next actions, and review dates`
- `Provenance and unresolved questions`

Do not load unrelated Career Direction or opportunity history merely because it is available. Follow the linked Career Direction priority only when its rationale, constraint, or unresolved uncertainty is needed to interpret the development goal.

## Working-record schema

The record must remain understandable without history and should contain, when applicable:

- canonical resource identity, owner, `Last updated`, effective date, `Last audited`, audit byte size, and material-change count since audit;
- current goals and a concise contents summary for bounded retrieval;
- source and evidence class for each strategic priority or development claim;
- development goals with stable IDs such as `PD-YYYY-MM-DD-NN`;
- unresolved constraints, dependencies, and decisions that affect sequencing; and
- concise provenance and unresolved questions.

Each development goal may include:

| Field | Required meaning |
| --- | --- |
| Goal ID | Stable `PD-...` identifier retained across updates. |
| Capability or credential | State whether the goal is capability acquisition, credential acquisition, or both. |
| Career rationale | Why this investment supports a current direction or target role; preserve its source and evidence class. |
| Linked Career Direction priority | Canonical identity plus stable heading/criterion identifier and last-verified or effective date when available. |
| Priority | User-confirmed or explicitly labeled working priority; do not infer a ranking silently. |
| Target capability or independence boundary | What the user should be able to do independently or what credential milestone is actually intended. |
| Current state | Not started, active, blocked, paused, completed, or another clearly labeled state with supporting detail. |
| Selected development approach | Course, project, practice, mentoring, reading, credential path, or other chosen approach and why it was selected. |
| Completed evidence | Specific completed work or verified credential evidence, separated from intended outcomes or plans. |
| Next action | Smallest useful action, owner, and any confirmation needed. |
| Dependencies | Prerequisites, access, budget, timing, or other blockers. |
| Target/review date | Confirmed target or review date, with timezone or scope when material. |
| Provenance | Source identity, user confirmation, external citation, or other basis for the field. |
| Last updated | Date and, when material, time or effective date of the latest change. |

Do not present a planned course, certification, capability, or experience as completed evidence. Distinguish capability acquisition from credential acquisition even when one may support the other.

## Coherent updates and lifecycle

Treat a material change as one bounded update to the current record: confirm the goal and current state, preserve exact IDs and provenance, update affected dependencies and next actions, record the effective or review date, and verify that no competing current formulation remains.

At an authorized write, consequential use, explicit audit, or proposed structural maintenance, consult [record-audits.md](record-audits.md). If structural maintenance is proposed, stage and validate the complete affected record under that shared audit procedure before replacement.

## Failure behavior

If the canonical record or a required pointer is missing, duplicated, ambiguous, inaccessible, or only partly writable, continue read-only where reliable, preserve uncertainty, and return a clearly labeled proposed update or incomplete operation. Never claim that a development goal was persisted, completed, or verified when the required write or evidence check did not succeed.
