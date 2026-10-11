# Record-backup intake review

## Scope and provenance

Issue #14 requirements came from the user-supplied screenshot: explicit intake, backup of the YAML and other canonical formats, efficient Library exploration, saved receipts, and a README with the latest weekly log and seven daily results. The two named conversations were unavailable; no diagnosis of their actual tool use is claimed.

Two independent clean-context agents simulated the same three prompts against repository HEAD (Work Smarter 1.10.0) and the revised working tree (1.11.0). Both inherited the parent model, used read-only local inspection, and received identical scenario facts and restrictions. Neither saw tests, evaluations, expected answers, or the other response. These are qualitative smoke trials, not live provider or marketplace tests.

The primary fixture specifies roots A/B, A's two pages containing x.md/y.json/z (extensionless binary), B's alias of y and pointer to A, and a known canonical profile YAML outside both roots. Versions are stable; content checks succeed. Receipt publication times out; fresh remote reads return identical receipt bytes and the expected README. Other prompts cover setup-only manual backups without chosen repository/fallback, and an unattended run missing profile identity/fallback. See regression.json for maintained acceptance criteria.

## Observed comparison

| Behavior | HEAD baseline | Revised skill |
| --- | --- | --- |
| Captured source identities | x, y, z; profile only read as configuration | x, y, z, profile captured |
| Initial listing calls, assuming one-page B | 3 | 3 |
| Initial content reads including profile loading | 4 | 4 |
| Pagination and deduplication | Correctly inferred | Explicit procedure followed |
| Final source checks | Kept separate | Kept separate |
| Root operational README | Identified validator rejection | Supported and checked against receipts |
| Lost receipt response | Remote read avoids duplicate | Same, with separate reporting commit and fallback lifecycle |
| Setup-only manual operation | Identified undefined schedule/fallback choices | Null schedule and explicit missing-choice intake |
| Unattended incomplete setup | Stops; reporting recovery unspecified | Stops with named missing fields and truthful persistence limitation |

Both simulations preserved non-Markdown content and avoided duplicate initial reads. This trial demonstrates clearer coverage/reporting decisions, not measured discovery speedup. In the revised response, reporting reachability and content-preservation checks remained unproven because the fixture only stipulated receipt/README byte readback; the agent correctly withheld unconditional completion. Neither agent invented hashes, SHAs, byte totals, repair counts, or historical revision continuity.

The revised response distinguished B's repeated pointer from a true cycle. Discovery guidance was clarified accordingly: an already traversed alias/cycle alone does not make coverage incomplete; unresolved pagination/access gaps do.

## Deterministic checks

The reporting test module exercises exact YAML/binary/extensionless capture, indexed profile requirements, legacy layout validation, receipt consistency, weekly evidence fields, completion-time ordering, retained history, failure/subset visibility, stale README rejection, surrounding-byte preservation, marker ambiguity, unindexed files, and both CLIs. These checks prove offline structure and transformations, not that provider evidence is true or that a remote publication succeeded.
