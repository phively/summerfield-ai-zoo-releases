# Coding preference record management

Read this reference only when a coding preference may materially affect a discretionary choice, or when the user asks to save, update, locate, or transfer a coding preference. The user owns the values. This skill maintains the selected coding record only within explicit user authorization.

## One Markdown authority

Use one external Markdown authority named `coding-preferences.md` or an existing authoritative Markdown equivalent. Do not create a companion YAML settings file or a second values profile. Do not keep user values, record copies, or a durable cache in this plugin, another package, a skill installation directory, or benchmark fixtures.

The record can use existing equivalent headings. Its minimum shape is:

```markdown
# Coding Preferences

## Record identity
- Format: coding-preferences/v1
- Owner: user
- Maintainer: dev-tools:coding-preferences
- Record ID: <stable record identifier>
- Provider: <verified provider or local filesystem>
- Container: <verified library, repository, or folder>
- Resource ID: <immutable ID when available>
- Canonical link: <link when supported>
- Durable path: <resolved path when applicable>
- Repository and branch: <when the record is Git-hosted>
- Revision: <record revision when independently maintained>
- Last updated: <actual date>
- Last verified: <date and observable verification evidence>

## Relevant coding preferences

### CP-001 — Python / general
- Preference: <exact, scoped preference>
- Source: <attributed source, including its date when known>
- Effective: <date or unknown>
- Last verified: <date or unknown>

## Explicit exceptions
<!-- Include only a bounded repository-specific exception retained at the user's request. -->
```

Use a stable record identifier and stable entry IDs. Each entry states its language or task scope, exact preference, attributed source (including its date when known), and effective date when known. For explicit user authorization, retain enough detail to identify the authorized value, destination, and authorization date without copying unnecessary conversation text. Include a repository identity and bounded exception only when the user wants it retained. Do not duplicate repository configuration or infer a durable exception from a one-time task. Keep general writing preferences, complete personal profiles, secrets, and routine conversation history out of this record. For an authorized change, update the record-level `Last updated` and `Last verified` fields and the changed entry's `Effective` and `Last verified` fields when present. Use the actual update date and fresh-readback evidence; preserve dates on unrelated entries. Do not invent provenance or advance another owner's audit metadata.

## Resolve the exact authority

1. Use an exact authority supplied in the current request. Otherwise use a verified pointer in applicable persistent user or project instructions, or an already user-selected accessible scope.
2. Search only that selected scope for `coding-preferences.md` or its established equivalent. Do not search the home directory, unrelated drives, package caches, or broad account history by default.
3. Verify the record's owner, stable record ID, provider, container, resource ID and canonical link when available, durable path, and repository/branch/revision for Git-hosted content. A matching filename or copied identifier alone does not establish authority.
4. If the candidate is ambiguous, stale in a material way, unavailable, or only partly readable, do not write or use uncertain values as verified preferences. Ask the smallest focused question needed, or continue with supplied instructions and neutral defaults where reliable.
5. A search miss is not proof of absence. Initialize a new record only after the user selects the exact external destination and explicitly authorizes the preference values to save.

An unknown destination does not block ordinary work: use the current task and repository rules, then disclosed task-only defaults. It does block an unscoped save. Offer a concise proposed entry and request only the missing destination or value.

## Read only what applies

Read the current canonical record before a consequential preference use or any write. Select only entries whose language, task, and repository scope apply. Preserve uncertainty, effective dates, and source attribution. A stale, inferred, conflicting, or missing entry is not a confirmed preference.

When the user supplies an exact preference value in the current request and asks you to apply it, use it only as a task-local instruction. This does not verify that a canonical record contains the value; do not describe it as a retrieved or saved preference, and do not write it without separate authorization. If the user refers to a value without supplying it and no record can be resolved, do not use it as a verified preference.

If a task instruction or applicable repository convention conflicts with a portable preference, do not alter repository configuration to conceal the conflict. Follow the current task and repository authority as specified in [coding workflow](coding-workflow.md), and state a material conflict when it affects the result. A one-time task override does not change the stored value.

## Authorized update procedure

Before writing, resolve the exact current authority and read its latest complete contents. Record the current provider revision, expected head, or equivalent concurrency token when supported. Confirm that the user authorized the exact value, scope, and destination; do not treat authorization to implement code as authorization to save a preference.

Make the smallest in-place Markdown change. Preserve unrelated language entries, record identity, provenance, and all fields outside the authorized scope. Use the provider's current revision as a concurrency token when supported. Keep that token separate from a `Revision` field in the document: when each content write advances the provider token, copying the returned token into the document would make it stale again. Update the document's `Revision` only when the provider defines an independently maintained record revision that remains valid after the write; otherwise preserve the existing value or leave it unknown. Update `Last updated` and the changed entry's `Effective` date as authorized, but do not advance `Last verified` before a matching readback. Attribute the changed value to the explicit authorization and include its date when known; keep that source date distinct from the effective, update, and verification dates. Mark the record-level and changed-entry verification state as pending, retaining their prior verification dates as context. If the record changed, reread it and reconcile only the authorized entry; stop if the authority changed or the new state creates a conflicting value. Do not force-write or silently migrate a record.

After the value write, read the canonical resource again and verify its identity, the authorized value and scope, and preservation of unrelated content. If that readback matches, make one audit-only write to advance the record-level and changed-entry `Last verified` fields with the actual date and readback evidence; use the latest provider token, and do not rewrite the preference value. Read the resource again to verify the final record. Treat this audit finalizer as separate from a retry of the authorized value. If the first value readback fails or disagrees, do not write verification metadata; report the value outcome as unverified. If the audit-only write fails or the final readback is missing or disagrees, its outcome is uncertain because the write may have committed. Do not claim that verification metadata remains pending or is verified; inspect the exact current authority before any retry or correction, and report the value readback and audit-finalizer outcomes separately. Confirm provider concurrency tokens through readback, but do not copy a token into the document's `Revision` field when each content write advances that token. A write acknowledgement alone is not verification. Only fresh matching readback establishes a verified save.

## Uncertain writes and discovery pointers

When a write or readback is uncertain, inspect the exact current authority before retrying. Preserve any newer or unrelated content. At most one reconciled retry is allowed, and only when the original authorization still covers the exact destination and value. A changed authority or conflicting value requires focused input. Do not roll back automatically or claim success after a partial write.

Content persistence and durable rediscovery are separate outcomes. Before claiming cross-session reuse, identify how a fresh session can receive the verified pointer: an already selected scope or an existing persistent instruction/index. A new pointer in user instructions or an index is a separate write and requires its own exact authorization. Do not edit project instructions automatically. If the content was verified but discovery remains unresolved, report the content save as verified and future retrieval as unresolved.

An ownership transfer or change of destination is a migration. Use the public [handoff contract](../../../shared/handoff-contracts.md#remember-me-to-coding-preferences-optional-specialist-routing) when Remember Me owns the current authority or routing pointer. Keep the old authority and recovery state until the new destination has been written and verified; reconcile old-owner pointers only under that owner's lifecycle process. Report content, pointer, and ownership outcomes separately whenever any target remains uncertain.
