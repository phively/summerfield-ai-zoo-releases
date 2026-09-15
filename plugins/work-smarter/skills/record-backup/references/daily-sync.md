# Daily and manual sync

Use this procedure for the scheduled daily run or an explicitly requested manual backup. The manual mode may run immediately with the same profile and lock. A subset is allowed only when the user names it; mark the receipt incomplete for omitted scope.

1. Read and validate the profile and acquire its lock. Check credentials, repository privacy and identity, branch, and the last verified receipt. If the destination is unknown or diverged, stop before writing.
2. Enumerate the complete configured source scope, including all pages and authoritative pointers. Compare stable source IDs and trustworthy versions with the last verified index. When metadata is missing or unreliable, read and hash content rather than assuming no change.
3. Read new or changed records and construct a deterministic staging tree and `backup-index.json`. Recheck inventory and source versions. Retry a moving record a bounded number of times; if a required record remains unstable or inaccessible, fail the complete publication and preserve the prior verified snapshot.
4. Run `scripts/validate_snapshot.py` against the staged tree. The script is an offline integrity check; it does not contact a provider or GitHub. Review its counts and hashes.
5. Create one commit containing all changes for the capture interval. Use a compare-and-swap or equivalent concurrency check when advancing the branch. Never force-push. If a competing commit appears, refetch, merge the intended current snapshot through the transport's supported atomic operation, and revalidate rather than overwriting it.
6. Independently read the remote commit and tree. Confirm branch reachability, manifest equality, all changed/new file hashes, expected removals, and repository path mappings. Resolve a lost response by reading remote state before retrying.
7. Emit a receipt. With no source changes, do not create an empty content commit; verify the remote snapshot and report `verified-no-change`.

Daily Git captures normally preserve the latest observed state for each day, not every intraday provider revision. Report that history limit accurately. Do not call a source-complete run a complete version-history archive unless the provider proves that coverage.
