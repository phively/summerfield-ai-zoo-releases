# Superb Skills evaluation protocol

Status: Evaluation design and partition protection are reconciled; local deterministic and command-smoke paths are validated for their stated scope. The current acceptance matrix in ignored `output/` is the single Phase 1–7 checklist. Existing T5/T6/T8 task pages have been adjudicated read-only and remain qualified because their output bytes are unavailable. T8's task-reported one preflight, one smoke, and four-attempt comparison are not model-quality or holdout evidence. Installed-entry-point activation remains unobserved; actual Cloud model/effort remain unknown under the accepted qualification. Overall Phase 1–7 acceptance remains incomplete.

The product being tested is Superb Skills' reusable ability to design and evaluate other skills, including itself. This suite is an initial development fixture, not the shipped general protocol. Extend it with other-skill design tasks, inspect the generated instructions and test plans, and define separate target runtime trials. Shipped guidance belongs in Superb Skills' conditional references and tools and must operate without this repository's evidence files.

This protocol establishes trustworthy tests and result provenance before changing live Superb Skills behavior. The machine-readable suite is [superb-skills-evaluation.json](superb-skills-evaluation.json). It is a test design artifact, not a benchmark result and not an instruction or memory authority.

## Scope and evidence sources

The suite covers scope control, conditional routing, preference intake, ownership, recurring operational errors, candidate comparison, unavailable runners, source-input delivery gates, result persistence, and icon requirements. Its two source-delivery cases distinguish diagnosis of an unexecuted gate from designing a verifiable handoff. It includes negative cases for a one-time prompt rewrite and ordinary style editing: neither should trigger a benchmark or create a durable record.

The four user-supplied shared conversations are retained as pointers to user-reported failure symptoms. They were reviewed in the authenticated browser on 2026-09-21. The summaries below record what is visible without treating a conversation as an independent reproduction:

| Evidence | Failure symptom used for testing | What it does not establish |
| --- | --- | --- |
| `conv-1` (private locator omitted) | A phased plugin redesign propagated redundant “no history file” statements into several files. | It does not independently reproduce a clean-context delegated-skill failure or authorize reconstructing unavailable history. |
| `conv-2` (private locator omitted) | A substantial teach-me implementation was reported complete before a follow-up supplied the missing `1.8.1` version decision and synchronization work. | It does not establish a universal versioning rule beyond the target repository's conventions. |
| `conv-3` (private locator omitted) | A Meal Planner implementation was followed by a separate request for the parent-plugin version bump and README update. | It does not replace deterministic manifest, catalog, and synchronization checks. |
| `conv-4` (private locator omitted) | Evaluation progressed with unresolved runner/output controls, and the user later corrected that permission to rerun the test suite had not been given. | It does not authorize a new run or prove a particular runner configuration. |

No conversation transcript is copied into the repository. Any later execution must record whether each source remains accessible. Independent red-light reproduction is `not_run` for all four sources.

### Reviewed evidence ledger

| Evidence | Instruction or context | Observed response/action | Correction or lesson | Reproduction status |
| --- | --- | --- | --- | --- |
| `conv-1` | Continue a phased plugin redesign with current lifecycle boundaries. | Repeated “no history file” statements were added to multiple Career Coach files, duplicating an existing audit authority. | Keep lifecycle rules in the canonical audit reference and pass missing context explicitly; do not create explanatory duplication. | `not_run`; no clean-context delegated invocation is shown. |
| `conv-2` | Review and implement approved teach-me visual-art changes. | Completion and validation were reported before a user follow-up supplied the `1.8.1` version decision; plugin and mirrored metadata were then updated. | Make version decisions and applicable mirror synchronization part of the completion gate. | `not_run`; no separate release checklist artifact is supplied. |
| `conv-3` | Implement the approved Meal Planner formatting plan. | The implementation completed before a separate follow-up requested the parent-plugin version bump and README update. | Check version, metadata, catalog scope, and validation before declaring completion. | `not_run`; no pre-follow-up completion checklist is supplied. |
| `conv-4` | Complete a controlled comparison and continue remaining evaluation work. | Some runner limits, output/collection conditions, and authorization boundaries remained unresolved; the user explicitly corrected an unauthorized rerun. | Smoke-test permission, runner identity, output completeness, and result integrity; retain valid attempts and retry only failed/invalid work under the frozen configuration. | `not_run`; provider-credit and local-runtime failures are environment-specific. |

## Test classes

Each case declares its evidence mode:

- Deterministic checks validate schemas, hashes, partitions when defined, links, paths, package metadata, dimensions, and artifact preservation. They do not prove that an agent followed the intended behavior.
- Behavioral trials run the same prompt and rubric against a named candidate in a clean context. They record observable actions, loaded references, clarifications, prohibited actions, and output evidence.
- Environment checks verify runner availability, permissions, output locations, and installed activation. An unavailable dependency produces `blocked` or `not_run`, never a synthetic pass.
- Input-integrity checks verify that the runner actually materialized the supplied bytes before opening them or beginning candidate work. Acknowledgements, empty command records, null hashes, or unexplained mismatches leave input integrity unverified; preserve the response and stop before candidate scoring.
- Visual checks are required for raster-icon legibility at 32×32. Pixel dimensions alone are insufficient. Existing valid SVG assets are preserved unless a visual review identifies a defect.

## Red/green design

The supplied failure evidence becomes paired red/green criteria. The source summaries are historical/user-reported red-light evidence; the green side still requires a same-criterion behavioral trial. The visible `conv-1` exchange supports authority-duplication testing. Context transfer without history remains a separate preservation case derived from the reusable requirements and is not presented as reproduced evidence.

| Criterion | Red-light baseline evidence | Green-light requirement | Current status |
| --- | --- | --- | --- |
| `instruction-authority-duplication` | `conv-1` visibly records duplicated no-history guidance across files with an existing audit authority. | The target design identifies one canonical owner, removes or redirects duplicates, and preserves the target boundary. | User-reported source reviewed; independent reproduction `not_run`. |
| `context-transfer-without-history` | No supplied conversation is claimed as an exact reproduction. | The target handoff carries current inputs, source identities, unresolved issues, and authorization without relying on unavailable designer history. | Requirement-derived preservation case; trial `not_run`. |
| `version-and-mirror-synchronization` | `conv-2` and `conv-3` visibly show version/catalog work supplied by follow-up requests after implementation. | Target manifest and applicable dependent metadata are checked together before completion is reported. | User-reported source reviewed; revised check `not_run`. |
| `benchmark-preflight-before-rerun` | `conv-4` visibly records unresolved runner/output gates and a user correction about rerun permission. | A smoke run verifies authorization, runner identity, output path, non-empty output, complete event/result state, and failure handling before full execution; valid attempts are not rerun. | User-reported source reviewed; revised trial `not_run`. |

An observed failure is not itself a green result. A criterion is green only when the same meaningful criterion is rerun with complete evidence and passes. If the baseline cannot be reproduced exactly, retain the supplied evidence as historical red-light evidence and record the reproduction as `blocked` or `not_run`; do not silently replace it with a nearby case.

Already-passing behavior remains in the suite as preservation cases. A candidate must not improve one red/green criterion by breaking scope boundaries, authority ownership, confirmation behavior, or ordinary non-triggering requests.

### Partition, exposure, and holdout policy

The fixture manifest contains a versioned partition policy. It supports 3-, 5-, and 10-fold grouped development evaluation and uses five folds with a requested 10% holdout as the initial configuration when coverage permits. The issue's example validation ratios—30% for three folds, 18% for five, and 9% for ten—are recorded as configurable examples. Related cases are assigned to an indivisible group before fold assignment. The assignment rule, rounding rule, exact fold counts, and coverage result are recorded in the manifest; unsupported ratios or undersized suites are reported as `insufficient_coverage` rather than forced into a claim.

The current visible fixture cases are development evidence. They were accessible while the cases and guidance were designed, so they are ineligible to serve as an untouched final holdout. The manifest records that exposure and an empty final holdout rather than pretending that a filename or label protects them. A later target evaluation must create a separate target-scope plan from the target-supplied suite.

Before final validation, freeze the candidate, suite, rubric, permissions, and partition plan. Keep holdout content and grading criteria out of the implementation agent's context while allowing the grader to inspect the frozen rubric. The exposure log must record each exposure with case or group IDs, actor, role, timestamp, reason, and exposure type. Any revision after exposure requires a fresh final holdout; it cannot silently become another tuning round.

## Target-design cases and scoring

The suite must test Superb Skills as a reusable designer for unrelated targets, not only as a self-update. These cases inspect the produced target instructions, ownership decisions, and evaluation plan before any target runtime trial:

1. A preference-dependent skill with missing preferences and unavailable optional records. The design must include focused intake, an editable target-owned Markdown/YAML authority, task overrides, verified-lesson boundaries, and a precise unavailable-record fallback.
2. A target with competing implementation candidates. The design must define a common suite and rubric, candidate identity and hashes, requested versus actual runner configuration, bounded parallel trials, permission and output gates, and a clarity/maintenance selection criterion in addition to behavior.
3. A simple deterministic target with no preference dependency or candidate uncertainty. The design must remain simple and explain why no benchmark, durable record, or evaluation dependency is warranted.

Resolve each case's fixture references through the versioned [fixture manifest](fixtures/superb-skills/manifest.json). The manifest supplies bounded target packages, candidate contents, starting records, tool availability, scripted failures, and artifact expectations. A design case may require a plan only; it must not be scored as though unavailable hashes, outputs, or tools existed.

Score each target-design case independently on a 0–2 scale for:

- target identity, trigger, scope, negative route, and target runtime behavior;
- ownership, authority boundaries, dependencies, and DRY/YAGNI rationale;
- evaluation cases, red/green criteria, provenance, and runner/environment separation;
- preservation of supplied requirements, permissions, and existing target conventions; and
- clarity and maintenance cost.

Use these score meanings: `0` means absent, contradicted, fabricated, or unsafe; `1` means partial, ambiguous, or dependent on an unresolved decision; `2` means explicit, target-specific, and supported by an inspected artifact. Every dimension must be scored by a named grader. Any `0`, fabricated evidence, unauthorized persistence/action, rubric leakage, ignored task boundary, or missing owner for a persistent rule blocks acceptance regardless of the total. Record unresolved grader disagreements instead of converting them into a pass.

The design artifact must record the score, grader ID, evidence span, unresolved limitation, and whether a clean-context target trial is warranted. A structural fixture pass or a polished plan is not a behavioral pass. For red/green criteria, link the green result to the prior red or preservation result using the same case and criterion IDs, candidate boundary, and rubric version.

### Clean-context target-trial contract

When a target trial is warranted, resolve the fixture manifest and run the target package in a clean context with only the declared target inputs, approved references, and authorized tools. Before submission, put the case's operational permission envelope in the agent-facing prompt: requested response/output form; permitted write paths (or none); whether source/package or durable-record changes, commands/tests, network/secrets, commits, pull requests, or publication are allowed. Do not rely on evaluator-only manifests, READMEs, rubrics, or hidden setup notes to communicate a restriction the agent must follow; keep grading-only expected/prohibited actions separate from operational permissions. Keep a child target's routing outcome separate from the supervising designer's response: a child's `out_of_scope` result does not imply the designer must refuse an in-scope request. Record the target content hash, parent design case, runtime trial ID, starting state, prompt/case ID, available tools, loaded references, task output, clarification and permission behavior, prohibited actions, expected and actual final state, persistence/output evidence, and status. Keep designer-quality scores, target runtime results, and runner/environment checks separately attributable. If a target does not need a behavioral trial, record the reason and run the applicable deterministic check instead.

The suite includes invalid-result fixtures for missing output, absent permission, unavailable runners, and interrupted runs with valid retained attempts. These must produce `failed` or `blocked` records as specified by the suite and must never be counted as `passed` or as a complete comparison.

## Required result record

Every trial result must identify:

1. `trial_id` and case ID.
2. Candidate identity and content hash, plus the target package content hash when a downstream target trial is involved.
3. Suite ID/version/hash and rubric ID/version.
4. Requested runner, model, and reasoning effort; actual runner, model, and effort; adapter identity; and a specific substitution reason if they differ.
5. Requested and actual environment identities, permissions profile, concurrency, timestamps, and the execution fingerprint without storing secrets.
6. Loaded references, an `evidence_valid` flag, observed evidence, output reference, and a status of exactly `passed`, `failed`, `blocked`, or `not_run`.
7. A failure or blocking reason whenever the status is `failed` or `blocked`; `not_run` records why execution was skipped.

`passed` requires complete supporting evidence and no blocking failure. `failed` means the case ran and a required criterion failed, but it is scoreable only when `evidence_valid` is `true`; infrastructure failures such as a reader error, incomplete output, unverified cleanup, or candidate-integrity failure set `evidence_valid` to `false`. `blocked` means a safe run was impossible because a required dependency, permission, input, or environment capability was unavailable. `not_run` means no execution evidence exists. Neither `blocked` nor `not_run` may be counted as a pass, and invalid evidence cannot supply red/green credit or complete a comparison.

The protocol records requested and actual runner and model settings separately. `luna-xhigh` is an example/default suggestion only when current target/task evidence and environment availability support it; runtime selection may choose another available configuration or determine that a model run is unnecessary. No invocation, model identity, permission, or Cloud compatibility may be invented.

For external inputs, record path/label, byte count, hash, and route. Use the smallest supported bounded route; never rely on prior history or stale checkout copies. Before candidate delivery, prove that route with a harmless max-chunk canary and retain execution, exit status, matching hashes, and exact returned bytes locally. Follow the detailed gate in `skills/superb-skills/references/evaluation.md`. If any part is unverified, preserve the response and mark only this gate blocked; state the observed evidence, unknown, and smallest resolving action. Perform and verify that safe, authorized action before dependent design or scoring when possible. Pause for user input only when required input or authority is missing, or the attempted remedy exposes a concrete capability limit. A repair needs a new trial ID and applicable user authorization; never retry automatically.

## Persistence and history rules

Each comparison receives a new trial identifier, an exclusive current-run report, an append-only attempt log, and per-attempt output artifacts under the authorized destination. The report links to raw results, candidate and suite hashes, rubric version, configuration, status counts, recommendation, and limitations. Existing historical results remain unchanged and clearly labeled historical. A report is evidence, not a current instruction, personal preference, or durable operational lesson.

When a run fails or is interrupted, preserve its partial evidence with an explicit state and reason. Do not rerun automatically, overwrite the partial output, or describe the comparison as complete. A later rerun must have a new trial identifier and record why it was authorized.

If a prior run contains valid, complete attempts, retain them as immutable evidence and retry only failed or invalid attempts under the same frozen candidate, suite, rubric, permission profile, and runner configuration. A rerun is never justified solely by an inconvenient score, an unread report, or a desire to obtain a cleaner result.

## Execution boundary for future execution

This protocol defines cases, provenance, and reusable partition/holdout controls only. Runner implementation and live comparison require separate authorization. No provider calls, benchmark runs, installation, publication, or live skill behavior change is authorized by this protocol alone.
