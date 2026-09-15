# Configuration and snapshot schema

Use one user-owned profile outside the skill package. It is configuration, not a source record and not a second authority. Keep the profile recoverable without credentials so a restored system can locate the destination and scope.

## Required profile fields

```yaml
schema_version: 1
source:
  provider: <provider name>
  containers: [<provider-scoped container IDs>]
  roots: [<authorized root or pointer rules>]
  exclusions: [<explicit paths, classes, or providers>]
destination:
  provider: github
  repository: <owner/repository>
  branch: <branch>
schedule:
  timezone: <IANA timezone>
  daily: <scheduler-owned expression>
  weekly_reconcile: <scheduler-owned expression>
retention:
  confirmed_deletion: remove-current-mirror-retain-history
  forget_requests: explicit-history-policy
notifications:
  target: <approved destination>
```

The profile must identify the source authority and the destination; it must not contain access tokens, private keys, passwords, recovery codes, or copied record contents. Validate repository identity and private visibility before any write. Require explicit authorization immediately before a first publication, branch change, deletion, or restoration.

## Repository layout

```text
records/<deterministic source-relative path>
backup-index.json
receipts/<run-id>.json                 # optional, if operational receipts are kept in Git
```

Keep receipts outside the content tree when they could disclose scope or operational detail. Do not store credentials or scheduler secrets in Git.

## `backup-index.json`

Use `schema_version: 1` and a `records` array. Each entry contains:

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

`source_version` may be absent when the provider does not expose one. `source_id` is required when the provider exposes an immutable identity; otherwise record the strongest available identity and label the limitation in the receipt. Keep paths relative, deterministic, and reversible. Reject absolute paths, `..`, path separators that can change meaning across platforms, reserved names, case collisions, duplicate `(source_provider, source_container, source_id)` identities, duplicate repository paths, and unindexed files outside the optional `receipts/<run-id>.json` area. The same source ID may occur in different provider/container scopes when its complete scoped identity differs.

The index describes the exact bytes stored in the same snapshot. Git commit metadata supplies history, parentage, and commit identity; do not create a self-referential manifest that claims its own commit SHA.
