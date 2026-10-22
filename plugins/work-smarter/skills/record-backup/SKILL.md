---
name: record-backup
description: Set up, back up, verify, reconcile, or stage restoration of durable records to a private GitHub repository. Use for backup intake, daily backups, weekly reconciliation, or an explicitly requested manual backup; do not use for ordinary record editing, Drive migration, or treating the backup as a source of truth.
---

# Record Backup

Protect durable records with a versioned GitHub backup while leaving their current authorities unchanged. This skill is a reusable workflow; the user's backup profile supplies the source scope, exclusions, destination repository and branch, schedule, and notification settings. Never invent those values.

## Authority and safety

- Treat the configured Library or plugin records as canonical. GitHub is backup and recovery history only.
- Discover the configured source scope independently. Do not rely only on a prior manifest, the remember-me index, or a writer's claim that it backed itself up.
- Keep credentials, tokens, passwords, private keys, recovery codes, and authentication material out of backups, prompts, manifests, and reporting. Sensitive non-credential records require the exact applicable grant in [configuration and snapshot schema](references/configuration-and-schema.md#sensitive-record-permission). Temporary exports and provider-native records already protected by their own system require explicit profile inclusion.
- A retrieval miss is not evidence of deletion. Preserve the last verified backup until deletion is positively established by source evidence or explicit confirmation.
- Do not change canonical records, disable another backup, migrate Drive data, rewrite Git history, force-update a branch, or expand scope without a separate explicit request and the applicable authorization.
- If a required source, identity, permission, or write-capable GitHub transport is unavailable, stop the affected operation and report it. Never simulate a backup or claim success from a local draft or API acknowledgement alone.

## Select one mode

For setup, a missing or ambiguous profile, or material configuration changes, read [intake](references/intake.md). Reuse valid answers; unattended runs report missing configuration instead of guessing. Setup alone does not authorize scheduling or publication.

Read only the reference for the requested mode, plus [configuration and snapshot schema](references/configuration-and-schema.md). When `destination.exclusions` is non-empty, also read [destination preservation evidence](references/destination-preservation.md):

- Daily or manually requested incremental backup: read [daily sync](references/daily-sync.md).
- Weekly audit or repair: read [weekly reconciliation](references/weekly-reconciliation.md).
- Requested recovery of source records: read [restore staging](references/restore-staging.md). Restoration is always staged and requires explicit confirmation before canonical writes.

An on-demand backup uses the daily-sync procedure immediately. A manually limited subset must identify the omitted scope and is not a complete backup. Scheduling belongs to the automation layer; it is not silently created by this skill.

## Common workflow

1. Load and validate the one configured profile. Confirm the source provider/container identities, authorized scope and exclusions, GitHub repository and branch, and credential availability. Check current sensitive-record grants under the schema; an unavailable or revoked grant stops affected inclusion without deleting its previous mirror. Acquire a profile-level lock so daily, weekly, and manual runs cannot publish concurrently.
2. Follow [source discovery](references/source-discovery.md) to enumerate every configured source page/root and resolve stable provider-scoped identities. Include the credential-free canonical profile and authorized canonical files regardless of extension. Preserve owner, current/supporting/history/configuration role, source version when exposed, path fallback, and the exact bytes captured. Never interpret record semantics while copying them.
3. When exclusions are configured, pin the destination branch commit and full tree before staging. Preserve the configured directories in the stage and run [the destination-preservation checker](references/destination-preservation.md) separately from `scripts/validate_snapshot.py`. Require `staged_preserved` before publishing.
4. Use deterministic repository paths and the manifest schema. Stage changes outside the destination branch and run `scripts/validate_snapshot.py`. With exclusions, pass the current profile-bound policy and independently checked expectations. Inspect identity, path, count, size, and SHA-256 results before publication.
5. Recheck the destination branch immediately before publishing. If it moved, discard the stale stage, refetch the latest tree, reapply only intended managed changes, and rerun both checks. Never force-push or replay an older excluded subtree. Publish one non-forced commit for a coherent capture interval. Recheck the source inventory and versions; retry a moving source a bounded number of times or fail. An atomic Git commit does not prove an atomic source transaction when the provider has no snapshot facility.
6. Independently read the content commit and tree. With exclusions, run the preservation checker with that readback and require `content_preserved`. Verify the manifest, changed-file hashes, and deletions against the independently enumerated expected tree. A no-change run still verifies the current remote snapshot and emits a receipt.
7. Follow [receipts and reporting](references/receipts-and-reporting.md) to write a durable run receipt and refresh the backup repository's README after content verification. With exclusions, record `content_preserved` in the receipt, independently read the operational commit, and require the preservation checker to return `preserved` across both publication phases. Persist the final operational commit ID and readback result in the durable fallback/publication record; the task is not complete until that record is stored. Use `verified`, `verified-no-change`, `incomplete`, or `failed`; distinguish snapshot validity, destination preservation, current-state completeness, intraday history coverage, and receipt persistence. Keep record contents out of notifications.

Do not describe the run as successful until both the deterministic local checks and the independent remote read and verification pass, subject only to the user's explicitly authorized unchanged-file reuse policy in [weekly reconciliation](references/weekly-reconciliation.md#user-authorized-unchanged-file-reuse). Report reused manual checks separately from fresh full restores. Preserve the last verified snapshot on any failure. Use bounded retries with backoff for transient errors and resolve uncertain timeouts by reading remote state before retrying, so a run cannot create duplicate commits merely because its response was lost.
