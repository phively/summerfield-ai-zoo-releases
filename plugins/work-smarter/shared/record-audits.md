# Work Smarter record audits

Read this reference before auditing, compacting, splitting, merging, migrating, deduplicating, reorganizing history, or transferring authority for records maintained by Work Smarter. This is the package's runtime audit protocol. Domain-specific triggers and content checks remain with the workflow that owns each record; for Remember Me records, follow [maintenance triggers and audit](../skills/remember-me/references/record-management.md#maintenance-triggers-and-audit).

## Loss-controlled audits

Treat every persistent-record rewrite as a staged, fail-closed transaction:

1. Resolve the canonical identity and role of every affected current record, history file, index, preference file, source, and pointer target. Use provider-scoped identity and canonical links when available; paths and filenames are recovery fallbacks.
2. Preserve a recoverable before-state or provider revision. Export the complete affected file set and record each relative path, byte size, and SHA-256 hash.
3. Inventory protected semantic items before drafting: current facts, exact constraints, numerical rules, provenance, stable identifiers, pointers, meaningful history, ownership, evidence classifications, and uncertainty. Classify potentially disposable items separately.
4. Build the proposed state outside the canonical location and export the complete after-state file set.
5. Create a bidirectional ledger mapping every before item to `retained`, `moved`, `reworded`, `updated`, `archived`, or justified removal, and every after item to its source or an authorized addition.
6. Review that current state remains usable without history, retained history can reconstruct material prior state, and no content crossed authority boundaries. Require a recorded semantic-equivalence review for protected rewording and explicit authorization for factual updates.
7. When the records are available as Markdown files, run `python scripts/validate_memory_audit.py <before-root> <after-root> <ledger.json>` from the Work Smarter package root. The validator is read-only. An unavailable validator or an inaccessible source leaves the audit incomplete.
8. Inspect the raw diff in both directions. Resolve every omission, altered exact value, duplicate identifier, broken pointer, missing provenance, or uncertain semantic change before promotion.
9. Replace canonical files only after the inventory, ledger, semantic, authority, and pointer checks pass. Use an atomic or recoverable replacement when supported.
10. Read back the written files and verify their identities, hashes, and pointer targets before releasing the recovery copy.

On an unexplained omission, changed exact value, semantic uncertainty, duplicate identifier, broken pointer, conflicting authority, inaccessible dependency, failed review, or partial write, leave canonical state unchanged and report the failed check.

## Audit ledger

Use schema version `1`. `before_files` and `after_files` must exactly match the validator's recursive Markdown inventories. Each inventory object contains `path`, `bytes`, and `sha256`.

Each semantic item contains:

- `id`: unique ledger-local identifier;
- `kind`: `active_fact`, `exact_constraint`, `numeric_rule`, `provenance`, `stable_id`, `pointer`, `historical_item`, or a documented disposable kind;
- `path`: relative Markdown path; and
- `text`: exact text present in that file.

A `pointer` also contains `target_path` and exact `target_text`. The target must exist in the same staged file set. For an external resource that cannot be staged, inventory its exact identity as provenance and record the access limitation; do not claim the local validator resolved it.

Each decision contains `before_id`, `disposition`, and `after_ids`. `retained` and `moved` preserve the item's kind and exact text. `reworded` requires `semantic_review: passed` and a justification. `updated` requires `authorized: true` and a justification. `archived` preserves exact source text as a historical item. `removed` is allowed only for a documented disposable kind and requires justification.

Every before item must have exactly one decision. Every after item must be linked to before state or listed in `new_after_ids`; new items require `new_items_justification`. Stable identifiers must also be reviewed across the complete affected file set; the validator's ID uniqueness check is ledger-local.

## Validation and limits

A successful validator result proves that supplied Markdown inventories are complete, declared items are present, before items are accounted for, after items have an origin or authorized-addition declaration, stable ledger IDs are unique, and declared local pointers resolve. A failed validation must prevent replacement; verify that the before-state remains unchanged.

Hashes prove bytes, not meaning. The validator checks declared coverage; it cannot establish that the inventory includes every semantic item, that reworded content is equivalent, that an external link resolves, that a provider export is complete, or that an authorization is genuine. Preserve those limits through explicit review and report uncertainty when they matter.
