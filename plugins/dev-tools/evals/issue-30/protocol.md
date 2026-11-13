# Issue 30 skill-boundary acceptance protocol

**Status:** Reusable source for a bounded development comparison. This document defines the method; it is not evidence that any trial ran or passed.

## Decision

Decide separately whether each proposed entry point adds a material workflow or routing benefit over an extension of its existing owner:

| Proposal | Split candidate | Existing-owner extension |
| --- | --- | --- |
| Benchmark advisory | `better-benchmarks`, with optional `superb-skills` contribution for instruction-package evaluation | Superb Skills extension: add a benchmark-advisory mode to `superb-skills`, which continues to own instruction-package evaluation |
| Code-quality review | Optional `code-quality-review`, with optional `coding-preferences` consultation for a material unresolved portable convention | Coding Preferences extension: add a requested-review mode to `coding-preferences`, which continues to own portable coding values |

The comparison concerns these workflows and package boundaries. It does not estimate general model quality, establish marketplace activation, or establish general superiority for the separate design.

## Inputs and maintenance

`cases.json` is the authoritative case and criteria source. `../fixtures/issue-30/manifest.json` identifies the exact synthetic benchmark and code-review inputs with SHA-256 hashes. These are reusable development sources, not trial results. The maintainer of this package updates them. When fixture bytes change, recompute hashes, review affected criteria and paired controls, update candidate-visible reference material only when required, and rerun affected cases before treating the new version as comparable. Preserve earlier candidate snapshots and raw runs under ignored `output/`.

The 13 cases cover AE1-AE9. Related cases share `group_id` so paired claims or conversation continuations remain together. The cases and rubric are public development material, not an untouched final holdout. Each candidate invocation starts with an independent starting state; no generalization beyond these supplied tasks is claimed.

## Candidate preparation

Freeze byte-exact package snapshots for both candidates in each comparison. Include the entry point and only the references and public contracts needed to perform the case. The extension candidate must receive a fair, coherent owner entry point and the same feature guidance, located within that owner. Do not add the evaluation cases, success or failure criteria, rubric, prior candidate outputs, or scorer notes to either candidate snapshot.

Record the complete file inventory, path, byte count, SHA-256, and delivery method for each candidate and supplied fixture. Materialize each trial in a unique temporary workspace outside the repository and outside every ancestor containing `AGENTS.md`; include only the frozen candidate package and case inputs. Verify the bytes received before the model sees them. Keep repository instructions, evaluator files, unrelated user data, and previous outputs out of the candidate workspace.

## Feasibility pilot and run method

Use the repository's existing `plugins/dev-tools/skills/superb-skills/scripts/compare_candidates.py` command adapter for capture and process control. Follow its [candidate comparison input contract](../../skills/superb-skills/references/evaluation-input-contract.md), including preflight, a successful inspected smoke artifact bound to the execution fingerprint, output hashes, timeout, and whole-process-tree cleanup. Keep one-off wrapper/configuration files and all run output under ignored root `output/dev-tools/issue-30/`; do not add a general runner.

Before the full comparison, pilot the exact candidate-delivery and capture route with one compliant request and one control that asks for an unsupported claim or prohibited operation. Confirm that the compliant response is retrievable and scorable, the violating requirement is detected, the actual command and exit status are retained, the event trace is available, and the copied inputs match their frozen hashes. A failed or unexecuted input, permission, evidence, or scoring gate is infrastructure-invalid or incomplete evidence; it is not a candidate failure and must stop the comparison.

For model-assisted runs, request GPT-6 Luna at Medium reasoning when available. Use Standard speed; do not enable Faster/1.5x. Record requested and observed runner, model, reasoning effort, speed, permissions, environment, and every operation. If a setting is not exposed by the route, record it as unobserved. Every pair uses the same model, reasoning effort, speed, permission profile, and case input. Each case is a separate ephemeral invocation with an isolated read-only workspace. Supply the candidate instructions and only the relevant fixture content, followed by the exact public case input. Do not supply evaluator criteria or prior answers.

The initial delivery method is direct instruction injection from the frozen package into a fresh Codex CLI session. This can provide evidence about those instructions and cases, but does not demonstrate automatic marketplace skill discovery. Record that limitation separately. For no-tool cases, the JSONL trace must show no tool operation; a single file read, retrieval, command, test, or child dispatch is a boundary failure. For the available-delegation case, record the generic child launch and returned output. If the selected runner cannot delegate, exercise that branch through an available host delegation tool; do not claim the CLI route supplied the capability. The unavailable-delegation control must disclose same-agent fallback and leave explicitly required independence unmet.

The caller's current request to execute this plan authorizes its bounded acceptance run and local raw output. It does not authorize executing or publishing any user benchmark, creating a new public benchmark, changing personal preferences, editing the synthetic target during review, committing from a trial process, or shipping from a candidate session. Do not retry an invalid or interrupted trial automatically; preserve it and stop if the evidence route cannot be repaired within this run's authority.

## Scoring and decision

After both candidates' outputs and event traces are retained, score them independently against `rubric.md` in a fresh evaluator context. Hide candidate identity where practical. Keep behavior score, runner-integrity status, and architecture cost separate. Report exact candidate, suite, rubric, and fixture identities plus the evaluated cases. An incomplete comparison or missing required output cannot select either candidate.

Retain a split entry point only if it passes every required case and critical gate, corrects at least one predeclared material failure or achieves a predeclared meaningful improvement, and introduces no unresolved critical or routing failure. A higher mean score cannot erase a critical failure. Prefer extending the existing owner on a tie. If a split fails this gate, revise or remove that entry point before packaging; do not use package tests as behavioral acceptance.

## Storage and reporting

Track this protocol, `cases.json`, `rubric.md`, synthetic fixtures, manifest, and source tests in their current package directories. Store raw captures, candidate snapshots, prompts as delivered, input receipts, JSONL event logs, outputs, scores, and comparator reports only under ignored root `output/dev-tools/issue-30/`. Do not publish trial artifacts as part of this protocol; any benchmark publication requires separate approval.
