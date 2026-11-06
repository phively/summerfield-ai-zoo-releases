# Remember Me memory benchmark: development protocol

This package defines a deterministic synthetic corpus and a local trace/scoring adapter for comparing four memory-retrieval treatments. It includes offline fixture/scorer controls and opt-in CLI runners. A protocol describes how to evaluate; it does not authorize model calls, establish a behavioral result, change Remember Me guidance, or demonstrate live-provider behavior.

## Calibration and corpus identity

`manifest.json` pins the structural calibration metadata and source identity used by the synthetic fixtures. The fixtures reproduce declared byte sizes and heading shapes without retaining source record payloads or personal facts. Calibration describes one illustrative snapshot, not population estimates or recommended thresholds. Read the manifest when reproducing fixture identities.

`fixtures.py` builds exact-size UTF-8 records, synthetic authoritative topics, a shorter routing index, and fixture/gold identities. The identity includes the calibration metadata, scenario, candidate and exact record-content hashes. A changed calibration revision therefore produces new fixture and reference identities. The source-shaped detailed index keeps the observed heading counts and non-frontmatter, non-table representation. The sample communication topic is exactly 2,428 bytes for index-scaling cases.

The development corpus has 29 declared scenarios across eight families: index scaling (2, 4, 8, 16, 32, 40 and 64 KiB), topic scaling (4, 8, 16, 32 and 64 KiB), multi-source/identity/freshness, evolution, staged audit/recovery, amortized read/save/audit sequences, authorized index maintenance at 16, 40, 64 and 80 KiB, and the combined `closeout-sequence-40k`. The fixed fact inventory retains exact synthetic values, attribution, uncertainty, authoritative record IDs, anchors and protected-item status. Large fixtures use unique structured synthetic entries distributed across existing sections rather than repeated HTML-comment padding.

The index-size trigger keeps the existing strict-greater-than boundary and is tested just below, at, and above 8/32/48/64 KiB. The 8/32/48/64 KiB treatments use the same 40,505-byte source-shaped index: the existing 8 KiB setting and 32 KiB alternative are due, while 48 and 64 KiB alternatives are not. The 8 KiB setting is the incumbent control, not a representative candidate threshold for the observed index. The alternatives span below and above this one sample; they are not recommended defaults or population estimates. Authorized-maintenance scenarios at 16, 40, 64 and 80 KiB distinguish each treatment and exercise both sides of the 64 KiB trigger. Separate scorer controls derive age, material-change-count and growth reasons from controller-held measurements; missing or zero growth baselines remain unavailable instead of inventing a trigger.

## Matched candidate design

All four candidates receive the same scenario task, authoritative topics and common read-tool envelope. The public trial packet also gives each candidate its assigned retrieval strategy: full-record reads for A/B, or heading-map navigation with expansion when needed for C/D. This makes the strategy experimentally actionable while keeping candidate IDs, gold answers, protected-item labels, fault schedules and grading criteria in controller-only data. Only index detail and retrieval strategy vary:

| Candidate | Index | Retrieval |
| --- | --- | --- |
| A | Detailed | Full reads |
| B | Compact routing summary | Full reads |
| C | Detailed | Heading map, selected sections and expansion |
| D | Compact routing summary | Heading map, selected sections and expansion |

A and C share byte-identical detailed indexes; B and D share byte-identical compact indexes. All four share byte-identical authoritative topic and source records. The compact index retains ownership, identity, freshness and stable topic pointers. Exact facts, attribution and uncertainty remain in the authoritative records for every candidate. The assigned retrieval instruction is the declared treatment; the public packet still omits candidate IDs, gold answers, protected-item labels, fault schedules, and grading criteria.

## Local adapter and operation accounting

`adapter.initialize_trial(root, bundle)` creates a new trial directory and refuses a non-empty one. The trial separates a public-facing directory from a controller directory. Only the generated public JSON task packet contains the task, record metadata and tool contract. `amortized-update-audit` and `closeout-sequence-40k` explicitly authorize one exact `save_append` to `topic-communication`, name the expected version and supply the synthetic text to append. Authorized-maintenance packets expose staging and promotion only when their declared trigger is due; the controller stores its approval decision separately and binds it to the staged index digest, expected version and completion date. No other scenario exposes either write authorization. Gold, protected inventory, save/maintenance control, initial state, trace and grading data stay in controller-only trial files, including initial, mutable and final state plus the event trace. This directory separation is a test-fixture boundary, not an enforced candidate sandbox; it does not enforce isolation for model trials.

The local MCP bridge is `python adapter.py serve TRIAL_ROOT`; the controller can use `python adapter.py call TRIAL_ROOT --request JSON` for deterministic controls and `python adapter.py snapshot TRIAL_ROOT` for the final-state capture. All scenarios expose the three read operations below. `amortized-update-audit` and `closeout-sequence-40k` also expose `save_append(record_id, expected_version, append_text)`. The controller accepts that operation once, for the authorized record and version, with byte-for-byte exact text; it appends the text and advances the record version. In authorized-maintenance scenarios, `stage_index_maintenance` writes a candidate beside the recoverable original without changing canonical state. A retry with the exact same record, version and candidate digest returns the persisted stage receipt without writing it again; conflicting retries fail. The scorer counts that receipt as one persisted stage while retaining all attempts and retry counts in measurements. An out-of-band controller action records either approval or denial for the exact staged digest. `promote_index_maintenance` accepts only the matching positive approval at the expected version; successful promotion changes the index content, version and audit date. Rejected, unapproved, tampered, stale-version or repeated writes are traced without changing canonical state or audit metadata.

The three staged-audit scenarios expose a family-level public scenario ID and a readable `staged-candidate` record containing its proposed fact inventory, pointer references and last verified audit date; exact variant IDs remain in controller gold. The public task and `staged_review_policy` tell the agent how to inspect that evidence; controller-only state holds the expected comparison. `audit-loss-control` omits a protected fact, `audit-pointer-recovery` has a stale topic anchor, and `audit-authorized-review` has reached the 180-day review interval but has no write approval. None of these scenarios exposes `save_append`. The scorer derives missing facts, unresolved anchors and review due status from the candidate record and public policy, then checks the answer's `audit_review` disposition, item/pointer findings, recovery anchor, due status, authorization claim, maintenance action and trace-backed candidate read. It does not grade from the scenario label alone.

- `read_full(record_id, reason)` returns the full exact record. `reason="fallback"` marks an actual fallback read.
- `read_heading_map(record_id)` returns only headings found in that record, with stable anchors, heading levels, exact UTF-8 byte boundaries, record identity and version. It includes no relevance or gold labels.
- `read_section(record_id, anchor)` returns the exact byte slice for the selected heading through the next same-or-higher-level heading, with record identity, version, offsets and a content hash.
- `save_append(record_id, expected_version, append_text)` applies the one controller-authorized synthetic append in `amortized-update-audit` and `closeout-sequence-40k`; the task must read the updated record back to verify the saved version and content.
- `stage_index_maintenance(record_id, expected_version, candidate_content)` creates one digest-bound recoverable candidate and charges the request, returned candidate and staged bytes.
- `promote_index_maintenance(record_id, expected_version, stage_id, candidate_sha256, approval_id)` performs one version-checked transition only after the controller records approval of that exact staged candidate. Its result exposes the new version and audit date for full readback.

The adapter records each request, result, content or append bytes, returned JSON bytes, SHA-256, record versions and `time.perf_counter_ns()` elapsed time. Read returned bytes stay in read totals; save request bytes and successful append bytes are reported separately. The scorer replays the trace from the independent initial state, validates reads against the record version and audit date at that point, applies only the authorized append or promotion, and compares the replay with an independently captured final state and recovery-state digest. A full record disguised as a section fails trace integrity and cannot receive section-read savings credit. The update/audit scenarios require a full readback after the save, exact preservation of the authorized delta and every other record, protected-inventory review, and pointer resolution. The maintenance scenario checks that the trigger packet matches its controller copy and initial state, the staged candidate preserves all protected facts and pointers, the approval binds to its digest, the promotion advances version/audit date once, and the promoted index reads back exactly. For the `amortized-update-audit` and `closeout-sequence-40k` answers, the candidate must include a `protected_inventory` array with each item’s `value`, `authority_id`, `anchor`, `attribution`, and `uncertainty`, plus trace citations to successful post-save reads of each authoritative record. The scorer matches items by authority and heading anchor, not by hidden controller IDs; those labels remain undisclosed. In the combined closeout, only the one gold-authorized topic append and exact version transition are allowed; the topic must be read back independently, and every other authority must equal its initial record. The scorer never accepts an inventory supplied separately from the answer. Rejected write or other unsupported operation attempts remain in the trace and fail even when the store is unchanged.

The heading/section route is evaluation support. These controls show only that this synthetic adapter can return bounded bytes; they do not show that the live Library route supports equivalent reads.

## Scoring and evidence fields

`score.score_trial(...)` applies independent checks for:

- complete exact recall, including attribution, authority, uncertainty and stable anchor;
- evidence references that point to a real traced read of the fact's authoritative record;
- heading-map and section boundaries, record/version identity, returned-byte totals and response hashes;
- exact final-state equality to the one permitted append, including preserved unrelated records, plus a later readback of the written version;
- rejected unauthorized operations, even when they did not alter the final store;
- exact protected inventory retention for update audits, with candidate-reported inventory bound to post-save trace evidence;
- evidence-derived disposition of staged candidates, including lost items, stale-pointer recovery, due review without write approval and a trace-backed read of the staged record; and
- trigger-to-packet binding, digest-bound staging approval, one versioned promotion, semantic pointer/fact preservation, recovery snapshot identity and post-promotion audit-date readback; and
- resolvability of every required pointer in both the final record set and index text.

A cheaper response with a missing exact constraint, fabricated fact or unsupported citation fails. Cost cannot compensate for a critical omission, wrong authority, lost protected item, unresolved pointer, unauthorized attempt, or false section-read trace.

Each score records index and per-topic byte sizes; read calls by operation; topic and fallback reads; charged read bytes by operation and total; save and maintenance request, stage, promotion and response bytes separately; monotonic adapter time per operation and per-trial sum; mutation attempts; and token usage provenance. Provider-reported input/output/cached token counts stay separate from tokenizer estimates, both overall and by supplied phase (for example, read, update, audit or maintenance). An absent phase remains unavailable; the scorer never fills it with zero. Missing or estimate-only telemetry yields `actual_total_tokens: null` and status `unavailable`; it is never converted to zero. Adapter timing is not presented as end-to-end session latency. A one-control result does not support median, p95 or candidate-selection claims.

## Deterministic controls and execution boundary

`plugins/work-smarter/tests/test_remember_me_benchmark.py` covers the compliant reference, an incomplete lower-cost answer, unavailable versus estimated token telemetry, a rejected unauthorized write, successful authorized update plus readback, wrong-target and altered-content saves, altered or lost unrelated content, required protected-inventory and pointer audits, distinct multi-source and identity-conflict evidence, all three staged-audit dispositions with positive and negative controls, actual heading/section reads, a full-file-as-section false trace, calibration identities, the matched four-candidate matrix, structured synthetic scaling entries, exact trigger boundaries and missing metadata, and maintenance approval/denial/tampering/recovery controls. The protocol and manifest remain development evidence; no final holdout is defined or run.

When the local test runner is available, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider plugins/work-smarter/tests/test_remember_me_benchmark.py
```

The deterministic controls perform no model call, host activation, live record access, or provider connectivity check. The development scenario list is not a behavioral result and is not a sealed holdout. Strict acceptance comparisons require an externally enforced restricted candidate runtime, fresh isolated stores/sessions, the same tasks and tool envelope, independently reviewed semantic outcomes, a separate holdout custodian, and an agreed model-trial allocation.

## Opt-in development runner

Obtain explicit authorization for the runtime, model, effort, tool access, evidence destination and bounded trial allocation before launching model attempts. This protocol and its examples grant no run permission. Freeze those choices for a matched comparison.

`run_pilot.py` accepts a declared scenario and candidate for a single-turn task. It includes the public instruction bundle, source hashes, public packet and response schema. Answers use candidate-chosen labels; scoring matches public authority and heading anchors rather than controller-only fact IDs. It checks values, attribution, uncertainty and trace-backed source operations. For heading treatments, a heading-map read must precede a section or fallback read of that record. A later map cannot repair an earlier read. Failed processes, missing completion, malformed answers and invalid treatments cannot pass.

Use `run_study.py run --root STUDY_ROOT --scenario SCENARIO --candidate CANDIDATE` for a bounded comparison. One shared study root contains the launch ledger and a fresh directory per cell. The runner admits the four declared retrieval workloads and `closeout-sequence-40k`, with A/B/C/D once per workload. Each process start, including continuation, is charged before launch; the panel cap is 26 starts. Behavioral failures cannot be retried. Direct `run_pilot.py trial` calls are a single-trial compatibility interface and do not enforce that shared panel budget.

For `closeout-sequence-40k`, the first launch is persistent and the second resumes only its captured session ID. The controller checks staged bytes, protected topic records and pointer bindings before recording exact-digest, version-bound approval or decline. The continuation promotes only an approved candidate and reads it back. Scoring requires the exact authorized topic append, its full readback, post-save protected inventory evidence, staged approval and promoted-index readback.

The maintenance runner defaults to `danger-full-access` because the adapter writes local state. Controller files and host resources remain accessible to candidate shell commands; prompt restrictions are procedural. Use this route only for an explicitly authorized exposed development trial. If a configured boundary prevents execution or evidence capture, retain the failure and obtain authorization for a changed route before another model attempt. Never describe this runtime as enforced isolation or an unseen holdout.

Example command shape, to use only after authorization with a new study root:

```sh
python plugins/work-smarter/evals/remember-me-benchmark/run_study.py run --root output/remember-me-benchmark/NEW_STUDY --scenario index-8k --candidate A --sandbox danger-full-access
```

### Recovery and evidence

The compatibility `recover` action is restricted to the runner's defined `closeout-sequence-40k-A` continuation path. It is not a general retry mechanism. Before using it, verify eligibility against the exact failed run, obtain the required authorization, preserve the original result and freeze an append-only amendment. Resume the same session with its persisted controller prompt; never rerun preparation, repair a model answer, or retry a behavioral failure. Other blocked measurements remain incomplete.

Requested model and effort are recorded from runner arguments. Personal CLI configuration, apps, plugins, hooks and subagents are disabled; authentication uses the existing sign-in. Without an authoritative served-model receipt, the served model remains `unverified`. Provider usage comes only from captured `turn.completed` events. Sum completed turns for a resumed sequence; cached input is a subset of input, not an additional charge. If any completed turn lacks usage, whole-sequence actual usage remains unavailable.

Retain each attempt's prompt, raw CLI output/stderr, answer, controller state, trace and score under ignored root `output/`. The runner refuses a populated trial root. Keep historical authorization and observed acceptance in separate internal evidence records. Existing records cannot authorize a new launch or establish that changed instructions passed.

A one-run-per-treatment comparison provides descriptive observations, not a winning policy, uncertainty estimate, threshold recommendation, provider latency or live Library section-read support. Do not reuse exposed cases as holdouts, weaken scoring to pass a failure, or change runtime settings within a matched comparison.
