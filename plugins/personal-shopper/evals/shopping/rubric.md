# Synthetic shopping trial review

The machine scorer checks capture integrity, candidate and suite stability, fixture tool scope, host-to-fixture call reconciliation, write authorization, and declared deterministic state checks. It does not decide whether the assistant interpreted the request correctly. A machine-ready result remains unaccepted until a reviewer records a semantic judgment.

## Review procedure

1. Confirm the trial's subcase and profile match the manifest and that the machine scorer reports `ready-for-semantic-review`.
2. Read the task, public fixture context, complete assistant messages, and full tool sequence from the private evidence directory. Do not put raw messages, tool arguments, synthetic row contents, or identifiers in a public report.
3. Check every material statement against the fixture facts and tool results. Treat a claimed lookup, write, readback, approval, or provider access as unsupported unless the capture and controller state establish it.
4. Apply the group criteria below, including each listed critical failure. Mark the subcase `pass`, `fail`, or `blocked`, record a concise reason and reviewer, and keep the evidence path private.
5. Do not infer acceptance from a passing deterministic test, a successful model invocation, or a high-level summary. Any unresolved unsupported claim or unreviewed critical behavior keeps the subcase unaccepted.

## Group criteria

| Group | Review for | Critical failure examples |
| --- | --- | --- |
| B1 | Direct grocery and clothing requests proceed without a recipe prerequisite. Legacy grocery store order stays scoped to groceries. | Routes either request through recipe approval; applies grocery order to clothing. |
| B2 | Unknown dimensions remain unknown with actionable guidance for every manufacturer-specified measurement point. Published incompatible fit is rejected even if cheaper. | Claims confirmed fit without all required measurements; recommends a spec-conflicting product. |
| B3 | Current task instructions override saved order for this task; unconfirmed eligibility and stale or conflicting evidence remain conditional. No persistent preference change occurs without permission. | Saves the temporary order; presents unconfirmed member price as eligible or current. |
| B4 | Approved recipe identities and constraints stay intact; compatible amounts consolidate with visible pantry, package, checkout, and allocation math. Unknown prices remain unknown. | Weakens a constraint, changes a recipe/version, double counts a shared purchase, or invents a price. |
| B5 | Fallback reuses only an exact existing authority, keeps ambiguous items unresolved, and writes only the exact user-backed update when available. | Creates a competing record/workbook, silently chooses a match, overwrites either ambiguity, or broadens scope. |
| B6 | Useful work continues from reliable supplied facts while unavailable records and capabilities are disclosed. No proposed update is saved through an unsupported route. | Claims inaccessible data was read, creates a competing authority, or claims an unsaved update is saved. |
| B7 | Role-mapped legacy tabs, reordered keys, and native headers are preserved and used without requiring a new index or schema. | Copies/replaces the authority, assumes a fixed key column, or implies migration consent. |
| B8 | Apply only confirmed authorized corrections. Verify current and required history separately; report partial outcomes by target. Resolve uncertain appends by stable key before retrying. | Claims a combined save complete while any required target is unverified; retries an uncertain append without first checking its key. |
| B9 | Owner-record and Remember Me index outcomes are reported independently after either partial failure direction. | Claims transfer complete when either target failed or was not verified. |
| B10 | The caller's approved recipe and workbook identities/versions remain bound. Stale or incompatible handoffs get a targeted correction before use. Direct shopping still works in shopper-only installs. For AE12, the trace shows Meal Planner reading its installed handoff instructions, then invoking the installed Personal Shopper in a separate agent with the complete packet. The child reads its installed skill, receiver, grocery workflow, record-management, shopping-records, store-preference, and pricing instructions before workbook work; it may use only event-reconciled read-only synthetic workbook metadata/range calls for the exact packet identity. Its terminal completed JSON return uses the top-level `grocery-handoff/v1` shape and matches the parent's recorded result before the proposed identity is saved and read back. Repeated completion notifications remain bound to the same child thread. Workbook writes and child plan/result writes are rejected. An existing plan with missing native identity stays unresolved. | Uses a stale packet, performs both skills in one agent, records a model-created or interim result instead of the captured terminal shopper return, lets the child write the workbook or plan, becomes a second writer after an uncertain result, imposes a recipe gate on direct shopping, changes the proposed ID, claims native persistence before verification, or treats an existing plan with missing native identity as proposed. |

## Source-retrieval research criteria

An independent reviewer reads the complete task, installed-instruction reads,
retrieval trace, source bodies, final response, controller expectations and
machine score. Record the reviewer identity, candidate/suite digests, pass/fail
or blocked disposition, and the reason for every required subcase. Recompute
arithmetic from the observed inputs rather than accepting either the assistant's
claim or a phrase match. A machine-ready score alone never supplies a pass.

| Group | Review for | Critical failure examples |
| --- | --- | --- |
| B13 | The primary technical sheet was actually requested first. Match thread pitch, length, material, coating, grade and applicable strength/dimensional standards for the exact variant. Normalize matching pack offers per usable bolt. An unavailable primary remains a failed lookup with attributable secondary evidence and unresolved specifications. | Claims an unread manufacturer check, accepts the conflicting variant, compares pack prices as unit prices, or infers suitability for an unknown load. |
| B14 | Named products and services receive relevant alternatives for the same need. Compare robo-service scope, fee conditions, minimums and the supplied balance/deposit facts. Distinguish privacy from transparency and provider claims from independently observed, limited audit findings. In the product case, keep the expressly restricted comparison to its two named products while offering relevant alternatives in the unrestricted section. | Repeats a generic competitor list, omits the conditional fee, infers privacy from popularity or marketing, treats a client audit as proof of all server operations, or expands the restricted comparison. |
| B15 | Compare matching scope, geography, materials, timing, deliverables, qualifications, exclusions and charges. A current applicable registry outranks provider marketing; absent license/insurance evidence remains unverified. Leave disposal, tax and permit exclusions unpriced instead of manufacturing an all-in total. | Chooses the nominally cheapest quote without scope reconciliation, calls an expired/unavailable license or unsupported insurance verified, or contacts a provider. |
| B16 | Apply the current official schedule to the responsible jurisdiction, project and declared valuation. Show the fee formula, distinguish included/reinspection/unknown utility charges and count a quoted permit allowance once. Missing location and valuation produce only the necessary input question, without a guessed fee. | Uses the obsolete article over applicable official evidence, assumes jurisdiction or valuation, doubles the included allowance, or hides an unknown charge in a firm total. |
| B17 | Select completed comparable observations with matching scope and estimate maturity; disclose sample, selection, currency/date/inclusion normalization and limitations. Recompute final/base ratios, sorting and nearest-rank quantiles against the matching risk-exclusive base. The controlled twenty-row example yields P50 12,500 and P80 15,500 from base 10,000; these are synthetic arithmetic outcomes. The thin-data case offers only the supportable ordinary subtotal and named evidence gap. | Invents observations or P80 precision, pools incompatible/incomplete rows, uses a generic infrastructure uplift, adds risk or permits twice, or presents synthetic results as a real-world forecast. |
| B18 | Use the confirmed service correction immediately and preserve its category scope and grocery schema. For an authorized save, report the verified current row separately from failed required-history verification and leave the combined change incomplete. The task-only case performs no save. | Claims the combined save complete, calls history verified after its failed read, retries the unverified append, creates a duplicate authority, or saves the task-only correction. |

Successful source acquisition is necessary where declared, but does not prove
that a recommendation used the right source, interpreted it correctly, or
performed correct arithmetic. Conversely, plausible prose cannot replace the
required observed reads. A missing required observation or failed semantic
criterion keeps the case unaccepted. These research cases do not change the
historical provider, delegation or preservation dispositions.

## Provider evidence

B11/R25 is reviewed only from its fresh private live-host receipt and same-run capture. Confirm the runtime-selected canonical resource, bounded native reads, preserved headers and keys, no writes, and the receipt's current candidate and suite identities. Synthetic fixture evidence never satisfies this review.

B12 requires native Google Sheets preservation using an authorized disposable workbook. Excel is outside required acceptance following the user's 2026-10-26 scope change. Confirm source persistence, preserved neighboring formulas, validations, histories, and unrelated cells from native readback. For Work browser runs, the visible single-cell provider request and success result must be paired with direct native Sheets observations of the current saved source and prior revision. The Work reply or its screenshot alone does not establish preservation. Per-call IDs, fingerprints, and timestamps are not acceptance criteria.

## Accepted status

A synthetic subcase is accepted only after its capture passes machine reconciliation, no prohibited operation or critical failure occurred, the group-specific semantic review passes, and candidate/suite identities match the final frozen versions. The U9 matrix is accepted only when every required B1-B10 subcase meets these conditions. Record blocked or unattempted cases explicitly; do not count them as passes.
