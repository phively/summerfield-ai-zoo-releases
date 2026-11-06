# Configuration and snapshot schema

Use one user-owned canonical profile outside the skill package. Back up its exact credential-free YAML bytes as configuration, with the same identity and hash checks as other included files. The Git copy is recovery history, not a second configuration authority.

## Required profile fields

```yaml
schema_version: 1
profile:
  provider: <provider name>
  container: <provider-scoped container ID>
  id: <stable identity or documented path fallback>
  path: <canonical YAML path>
  repository_path: records/configuration/backup-profile.yaml
source:
  provider: <provider name>
  containers: [<provider-scoped container IDs>]
  roots: [<candidate search boundaries; not inclusion rules>]
  exclusions: [<explicit paths, classes, or providers>]
  canonical_records: # optional verified canonical identities not already supplied by routing metadata
    - source_provider: <provider>
      source_container: <provider-scoped container ID>
      source_id: <immutable identity or documented fallback>
      owner: <authoritative record owner>
      evidence_reference: <bounded canonical-routing reference>
  supporting_records: # optional records explicitly designated by the user
    - source_provider: <provider>
      source_container: <provider-scoped container ID>
      source_id: <immutable identity or documented fallback>
      designation_reference: <bounded user-designation reference>
destination:
  provider: github
  repository: <owner/repository>
  branch: <branch>
  exclusions: []
schedule:
  timezone: <IANA timezone>
  daily: null # null for manual-only operation; otherwise scheduler-owned expression
  weekly_reconcile: null
retention:
  confirmed_deletion: remove-current-mirror-retain-history
  forget_requests: explicit-history-policy
notifications:
  target: null # or approved destination
reporting:
  fallback: <authorized durable receipt location outside disposable scratch storage>
  freshness_threshold_hours: null # or user-configured positive number
```

`source.canonical_records` and `source.supporting_records` are optional additions to schema 1. The canonical profile is always included separately. Verified Remember Me routing metadata or another identified owner may supply canonical identities without copying their contents into this profile. For an existing profile with neither list, resolve canonical identities from a fresh read of that authority. If required authority cannot be read or resolved, ask for the narrow missing identity or report an unattended coverage gap; never promote the rest of a root to canonical scope. A canonical-file mention independently qualifies its resolved target as a supporting record, so it need not be duplicated in `supporting_records`.

`source.roots` bounds candidate enumeration only. A user designation is an identity-scoped record with a bounded provenance reference, not a folder, file extension, topic, or prior-manifest match. A designated supporting record does not make its own links eligible. Keep distinct path mappings and provider identity evidence in run-local inventory; the scope helper receives identities and selection evidence, not file contents.

The profile must identify the source authority and the destination; it must not contain access tokens, private keys, passwords, recovery codes, or copied record contents. Validate repository identity and private visibility before any write. Require explicit authorization immediately before a first publication, branch change, deletion, or restoration.

## Destination-directory exclusions

`destination.exclusions` is optional and defaults to an empty list. It contains literal repository-relative directory roots whose files are independently managed in the destination repository:

```yaml
destination:
  provider: github
  repository: <owner/repository>
  branch: <branch>
  exclusions:
    - separately-managed/research
    - archive/vendor-files/
```

One trailing slash is accepted and removed during normalization. Matching uses complete path components, so `archive/vendor-files` does not cover `archive/vendor-files-old`. These rules affect only the validator's extra-file coverage check. They do not change source discovery, required records, hashes, permission decisions, or publication authority, and excluded files are not represented as verified Library backups. An absent directory is allowed; an existing exclusion root must be a directory.

Use safe literal directory paths. Empty/root, absolute, drive-qualified, traversal, backslash, dot or repeated-separator, wildcard, duplicate, nested, and case-colliding rules fail closed. Rules may not overlap `records/`, previous or proposed managed paths, the indexed profile, `receipts/`, `README.md`, `.git`, the manifest, or another operational path. Symlinks and paths escaping the staging root remain errors, including inside an excluded directory. Files outside configured roots continue to fail as unindexed extras.

The run derives a disposable JSON policy packet from a fresh canonical YAML read; the JSON is input evidence, never a second profile. The packet has exactly this shape:

```json
{
  "schema_version": 1,
  "profile": {
    "provider": "<provider>",
    "container": "<container ID>",
    "id": "<stable profile identity>",
    "path": "<canonical YAML path>",
    "repository_path": "records/configuration/backup-profile.yaml",
    "sha256": "<64 lowercase hex characters of the exact profile bytes>"
  },
  "destination": {"repository": "<owner/repository>", "branch": "<branch>"},
  "context": "snapshot-validation",
  "exclusions": ["separately-managed/research", "archive/vendor-files/"]
}
```

Pass it with a separate `--policy-expectations` JSON derived from independently evidenced fresh profile and destination reads. Expectations contain `profile` with the same six fields, `destination`, `context`, `managed_paths` (the union of old and proposed manifest record paths), and `exclusions` extracted and normalized from the fresh canonical YAML. Retain the profile-read and extraction evidence; the helper does not parse YAML or prove that the supplied extraction is fresh or faithful. The validator compares the packet's normalized exclusion roots to this independently derived set, then checks the other bindings, indexed profile record identity, staged profile hash, exact path overlaps, and the manifest's matching `capture_policy` metadata. New exclusion-aware snapshots record the normalized exclusions and profile/destination binding in that metadata for historical interpretation; it does not grant current write authority.

```text
python scripts/validate_snapshot.py STAGING_ROOT \
  --destination-policy RUN_INPUT/policy.json \
  --policy-expectations RUN_INPUT/policy-expectations.json
```

Both JSON files are disposable run inputs. Supplying only one fails. Without a packet, the validator retains strict legacy behavior even if a historical manifest has capture-policy metadata. An empty exclusion list also exempts no files. This validation proves scoped manifest coverage only; it does not prove separately managed destination files were preserved during staging or publication.

## Sensitive-record permission

The user owns backup authorization. Preserve the canonical profile's existing record owner and identify the workflow permitted to maintain it. Extend that one profile at its verified `profile.path`; never make a second permission file or infer authorization from the Git backup copy. Existing ordinary-record profiles remain usable; sensitive inclusion requires the following optional section with actual user-approved values:

```yaml
sensitive_backup:
  owner: <user who owns authorization>
  maintainer: <workflow allowed to maintain this canonical profile>
  approved_data_types:
    - id: <unique approval ID>
      data_type: <user-approved type, e.g. salary>
      source_provider: <provider>
      source_container: <provider-scoped container ID>
      destination:
        repository: <owner/repository>
        branch: <branch>
      sensitivity_classes: [<approved non-credential class, e.g. financial>]
      authorized_by: <user identity>
      authorization_reference: <bounded reference to the explicit approval, not its contents>
      granted_at: <ISO-8601 timestamp with timezone>
      expires_at: null # explicitly approved duration; or an ISO-8601 expiry
      revoked: false
      first_approved_record: # optional provenance; never a matching restriction
        source_provider: <provider>
        source_container: <provider-scoped container ID>
        source_id: <immutable file ID or documented strongest identity fallback>
        reference: <bounded recovery reference>
  grants:
    - id: <unique grant ID>
      source_provider: <provider>
      source_container: <container ID or documented manifest fallback>
      source_id: <immutable file ID or documented strongest identity fallback>
      destination:
        repository: <owner/repository>
        branch: <branch>
      sensitivity_classes: [<approved non-credential class, e.g. financial>]
      content_scope:
        mode: exact-sha256
        sha256: <exact approved content hash>
      authorized_by: <user identity>
      authorization_reference: <bounded reference to the explicit approval, not its contents>
      granted_at: <ISO-8601 timestamp with timezone>
      expires_at: null # explicitly approved duration; or an ISO-8601 expiry
      revoked: false
```

An `approved_data_types` entry authorizes future eligible records and versions containing the named type within its exact source provider, source container, destination repository, and branch. `data_type` identifies content such as `salary`; `sensitivity_classes` classifies handling and does not imply a data type. The workflow must declare every type and class from authorized evidence. Compatible approvals may combine to cover all declared types and classes. Two effective approvals for the same type and scope are ambiguous. The optional `first_approved_record` documents how the approval began; a missing, renamed, or inaccessible first file does not restrict later matching. It is provenance, not authority or a per-file allowlist.

`grants` remains the legacy identity-specific authorization list and may be omitted when `approved_data_types` is present. A legacy grant still authorizes only its exact source identity, destination, classes, and declared content scope. Use `content_scope: {mode: future-versions}` only when the user explicitly authorizes future versions of that same identity. A different identity may use only a matching type approval or its own record grant. An exact-hash mismatch or narrower class restriction on an identity cannot be bypassed by a type approval. A changed destination needs an applicable new authorization. Record a path/container fallback limitation when immutable identities are unavailable; a rename must not silently authorize a different file. Both approval forms contain metadata, not record contents or credentials. Never describe them as a guarantee that external approval review will accept a publication.

Apply permission in this order:

1. Require eligible source identity and inclusion provenance, resolved data classification when using type approvals, explicit exclusion and credential decisions, and the existing content hash. A grant cannot make an ineligible candidate eligible.
2. An applicable record revocation or revocation of a required data type denies publication, including task-only approval. Reinstatement needs an authorized canonical profile update.
3. A valid exact current-task grant may override missing, expired, or narrower persistent permission for that task. It is never persisted automatically and cannot override exclusions, credentials, or revocation.
4. An applicable identity-specific legacy grant keeps its existing owner, class, version/hash, time, destination, and ambiguity restrictions. A type approval cannot bypass any restriction on that identity. A matching expired or narrow record grant still requires focused reauthorization.
5. With no applicable identity restriction, compatible effective type approvals may combine to cover every declared data type and sensitivity class in scope.
6. Missing coverage, duplicate or conflicting applicable approvals, or unresolved metadata denies affected inclusion. An expired approval for an unrelated type does not veto a separate effective approval.

Never turn a task-only grant into a durable grant without exact save authorization.

Reload the current canonical profile each run and before publication if it changed. Known sensitive records without sufficient permission stop affected inclusion; preserve their previous backups and report incomplete coverage rather than treating omission as deletion. Unknown classification needs focused input. In unattended mode report missing identity, class or grant and stop the affected operation. Do not scan or summarize unrelated records to infer blanket permission.

For a deterministic check, serialize the freshly parsed YAML profile and the declared record metadata to run-local JSON and use `scripts/check_permission.py INPUT.json`. The packet contains `profile`, `record`, `destination`, `at`, and optional `task_grant` with the legacy grant shape. Record metadata uses the three manifest identity fields, `inclusion_basis` from the source selector, current `sha256`, declared `data_types` when using type approvals, `sensitivity_classes`, and explicit `excluded: false` and `credential_material: false` classifications established by the run. Legacy profiles without `data_types` may use a matching legacy grant; type approvals require resolved data types and inclusion provenance. Exit 0 means the declared authorization matches; exit 1 denies inclusion. This checks declared metadata, not profile freshness, actual consent, secret absence, classification quality, or publication authority. The JSON is disposable input, never a replacement canonical profile.

Update the profile only with exact persistence authorization through its established owner. Read the latest complete record, preserve unrelated values, write the narrow change, and reread it. If unavailable or partially writable, preserve the last verified authority, mark persistence uncertain, and do not fall back to a stale permission copy. Revocation governs future publication; deleting current backup copies or removing Git history requires its separate applicable authorization.

## Repository layout

```text
records/<deterministic source-relative path and original extension>
records/configuration/backup-profile.yaml
backup-index.json
receipts/<run-id>.json
README.md                            # generated status block plus preserved user content
```

Keep record contents and credentials out of receipts and README. See [receipts and reporting](receipts-and-reporting.md) for publication order, failure fallback, and schema. The seven-row README limit never deletes historical receipts.

Schema-1 receipts may add the optional `personal_data_additions` field. It reports eligible personal-data identities newly present in a verified current snapshot, with declared data types, redacted selection provenance, and the exact approval or grant IDs used. Unknown prior verification state does not count as an empty baseline; a verified-empty baseline requires a bounded reference to evidence of the check. See [personal-data addition notices](receipts-and-reporting.md#personal-data-addition-notices) for the closed entry shape, verification boundary, and retry behavior. This receipt extension does not change `backup-index.json` or the README summary table; older receipts remain valid without it.

## `backup-index.json`

Use `schema_version: 1` and a `records` array. New snapshots also declare `operational_layout: 1` and `profile_repository_path` matching the profile's indexed path. The profile entry uses classification `configuration`. Legacy snapshots without this opt-in remain valid under the original layout. Each entry contains:

```json
{
  "repository_path": "records/remember-me/technology-tools.md",
  "source_provider": "ChatGPT Library",
  "source_container": "<provider-scoped container>",
  "source_id": "<immutable source ID>",
  "source_path": "remember-me/technology-tools.md",
  "owner": "remember-me",
  "classification": "current-authority",
  "source_version": 7,
  "byte_size": 1234,
  "sha256": "<64 lowercase hexadecimal characters>"
}
```

`source_version` may be absent when the provider does not expose one. `source_id` is required when the provider exposes an immutable identity; otherwise record the strongest available identity and label the limitation in the receipt. Keep paths relative, deterministic, and reversible. Reject absolute paths, `..`, path separators that can change meaning across platforms, reserved names, case collisions, duplicate `(source_provider, source_container, source_id)` identities, duplicate repository paths, and unindexed files except the layout's defined operational files. Legacy snapshots may retain direct receipt JSON files; a root operational README must pass the same reporting check as layout 1. The same source ID may occur in different provider/container scopes when its complete scoped identity differs.

A newly captured current record omits `selection_status`. A prior indexed record that fresh inventory confirms is no longer eligible under the corrected scope may remain byte-for-byte as a frozen mirror with `selection_status: retained-out-of-scope`. Its identity, path, version, size, hash, and stored bytes remain indexed and validated, and its bytes remain in snapshot counts. It is excluded from current eligible-source completeness, fresh permission checks, and `personal_data_additions`. Report its retention as a coverage limit using a neutral reference. Do not assign this status to records omitted only because a manual run was limited, whose source is inaccessible or missing, or whose current permission is denied; preserve those copies under their existing incomplete/uncertain outcome. Removing a frozen mirror needs separate authorization and the applicable retention/history procedure. Historical snapshots without this marker remain unchanged.

For operational layout 1, the only unindexed files allowed are validated direct receipt JSON files and the root README, whose generated block must match the receipts. Validate these with the snapshot validator. Arbitrary operational files are not exempt. Preserve existing layout markers; adding compatibility evidence does not require a new layout or archive namespace.

An optional manifest `legacy_receipts` array supports an explicitly reviewed set of historical files in their original paths. Each entry has `repository_path` (`receipts/<safe-stem>.json`), exact `byte_size`, lowercase `sha256`, and nonempty `provenance` identifying the reviewed historical source. These are byte-integrity facts, never new verification claims. The reporting helper accepts only inspected historical `daily-sync`, `weekly-reconciliation`, and `daily-missed-recovery` shapes when the exact bytes match their entries. It retains but excludes them from current summary rows and displays their count. Unknown formats, missing files, changed bytes, duplicate paths, and malformed modern receipts fail. Do not allowlist a failed modern receipt to bypass its validation. Before adding entries, inspect each full historical receipt and present the exact proposed index change under the applicable publication authorization. Never manufacture verification evidence for old runs.

The index describes the exact bytes stored in the same snapshot. Git commit metadata supplies history, parentage, and commit identity; do not create a self-referential manifest that claims its own commit SHA. Optional `representation` describes an explicitly authorized provider export; do not claim exported bytes are the provider-native original. File extension never determines inclusion.

## Manual remote verification reuse

Only after explicit user authorization, the destination `backup-index.json` may retain a `manual_remote_verifications` array. Its entries contain metadata, never file contents or credentials. This array is the durable record of the user's unchanged-file reuse decision; preserve it across index regeneration. It neither alters source ownership nor changes the canonical backup profile or sensitive-record grants.

Each entry requires `id`, `basis: user-reported-github-raw-download`, `verified_on` (ISO calendar date), `verified_by`, nonempty `evidence_reference`, `destination` with exactly `repository` and `branch`, `source_provider`, `source_container`, `source_id`, `repository_path`, `byte_size`, `sha256`, `remote_blob_id`, `reuse_policy: until-identity-version-or-content-changes`, and boolean `revoked: false`. Copy `source_version` when exposed; its presence and value must match subsequent fresh source captures. The remote blob ID identifies the checked content, not an assertion that the user downloaded a particular commit. Record the basis for associating it with the user's size/hash evidence; never invent a download commit or time of day. The policy lasts only while every scoped value still matches and the user has not revoked it. New versions or changed scope require new verification and explicit reuse authorization.

Apply [weekly unchanged-file reuse](weekly-reconciliation.md#user-authorized-unchanged-file-reuse) with the deterministic eligibility helper. Ordinary attestations without this explicit policy receive no reuse credit. The offline snapshot validator still verifies every materialized record against its manifest; manual entries never exempt mismatched or missing local bytes.
