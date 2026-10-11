# Receipts and reporting

Every attempted run gets one stable run ID and a durable receipt, including failures, subsets, and no-change runs. Retain receipt history. A notification or temporary local file is not durable storage.

## Publication lifecycle

1. Under the profile lock, capture and validate the content snapshot (including the profile). Preserve prior receipts and README while creating this commit. A first snapshot may have no receipts yet; generate the empty status block with the reporting helper. Validate an exported tree without `.git` using `validate_snapshot.py`.
2. Publish content without force, then independently verify its reachable commit, manifest, paths, and hashes. With no source changes, verify the existing snapshot instead. A successful capture is not evidence of receipt persistence.
3. Create a schema-1 receipt below. `snapshot_commit` identifies the independently verified snapshot, never the commit containing this new receipt. For failed/unverified capture use null, or the prior verified snapshot only if independently checked during this run; explain the failure. Save pending receipts at the configured durable fallback before attempting reporting publication. If fallback is unavailable, explicitly report inability to persist; never claim all reporting completed.
4. Use `scripts/reporting.py ROOT --write` to validate all receipts and rebuild only the README's marked block. Validate the complete tree. Publish the receipt and README together in a separate operational commit, preserving the verified content. Even no-change runs create this non-empty operational commit. Do not write to an unknown, wrong, or non-private destination merely to log failure.
5. Independently read the reporting commit, confirm branch reachability and exact receipt/README bytes, and ensure content/index still match the verified snapshot. Report content outcome and reporting persistence separately; do not put the reporting commit's SHA inside itself. Keep its SHA in the notification or fallback publication record. A failed reporting write does not invalidate already verified content, but the overall operation is not fully completed.
6. Resolve uncertain responses by looking for `receipts/<run-id>.json` remotely before retrying. Identical bytes mean the receipt is already present; divergent bytes for the same run ID are a conflict. On branch races, refetch and revalidate, regenerate README from the union of receipts, and never overwrite a competing content snapshot. Retry boundedly, then retain the pending receipt for a later authorized run. Do not mutate a failed run into a later successful run; retries within a run precede its finalized receipt.

Failure before any snapshot exists may leave only a fallback receipt; a later authorized reporting run can publish it after establishing a valid destination tree. Do not fabricate a content manifest for a failed capture. Reconciliation may retry pending receipt publication idempotently. Canonical source records and last verified content remain intact.

## Receipt schema 1

Each direct `receipts/<run-id>.json` is a JSON object with:

- `schema_version`: 1; `run_id`: filename stem, ASCII letters/digits/hyphens/underscores, starting with a letter or digit.
- `mode`: `daily`, `weekly`, `manual`, or `restore`; `status`: `verified`, `verified-no-change`, `incomplete`, or `failed`.
- `started_at`, `ended_at`: ISO-8601 timestamps with timezone; end cannot precede start.
- `snapshot_commit`: full hexadecimal Git SHA or null; `checks`: object of named boolean checks, including `local_snapshot` and `remote_snapshot`.
- `scope`, `exclusions`, `history_coverage`: concise strings; `coverage_limits`: list of strings. Never include record contents or credentials.
- `counts`: object containing nonnegative integer `records`, `bytes`, `changed`, `deleted`; `current_state_complete`: boolean.
- `discovery`: nonnegative integer counters `listing_calls`, `content_reads`, `duplicates`, `pointer_cycles`, `retries`.
- For weekly runs: `repaired_items`, `unrecoverable_gaps`, `source_access_limits` as lists of concise strings and `restore_test` as a nonempty result/limitation string.
- Optional `published_content_commit` identifies a published commit without implying full snapshot verification. Optional weekly checks `full_latest_restore` and `full_older_restore` describe fresh full remote recovery drills; a false value cannot coexist with a verified weekly status. Record binary route/byte-check limitations. Informational attestations receive no independent verification credit; explicitly authorized unchanged-file reuse follows [weekly reconciliation](weekly-reconciliation.md#user-authorized-unchanged-file-reuse), with separate policy checks and `reused_manual_verifications` evidence. Do not claim a fresh full restore when reusing a manual check.

Verified statuses require a snapshot SHA, both snapshot checks true, and current-state completeness. Failed/incomplete outcomes cannot claim completeness. A published subset remains `incomplete` even if its checks pass. For `verified-no-change`, changed/deleted counts are zero. The helper checks structure and logical consistency, not the truth of remote evidence or the absence of secrets; the run must establish those facts independently.

## README summary

`scripts/reporting.py ROOT --write` preserves text outside `<!-- record-backup:start -->` and `<!-- record-backup:end -->`, or appends a block if absent. Without `--write` it checks that the existing block is current. It selects the latest weekly result and seven latest daily results by completion instant with run ID as deterministic tie-breaker; manual and restore receipts remain in history but do not crowd out daily results. Failures and no-change runs remain visible. Each row links to the full receipt and shows status, counts, and coverage. Missing history is stated explicitly. This is the destination backup repository's README, not the plugin source repository's catalog README.

Historical receipts use the exact-byte, reviewed manifest allowlist in [configuration and snapshot schema](configuration-and-schema.md#backup-indexjson). Retain their bytes and original paths; show their count separately rather than converting historical claims into current summary rows. Malformed current receipts must fail, even if someone attempts to allowlist them.

## One-time legacy README cleanup

Ordinary `--write` preserves surrounding text. For old generated logs outside the block, first inspect the exact README and create a run-local JSON plan with `readme_sha256` of its UTF-8 bytes and ordered `remove_ranges`. Each range has zero-based byte offsets `start` (inclusive), `end` (exclusive), and `sha256` of exactly those bytes. Select only reviewed obsolete backup-log sections beginning at their legacy heading, preserve unrelated user text, and leave the marked block untouched. The full-file hash prevents applying the plan to a changed README.

`scripts/reporting.py ROOT --migration-plan PLAN.json` produces a concrete before/after diff without writing. Review that diff, then apply the exact authorized cleanup locally with the same arguments plus `--write`; validate the complete staged tree before any publication. Subsequent runs omit the plan and remain idempotent. A reused plan against a changed README is rejected. Do not remove receipts, rewrite Git history, or update the plugin source catalog README during this migration. Review and publish destination changes only under the applicable exact authorization.
