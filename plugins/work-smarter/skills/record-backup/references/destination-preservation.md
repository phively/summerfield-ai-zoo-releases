# Destination preservation evidence

Destination exclusions only remove independently managed files from the snapshot's extra-file check. A second check must prove that the excluded directory stayed unchanged at staging and through publication. Snapshot validity and destination preservation are separate results.

## Evidence packet

Create a run-local JSON packet for `scripts/check_destination_preservation.py`. Keep it in private scratch storage; it contains destination paths and Git object IDs. The packet has this shape:

```json
{
  "schema_version": 1,
  "destination": {"repository": "owner/repository", "branch": "main"},
  "protected_roots": ["separately-managed/research"],
  "baseline": {
    "destination": {"repository": "owner/repository", "branch": "main"},
    "commit": "<full commit object ID>",
    "tree_id": "<full tree object ID>",
    "evidence_id": "<independent read evidence reference>",
    "inventory": [
      {"path": "separately-managed", "mode": "040000", "type": "tree", "object_id": "<tree ID>"},
      {"path": "separately-managed/research", "mode": "040000", "type": "tree", "object_id": "<tree ID>"},
      {"path": "separately-managed/research/reference.md", "mode": "100644", "type": "blob", "object_id": "<blob ID>"}
    ]
  },
  "staged": {
    "destination": {"repository": "owner/repository", "branch": "main"},
    "base_commit": "<the baseline commit ID>",
    "tree_id": "<staged tree ID>",
    "evidence_id": "<staged tree evidence reference>",
    "inventory": []
  },
  "publications": []
}
```

Each inventory must contain the full recursive tree, including directory entries. Every entry has its exact path, Git mode, object type, and full object ID for that type. Valid Git mode/type pairs are `040000/tree`, `100644/blob`, `100755/blob`, `120000/blob`, and `160000/commit`. Include the protected root entry when it exists. An absent root is represented by no matching path. The checker reconstructs each tree object and the root tree ID from the inventory, so an omitted entry or inconsistent tree ID fails closed. It also rejects incomplete parent paths, duplicate or case-colliding entries, invalid mode/type pairs or object IDs, and an exclusion whose root is a file.

The destination object and every evidence object must name the same repository and branch. The staged evidence must bind to the exact baseline commit. Add readback entries under `publications` in order:

```json
{
  "phase": "content",
  "destination": {"repository": "owner/repository", "branch": "main"},
  "parent_commit": "<baseline commit ID>",
  "commit": "<independently read content commit ID>",
  "tree_id": "<content tree ID>",
  "evidence_id": "<independent content tree read reference>",
  "inventory": []
}
```

The `content` readback is required. Add a second entry with `phase: "operational"` after the receipt and README commit; its `parent_commit` must be the content commit ID and its inventory must come from an independent read of that commit's tree. A no-op phase may reuse its parent commit only when its tree ID also stays unchanged. The status is `staged_preserved` before publication, `content_preserved` after content readback, and `preserved` only after both content and operational readbacks pass. Missing final evidence cannot produce `preserved`.

Run the checker with:

```sh
python scripts/check_destination_preservation.py RUN_INPUT/preservation.json
```

The checker first verifies that every supplied inventory hashes to its declared tree ID, then compares each protected subtree by path, type, mode, and Git object ID. It reports additions, removals, and changed entries, including a root that appears when it was absent from the baseline. It returns status for this comparison only; it does not authenticate the `evidence_id`, query GitHub, prove branch reachability, validate the managed snapshot, or grant publication authority. The run must preserve the independent provider reads and confirm each reference and tree identity before treating `preserved` as verified.

## Run sequence

1. Reload the canonical profile. Derive the protected roots from its current `destination.exclusions`; do not substitute a historical manifest's policy.
2. Read the destination branch head and full tree independently. Record the commit and tree IDs, then build the baseline inventory for each configured root. If a root is absent, record that fact through the complete inventory.
3. Build the staging tree from that pinned destination base. Apply managed-record changes without altering protected entries. Run both `validate_snapshot.py` with the current policy packet and the preservation checker with `publications: []`. Require snapshot validity and `staged_preserved` separately.
4. Immediately before publishing content, reread the branch head. If it moved, discard the stale stage, refetch the new head, reapply only the intended managed changes, and repeat both checks. Never force-push or replay an obsolete protected subtree.
5. Publish content with the existing non-forced concurrency control. Independently read its reachable commit and complete tree. Run the checker with the `content` readback and require `content_preserved` before reporting content verification.
6. Build and publish the receipt and README from the verified content. Preserve previous receipts. Independently read the operational commit and full tree, then run the checker with both readbacks. Report preservation separately from snapshot and receipt checks. Only `preserved` confirms the protected subtrees across the complete run.

If any comparison changes a protected entry, stop before the next write. Keep the latest destination contents, refetch and restage only after resolving the conflict, and preserve the failed evidence with an incomplete or failed outcome. Do not set a backup receipt to `verified` solely because the policy allowed the excluded files to remain outside manifest coverage.

## Durable operational readback record

The receipt stored in the destination records `content_preserved` with the baseline and content commit IDs. After the operational commit is independently read and the checker returns `preserved`, update the existing durable fallback/publication record with the run ID, destination repository and branch, content and operational commit IDs, receipt and README hashes, the final preservation status, and references to the independent readback evidence. Keep this record outside the commit it describes; it must not include record contents. A transient notification can summarize the result but is not the durable record. If no durable location is available, report the operation as incomplete after preserving the verified content and pending publication evidence.
