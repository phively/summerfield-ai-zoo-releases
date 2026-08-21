# Opportunity record management

Read this reference when locating, reading, creating, updating, closing, reopening, validating, or handing off persistent opportunity records. The canonical authority and ownership rules are in [handoff-contracts.md](handoff-contracts.md); this file defines schemas and procedures without creating another authority.

## Contents

- [Canonical pair](#canonical-pair)
- [Canonical identity and native retrieval](#canonical-identity-and-native-retrieval)
- [Opportunity-description files](#opportunity-description-files)
- [Current-record schema](#current-record-schema)
- [Ranked current-state table](#ranked-current-state-table)
- [Historical-record schema](#historical-record-schema)
- [Stable identities and pointers](#stable-identities-and-pointers)
- [Targeted retrieval](#targeted-retrieval)
- [Lifecycle](#lifecycle)
- [Coherence validation](#coherence-validation)
- [Failure behavior](#failure-behavior)

## Canonical pair

Use these identities unless an existing clearly equivalent pair is already authoritative in the user's selected location:

- `opportunities-current.md`: working record and sole authority for active opportunities and their current state.
- `opportunities-history.md`: historical companion and authority only for inactive or prior opportunity state and material changes.

Preserve an existing authoritative equivalent record's exact identity and update it in place. Keep the pair together in the same selected library or project location. Do not create skill-local copies, competing current records, or per-opportunity files other than the canonical posting files defined below. Do not create a replacement because access is inconvenient. Resolve multiple plausible candidates before substantive use or writing.

Prefer an existing accessible, writable Google Drive folder named `opportunity descriptions`, `job descriptions`, or a clearly equivalent name for canonical captured-posting files. If no such Drive folder is available, store each posting file directly in the selected library location. Each posting file is authoritative for captured posting content, while `opportunities-current.md` remains the sole authority for active state and ranking. Preserve an already selected canonical posting location unless the user requests migration, and resolve multiple plausible Drive folders before writing when the choice could matter.

`evaluate-opportunity` owns creation and bounded durable updates to both records. `career-direction` and `update-resume` may read relevant opportunity context and request bounded changes through `evaluate-opportunity`; they must not maintain parallel opportunity records.

`evaluate-opportunity` also owns creation and updates of canonical posting files. Other Career Coach skills may read the smallest relevant portion and must request changes through `evaluate-opportunity`.

## Canonical identity and native retrieval

Record the storage provider, immutable resource or file ID when available, canonical link or durable path, visible filename, selected library or folder identity, record role, owner, `Last updated`, `Last audited`, audit byte size, and material-change count since audit. Preserve an existing equivalent metadata model. A filename, line number, employer name, or vague folder description alone is insufficient.

Use the Markdown files as their own retrieval layer. Treat the comparison table in `opportunities-current.md` as the native index: read it first for discovery or comparison, then retrieve only the detailed `O-...` headings needed for the task. Keep every active opportunity exactly once in the table and once under its stable detailed-entry heading. Search history directly by `OH-...`, related `O-...`, status, date, or relationship only when a history retrieval condition applies. Do not create a sidecar opportunity index by default.

## Opportunity-description files

Create a canonical posting file when a real opportunity is added to durable tracking and either the full posting text is available or the user has explicitly authorized a source-grounded summary after learning that full text is unavailable. Use this filename in the selected Google Drive description folder or directly in the library fallback:

`O-YYYY-MM-DD-NN -- Employer -- Role.md`

For example:

`O-2026-08-14-02 -- Cook County State's Attorney -- Chief Data Officer.md`

Use the same stable opportunity identifier as the current record. Use exactly two ASCII hyphens (`--`) surrounded by single spaces as separators; never use em dashes as filename separators. Preserve readable employer and role text, including spaces and apostrophes. Sanitize only characters invalid for the target filesystem: replace invalid path characters with a hyphen, remove prohibited trailing spaces or periods, and shorten employer or role text only when a target path-length limit requires it. Preserve the complete opportunity identifier and both separators. If employer or role is unknown, use an explicit `Unknown Employer` or `Unknown Role` label and retain the uncertainty in the record. Do not create a second file for the same opportunity identifier.

Begin each file with concise provenance metadata containing the opportunity identifier, employer, role, storage provider, immutable resource or file ID when available, canonical link or durable path, selected folder identity, source URL or source identity, source date when known, captured date, and content type: `full posting text` or `source-grounded summary`. Identify a third-party source explicitly. Follow the metadata with only the captured role content. Preserve full text without summarizing, silently correcting, embellishing, or filling omissions. Label an authorized summary prominently, summarize only source-supported role content, and disclose material source limitations.

Never include user- or candidate-specific information in a canonical posting file. Exclude the user's name, personal contact details or other user identifiers, resume evidence, experience claims, qualification comparisons, career preferences or constraints, candidate-to-role or role-to-candidate fit, recommendations, rankings, decisions, application status, next actions, and other personal context. Keep that information only in the applicable opportunity, career-direction, or resume records. Employer or recruiter details present in the source posting and neutral posting provenance are permitted; do not misclassify them as user identifiers.

If full posting text is unavailable, incomplete, inaccessible, or cannot be saved, do not silently save partial text or create a summary. Ask the user to choose: (1) supply the full job-description text, or (2) authorize `evaluate-opportunity` to save a source-grounded summary. If the user chooses the first option, pause capture and do not create or replace the canonical posting file until the text is supplied. If the user chooses the second, save the summary only after that explicit authorization. If the user has already made either choice in the current request, do not ask again. If neither full text nor summary authorization is available, do not create an empty or invented posting file or claim one was saved; record the missing source as an unknown in the current entry.

Treat the posting file as authoritative only for captured posting content. Record its filename and exact resolvable location or resource identity in both `opportunities-current.md` and any historical entry for that opportunity, together with the source website or other original source identity. Link the recorded location when the storage system supports a durable link, and do not copy the complete posting into either record. When clarifying job-posting language, retrieve the captured file from that recorded location before accessing the live website. Use the website only when the captured file is missing or broken, the user requests current verification, or refreshing the captured source is part of the task; never silently replace captured language with changed live-site wording.

On a user-supplied or explicitly refreshed revision for the same opportunity, apply the same personal-information boundary and full-text-or-authorized-summary choice, then update the canonical file in place. When the prior full text has continuing evidentiary or audit value, archive it first as a clearly dated superseded sibling in the same selected posting location and add its filename and exact location to a targeted `opportunities-history.md` entry; otherwise replace it without creating routine history. A superseded posting file must not appear to be the current canonical source.

## Current-record schema

Keep the smallest operationally complete current state, organized as one independently retrievable entry per active opportunity. Each entry should contain, when applicable:

- stable opportunity identifier in the form `O-YYYY-MM-DD-NN`;
- organization, role or opportunity name, canonical captured-posting resource ID, filename, exact resolvable location, and folder identity when one exists, source website or other original source identity, and source date;
- lifecycle status: `considering`, `applying`, `applied`, `interviewing`, `offer`, or another explicit active status;
- current decision, next action, owner, relevant date or deadline, and last-updated date;
- candidate-to-role and role-to-candidate conclusions with confidence;
- material facts, supported inferences, hypotheses, unknowns, risks, and unresolved due-diligence questions under explicit labels;
- relevant career-direction and resume artifact identities without duplicating their canonical content;
- provenance for material state; and
- a historical pointer only when a prior state or change could materially aid interpretation, audit, or restoration.

At the record level, also preserve `Last audited`, audit byte size, and material-change count since audit. Reference applicable reusable career criteria by exact direction-record resource identity, stable heading or criterion identifier when present, and last-verified or effective date; do not copy their formulations into each opportunity entry.

Do not copy complete postings, resumes, career-direction records, interview transcripts, or routine activity logs into the current record. Link or identify canonical sources and retain only the current opportunity state needed across workflows.

## Ranked current-state table

Place one concise comparison table before the detailed active-opportunity entries in `opportunities-current.md`. Include every active opportunity exactly once with these columns, in this order:

| Rank | Opportunity ID | Employer | Role | Annualized salary range | Candidate-to-role fit | Role-to-candidate fit | Status | Next action | Last updated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Link the opportunity identifier or role to the recorded canonical posting location when the storage system supports a durable link. Keep the explicit filename and location in the detailed entry, and keep detailed evidence, risks, unknowns, and due-diligence questions out of the comparison cell.

Treat rank as confirmed current state. Add or change a numeric rank only from the user's explicit ranking or an explicit authoritative ranking rule. Do not derive rank silently from fit, salary, status, recency, or table order. Use `Unranked` when no rank is confirmed; place unranked rows after ranked rows and order them by opportunity identifier for a neutral, deterministic display. Surface duplicate or conflicting numeric ranks for resolution rather than silently renumbering them.

Preserve salary currency and distinguish stated annual compensation from calculated annualization. Use stated workload assumptions when converting hourly, daily, monthly, or contract compensation. If they are absent, show the calculation assumption in the cell; use `Unknown` when the source does not support a range. Never present calculated annualization as employer-stated compensation.

Summarize candidate-to-role and role-to-candidate fit separately from the detailed rubric, including confidence and a material caveat when needed. Use concise evidence-grounded language rather than percentages or an undeclared numeric scoring model. Preserve `Unknown` where evidence is insufficient.

## Historical-record schema

Organize history into independently retrievable entries. Each entry must include:

- stable history identifier in the form `OH-YYYY-MM-DD-NN` and the related `O-YYYY-MM-DD-NN` opportunity identifier;
- organization and role or opportunity name;
- status: `closed`, `declined`, `withdrawn`, `rejected`, `expired`, `superseded`, or `reopened`;
- recorded date and, when known, effective date;
- final or prior material state, decision, outcome, rationale, and unresolved uncertainty;
- source identity and evidence classification;
- canonical captured-posting filename and exact resolvable location when one exists, plus the source website or other original source identity;
- reason the entry retains explanatory, evidentiary, audit, or restoration value; and
- replacement, reopening, or related-entry identifiers when applicable.

Preserve material state changes when they affect later interpretation, evidence, audit, or restoration. Do not turn history into an append-only transcript: omit trivial wording changes, routine process events, duplicated source content, incorrect material, and transient facts without continuing value.

## Stable identities and pointers

Use the same opportunity identifier across both files. A pointer from the current record must identify `opportunities-history.md` or its resolved canonical identity, the `OH-...` entry identifier, subject, and condition for retrieval. Do not use line numbers, a filename alone, organization name alone, or an unqualified keyword as a durable pointer.

Example:

> For the prior withdrawal rationale, consult `opportunities-history.md`, entry `OH-2026-08-14-01`, opportunity `O-2026-07-28-01`, only when reconsidering or explaining this opportunity.

## Targeted retrieval

Read `opportunities-current.md` first when an active opportunity could affect the task. Do not read `opportunities-history.md` by default. Retrieve only the smallest relevant historical entry when:

- the open entry contains a relevant pointer;
- the user asks about an inactive opportunity, previous decision, outcome, or change over time;
- provenance is needed to resolve a material contradiction or ambiguity;
- a closed, declined, withdrawn, rejected, or expired opportunity becomes relevant again;
- an opportunity may need reopening; or
- intentionally omitted evidence or rationale is necessary.

Search by stable identifier, organization, role, status, date, or relationship. A retrieval miss is not evidence that history does not exist; preserve uncertainty when missing history could materially change the result.

## Lifecycle

Treat each consequential change as one coherent operation:

1. Resolve the authoritative pair and opportunity identifier.
2. Resolve the canonical posting identity, if any, and confirm the revised current state, lifecycle status, source, ranking, and effective date when material.
3. Preserve prior state in history only when it retains explanatory, evidentiary, audit, or restoration value.
4. Create or update the canonical posting file when supplied posting content requires it.
5. Update both the comparison row and detailed open entry with the sole authoritative active formulation, or remove both when the opportunity becomes inactive.
6. Add or revise a historical entry with explicit status and relationships when required.
7. Add a pointer only when later targeted retrieval would materially help.
8. Verify that no conflicting active entry, duplicate identifier, duplicate posting file, ranking conflict, or unresolved pointer remains.

Apply lifecycle actions as follows:

- **Open:** create one comparison row and one detailed current entry after the user identifies a real opportunity and durable tracking is appropriate. Create its canonical posting file when posting text is supplied; do not create records for hypothetical examples.
- **Advance:** update current status, decision, next action, dates, and material assessment without logging routine activity.
- **Revise:** replace a material current conclusion, preserving the prior state only when it retains continuing value.
- **Close:** remove the opportunity from the current record and create one historical entry with the confirmed inactive status and material final state, including the captured-posting filename, location, and source website when available.
- **Reopen:** restore current state to the current record under the same opportunity identifier and mark or relate history as `reopened`; do not erase intervening history.
- **Remove:** delete incorrect, transient, or valueless duplication rather than archiving it.

A change requiring both files is incomplete unless both can be written coherently. Do not claim persistence after a partial write.

Check the shared lifecycle triggers at an authorized write or consequential use. Before compaction, splitting, merging, migration, deduplication, history reorganization, captured-posting relocation, or authority transfer, preserve a recoverable snapshot, stage the proposed state, build a complete bidirectional semantic ledger, and run the deterministic validation in [record-audits.md](record-audits.md). A size, age, entry-count, or change-count threshold makes review due but never authorizes a lifecycle action.

## Coherence validation

After a consequential update, verify:

- every active opportunity appears once in the current record;
- every active opportunity appears once in the comparison table and once as a detailed entry;
- no inactive opportunity is presented as active;
- current status, decision, next action, dates, provenance, and uncertainty are explicit;
- stable identifiers are unique and consistent across both files;
- every recorded posting filename and location resolves to the one canonical current file for that identifier, the source website remains recorded, and full text or an explicitly authorized, clearly labeled source-grounded summary and its provenance are preserved;
- every canonical posting file contains only role-source content and neutral provenance, with no user- or candidate-specific information;
- numeric ranks are confirmed and unique, unranked rows remain neutral, and salary annualization exposes its assumptions;
- historical state cannot silently override current state;
- pointers and reopening or replacement relationships resolve;
- copied posting content, unsupported fit precision, and unrelated history are absent; and
- each downstream skill receives only the relevant current context and targeted history needed for its task.

## Failure behavior

- Missing current record: if durable tracking is authorized and no equivalent exists, `evaluate-opportunity` may create `opportunities-current.md` in the user's selected location. Do not create `opportunities-history.md` until meaningful history exists or a lifecycle change requires it.
- Missing full posting text: ask the user to choose between supplying the full text and explicitly authorizing a source-grounded summary. Do not create or replace a canonical posting file with partial text or a summary before that choice; retain the source identity and limitation as an unknown.
- Missing or broken posting file: preserve uncertainty; use the recorded source website to recover or refresh it only when access is authorized and the source remains authoritative. If full text still cannot be saved, require the same two-option choice. Never reconstruct posting content from fit analysis, resume evidence, preferences, or other personal context.
- Contaminated proposed posting: reject a proposed canonical posting file that contains user identifiers or other candidate-specific context. Do not write it or claim posting persistence until source-derived role content and neutral provenance have been cleanly separated. Route authorized personal analysis to its owning record; if clean separation is uncertain, request clean full text or apply the authorized-summary choice instead.
- Duplicate posting candidates: resolve the canonical file by stable opportunity identifier and provenance before reading or writing; do not choose or overwrite silently.
- Missing history: preserve uncertainty and do not infer nonexistence from a retrieval miss.
- Duplicate candidates: resolve the authoritative pair before substantive use or writing; do not choose silently when the result could differ.
- Partial access or writability: treat creation or a material update of the comparison row, detailed entry, and required posting or history files as one coherent operation. Provide a clearly labeled proposed update or report the failed operation; do not imply persistence succeeded.
- Unconfirmed lifecycle state: keep it labeled unknown or proposed. Do not close, reopen, or materially revise an opportunity based only on inference.

Do not modify unavailable user records during plugin development. Update schemas, instructions, evaluations, and tests instead.
