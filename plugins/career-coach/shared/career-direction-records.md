# Career-direction record management

Read this reference when locating, reading, creating, updating, migrating, validating, or handing off persistent career-direction records. The canonical authority and ownership rules are in [handoff-contracts.md](handoff-contracts.md); this file defines schemas and procedures without creating another authority.

## Contents

- [Canonical pair](#canonical-pair)
- [Canonical identity and native retrieval](#canonical-identity-and-native-retrieval)
- [Working-record schema](#working-record-schema)
- [Historical-record schema](#historical-record-schema)
- [Pointers](#pointers)
- [Targeted retrieval](#targeted-retrieval)
- [Coherent update lifecycle](#coherent-update-lifecycle)
- [Migration](#migration)
- [Coherence validation](#coherence-validation)
- [Failure behavior](#failure-behavior)

## Canonical pair

Use these identities unless an existing clearly equivalent pair is already authoritative in the user's selected location:

- `career_direction_record.md`: working record and sole authority for current career direction.
- `career_direction_history.md`: historical companion and authority only for historical state.

Preserve the existing working record's identity. Introduce only one historical companion beside it. Do not create skill-local copies, competing current records, or a replacement merely because access is inconvenient. If multiple plausible working or historical records exist, resolve the authoritative pair before writing.

`career-direction` owns both records. `evaluate-opportunity` and `update-resume` may read applicable current context and request bounded durable updates through `career-direction`; they must not maintain either record.

## Canonical identity and native retrieval

Record the storage provider, immutable resource or file ID when available, canonical link or durable path, visible filename, selected library or folder identity, record role, owner, `Last updated`, `Last audited`, audit byte size, and material-change count since audit. Preserve an existing equivalent identity and metadata model. A filename or line number alone is insufficient.

Use the Markdown file itself as the retrieval layer. Keep a short table of contents and stable descriptive headings for `Current goals and direction`, `Requirements and non-negotiables`, `Preferences and flexible criteria`, `Positioning and strengths`, `Evidence limitations`, `Unresolved questions`, and `Historical pointers` when those sections apply. Retrieve the smallest relevant heading first and expand only when it is incomplete, stale, ambiguous, conflicting, or points to consequential detail. Do not create a sidecar index merely because the record grows.

## Working-record schema

Keep the smallest operationally complete current state. It must be understandable without history and should contain, when applicable:

- exact canonical resource identity, owner, last-updated date, effective date, last-audited date, audit byte size, and material-change count since audit;
- current goals, desired impact, target roles or hypotheses, and time horizon;
- requirements, preferences, flexible criteria, and non-negotiable constraints;
- compensation formulas and thresholds, location and commute boundaries, travel limits, eligibility exclusions, and other consequential rules exactly as confirmed;
- strengths, development priorities, decision-relevant examples, and evidence limitations;
- user-stated facts, example-supported patterns, working hypotheses, and unresolved issues under explicit labels;
- provenance or source identity for material current state; and
- concise historical pointers only when later retrieval could materially aid interpretation, audit, or restoration.

Consolidate repeated active formulations into one statement. Do not duplicate detailed historical narrative, archived opportunities, superseded rules, or routine workflow events.

## Historical-record schema

Organize material history into independently retrievable entries. Each entry must include:

- stable identifier in the form `H-YYYY-MM-DD-NN`;
- subject;
- status: `superseded`, `archived`, `rejected`, or `restored`;
- recorded date and, when known, effective date;
- prior formulation, decision, opportunity, alternative, or provenance being preserved;
- reason it remains useful;
- source identity or evidence classification;
- replacement or restoration relationship when applicable; and
- unresolved uncertainty that must not be silently collapsed.

The historical record may contain superseded criteria, archived decisions and opportunities, prior formulations, rejected alternatives, detailed change history, and provenance with continuing explanatory, evidentiary, audit, or restoration value. Do not store trivial wording edits, complete conversation transcripts, routine workflow events, transient facts, incorrect material, or valueless duplication.

## Pointers

A working-record pointer must identify:

- canonical file: `career_direction_history.md` or the resolved equivalent;
- entry identifier;
- subject; and
- condition under which the entry should be read.

Example:

> Consult `career_direction_history.md`, entry `H-2026-08-13-02`, subject “routine travel boundary,” only when reviewing, explaining, or restoring that boundary.

Do not use line numbers, a filename alone, or an unqualified keyword as a durable pointer. Verify pointers after material updates. Remove a pointer when the target is invalid, valueless, or no longer relevant.

## Targeted retrieval

Read the working record first. Retrieve only the relevant historical entry or section when:

- the working record contains a relevant pointer;
- the user asks about a previous decision, prior reasoning, or change over time;
- history is needed to resolve a material contradiction or ambiguity;
- an archived employer, opportunity, or criterion becomes relevant again;
- a superseded criterion may need restoration; or
- intentionally omitted detailed provenance is necessary.

Do not load the complete historical record merely because it is accessible. Search by stable identifier, subject, status, or replacement relationship and preserve the exact record identity.

A failed search or broken pointer is not evidence that historical material does not exist. Label the evidence unavailable or unresolved when missing history could materially affect the result. Continue with current state only when doing so does not require inventing the missing history.

## Coherent update lifecycle

Treat each material change as one coherent operation:

1. Confirm the revised current state and effective date.
2. Decide whether the prior formulation has continuing explanatory, evidentiary, audit, or restoration value.
3. If it does, preserve it as one historical entry with a stable identifier, status, dates, provenance, and replacement relationship.
4. Update the working record with the sole authoritative current formulation.
5. Add or update a working-record pointer only when later historical access could materially aid interpretation.
6. Verify no contradictory active formulation remains and every retained pointer resolves.
7. Report both records as updated only after both required writes and coherence checks succeed.

Apply lifecycle actions as follows:

- **Promote:** move archived information into the working record when the user confirms it is current again; retain history and mark the relevant entry `restored` with the new effective date.
- **Demote:** remove no-longer-current information from the working record and archive it only when it retains material value.
- **Invalidate:** mark replaced formulations `superseded` and identify the replacement; never leave them active.
- **Remove:** delete incorrect, transient, or valueless duplication rather than archiving it.
- **Restore:** make the prior criterion current without deleting the intervening history; record the restoration relationship and preserve the current effective date.

If the prior state has no continuing value, update the working record without creating archive noise. A material update that requires both files is incomplete unless both can be written coherently.

## Migration

Migrate an existing combined record only when it is explicitly available and the task authorizes migration.

1. Resolve the authoritative existing record and destination pair before writing, then read [the shared audit protocol](record-audits.md).
2. Inventory current rules, superseded rules, archived decisions and opportunities, process history, provenance, evidence classifications, conflicts, and uncertainty.
3. Retain all current operational criteria in the working record, preserving exact consequential thresholds, formulas, boundaries, exclusions, and limitations.
4. Consolidate repeated current formulations into one authoritative statement without silently resolving material conflicts.
5. Move only material superseded rules, archived opportunity decisions, obsolete process events with continuing value, rejected alternatives, and detailed change history into identified historical entries.
6. Retain provenance and evidence classifications. Preserve unresolved conflicts and missing evidence explicitly.
7. Add concise pointers in the working record only when future historical retrieval could materially help.
8. Verify that opportunity evaluation still receives current requirements, preferences, constraints, hypotheses, and unresolved issues, and that resume tailoring still receives current positioning context and evidence limitations.

Do not modify an unavailable user record during plugin development. Update schemas, instructions, examples, procedures, and tests instead.

Check the shared lifecycle triggers at an authorized write or consequential use. Before migration or any compaction, split, merge, deduplication, history reorganization, or authority transfer, preserve a recoverable snapshot, stage the proposed state, produce a complete bidirectional semantic ledger, and run the deterministic validation in [record-audits.md](record-audits.md). A size, age, or change-count threshold makes review due but never authorizes a lifecycle action.

## Coherence validation

After migration or a consequential update, verify:

- the working record alone contains every current decision-relevant rule;
- the historical record has no authority over current state;
- no superseded formulation remains active;
- no current rule has competing formulations;
- statuses, dates, provenance, and replacement or restoration relationships are explicit;
- numerical thresholds, compensation formulas, commute and travel boundaries, eligibility exclusions, and evidence limitations remain exact;
- pointers resolve to the intended canonical entries;
- downstream handoffs exclude irrelevant history; and
- routine career-direction work can proceed without reading history.

## Failure behavior

- Missing history: preserve uncertainty; do not infer nonexistence from a retrieval miss.
- Broken pointer: report the unresolved pointer, use current state only within its authority, and repair it only when the canonical target is verified.
- Duplicate candidates: present or otherwise resolve the plausible pair before writing; do not choose silently when the result could differ.
- Partial access or partial writability: do not claim persistence succeeded. Provide a clearly labeled proposed update or report which write failed.
- Incoherent partial update: do not describe either record as coherently updated. Preserve the confirmed intended state and identify the recovery action.
