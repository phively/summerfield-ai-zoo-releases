# Candidate comparison input contract

Use this contract when a target skill has competing candidates and a repeatable comparison is warranted. The contract applies to unrelated target skills and to Superb Skills itself. It does not authorize provider calls, external writes, or a final holdout run.

## Files and command

The comparison helper accepts at least two candidate arguments and four JSON files:

```text
python compare_candidates.py \
  --candidate baseline=path/to/baseline \
  --candidate improved=path/to/improved \
  --suite path/to/suite.json \
  --partition-plan path/to/partition.json \
  --config path/to/config.json \
  --output path/to/current-report.json \
  --adapter deterministic
```

Candidate paths may be files or package directories. The complete candidate content is hashed before execution; package directories must not contain symbolic links or junctions. Candidate and trial identifiers may contain user-defined text, but the helper must map them to collision-resistant filesystem names. Command trials receive candidates below a dedicated `candidate/` path, keeping helper-generated files such as `suite.json` separate from candidate content. The output report, `.attempts.jsonl` sidecar, and `.attempts/` evidence directory must be new paths for each run.

All content hashes use exact file bytes. The helper does not normalize line endings or decode text while hashing, so a byte-level change in a candidate, suite, dependency, target, or smoke artifact changes its identity. Hashes describe the content actually supplied to the runner.

Run preflight before the smoke trial by adding `--preflight`. Preflight validates the candidates, suite, partition, configuration, red/green boundaries, target identity, and command dependencies. It prints the execution fingerprint and performs no trial, report, or artifact write.

After preflight, run the authorized smoke trial using the printed fingerprint. Inspect its output and permissions, record its non-empty artifact hash, set `smoke_test.status` to `passed`, and copy the same fingerprint into `smoke_test.execution_fingerprint`. A normal comparison refuses a missing, changed, or unbound smoke artifact.

## Candidate and suite schema

Each suite has:

```json
{
  "suite_id": "target-evaluation",
  "suite_version": "1.0.0",
  "rubric_id": "target-rubric",
  "rubric_version": "1.0.0",
  "cases": [
    {
      "id": "required-behavior",
      "required": true,
      "critical": false,
      "checks": [{"type": "contains", "value": "expected text"}]
    }
  ],
  "red_green": [
    {
      "criterion_id": "criterion-name",
      "red_candidate_id": "baseline",
      "green_candidate_id": "improved",
      "case_ids": ["required-behavior"]
    }
  ]
}
```

Checks are deterministic adapter checks. A passing check does not establish model quality or Cloud compatibility. Required and critical cases must pass before a candidate can be selected. A red/green entry is demonstrated only when the named red candidate has an observed declared-check failure and the named green candidate passes the same checks; a command failure, candidate mutation, blocked attempt, or missing result cannot manufacture red/green evidence. If a declared criterion is not demonstrated, the helper reports the limitation and does not automatically select a candidate.

## Partition schema

The partition must use `scheme: grouped_development_evaluation`, list the complete planned case-ID universe once, and include `grouping_key`, `assignment.algorithm`, `assignment.version`, deterministic non-empty `assignment.stable_inputs`, `requested_fold_count` (3, 5, or 10), `requested_holdout_percent`, `rounding_rule: round_half_up`, `coverage.status` (`sufficient` or `insufficient_coverage`) and reason, and an `exposure_policy` with a schema-valid exposure log. Keep related cases in whole groups, keep development and holdout group IDs distinct, list each development case in exactly one fold, and include the complementary `training_group_ids` for every fold. A sufficient plan uses its requested fold count and its rounded requested holdout count; an undersized plan may use an achievable count only when it records `insufficient_coverage` and the exact limitation. An empty holdout with a positive requested percentage must be marked `insufficient_coverage`. The supplied suite must contain exactly the development IDs; holdout IDs and groups may be recorded in the partition without their content or grading checks. The helper runs development cases only. Final holdout validation uses a separate authorized workflow.

```json
{
  "plan_id": "target-development",
  "scope": "target_runtime",
  "scheme": "grouped_development_evaluation",
  "case_ids": ["required-behavior"],
  "groups": [{"id": "behavior", "case_ids": ["required-behavior"]}],
  "grouping_key": "scenario_family",
  "assignment": {"algorithm": "stable_group_order", "version": "1", "stable_inputs": ["behavior"]},
  "requested_fold_count": 5,
  "requested_holdout_percent": 10,
  "rounding_rule": "round_half_up",
  "coverage": {"status": "insufficient_coverage", "reason": "The suite is too small for the requested partition."},
  "exposure_policy": {"holdout_content_before_freeze": "implementation_agent_prohibited", "exposure_log": []},
  "folds": [{"id": "fold-1", "group_ids": ["behavior"], "training_group_ids": [], "case_ids": ["required-behavior"], "case_count": 1}],
  "holdout": {"case_ids": [], "case_count": 0, "status": "insufficient_coverage"}
}
```

## Configuration schema

Configuration records requested and actual runtime settings separately. `requested_model` may be a runtime suggestion such as `luna-xhigh`. When Cloud does not expose model, reasoning, or speed controls or actual runtime metadata, record the corresponding actual value as `unobserved`; this is a qualification, not a run gate or proof that the request was honored. Verify the runner, environment, permissions, and output route required for the trial, and record any observed substitution. Never select Faster/1.5x for delegated tasks; stop if it is visibly enabled.

Required fields include:

- requested and actual runner, model, reasoning effort, environment identity, permissions profile, and substitution reason;
- `model_selection` with `policy`, `basis`, and `reason`;
- `authorization.run` and `authorization.output` booleans;
- bounded integer `concurrency` from 1 through 32;
- `target_package_id` and `target_content_hash`, with optional `target_package_path` for direct hash verification;
- `smoke_test` with status, trial ID, artifact path, output inspection, permission verification, output hash, and execution fingerprint;
- `command_output_limit_bytes`, a bounded per-stream retention limit for command stdout and stderr; and
- `artifact_paths`, a list of relative paths or globs to preserve from each command trial; and
- `command_dependencies`, a list of files or directories whose hashes affect the command.

Relative `target_package_path`, `command_dependencies`, and `smoke_test.artifact_path` values resolve from the configuration file’s directory. Reports retain their resolved paths and content hashes.

The command adapter additionally requires `command_argv`, a finite timeout greater than 0 and no greater than 600 seconds, and a bounded `command_output_limit_bytes` (applied per output stream; the default is 10,000,000 bytes and the maximum is 50,000,000). Use `{candidate}`, `{candidate_id}`, `{suite}`, `{case_id}`, and `{trial_dir}` placeholders. Commands run with `shell=False` in an isolated, whole-process-tree trial. On Windows the helper launches suspended, attaches the process to a kill-on-close Job Object, and fails before user code runs if that containment cannot be established. On POSIX it uses a dedicated process group. The helper terminates descendants on normal completion, timeout, interruption, or output-limit breach, bounds process and pipe cleanup, and retains only bounded stdout/stderr evidence. An unverified process-tree cleanup makes the trial fail and prevents candidate selection. Declare every external script or package path in `command_dependencies`; use an empty list only when the command is self-contained and its environment identity is recorded.

Artifact patterns must remain below `{trial_dir}`. The helper rejects absolute paths and parent traversal and applies bounded file-count and total-size limits. Retained files are hashed and linked from the individual attempt result. Report, attempts, and artifact destinations must not overlap candidate, target, dependency, smoke, suite, partition, or configuration inputs.

## Result and exit contract

The report records candidate, target, suite, rubric, the complete normalized partition (including groups, folds, training groups, derived coverage counts, and exposure policy), requested and actual runtime, fingerprint, authorization, attempts log, artifact directory, per-trial output hashes and previews, retained files, command timeout and output limits, elapsed time, termination reason and method, process containment and cleanup status, red/green outcomes, recommendation, and limitations. Every trial result also records `evidence_valid`: `true` means the declared checks were actually evaluated, including a valid observed behavioral failure; `false` means the result is infrastructure-invalid or incomplete and cannot supply score or red/green credit. Reader errors, candidate-integrity failures, nonzero exits, timeouts, output-limit breaches, missing artifacts, empty output, unverified process cleanup, exceptions, interruptions, and unstarted trials must set `evidence_valid` to `false`. A declared `contains` or `not_contains` check that runs successfully but fails remains valid red evidence. Every declared `artifact_paths` pattern is required to match and be retained; a missing pattern fails the trial. Reports and evidence are append-only across runs and are never overwritten.

The comparison is `complete` only when every expected trial result is present and has `evidence_valid: true`; otherwise it is `incomplete` or `blocked`, no candidate may be selected, and the helper returns exit code `3`. Red/green evaluation treats any result without valid evidence as `invalid_evidence`, never as an observed red failure.

Exit codes are:

- `0`: complete comparison with one eligible selected candidate;
- `1`: complete comparison with no unique eligible selection;
- `2`: invalid input, stale smoke evidence, or unavailable output destination; and
- `3`: blocked or incomplete comparison, including missing run authorization or interruption.

The report is evidence about the named target and run. It is not a durable user preference, a lesson, or permission for a later rerun.
