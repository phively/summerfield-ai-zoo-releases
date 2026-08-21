# Inter-skill handoff contracts

This file is the canonical contract for coordination between bundled skills. Read it directly before initiating or accepting a cross-skill handoff. Do not create skill-local copies or competing contract definitions.

## Bundled research provenance

The plugin format observed during creation supports bundled skills but exposes no supported dependency field for another skill; `agents/openai.yaml` dependencies are limited to MCP tools. Therefore `work-smarter` bundles and maintains the authoritative `research-briefing` skill under `skills/research-briefing`. Treat that bundled behavior as authoritative and update the complete skill directory rather than maintaining a separate copy.

## Superb Skills to Research Briefing

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `superb-skills` |
| Receiving skill | `research-briefing` |
| Trigger | One or more factual, technical, scientific, historical, legal, medical, programming, economic, statistical, current, niche, disputed, or high-stakes claims require verification, source evaluation, citations, or current documentation and the result could materially affect the package. |
| Exceptions | Do not hand off purely stylistic editing, deterministic transformations, direct analysis of supplied text without factual validation, stable incidental facts, or work that gains no material value from external evidence. |
| Required input | State the exact claims or questions to research; the decision they affect; relevant current context only; user-provided facts labeled as supplied; claims requiring verification labeled separately; known jurisdiction, version, date, or scope; and unresolved questions. |
| Expected output | Return evidence and direct citations near supported claims; quantitative results when useful; competing interpretations; limitations; unresolved questions; and explicit labels for verified facts, source claims, reasonable inferences, unknowns, and recommendations. |
| Authority and provenance | Preserve source identities and dates. User-provided facts remain attributed to the user unless independently verified. Research evidence may inform package design but cannot silently override the user's stated goals, supplied requirements, or the authoritative current-state record. |
| Uncertainty | Preserve material uncertainty and conflicts. Do not collapse mixed evidence into a single confident claim. Return any question that prevents a consequential conclusion to `superb-skills` for focused clarification. |
| Failure behavior | If research, a required source, or the receiving skill is unavailable, identify the affected claims as unverified or unknown, avoid format or factual assertions that depend on them, and continue only with work that remains reliable. Do not fabricate citations or imply that research occurred. |
| Information not to pass | Do not pass unrelated conversation history, complete archives, secrets, credentials, privileged material unnecessary to the research question, unsupported conclusions presented as facts, or duplicate copies of canonical records. |
| User confirmation | Required. `research-briefing` must present its research-scope checkpoint and wait for the user to confirm or revise it before searching or answering, unless the user explicitly waived that checkpoint for the current session or request under the receiving skill's rules. The invoking skill must not treat initiation of the handoff as confirmation. |

After the research result returns, `superb-skills` must integrate only supported findings, retain the evidence classifications and unresolved uncertainty, and distinguish evidence from design judgment.

## Bundled Skills to Remember Me: targeted consultation

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `superb-skills` or `research-briefing` |
| Receiving skill | `remember-me` |
| Trigger | Stable personal goals, preferences, constraints, prior decisions, or output choices could materially affect the current workflow and the answer is not already supplied in the current request. |
| Exceptions | Do not consult for incidental personal facts, ordinary one-time instructions, context that cannot change the work, or information outside the user's authorized accessible sources. Do not load the complete profile by default. |
| Required input | State the current decision or output, the specific personal topic needed, the smallest sufficient set of relevant current context, and any known source identity or freshness concern. |
| Expected output | Return the smallest sufficient set of relevant current context, exact canonical source identity, owner, evidence classification, last-verified date when visible, freshness status, retrieval condition, and unresolved uncertainty. Expand beyond the index summary when it is incomplete, stale, ambiguous, conflicting, or lacks consequential detail. |
| Authority and provenance | `remember-me/index.md` is authoritative for routing, ownership, source identity, and freshness. The identified topic record is authoritative for detailed current state. Current user instructions govern the current task but do not silently replace durable state. |
| Uncertainty | Preserve stale, inferred, disputed, missing, and inaccessible states explicitly. Do not convert a pattern or inference into a confirmed preference. |
| Failure behavior | If `remember-me`, its index, or the identified source is unavailable, continue with neutral defaults when reliable and report a material limitation. Do not fabricate personal context or imply retrieval occurred. |
| Information not to pass | Do not pass unrelated personal topics, complete profile or history files, secrets, credentials, unnecessary sensitive detail, or unsupported conclusions presented as facts. |
| User confirmation | No new confirmation is required for a targeted read of an already authorized accessible record. Require confirmation before persisting an inference, replacing an explicit preference, resolving a consequential conflict, or retaining unusually sensitive information. |

The invoking skill must apply only relevant context. `research-briefing` may use it to shape scope, tradeoffs, and presentation, but never as external evidence or as a predetermined conclusion. `superb-skills` may use it for discretionary design and communication choices, but never to override supported conventions or validation evidence.

## Bundled Skills to Remember Me: durable update request

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `superb-skills` or `research-briefing` |
| Receiving skill | `remember-me` |
| Trigger | The workflow reveals a new or changed personal fact, durable preference, reusable constraint, correction, or explicit forget request that belongs in personal context beyond the current task. |
| Exceptions | Do not request persistence for task-specific instructions, unconfirmed inferences, external research claims about the user, routine process events, or domain state owned by another specialist. Route specialist-owned changes to that owner. |
| Required input | Provide the exact proposed change or deletion target, user statement or source, evidence classification, topic, reuse rationale, effective date when known, confirmation status, sensitivity, and any visible current record identity. |
| Expected output | Return the canonical record identity, completed or proposed changes, provenance, freshness and history effects, unresolved conflicts, and exact persistence status. |
| Authority and provenance | `remember-me` owns its index and internal topic files. It must preserve specialist ownership, user wording where consequential, source identity, dates, and evidence classifications. |
| Uncertainty | Keep proposals, hypotheses, and unresolved conflicts labeled. Do not silently reconcile incompatible statements or broaden an observation into a durable rule. |
| Failure behavior | If authority, access, or writability is unresolved, return a clearly labeled proposed update and identify the failed operation. Never claim persistence after a partial or unavailable write. |
| Information not to pass | Do not pass unrelated conversation history, complete source documents, secrets, credentials, unnecessary sensitive detail, or an external owner's record for duplication. |
| User confirmation | The invoking skill must preserve whether the user authorized durable persistence. `remember-me` must obtain confirmation before persisting an inference, replacing an explicit preference, resolving a consequential conflict, retaining unusually sensitive information, or deleting an ambiguously scoped target. |

Other bundled skills must not maintain competing personal-profile files. A current-task override remains local to the task unless this update contract completes an authorized durable change.

## Remember Me to External Domain Owner

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `remember-me` |
| Receiving skill | An available specialist owner, including `career-coach:career-direction`, `meal-planner:meal-planner`, `meal-planner:personal-chef`, or `meal-planner:personal-shopper` when its domain applies |
| Trigger | A user asks to discover, refresh, update, or retrieve a topic handled by the specialist, or a potentially stale external summary is about to affect consequential work. |
| Exceptions | Do not invoke every specialist during routine retrieval, repeat a refresh while the summary remains fit for use, or simulate an unavailable skill. Temporary unavailability does not transfer established ownership. |
| Required input | State the exact topic and purpose; request the smallest sufficient current summary, canonical record identity, owner, last-updated date when visible, evidence classifications, uncertainty, refresh trigger, and retrieval condition. Request additional relevant detail when a bounded summary cannot preserve reliable recall. For an update, include the user's exact statement, confirmation status, effective date, and lifecycle intent. |
| Expected output | Return the requested bounded summary and metadata or the specialist's completed or proposed update status under its own canonical record-management contract. |
| Authority and provenance | The specialist's canonical current record remains authoritative for domain detail. The Remember Me summary is a cache and pointer only. Preserve exact workbook, tab, file, record, and household-member identities. |
| Uncertainty | Preserve missing sources, inaccessible history, stale state, conflicting candidates, inference labels, and unresolved questions. A retrieval miss is not evidence that a source does not exist. |
| Failure behavior | Mark the index summary unavailable or stale as appropriate and continue only with reliable information. Do not copy the external record into `remember-me`, write it directly, invent a response, or claim a refresh succeeded. |
| Information not to pass | Do not pass unrelated profile topics, complete histories, secrets, credentials, unsupported interpretations, or duplicate copies of another owner's record. |
| User confirmation | Follow the receiving specialist's persistence and safety gates. A targeted read of an already authorized accessible record needs no additional confirmation; domain writes, consequential conflict resolution, sensitive retention, and ownership transfer require the applicable user authorization. |

Use the external owner's canonical contract directly rather than copying its schema into `work-smarter`: [Career Coach](../../career-coach/shared/handoff-contracts.md) and [Meal Planner](../../meal-planner/shared/handoff-contracts.md).

## No reverse handoff

`research-briefing` remains an independent entry point and has no automatic handoff to `superb-skills`. Use both only when the user's request includes both substantive research and instruction-package design.
