# Persistent-record lifecycle and audits

Read this reference before auditing, compacting, splitting, merging, migrating, deduplicating, reorganizing history, or transferring authority for any Career Coach record. Authority and ownership remain defined in [handoff-contracts.md](handoff-contracts.md); record schemas remain in [career-direction-records.md](career-direction-records.md) and [opportunity-records.md](opportunity-records.md).

## Contents

- [Native Markdown retrieval](#native-markdown-retrieval)
- [Review triggers](#review-triggers)
- [Lifecycle decisions](#lifecycle-decisions)
- [Staged audit](#staged-audit)
- [Audit ledger](#audit-ledger)
- [Validation and replacement](#validation-and-replacement)
- [Limitations](#limitations)

## Native Markdown retrieval

Use the existing Markdown files as their own retrieval layer. Do not create a sidecar index by default.

- Treat `career_direction_record.md` as a single-subject current profile. Keep a short table of contents and stable descriptive headings for current goals, criteria, constraints, positioning, evidence limits, and unresolved questions. Use the heading and canonical resource identity for bounded retrieval.
- Treat `opportunities-current.md` as a multi-entry operational ledger. Use its ranked comparison table as the index and `O-...` headings as stable entry keys. Retrieve the table first when comparison or discovery is needed, then only the applicable detailed entries.
- Treat each captured posting file as authority only for full posting text or an explicitly authorized source-grounded summary and its neutral provenance. It must not contain user- or candidate-specific context. Retrieve it through the exact resource identity recorded for its `O-...` entry.
- Search history by `H-...` or `OH-...` identifier, subject, status, date, or relationship only when a documented retrieval condition applies.

Create a sidecar index only when the native headings, comparison table, stable IDs, and storage-provider search cannot support reliable bounded retrieval. Document its owner, update transaction, and non-authoritative routing role before creation.

## Review triggers

Check inexpensive metadata at an authorized write, explicit audit, or consequential use. The following defaults are conservative design heuristics, not research findings. An audit is due when any condition applies:

- a current or routing record exceeds 8 KiB;
- a detailed current file, including a captured posting, exceeds 16 KiB and routine tasks repeatedly load unrelated content;
- `Last audited` is missing or more than 180 days old;
- either current record has accumulated 25 material changes since its recorded audit;
- duplicate or conflicting active entries, stable IDs, ranks, or authorities are detected;
- a required history or posting pointer is missing or broken;
- a current record is no longer understandable without routinely reading history; or
- compaction, splitting, merging, migration, deduplication, history reorganization, or authority transfer is proposed.

A trigger requires review; it never selects a lifecycle action. If an audit is due but not authorized or cannot run safely, report it as due and continue read-only with explicit uncertainty. Do not repeatedly load full records merely to check a trigger.

## Lifecycle decisions

Choose among retaining, narrowly updating, structurally compacting, splitting, archiving, or removing according to retrieval quality, current decision relevance, evidence and provenance needs, ownership, and restoration value. Age, byte size, token estimate, entry count, or change count alone never authorizes deletion, demotion, summarization, splitting, or authority transfer.

Preserve exact compensation values and formulas, percentages, travel and location limits, dates, ranks, statuses, deadlines, stable IDs, source identities, evidence classifications, uncertainty, ownership, confirmation state, captured posting content and its full-text-or-authorized-summary label, and required pointer targets. Remove only information already classified as incorrect, transient, formatting-only, redundant wording, or valueless duplication.

## Staged audit

Treat maintenance as a fail-closed transaction:

1. Resolve the canonical resource identity and role of every affected current record, history file, captured posting, preference file, resume evidence source, and pointer target.
2. Preserve a recoverable copy or provider revision. Export the complete before file set and record each relative path, byte size, and SHA-256 hash.
3. Inventory every protected semantic item: active facts, exact constraints, numerical rules, provenance, stable IDs, pointers, meaningful history, authority, evidence classifications, and uncertainty. Classify disposable items separately.
4. Build the proposed state outside the canonical location and export the complete after file set.
5. Create a bidirectional ledger mapping every before item to `retained`, `moved`, `reworded`, `updated`, `archived`, or justified removal, and every after item to its origin or an authorized addition.
6. Review that each current record remains operationally complete without history, retained history can reconstruct the material prior state, and no content crossed authority boundaries. Record each review as `passed` only after inspection.
7. Run `python scripts/validate_record_audit.py <before-root> <after-root> <ledger.json>` from the plugin root and inspect the raw diff in both directions.
8. Replace canonical files only after every check passes. Use an atomic or recoverable replacement when supported, verify the written files against the accepted after inventory, and retain the recovery copy until verification succeeds.

On an unexplained omission, altered exact value, semantic uncertainty, duplicate stable ID, broken pointer, conflicting current authority, missing provenance, inaccessible dependency, failed review, or partial write, leave the canonical state unchanged and report the failed check.

## Audit ledger

Use schema version `1`. `before_files` and `after_files` must exactly equal the validator's recursive Markdown inventories. Each inventory object contains `path`, `bytes`, and `sha256`.

Each semantic item contains:

- `id`: unique ledger-local identifier;
- `kind`: `active_fact`, `exact_constraint`, `numeric_rule`, `provenance`, `stable_id`, `pointer`, `historical_item`, `authority`, `evidence_class`, `uncertainty`, or a documented disposable kind;
- `path`: relative Markdown path; and
- `text`: exact text present in that file.

A `stable_id` also contains a namespace such as `direction-history`, `opportunity-current`, or `opportunity-history`. IDs must be unique within their namespace. Record the same cross-file identifier as a primary stable ID in its owning namespace and represent other occurrences as pointers or provenance so legitimate references are not mistaken for duplicate authorities.

A `pointer` also contains `target_path` and exact `target_text`. The target must exist in the same staged file set. For an external resume, website, or provider resource that cannot be staged, inventory its exact identity as provenance and record the access limitation; do not claim the local validator resolved it.

Each decision contains `before_id`, `disposition`, and `after_ids`. `reworded` requires `semantic_review: passed` and a justification. `updated` requires `authorized: true` and a justification. `archived` requires the exact source text as a historical item. `removed` is allowed only for a disposable kind and requires justification. List authorized additions in `new_after_ids` with `new_items_justification`.

The ledger must also contain:

```json
{
  "schema_version": 1,
  "current_state_review": "passed",
  "history_reconstruction_review": "passed",
  "cross_authority_review": "passed"
}
```

## Validation and replacement

The validator is read-only. A successful result proves that the supplied Markdown inventories are complete, protected items are bidirectionally accounted for, stable-ID namespaces are unique, declared local pointers resolve, and the required human reviews were recorded as passed. A failed validation must prevent replacement; verify this behavior in tests by hashing the before files before and after the failure.

After a pass, separately verify storage-provider links, external resources, permissions, and the files written to the canonical location. Do not report coherent persistence until post-write verification succeeds.

## Limitations

Hashes prove exact bytes, not meaning. A ledger proves declared coverage, not that the inventory author identified every semantic item. The validator cannot independently establish semantic equivalence, completeness of a connector export, external-link availability, or truth of a claimed authorization. Preserve these limitations through explicit reviews and fail closed when they matter.
