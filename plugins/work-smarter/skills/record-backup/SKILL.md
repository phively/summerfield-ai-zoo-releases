---
name: record-backup
description: Back up, verify, reconcile, or stage restoration of configured durable records to a private GitHub repository. Use for daily backups, weekly reconciliation, or an explicitly requested manual backup; do not use for ordinary record editing, Drive migration, or treating the backup as a source of truth.
---

# Record Backup

Protect durable records with a versioned GitHub backup while leaving their current authorities unchanged. This skill is a reusable workflow; the user's backup profile supplies the source scope, exclusions, destination repository and branch, schedule, and notification settings. Never invent those values.

## Authority and safety

- Treat the configured Library or plugin records as canonical. GitHub is backup and recovery history only.
- Discover the configured source scope independently. Do not rely only on a prior manifest, the remember-me index, or a writer's claim that it backed itself up.
- Keep profile credentials out of prompts, manifests, receipts, and repository content. Do not back up secrets, temporary exports, or provider-native records already protected by their own system unless the profile explicitly and safely includes them.
- A retrieval miss is not evidence of deletion. Preserve the last verified backup until deletion is positively established by source evidence or explicit confirmation.
- Do not change canonical records, disable another backup, migrate Drive data, rewrite Git history, force-update a branch, or expand scope without a separate explicit request and the applicable authorization.
- If a required source, identity, permission, or write-capable GitHub transport is unavailable, stop the affected operation and report it. Never simulate a backup or claim success from a local draft or API acknowledgement alone.

## Select one mode

Read only the reference for the requested mode, plus [configuration and snapshot schema](references/configuration-and-schema.md):

- Daily or manually requested incremental backup: read [daily sync](references/daily-sync.md).
- Weekly audit or repair: read [weekly reconciliation](references/weekly-reconciliation.md).
- Requested recovery of source records: read [restore staging](references/restore-staging.md). Restoration is always staged and requires explicit confirmation before canonical writes.

An on-demand backup uses the daily-sync procedure immediately. A manually limited subset must identify the omitted scope and is not a complete backup. Scheduling belongs to the automation layer; it is not silently created by this skill.

## Common workflow

1. Load and validate the one configured profile. Confirm the source provider/container identities, authorized scope and exclusions, GitHub repository and branch, and credential availability. Acquire a profile-level lock so daily, weekly, and manual runs cannot publish concurrently.
2. Enumerate every configured source page/root and resolve stable provider-scoped identities. Preserve owner, current/supporting/history role, source version when exposed, path fallback, and the exact bytes captured. Never interpret record semantics while copying them.
3. Use deterministic repository paths and the manifest schema. Stage changes outside the destination branch, run `scripts/validate_snapshot.py`, and inspect identity, path, count, size, and SHA-256 results before publication.
4. Publish one non-forced commit for a coherent capture interval. Recheck the source inventory and versions before publishing; if a source changes during capture, retry a bounded number of times or fail the run. An atomic Git commit does not prove an atomic source transaction when the provider has no snapshot facility.
5. Verify the result with a fresh, independent remote read: the configured branch must reach the intended commit, the tree and manifest must match, and every new or changed stored file must hash to the expected value. Verify deletions against the independently enumerated expected tree. A no-change run still verifies the current remote snapshot and emits a receipt.
6. Write a durable run receipt containing mode, run ID, start/end times, scope and exclusion summary, counts, result, checks, coverage limits, and commit SHA/link when available. Use `verified`, `verified-no-change`, `incomplete`, or `failed`; distinguish current-state completeness from intraday history coverage. Keep record contents out of notifications.

Do not describe the run as successful until both the deterministic local checks and the independent remote verification pass. Preserve the last verified snapshot on any failure. Use bounded retries with backoff for transient errors and resolve uncertain timeouts by reading remote state before retrying, so a run cannot create duplicate commits merely because its response was lost.
