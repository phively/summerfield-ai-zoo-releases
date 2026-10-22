# Superb Skills architecture and ownership decision

Status: The Phase 1–7 implementation artifacts are present, but acceptance remains incomplete. The current acceptance matrix in ignored `output/` is the single checklist. Existing T5/T6/T8 task pages have been adjudicated read-only and remain qualified because their generated outputs are unavailable. T8 reports one preflight, one smoke, and four development attempts at concurrency one; this does not establish target model quality, installed-skill activation, or holdout performance. Actual model/effort remain unknown under the user's accepted qualification.

## Decision

Keep `superb-skills` as one thin coordinating skill that designs, reviews, refines, and evaluates target prompts, skills, plugins, contracts, and instruction packages. A target may be Superb Skills itself, but self-evaluation is one application of the reusable workflow.

The installed package contains reusable routing, design, architecture, evaluation, memory-boundary, and handoff guidance plus the smallest deterministic evaluation tool justified by later evidence. Development suites, private source links, benchmark archives, and repository-only records remain evidence inputs. They are not runtime dependencies for installed Superb Skills or for a standalone target package.

The architecture has two separately attributable layers:

1. The design layer selects the smallest applicable workflow, places target behavior under the correct authority, defines boundaries and handoffs, and produces a target-specific implementation and evaluation plan.
2. The evidence layer validates deterministic structure and, when authorized and available, runs isolated target trials and compares candidates. It supports design decisions and does not become an automatically activated target skill.

Benchmarking is conditional development work. A target receives benchmarking when its risk, candidate uncertainty, or user request warrants it. A simple target transformation remains simple and does not gain a benchmark, durable record, or evaluation dependency merely because Superb Skills is available.

## Target design contract

For every target package, Superb Skills records:

| Contract element | Required content |
| --- | --- |
| Target identity | Name, package type, version or version decision, platform, owner, and whether the target is bundled or standalone. |
| User goal and scope | Recognizable trigger, intended users, inputs, outputs, important limits, negative routes, and mixed-workflow boundaries. |
| Existing authority | Current instructions, contracts, records, conventions, assets, and source classifications that must be preserved. |
| Design decisions | Skill versus reference versus script versus current prompt placement; unified versus split architecture; DRY/YAGNI rationale; target dependencies. |
| Runtime behavior | Applicable intake, authority, handoff, confirmation, failure, lesson, and persistence behavior the target itself must perform. |
| Evaluation design | Baseline, candidates, cases, rubric, evidence types, runner request, permissions, partitions, holdout policy, outputs, and stopping rules when evaluation is warranted. |
| Deliverables | Target files or a copy-ready artifact, validation plan, provenance fields, unresolved issues, and explicit claims the evidence does not support. |

The designer must distinguish guidance that Superb Skills uses from behavior the target must implement. A target runtime cannot depend on the designer's chat history, hidden repository context, private conversation links, or a development-only benchmark report.

## Ownership map

| Responsibility | Single owner | Boundary |
| --- | --- | --- |
| Route the target design request and load references | `plugins/work-smarter/skills/superb-skills/SKILL.md` | Coordinates the work and states completion requirements; does not copy reference procedures. |
| Place and reduce target instructions | `references/instruction-design.md` | Owns target prompt/project-instruction placement, concise authoring, limits, and authority separation. |
| Design target package boundaries and decomposition | `references/plugin-architecture.md` | Owns focused workflows, DRY/YAGNI, asset guidance, and target handoff design. |
| Define target evaluation and candidate selection | `references/evaluation.md` | Owns cases, scoring, red/green evidence, partitions, holdouts, and recommendation rules; the script owns deterministic execution. |
| Define current state, history, and lifecycle decisions | Existing `references/working-memory.md` | General design authority; does not create a Superb Skills user profile. |
| Route missing preferences and recurring lessons | `references/preferences-and-lessons.md` | Owns triggers, target-facing routing, evidence labels, and fallbacks; it does not duplicate record-management procedures. |
| Own personal context | `remember-me` and existing handoff contracts | Remains authoritative when available; Superb Skills requests the smallest sufficient context and does not duplicate records. |
| Own target project settings and lessons | Target-selected Markdown or YAML authority | Requires explicit owner, path, format, precedence, identity, write authorization, and unavailable-record behavior. |
| Execute repeated deterministic evaluation operations | A small script under `skills/superb-skills/scripts/` | Accepts target-specific inputs, validates configuration and partitions, isolates trials, bounds concurrency, and writes result schemas. It does not choose target architecture or grant permissions. |
| Own target benchmark reports | The target project's authorized artifact location | Stores raw links, summaries, recommendations, provenance, and limitations; it is not a current instruction or personal record. |
| Define cross-skill handoffs | `shared/handoff-contracts.md` | Every permitted handoff has one contract with authority, uncertainty, failure, prohibited information, and confirmation boundaries. |

## Authority and dependency rules

- Keep one authoritative home for each target rule. Use a conditional reference before creating another skill or storage tier.
- Use the target's existing records and contracts when they exist. If a target is standalone, preserve equivalent behavior without adding an unavailable companion dependency.
- Keep user preferences, project settings, task overrides, verified lessons, benchmark evidence, and historical records distinct.
- A stored lesson describes an applicable verified remedy; it never grants a new permission or replaces a confirmation boundary.
- Agent or model roles are bounded assignments with explicit inputs, outputs, and failure states. They do not justify new skills by themselves.
- Target version decisions and applicable mirrored metadata are checked under the target repository's conventions. General Superb Skills guidance does not hard-code Work Smarter mirror names or paths.
- Do not add benchmark behavior to a target runtime unless the target's user goal requires it. Development evaluation remains outside the target's normal workflow.

Preserve the memory priority of reliable recall, token efficiency, and retrieval speed. When behavioral results are adequate, prefer the target architecture that makes reasoning, authority, and maintenance easiest to inspect, even when it is marginally slower. A split target architecture requires evidence of a meaningful improvement that exceeds added routing and handoff cost.

## Architecture acceptance

This decision is complete when:

- Superb Skills remains the single coordinator for its reusable design workflow.
- The target design contract distinguishes reusable designer guidance, target runtime behavior, and development evidence.
- Every planned rule has one owner and a defined boundary.
- Target-specific paths, versions, companion skills, and records are supplied as inputs rather than hard-coded.
- Personal context remains owned by `remember-me` where available; target project records remain target-owned.
- The deterministic runner remains a script and does not add user-facing activation.
- Benchmark artifacts remain evidence and do not become instructions or memory.
- No live skill behavior, target package, benchmark, installation, or publication has been executed.
