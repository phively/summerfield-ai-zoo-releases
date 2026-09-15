# Weekly reconciliation

Reconciliation is an independent coverage and recovery audit, not a slower daily sync. It must rediscover the complete configured scope without trusting the daily cache or prior manifest.

1. Enumerate every configured source root, page, and authoritative pointer. Record inaccessible, ambiguous, duplicate, and out-of-scope candidates separately.
2. Read every included current, supporting, and history record and calculate the exact stored-byte hash. Compare provider/container identity, immutable ID, path, role, source version, size, and hash with the latest reachable Git snapshot.
3. Check missing and extra records, confirmed deletions versus retrieval misses, renames, duplicate mappings, case collisions, index pointers, exclusions, branch ancestry, manifest consistency, and repository structural integrity. Run the offline snapshot validator on a fresh download.
4. Repair recoverable current-state omissions through the same staged, atomic, remotely verified publication path. Do not manufacture unseen intermediate versions. If source revisions expose continuity, record recoverable gaps; otherwise report historical coverage as unknown.
5. Reconstruct the complete latest snapshot from GitHub into isolated scratch storage and verify all hashes and mappings. Periodically reconstruct an older commit as a recovery drill. Test provider restoration only in an isolated destination when supported; it may require new source IDs and pointer remapping.
6. Emit a receipt that separates `current_state_complete`, `history_coverage`, `repaired_items`, `unrecoverable_gaps`, `source_access_limits`, and `restore_test`. Alert when the audit is incomplete or the last verified daily-equivalent run exceeds the configured threshold.

Never treat a successful Git API response as reconciliation proof. The audit succeeds only after fresh remote reads and reconstruction checks pass. A retrieval miss never authorizes removing a current mirror entry.
