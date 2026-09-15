# Restore staging

Use only for an explicit request to recover or inspect prior state. GitHub is non-authoritative. A restore must never silently overwrite a newer or different canonical source.

1. Identify the requested commit, paths, and source identities. Show the commit timestamp/SHA, manifest metadata, and whether the source identity still resolves.
2. Download the selected tree into isolated staging storage and run `scripts/validate_snapshot.py`. Compare staged bytes and identities with the current canonical source; do not infer authority from filenames.
3. Prepare a proposed per-record operation: create, update, rename, or delete. Preserve source ownership, provenance, classification, and unresolved uncertainty. Ask the owning workflow to perform specialist-owned writes when required.
4. Obtain explicit confirmation for the exact staged changes and destination. If identity, scope, or current-version checks conflict, stop and present the conflict instead of overwriting.
5. After an authorized restore, reread the canonical records and verify the resulting identities, bytes, pointers, and hashes. Then run a manual backup so the restored state is captured as a new backup commit.

Deleting the current Git file does not erase its historical objects. A forget request needs a separately authorized retention and history-removal procedure; never rewrite history as an incidental restore step.
