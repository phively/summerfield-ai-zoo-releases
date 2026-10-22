# Superb Skills requirements and acceptance record

Status: Phase 1–7 implementation artifacts are present, but acceptance remains incomplete. Historical test and validator results are tied to their recorded snapshots below. The current acceptance matrix in ignored `output/` is the single checklist. Existing T5/T6/T8 task pages were adjudicated read-only and remain qualified because their generated outputs are unavailable. T8 used local branch alias `work` for selected remote branch eval/superb-skills-acceptance-20260927-t8 and reports one preflight, one smoke, and four development attempts. Its deterministic result is not model-quality or holdout evidence. Actual model/effort remain unknown under the user's accepted qualification.

This record defines Superb Skills as a reusable designer and evaluator for other skills, plugins, prompts, and instruction packages, including itself. The current Superb Skills revision is one dogfooding target. The record separates reusable capability requirements from evidence that the capability works on target packages.

## Baseline identity

| Field | Value |
| --- | --- |
| Repository | `phively/summerfield-ai-zoo` |
| Branch | `phively/issue13` |
| Baseline commit | `1bcad1191b7ff60aedf2c906c1134a17578b4265` |
| Work Smarter version | `1.11.0` |
| Baseline source | Committed tree at the baseline commit; uncommitted work is excluded from baseline claims. |
| Worktree state | The baseline excludes uncommitted changes; the current worktree is not used as evidence. |
| Execution status | One read-only Codex Cloud checkout/scope smoke was completed; the local deterministic comparison is recorded separately. Response-only designer tasks occurred, but no clean-context target-runtime behavioral trial, final holdout validation, installation, publication, or live skill change has occurred. |

The plan is the ignored file `output/20260921 superb-skills implementation.md`. The canonical requirements and architecture records define the design; the evaluation JSON and protocol define the evaluation artifact. None of these records alone establishes behavioral evidence.

## Relevant baseline file hashes

These hashes identify committed or inspected inputs used to design the current work.

| Path | SHA-256 | Bytes | Role |
| --- | --- | ---: | --- |
| `plugins/work-smarter/.codex-plugin/plugin.json` | version `1.11.0` | — | Plugin version and supported package metadata |
| `plugins/work-smarter/skills/superb-skills/SKILL.md` | `C91F2841DACD66B3F86CAE7628ABF9241B03A78CEBD0E6E1D7361F1294FF27FE` | 5778 | Coordinator and conditional routing |
| `plugins/work-smarter/skills/superb-skills/references/instruction-design.md` | `8102CA296AF4ED11FC5FDF589F942D7D05B8FCFC8620E134653A0B8D45955AA2` | 4605 | Instruction placement and authoring |
| `plugins/work-smarter/skills/superb-skills/references/plugin-architecture.md` | `8F09F36445F80088E7E59417D4596C419395B669C40E3A148EA5BD87591062B6` | 2905 | Package boundaries, handoffs, and assets |
| `plugins/work-smarter/skills/superb-skills/references/evaluation.md` | `CFB3B808B21042B12A17026E102F018191E74F81EA1BE8469A0149C873BE204C` | 2678 | Existing evaluation guidance |
| `plugins/work-smarter/skills/superb-skills/references/working-memory.md` | `450633B2C49D099AB9D0001B60D872CE3BAE2156600D34FD8C2C68D0ED96D5DC` | 14870 | Current/history and lifecycle authority |
| `plugins/work-smarter/shared/handoff-contracts.md` | `10F1745580FAEC6A816C9422CE6476EBB0E769E730C4F8D6C31E18148E9C1C34` | 16732 | Cross-skill authority and confirmation boundaries |
| `plugins/work-smarter/evals/regression.json` | `32EDBB1635907598DFCBBCFFEFAE5EC85AAD083A3B871FFBAA23012491E3D568` | 72458 | Existing regression cases |

## Source and evidence status

The live [issue body](https://github.com/phively/summerfield-ai-zoo/issues/13) and its three comments were reviewed on 2026-09-21. The supplied screenshot is the source for the visible issue requirements. The four shared conversations were reviewed in the authenticated browser on 2026-09-21. They are user-reported failure evidence, not independent red-light reproductions; the exact observed action and correction are recorded below and reproduction remains `not_run`.

| Source | Status | Permitted use |
| --- | --- | --- |
| Issue #13 screenshot | `available` | Transcribe visible requirements; do not infer hidden requirements. |
| Issue #13 body and comments | `reviewed` | Reconcile requirements, including the corrected 10% holdout plus 30% × 3, 18% × 5, or 9% × 10 development examples. |
| `conv-1` — Propagating instructions to skill (no history; private locator omitted) | `reviewed_user_report` | The visible exchange shows redundant “no history file” statements propagated into multiple Career Coach files; the user identified `record-audits.md` as the existing lifecycle authority and requested cleanup. It does not independently reproduce a clean-context delegated-skill failure. |
| `conv-2` — Forgetting version number bump (private locator omitted) | `reviewed_user_report` | After a substantial teach-me implementation, the user had to request the `1.8.1` bump; the follow-up updated plugin, standalone, dependent mirrored, and evaluation metadata. This supports a missing completion gate, not a universal version policy. |
| `conv-3` — Forgetting version number bump (private locator omitted) | `reviewed_user_report` | After the Meal Planner formatting implementation, the user separately requested an appropriate version bump and README update; the follow-up changed the parent plugin to `1.5.0` and synchronized evaluation and catalog metadata. This is a second user-reported omission pattern. |
| `conv-4` — Repeated benchmark reruns (private locator omitted) | `reviewed_user_report` | The exchange records incomplete runner/output controls, a later explicit user correction that rerun permission had not been given, and preflight/collection/output problems. Later corrections require smoke tests, explicit authorization, preserved attempts, and retrying only invalid packets. It does not establish a reusable runner invocation. |
| “Design Engineering Skill” conversation referenced by issue comment | `reviewed_user_report_2026-09-27` | Its requirements and architectural reasoning were reviewed in the authenticated browser; its locator and private content are not recorded here. |

### Reviewed conversation evidence ledger

| Evidence | User instruction or context | Observed response/action | Correction or lesson | Unavailable artifact or reproduction status |
| --- | --- | --- | --- | --- |
| `conv-1` | Continue a phased plugin redesign with current instructions and lifecycle boundaries. | The implementation added repeated “no history file” statements across several files, duplicating an existing audit authority. | Remove the duplication and keep lifecycle rules in the canonical audit reference; do not infer a missing history source. | No clean-context delegated invocation is shown; independent reproduction `not_run`. |
| `conv-2` | Review and implement approved teach-me visual-art changes. | The implementation summary reported completion and validation before a version-bump follow-up; the user then supplied the missing version decision. | Include version and applicable mirror synchronization in the release-completion gate. | No separate release checklist artifact is supplied; independent reproduction `not_run`. |
| `conv-3` | Implement the approved Meal Planner formatting plan. | The implementation completed before a separate request added the parent-plugin version bump and README update. | Treat version decision, metadata synchronization, and explicit README scope as completion checks, not afterthoughts. | No pre-follow-up completion checklist is supplied; independent reproduction `not_run`. |
| `conv-4` | Complete a controlled comparison and later continue remaining evaluation work. | Runs and analysis progressed while some CLI limits, output/collection conditions, and authorization boundaries were unresolved; the user later stated rerun permission had not been given. | Gate full runs on permission, runner identity, output completeness, and smoke-test results; retain valid attempts and retry only failed/invalid work under the same frozen configuration. | Provider-credit and local runtime failures are environment-specific; independent reproduction `not_run`. |

## Authority and deliverable separation

| Layer | Authority | Acceptance boundary |
| --- | --- | --- |
| Reusable coordination and workflow selection | `plugins/work-smarter/skills/superb-skills/SKILL.md` | Routes the target design request and loads only applicable references. |
| Instruction placement and concise authoring | `references/instruction-design.md` | Produces target-specific instructions without copying other skill procedures. |
| Target architecture, decomposition, DRY/YAGNI, handoffs, and assets | `references/plugin-architecture.md` | Gives one owner to each target rule and makes target dependencies explicit. |
| Evaluation and candidate selection | `references/evaluation.md` plus `skills/superb-skills/scripts/compare_candidates.py` | Applies to target-supplied suites and candidates; does not benchmark every target by default. The script provides local deterministic and command paths but does not by itself establish Cloud compatibility. |
| Current/history and lifecycle | Existing `references/working-memory.md` | Defines general memory decisions; it does not become a hidden Superb Skills user record. |
| Personal context | `remember-me` and existing handoff contracts | Remains authoritative when the target environment provides it; standalone targets retain equivalent local boundaries. |
| Project settings and lessons | `references/preferences-and-lessons.md` plus target project-owned Markdown or YAML authority | Requires explicit ownership, location, precedence, authorization, and unavailable-record behavior. |
| Repeated deterministic operations | Small Superb Skills script | Accepts target-specific inputs and owns validation, isolation, result schema, and bounded execution. |
| Evidence | Target project’s authorized evaluation artifact location | Reports provenance and limitations; never becomes current instructions or personal memory. |

Deliverable A is the reusable Superb Skills guidance, references, script, contracts, and tests. Deliverable B is evidence from at least one unrelated target skill design plus Superb Skills self-regression. Repository evaluation files, private conversation links, and the ignored plan are development inputs; installed Superb Skills cannot require them at runtime.

## Requirements and acceptance matrix

Baseline classifications use `supported`, `partial`, `missing`, or `dependent_on_unavailable_context`. Evidence status uses `not_run`, `design_only`, `blocked`, or `observed` only when the underlying artifact or behavior is actually inspected.

| ID | Requirement applied to target skill design | Owner | Proposed change | Observable acceptance criterion | Baseline | Evidence status |
| --- | --- | --- | --- | --- | --- | --- |
| RS-01 | Superb Skills applies the issue improvements when designing any target skill, plugin, prompt, or instruction package, including itself. | `SKILL.md`, references, evaluation suite | Make target identity and target runtime behavior explicit in every workflow. | An unrelated target design receives applicable guidance, and self-design is reported as one application rather than the product scope. | `partial` | `design_only` |
| RS-02 | Installed guidance works without repository-only evaluation artifacts or the designer’s conversation history. | `SKILL.md`, references, handoff contract | Keep reusable rules and tools under the installed skill; pass source identity and unresolved context explicitly. | A clean target design can proceed with supplied inputs and reports unavailable history or records without fabrication. | `partial` | `not_run` |
| SS-01 | Use red-light/green-light testing. | `references/evaluation.md` and target evaluation artifacts | Require a meaningful baseline failure and later pass for each changed target criterion, while preserving existing successes. | The same target case and criterion have paired results; fixture/schema passes are not behavioral passes. | `partial` | `not_run` |
| SS-02 | Compare multiple target candidates with a Cloud-capable script. | `skills/superb-skills/scripts/` and evaluation reference | Use the canonical candidate, suite, normalized partition, runtime configuration, permission, smoke, and output contract. | A local report compares two candidates with candidate, target, suite, rubric, partition, runtime, output, and attempt identities; the Cloud path is separately verified or reported blocked. | `partial` | `observed` |
| SS-03 | Run independent target trials in parallel by default with a runtime-selected cost/intelligence-appropriate runner and model. | Evaluation reference and runner configuration | Record requested and actual runner, model, effort, concurrency, and substitutions; mark unavailable Cloud model/effort/speed telemetry unobserved. | A target report shows observed configuration, identifies unobserved settings, or gives an explicit blocked reason; missing Cloud selectors alone do not block a run. | `missing` | `dependent_on_unavailable_context` |
| SS-04 | Store target benchmark results and recommendations. | Evaluation artifact contract | Define an exclusive report, append-only attempt log, retained per-attempt outputs, provenance, limitations, and target-authorized destination. | A current local comparison produces durable evidence without rewriting historical results; behavioral and Cloud evidence remain labeled separately. | `partial` | `observed` |
| SS-05 | Follow memory hierarchy; use skills as coordination; apply DRY and YAGNI. | `SKILL.md`, `plugin-architecture.md`, `working-memory.md`, handoff contract | Map every target rule to one owner and require a boundary before adding a skill, record, or handoff. | Target design review names owners, dependencies, and the reason for every new component. | `partial` | `not_run` |
| SS-06 | Prefer understandable target reasoning and codebase clarity over marginal speed. | Architecture reference and candidate rubric | Score clarity, maintenance, irrelevant context, handoff complexity, and runtime together. | Target selection records clarity and maintenance evidence; speed alone cannot select a more complex design. | `partial` | `not_run` |
| SS-07 | A preference-dependent target skill has an intake process. | `references/preferences-and-lessons.md` and target authority | Ask only for missing decisions, reuse supplied/canonical values, and report unavailable records precisely. | Target instructions handle supplied, missing, unavailable, and override cases without repeated interviews. | `partial` | `design_only` |
| SS-08 | Editable preferences and settings use an appropriate readable/writable Markdown or YAML authority. | `references/preferences-and-lessons.md`; `remember-me` for personal context; target project for settings | Specify owner, path, format, precedence, identity, authorization, cache boundary, and fallback. | Target design produces an editable authority or explains why no persistent setting is needed. | `partial` | `design_only` |
| SS-09 | A target may turn one observed mistake into a preventive lesson only after verifying a scoped remedy; one occurrence does not prove a recurring pattern. | `references/preferences-and-lessons.md`, working-memory/record-management guidance, and target lesson authority | Define recognition, diagnosis, remedy verification, target-owned recording, retrieval in a fresh context, and revision or retirement when applicability changes; keep permission limits separate. | A target records the verified remedy with applicability, evidence, date, owner, status, and permission limits; reuses it only when applicable; labels a single observation accurately; and revises or retires it when scope changes. | `partial` | `design_only` |
| SS-10 | Target raster icons are readable at 32×32 and no larger than 128×128. | Architecture reference and asset checks | Require dimension checks plus visual review; preserve valid SVGs unless defective. | Target package passes deterministic dimensions and a visual legibility check. | `partial` | `not_run` |
| SS-11 | Final target validation uses an untouched holdout. | Evaluation reference and runner | Define holdout ownership, access/exposure records, freeze criteria, and fresh validation after exposure. | Target holdout is frozen before access; a failure triggers a fresh set after revision. | `partial` | `design_only` |
| SS-12 | Use grouped 3-, 5-, or 10-fold development evaluation when appropriate. | Evaluation reference and target suite manifest | Record grouping, assignment algorithm, counts, fold development use, and exposure. | Related target paraphrases stay together and every partition is reproducible. | `partial` | `observed` |
| SS-13 | Use the issue’s example ratios when appropriate: 10% holdout plus 30% × 3, 18% × 5, or 9% × 10 development folds. | Suite manifest and runner | Make alternative ratios configurable with exact-count rounding and coverage checks. | Target report shows exact counts and explains the selected scheme; no ratio is forced onto an undersized suite. | `partial` | `observed` |
| SS-14 | Select an available model and runner at runtime using current benchmark evidence and task cost/intelligence/time trade-offs; treat `luna-xhigh` as an example/default suggestion when supported. | Runner configuration and target report | Verify the runner, environment, permissions, and output route; record requested versus observed model, effort, and speed with the selection basis. | Every target trial records verified settings where exposed and marks unavailable Cloud telemetry unobserved; missing model/speed selectors alone do not block a run. | `missing` | `dependent_on_unavailable_context` |
| SS-15 | Avoid repeating known mistakes, including failure to review supplied sources. | Lesson reference, evaluation cases, and target workflow | Add regression cases for missed sources, permissions, output checks, version decisions, and stale remedies. | A later comparable target task retrieves the lesson or reports why it was unavailable; it never claims unperformed review. | `partial` | `not_run` |

## Phase 1–7 verification status

This subsection records only the 2026-09-24 checkpoint. Its `not_run` and no-smoke statements are historical, not current. The 2026-09-27 acceptance matrix in ignored `output/` supersedes them for current Phase 1–7 status.

Verification ran on 2026-09-24 against commit `77ffc94de6f47b365d5183ea01fd23b860eb8525` with Work Smarter `1.11.0`. The detailed evidence index and retained local comparison are in ignored `output/superb-skills-phase1-7-acceptance-20260924/verification.json`.

Completed checks:

- All Work Smarter pytest tests passed: `104 passed, 1 skipped`. The skipped test is the optional installed-copy comparison when `WORK_SMARTER_INSTALLED_SKILLS_ROOT` is unset. Separate helper tests verify matching copies, changed content, a missing source, and rejection of identical source/bundled paths.
- `requirements-test.txt` records the pytest and PyYAML versions for setup with `python -m pip install -r requirements-test.txt`.
- The Work Smarter plugin validator and Superb Skills quick validator passed; `git diff --check` passed.
- The partition validator accepted synthetic 100-case plans for 3, 5, and 10 folds with 10 holdout cases and the example 30%, 18%, and 9% validation counts. This is deterministic partition evidence, not agent evaluation or final holdout evidence.
- The unrelated Document Assistant fixture completed a local command-adapter comparison with four valid attempts. It demonstrated the declared text-check red/green criterion and retained the report, configuration, smoke output, and attempt artifacts. It demonstrates local deterministic comparison only, not model quality.

Acceptance still open:

- Preference, lesson, authority, context-transfer, red/green, routing, and version-synchronization target behavior trials have no clean-context results and remain `not_run`.
- The tracked icon fixture contains only dimension metadata and no raster images. Ignored synthetic samples were dimension-checked (32×32 and 128×128 accepted; 129×129 rejected) and visually inspected at the two supported sizes. This demonstrates fixture-level handling only; review of a real target-package raster asset remains `not_run`.
- One read-only Codex Cloud task checked out the pinned sanitized private-repository commit, confirmed evaluation and private repository instruction content were absent, and made no file changes. This verifies checkout/scope only, not implicit skill activation, model/reasoning-effort propagation, or behavioral compatibility. Subsequent response-only designer tasks do not establish those capabilities. Task metadata did not expose actual model/effort. The latest user-provided screenshot showed 71% five-hour and 95% weekly usage remaining, and the user authorized bypassing usage checks for the rest of closeout; no API billing, paid credits, or auto-reload were used. This does not waive the user's separate no-test instruction: target-runtime trials, benchmarks, preflight, and smoke remain unrun. Actual model/effort are a qualified limitation, not an inferred value. The local report does not establish Cloud compatibility.
- The installed-copy pytest is a skip unless a distinct installed skill root is supplied. Its comparison logic was separately exercised against a distinct temporary copy by the helper tests.
- Final untouched-holdout validation remains reserved for the later final-validation phase. Historical `evals/results.json` belongs to Work Smarter `1.8.1` and is not current or target evidence.

At the 2026-09-24 checkpoint, Phase 1–7 implementation was described as complete while acceptance remained incomplete; the recorded clean-context and visual trials were still unrun at that date. This statement is historical only. The 2026-09-27 acceptance matrix supersedes it for current status.

## Requirements acceptance

This record is complete when the requirements, architecture decision, and evaluation design are present; every screenshot and GitHub requirement has an owner, proposed change, observable acceptance criterion, baseline classification, and evidence status; source accessibility and unresolved context are explicit; and target design is separated from self-regression. No live Superb Skills behavior or target benchmark result is claimed here.
