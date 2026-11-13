# Dev Tools handoff contracts

This file defines Dev Tools caller-side requirements and its public ownership handoff. Use an optional handoff only when the receiving skill is available and its work materially supports the current request. The receiving skill remains authoritative for its own procedure, permissions, and output.

## Superb Skills to Research Briefing

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `dev-tools:superb-skills` |
| Receiving skill | An available `research-briefing` skill |
| Trigger | A material external factual claim needs current verification, source evaluation, or citation before the instruction package can be designed or assessed reliably. |
| Required input | State the exact claims or questions, the design decision they affect, relevant current context, user-provided facts as such, known version/date/jurisdiction, and unresolved questions. Preserve any user authorization and its scope. |
| Expected output | Return evidence with direct citations, decisive source identities, relevant measurements, competing interpretations, limits, and explicit fact/source-claim/inference/unknown labels to the originating design task. For factual or evaluative comparisons, identify the reference set and supporting evidence. |
| Authority and provenance | Research supports factual claims; it does not replace the user's objective, supplied requirements, or the instruction package's design judgment. |
| Uncertainty and failure | Preserve material uncertainty. If research or the receiver is unavailable, mark dependent claims unverified and continue only with work that remains reliable. Do not imply research occurred. |
| User confirmation | Follow the receiving skill's research-scope checkpoint unless the user explicitly waived it for this request or session. Starting a handoff is not confirmation. |

## Dev Tools to Remember Me: targeted consultation

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `dev-tools:superb-skills` or `dev-tools:coding-preferences` |
| Receiving skill | An available `remember-me` skill |
| Trigger | Relevant stable personal context is missing from the current request and could materially shape a discretionary design or coding choice, or a relevant general writing preference could materially shape explicitly requested engineering prose. |
| Exceptions | Do not consult for one-time instructions, incidental facts, context that cannot change the work, or information outside authorized accessible sources. |
| Required input | State the current decision, specific topic needed, smallest sufficient context, and any known source identity or freshness concern. |
| Expected output | Return only relevant context with canonical source identity, owner, evidence classification, freshness, retrieval condition, and material uncertainty. |
| Authority and provenance | The canonical personal record governs durable context. General writing preferences remain with Remember Me; coding values remain with the coding-preferences specialist. Current user instructions govern the present task and do not silently rewrite either authority. |
| Uncertainty and failure | Keep inferred, stale, missing, conflicting, or inaccessible states explicit. If the skill or source is unavailable, continue with neutral defaults when reliable and state any material limitation. |
| User confirmation | A targeted read of an already authorized accessible record needs no new confirmation. The receiving skill's setup gate still applies; unknown setup permits no implicit personal-topic use or persistence. Persistence, replacing an explicit preference, resolving a consequential conflict, or retaining materially sensitive information requires the applicable user authorization. |

## Dev Tools to Remember Me: durable update request

| Contract field | Requirement |
| --- | --- |
| Invoking skill | A Dev Tools skill requesting an explicit update only for non-coding personal context owned by Remember Me. |
| Receiving skill | An available `remember-me` skill |
| Trigger | The work reveals a reusable non-coding personal fact or preference that the user explicitly wants maintained beyond this task. Coding conventions remain owned by `dev-tools:coding-preferences`. |
| Required input | Provide the exact proposed change, source and evidence classification, topic, reuse rationale, effective date when known, sensitivity, approved content and destination, authorization scope, and visible current record identity. |
| Expected output | Return the canonical record identity, exact persistence status, provenance, conflicts, and fresh readback evidence for each verified change. |
| Authority and provenance | `remember-me` owns its index and topic records. Dev Tools must not maintain a competing personal profile or claim another skill's write succeeded. |
| Uncertainty and failure | If authority, access, or writability is unresolved, return a labeled proposal and identify the failed operation. Never report persistence after an unavailable or partial write. |
| User confirmation | Preserve actual user authorization. A handoff cannot manufacture permission to save, replace, resolve a conflict, or retain sensitive information. |

## Remember Me to Coding Preferences: optional specialist routing

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `remember-me` |
| Receiving skill | `dev-tools:coding-preferences`, when available. |
| Trigger | The user asks to retrieve, update, or transfer coding-convention values already routed to the specialist, or explicitly selects it as the owner for coding preferences. |
| Required input | Provide only the relevant coding topic, the exact source identity when an existing record is involved, and the user's exact authorization, scope, and selected destination for a transfer or write. Do not pass a full personal profile. |
| Expected output | Return the relevant current preference or proposed change, a verified or unverified outcome for each requested update, and any unresolved ownership or reconciliation state. |
| Authority and provenance | `dev-tools:coding-preferences` owns coding values. Remember Me may identify the owner, but must not keep a second collection of coding preferences or change the owner's preferences itself. |
| Uncertainty and failure | If the specialist or destination is unavailable, preserve the established authority, continue only with reliable current-task information, and report the limitation. Do not create a replacement or imply a transfer occurred. |
| User confirmation | A read follows Remember Me's existing setup and access gate. A transfer requires explicit authorization for the exact values, destination, and ownership change. |

For an authorized transfer, the receiving specialist verifies the selected destination before Remember Me changes its own source information. Keep the source recoverable until both sides are verified. Report the destination update, Remember Me changes, and ownership outcomes separately whenever any result remains uncertain.

## Caller to Code Quality Review: bounded review request

| Contract field | Requirement |
| --- | --- |
| Invoking skill | A caller that the user asked to review code or for which the user accepted a review recommendation |
| Receiving skill | An available `dev-tools:code-quality-review` skill |
| Trigger | The user requests a code-quality review or accepts a specific recommendation. Ordinary implementation and coding-preference tasks do not acquire a reviewer prerequisite. |
| Required input | Provide the target paths or supplied code, intended behavior, base and head or captured dirty-diff identity, applicable repository instructions and public contracts, relevant tests and observed checks, any resolved conventions with their authority, review questions, allowed operations, and whether independent review is required. |
| Expected output | Return the reviewed target identity and scope, delegation route and completion limits, supported findings with locations, evidence, consequences, and bounded remedies, optional suggestions labeled separately, observed checks, and missing coverage. Do not change the target or claim checks that were not observed. |
| Authority and provenance | The user's requested scope and applicable repository instructions govern the review. Project rules take precedence over portable preferences; only applicable resolved conventions and their source should be passed. The review skill owns its private rubric. |
| Uncertainty and failure | If the target changes after capture, bind findings to the captured contents and identify the new target as unreviewed. Missing evidence, unavailable context, or an incomplete reviewer remains a disclosed limitation rather than a clean pass. If tools are prohibited, use supplied content only and do not retrieve, run commands, or spawn a reviewer. |

## Code Quality Review to Coding Preferences: optional convention consultation

| Contract field | Requirement |
| --- | --- |
| Invoking skill | `dev-tools:code-quality-review` |
| Receiving skill | An available `dev-tools:coding-preferences` skill |
| Trigger | A specific portable coding convention remains unresolved after applicable task instructions, repository rules, and public interfaces are checked, and resolving it could change the review conclusion. Do not consult for generic taste or when the relevant value is already verified. |
| Required input | State the exact unresolved convention, relevant language or artifact type, the smallest affected code context, the instructions already checked, and any retrieval limits. Ask only for the applicable convention. |
| Expected output | Return only a relevant resolved value with its authority, provenance, applicability, freshness, and uncertainty. Do not include unrelated personal context or write a preference. |
| Authority and provenance | Repository instructions and explicit task requirements govern the repository. Coding Preferences owns portable coding values; a consultation informs the review but does not change the target or the review skill's private procedure. |
| Uncertainty and failure | If the receiver or source is unavailable, use applicable repository guidance or a disclosed neutral default and mark any material convention question unresolved. Do not create a competing preference store or route the same question back in a loop. |

## No automatic continuation

A handoff supports the originating task and does not replace it. Do not begin a separate research report or personal-record workflow unless the user requested that deliverable.
