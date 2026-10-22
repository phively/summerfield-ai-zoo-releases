# Record Backup destination-exclusion mode fixtures

Status: Offline deterministic controls cover the policy delta through synthetic packets. The accompanying [evidence review](../record-backup-destination-exclusions-review.md) maps those controls and the instruction boundary to R5-R12 and AE4-AE9. These fixtures do not publish files, enumerate a provider, activate the skill, or demonstrate provider behavior.

The fixtures use generated YAML bytes, synthetic source identities, bounded Markdown, and independently managed fixture files. No user records or credentials are read. `write_snapshot` creates an operational-layout snapshot with a profile-bound exclusion packet and captures the exact synthetic profile bytes and digest. `preservation_packet` builds complete synthetic Git tree inventories for baseline, staging, content, and operational phases. Its object IDs are internally consistent; evidence labels identify fixture data, not provider reads.

## Existing deterministic controls

`test_record_backup_modes.py` exercises four boundaries:

- Daily staging and both synthetic publication readbacks preserve the independent tree while the manifest covers managed records.
- A named manual subset retains an omitted prior record and produces an incomplete receipt.
- Weekly fixtures distinguish a fresh paginated source listing from a deliberately incomplete daily cache. When source access is denied, the last verified record remains present and the receipt stays incomplete.
- Historical validation uses the historical snapshot's matching profile packet. A later manual snapshot uses a separately generated current profile and exclusion set. The current packet fails against the historical profile bytes, and validation does not rewrite historical metadata.

`test_record_backup_destination_policy.py` contains the main path-policy, snapshot-corruption, and preservation-checker controls. It covers literal path normalization, unsafe and overlapping roots, duplicate/nested/case-colliding rules, prefix neighbors, missing and file roots, symlinks, unexpected files outside exclusions, managed-record corruption or deletion, full synthetic tree inventories, and protected-subtree changes at staging, content, and operational phases.

`test_record_backup_reporting.py` checks receipt shape and status consistency, separate destination-preservation fields, incomplete subsets and failures, legacy receipts, history retention, and the README status block. `test_record_backup_permissions_and_downloads.py` checks permission matching and exact payload handling; it is an adjacent safety control, not a destination-exclusion test. `test_record_backup_manual_verification.py` checks unchanged-file reuse eligibility and confirms that reuse does not override a failed fresh recovery check. These helper tests use supplied data and do not establish the truth or provenance of provider evidence.

Together, these controls check that an exclusion only removes files beneath its exact configured root from unindexed-extra accounting; it does not suppress managed-record hash or presence checks, exempt a prefix neighbor, or make preservation optional. They also check that a valid snapshot and a preserved independent destination are separate claims. Tree-inventory fixtures are synthetic, even when the checker reconstructs their declared Git tree IDs.

## Run command

The deterministic modules can be run with:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider \
  plugins/work-smarter/tests/test_record_backup_modes.py \
  plugins/work-smarter/tests/test_record_backup_destination_policy.py \
  plugins/work-smarter/tests/test_record_backup_reporting.py \
  plugins/work-smarter/tests/test_record_backup_permissions_and_downloads.py \
  plugins/work-smarter/tests/test_record_backup_manual_verification.py
```

Listing this command describes the existing controls; it is not a result for the current documentation change.

## R12 evidence boundary

The approved 2026-10-19 Product Contract decision, **Descriptive evidence with current policy retained**, governs R12. KTD12 reuses the historical/current packet-binding regression and restore instructions. The user's prior personal-context provider publication and restore/recovery exercise is credited as user-attested evidence for unchanged mechanics. This repository does not independently verify that attestation, and it does not show that the prior exercise tested the exclusion delta.

Fresh activated daily, manual, or weekly exclusion-aware runs were not performed. Under the approved R12 scope, those runs were removed as closure gates; they remain unmeasured and must not be described as passed. Offline tests do not activate an agent, connect to a provider, or publish to GitHub. The mode fixtures link deterministic helpers with synthetic state only.
