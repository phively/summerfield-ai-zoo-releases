# Evaluation and architecture comparison

Use this reference to design tests, compare architectures, validate implicit activation, diagnose observed failures, or determine whether a revision improves performance.

## Build the evaluation set

Include representative cases for:

- explicit invocation;
- indirect requests expressing the intended goal;
- incomplete inputs requiring a focused question;
- adjacent requests that must not activate the skill;
- ambiguous vocabulary shared by multiple skills;
- mixed workflows that may require coordination;
- unavailable tools or references;
- likely fabrication, authority, or compatibility failures; and
- unsupported explicit and implicit comparisons, supported comparisons with a named reference set, and clearly labeled subjective comparisons; and
- regressions in existing triggers and outputs.

For every case define the input, intended activation and behavior, observable success criteria, and failure criteria. Do not encode only ideal outputs; evaluate process requirements such as confirmation, source use, file preservation, and prohibited actions.

For evaluations based on mutable source material, the plan must name the authoritative inputs and who updates them. State the maintenance procedure: when an input changes, replace affected fixtures and reference responses, confirm the criteria still apply, and rerun affected checks before freezing. Keep prior versions as historical evidence; apply this only where inputs can materially change. Merely listing cases involving changed inputs does not satisfy this requirement.

When designing another target's evaluation, provide a target-specific scorecard separate from the designer's own score. Define behavior-linked dimensions, an anchored scoring scale with evidence requirements, critical failure gates, and a minimum pass or candidate-selection rule. Include clarity and maintenance alongside behavior and speed when comparing architectures. A case list or unweighted measures alone is not a scorecard. If the task or packet cannot support a required score, mark that limitation instead of inventing evidence.

## Check feasibility before freezing criteria

Before freezing a benchmark or gate rubric, run a bounded feasibility pilot through the intended runner, permissions, input delivery, evidence capture, scoring, and local artifact retrieval. Use harmless development fixtures and the applicable run/output authorization. In planning-only work, record the pilot as pending and the criteria as provisional.

1. Cover each distinct critical gate and evidence requirement with the smallest set of controls. A deliberately compliant reference must pass every applicable gate; controls that deliberately violate a critical requirement must be rejected for that requirement. Calibrate content scoring with reference outputs. For process gates, execute the required operations and capture actual events and exit status; proposed actions or self-reports cannot prove feasibility.
2. For a model-assisted pilot, default to **GPT-6 Luna / Medium** (requested model `gpt-6-luna`, reasoning `medium`) when available on the selected route. [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) is an efficient model for focused tasks; Medium is a practical pilot default, not a guarantee of success. Recheck model and effort availability at launch. If unavailable or inadequate, record an available, inexpensive alternative and the reason. Use deterministic checks without a model when sufficient. Request **Standard** speed; never enable **Faster/1.5x**. Apply the runtime-selection rules below and record unavailable actual settings as unobserved.
3. Verify that the compliant control's required evidence can be captured, retained, retrieved, and scored through this exact route. Distinguish a model mistake from an ambiguous criterion, unavailable capability, or missing telemetry: one generated failure does not prove that a criterion is impossible to satisfy. Repair the control or diagnose the route before changing the requirement.
4. Resolve feasibility failures before freezing. Preserve the intended behavioral requirements; do not lower thresholds simply to get a pass. If the observable acceptance scope must change, explicitly document the limitation, applicable authorization, and new rubric version. Preserve prior frozen criteria and results under their original identities.
5. Retain control inputs and hashes, expected and observed gate outcomes, requested and observed settings, executed operations and status, complete outputs, artifact retrieval, and unresolved limitations. Freeze only when applicable controls pass and violations are detected. Pilot success establishes feasibility for the tested route and criteria; it does not establish candidate quality or guarantee every case will pass.

For a planning-only deliverable, explicitly carry the pilot acceptance conditions into the target plan: actual operations and command exit statuses are retained; compliant references pass all applicable gates; violating controls fail their intended gates; and evidence failures are resolved before freezing. Also state that future validation receives stable whole-group IDs before partitioning, independent starting states, and protection from candidate-development access. A shortened summary must preserve these conditions.

Keep pilot fixtures and results as exposed development evidence. Do not access final holdout content or grading criteria. Use the existing clean-context input checks and comparison smoke procedure when they cover the pilot requirements; avoid duplicating those runs.

## Compare architectures

Use the same prompt set, environment, model configuration, permissions, and scoring rules for each candidate. Measure when observable:

1. activation precision and recall;
2. false-positive and missed activation rates;
3. number of skills and references loaded;
4. relevant versus irrelevant instruction volume;
5. clarification turns;
6. completion of task-specific requirements;
7. contradictions or constraints lost across handoffs;
8. unsupported claims or actions;
9. end-to-end latency; and
10. maintenance surface, including duplicated rules and contracts.

Prefer high precision on negative and adjacent prompts before marginal recall gains. Accept a more modular design only when it produces a meaningful behavioral improvement without a disproportionate rise in multi-skill activation, handoff failures, or duplicated authority.

## Resolve blockers at each gate

Stop dependent work at the first failed gate. Report what was observed, what remains unknown, and the smallest safe, authorized diagnostic or repair; perform and verify it before continuing when possible. Do not call the whole phase blocked while that action remains available. Ask only for missing input or authority, preserve completed evidence, and resume at the failed gate without rerunning completed work.

## Select a runner and model at runtime

Treat runner and model choice as evaluation-time configuration. Named defaults in this reference remain conditional on current availability and task suitability. `luna-xhigh` is an example of a requested default for independent cloud trials when current evidence supports its cost/intelligence/time trade-off; it is not a required model name, effort level, or invocation.

Before a run:

1. Inventory the models, reasoning levels, runners, permissions, and output paths exposed by the selected route; mark controls and telemetry that Cloud does not expose as unobserved.
2. Select a configuration that fits the target task and current benchmark evidence, balancing expected quality, cost, and human or elapsed time. Prefer a lower-cost model for simple or interactive work when it is adequate, and reserve higher-effort configurations for uncertainty that justifies them.
3. Record the selection policy and evidence basis without copying private conversations, secrets, or inaccessible links into the target package.
4. Record requested and actual runner, model, reasoning effort, concurrency, environment, and any substitution reason as separate fields.
5. Verify the runner, environment, permissions, and output route needed for the trial. Cloud's missing model or reasoning controls or telemetry do not by themselves block an authorized run: record the requested values and mark actual values unobserved. Never silently substitute a runner or claim an unobserved setting was verified.
6. Never select the product's Faster/1.5x speed setting for delegated tasks. Request standard speed where a control exists. Cloud's missing speed selector or telemetry is not a launch gate: mark actual speed unobserved, and do not claim standard speed was verified. Stop if Faster/1.5x is visibly enabled. Record requested and observed speed separately from model and reasoning effort.

Apply this selection process when designing and evaluating another skill as well as when evaluating Superb Skills itself. A deterministic target with no candidate uncertainty may not need a model run at all.

## Verify inputs before a clean-context trial

When a trial depends on files or context supplied outside the runner's checkout, design an explicit delivery gate before the trial:

- Identify each authoritative input by path or label, exact byte count, SHA-256, and delivery method. Prefer a supported attachment or bounded payload chunks; do not rely on prior conversation history or an unverified checkout copy. Verify each needed transfer within its execution rather than assuming temporary files persist across task turns.
- Before sending, estimate total and per-call payload size and choose the smallest supported route that does not repeat source bytes. If an agent stops before a call because it anticipates overflow, record that as an unverified concern—not an observed platform limit—and do not replay the same oversized call. For chunked delivery, cap each call, number non-overlapping chunks, and verify the reconstructed source hash.
- Before sending candidate sources, prove the chosen route with harmless data at least as large as the largest planned chunk. Capture the executed operation, exit status, exact output/hash, and local artifact retrieval through the same route. A smaller canary or a capacity estimate alone does not prove the planned transfer fits; if the check or retention cannot be evidenced, stop and report the missing capability.
- Have the runner materialize or decode each input into a unique, isolated temporary directory, then hash the bytes actually written before opening the files or starting design work. Keep the repository read-only when the task prohibits repository changes.
- Count the gate as passed only when the execution record shows the operation actually ran, its exit status, and matching byte counts and hashes for every required input. Acknowledgement, a narrative assertion, `commands_run: []`, null hashes, or unexplained `exact_match: false` is not proof of delivery.
- On a missing payload, failed decode, or unexecuted gate, preserve the complete response and any partial files, mark input integrity unverified, and stop before candidate design or scoring. Do not substitute older checkout files or treat the delivery failure as a candidate-quality result.
- Retain the source-delivery record and complete trial outputs locally before adjudicating. Any repaired attempt uses a new trial ID and the user's applicable authorization; do not retry automatically.

## Use one comparison input contract

When repeated comparison is warranted, supply four explicit inputs to the comparison helper:

Read the [comparison input contract](evaluation-input-contract.md) before constructing these files or invoking the helper. Use its preflight command to validate the inputs and obtain the smoke-test fingerprint without starting trials.

- `candidates`: at least two named files or package directories; hash the complete source before execution;
- `suite`: a versioned development-suite object with `suite_id`, `suite_version`, `rubric_id`, `rubric_version`, development cases, and optional red/green criterion pairs. Each supplied case has an ID and deterministic checks only when the selected adapter can score them; final holdout content and grading checks remain outside this file;
- `partition_plan`: a normalized grouped-development plan with the complete case list, whole development groups, folds, and holdout groups; and
- `configuration`: requested and actual runtime settings, target identity and hash, permissions, bounded concurrency, command details when applicable, and an inspected smoke artifact bound to the execution fingerprint.

Treat `authorization.run` and `authorization.output` as records of explicit user permission for the named run and artifact destination, never as defaults, recommendations, or proof of technical capability. In a preparation-only or not-yet-authorized state, keep both false and do not execute preflight, smoke, or comparison steps that the user has not authorized. Set either true only when the user explicitly authorizes that action and destination. A prior failure or lesson is not permission; smoke authorization does not by itself authorize the full comparison unless the user explicitly authorized both. Stop at each authorization boundary. Any later authorization change changes the execution fingerprint and requires fresh preflight before further execution.

The helper runs development cases only. Its suite must contain exactly the partition's development cases; final holdout IDs may appear in the partition, but their content must remain in a separate authorized validation workflow. A green result references its red or preservation result by criterion, case, candidate boundary, and rubric version; a structural check cannot supply the green behavioral evidence.

The report is a new immutable artifact. It includes candidate, target, suite, rubric, the complete normalized partition, runtime, output, attempt, red/green outcome, and limitation identities. Per-attempt output is preserved under the authorized artifact destination. Every declared artifact pattern must match and be retained; a missing pattern is a failed trial. Reject any report, sidecar, or artifact destination that overlaps a candidate, target, dependency, or other canonical input. Existing reports and attempt logs are never overwritten.

The command adapter hashes exact input bytes and runs each command in a bounded process tree. It records requested limits, retained and total output bytes, truncation, termination reason, containment method, cleanup verification, and an `evidence_valid` flag. A timeout, output-limit breach, failed tree cleanup, reader error, nonzero exit, missing artifact, candidate mutation, empty output, exception, or interruption is failed or incomplete evidence with `evidence_valid: false`; it cannot supply score or red/green credit. A declared check that runs successfully but fails remains valid red evidence. A comparison is complete only when every expected trial has `evidence_valid: true`.

## Partition development cases and protect the final holdout

Treat partitioning as part of the target suite contract. Keep the designer evaluation and each downstream target evaluation in separate plans; never let a designer case or result silently become evidence about target runtime behavior.

1. Assign a stable group identifier before partitioning. Keep paraphrases, related scenarios, and cases sharing a starting state in one group so they cannot cross a validation or holdout boundary.
2. Record the suite identity, grouping key, assignment algorithm, seed or stable inputs, exact case and group counts, fold count, fold membership, rounding rule, and coverage decision. A reproducible plan must be derivable from the recorded data without inspecting the agent's hidden context.
3. Support grouped development evaluation with 3, 5, or 10 folds. Use five folds and a 10% holdout as the initial defaults when coverage permits. When the issue's example ratios are appropriate, record 30% validation exposure for three folds, 18% for five folds, or 9% for ten folds; these are configurable examples, not mandatory ratios for an undersized suite. For each fold, record the validation groups and the training groups used to develop the candidate. Call the process cross-validation only when every candidate revision is developed using the corresponding training partition and evaluated on its unseen validation fold; otherwise label it grouped development evaluation.
4. Calculate the requested holdout count with a declared deterministic rule such as round-half-up, then preserve whole groups. If the requested ratio, fold count, or minimum coverage cannot be met, record the exact achievable counts and `insufficient_coverage`; do not force a small suite into an unsupported claim.
5. Freeze the candidate, suite, rubric, permissions, and partition plan before exposing the final holdout. Keep holdout case content and grading criteria outside the implementation agent's accessible context. The grader may access the frozen rubric and holdout, but the tested agent may not receive the rubric or holdout before final validation.
6. Log every holdout exposure with the case or group identifiers, actor and role, timestamp, reason, and exposure type. If a revision is made after any final-case exposure, record the exposure and create a fresh holdout before calling the next run final. A file named `holdout` without an access record is not protection.

The partition record is evidence about evaluation design, not a benchmark result. Preserve visible development fixtures as development evidence only; do not relabel them as an untouched holdout after the fact. Development and holdout groups must have distinct identities so related cases cannot cross the boundary. Downstream target plans must repeat the same controls using the target's own suite, package, artifact destination, and authorization.

## Test sequence

1. Establish a baseline before revising the architecture.
2. Change one architectural or metadata variable at a time when practical.
3. Run deterministic structural checks and the targeted prompt set.
4. Forward-test judgment-heavy workflows in clean contexts without revealing expected answers or suspected defects.
5. Compare observed behavior with the predefined criteria.
6. Revise only where evidence identifies a problem.
7. Rerun affected cases and a suitable regression set.

Treat simulated or clean-context trials as evidence about behavior, not proof of live marketplace activation, production latency, or tool availability.

The reusable comparison helper under `scripts/` accepts target-specific candidates, suites, partition plans, and configuration records. It runs only the partition's development cases; a non-empty holdout remains outside the comparison until a separately authorized final-validation workflow. A declared red/green criterion is demonstrated only when every paired result has valid declared-check evidence, the red candidate has an observed declared-check failure, and the green candidate passes the same checks; infrastructure failures are `invalid_evidence` and cannot count as red. Otherwise the report cannot automatically select a candidate. Candidate mutation or failed post-trial hashing invalidates the trial. It provides a deterministic adapter for local checks and a separately identified local command path; neither one proves Cloud compatibility. Inspect the smoke output and permissions before allowing a full run, preserve failed or interrupted attempts, bound stdout and stderr retention, and require verified whole-process-tree cleanup before treating a command result as usable. Do not add retries or resume behavior unless observed trial cost justifies them. A nonzero result code means the report was invalid, incomplete, or had no eligible candidate.

## Complete the delivered evaluation plan

For a written evaluation plan, include the pre-freeze feasibility contract even when execution is prohibited: retain actual operations and exit statuses, require compliant controls to pass every applicable gate and violating controls to fail their named gates, and resolve evidence failures before freezing. Give future validation independent starting states and stable whole-group IDs, keep related cases together, and protect their prompts and criteria from candidate development. Planning leaves these checks pending; it supplies no execution or acceptance credit. Detailed procedures remain in the routed references.
