---
name: remember-me
description: Maintain and query a durable personal-context index in the user's accessible library, route topics to authoritative records owned by other skills, and manage remember-me-owned Markdown topic files and targeted history. Use when the user asks to remember, update, forget, locate, summarize, audit, or refresh reusable information about themselves. Do not use for a merely one-time preference or for specialist-domain work unless durable personal context must be consulted or changed.
---

# Remember Me

Maintain useful personal context without creating competing copies of authoritative records.

## Resolve the request

1. Identify whether the user wants to remember, retrieve, locate, refresh, audit, correct, or forget durable information.
2. Treat an explicit request to remember or update information as authorization for that bounded persistence. Keep an ordinary current-task instruction in the conversation unless the user asks to retain it or an established workflow already authorizes the write.
3. Ask only when a missing answer would change the canonical record, topic ownership, sensitivity decision, or destructive scope. Never persist an ambiguous inference as fact.
4. Read the canonical [inter-skill handoff contracts](../../shared/handoff-contracts.md) before invoking another skill, accepting personal context from a bundled skill, or returning a durable update request.

## Locate the index first

1. Search accessible library and project sources for `remember-me/index.md` or a clearly equivalent master index. Resolve it by provider and library or container scope, immutable resource identifier, and canonical permalink when available; use its visible filename, title, path, and search terms only as recovery fallbacks. Preserve its exact identity.
2. Treat the index as the authority for topic routing, ownership, source identities, and freshness. Treat the topic's identified current record as the authority for detailed current state.
3. If several plausible indexes exist and the choice could change the result, resolve the authority before substantive use or writing. Do not create a replacement because access is inconvenient.
4. If no index exists, create `remember-me/index.md` in the user's selected accessible library only when durable persistence is authorized. Do not create profile data inside the installed skill or plugin directory.
5. Read [record management](references/record-management.md) before creating or changing the index or a topic file, selecting topic ownership, refreshing external summaries, retrieving history, forgetting information, or handling duplicate or partial records.

## Retrieve only relevant context

- Read the index first, then retrieve the smallest sufficient set of relevant current context from the topic section or canonical source.
- Expand beyond the index or initial section when it is incomplete, stale, ambiguous, conflicting, or lacks consequential detail. Reliable recall takes priority over reducing context tokens, which takes priority over retrieval speed.
- Do not load every topic, contact every available skill, or read complete history merely because it is accessible.
- Apply current explicit instructions to the current task. Do not treat a current-task override as authorization to change durable records.
- Never let stored preferences weaken factual accuracy, evidence integrity, safety requirements, privacy constraints, or non-fabrication rules.
- Distinguish user-stated facts, confirmed preferences, evidence-supported patterns, reasonable inferences, working hypotheses, unknowns, and superseded information when material.
- For a factual or evaluative explicit or implicit comparison about the user or their records, identify the compared observations or reference set and the supporting evidence. Otherwise state only the supported absolute property and reasons. Clearly labeled subjective guidance may compare without empirical comparative evidence.

## Select the topic owner

- Preserve a specialist skill and its canonical record as owner when it handles the topic. Ask the available owner for a bounded summary, exact source identity, update date when visible, uncertainty, refresh trigger, and retrieval condition under the shared contract.
- Keep an externally owned index summary as a convenience cache. The canonical external source wins on conflict; mark the summary stale until it can be refreshed.
- Never copy a complete external record into `remember-me`, duplicate its schema, or write to another skill's records.
- When no available specialist handles a reusable topic, maintain one current Markdown file under `remember-me/` using the default taxonomy and schema in the record-management reference. Create no empty topic files.
- If a suitable owner later becomes available, propose a bounded migration or handoff. Do not silently transfer ownership or leave parallel current authorities.

## Update coherently

1. Confirm the new current state, evidence class, source, and effective date when material.
2. Preserve prior state in `remember-me/history.md` only when it retains explanatory, evidentiary, audit, or restoration value.
3. Update the authoritative remember-me-owned topic file or obtain the domain owner's completed update; never write an external owner's record directly.
4. Refresh the index summary, canonical identity, provenance, freshness, retrieval condition, and unresolved issues.
5. Add or revise a history pointer only when later retrieval could materially help.
6. Verify that no contradictory active formulation or competing authority remains.

For a request to forget information, resolve the exact target before deletion when scope is ambiguous. Remove it from current records and summaries; do not preserve information in history when that would defeat the user's request. Report what was removed and whether any externally owned or inaccessible copy remains outside this skill's control.

## Refresh and audit

Refresh a summary when the source is newer, the user reports a change, a contradiction appears, an identity or pointer no longer resolves, bounded retrieval fails, the topic is about to affect a consequential decision and may be stale, or its justified review condition is met. Do not refresh solely because time elapsed when the topic is stable and no decision needs it.

At an authorized write, explicit audit, or consequential use, check the measurable maintenance triggers in [record management](references/record-management.md) without loading unrelated topic contents. A due trigger requires review, not automatic refresh, deletion, compaction, or splitting.

During an audit, apply the general loss-controlled process in [working memory](../superb-skills/references/working-memory.md#loss-controlled-audits), then the user-record rules in record management. Verify topic ownership, canonical identities, source access, freshness, unresolved conflicts, broken pointers, unnecessary duplication, sensitive-data minimization, and whether the taxonomy still supports targeted retrieval. Propose repairs before making consequential authority or deletion decisions. Never replace the canonical records unless the staged before/after comparison passes; keep the original recoverable until the written state is verified.

## Protect personal information

- Retain only information with plausible future value.
- Never store passwords, authentication secrets, financial credentials, or unnecessary sensitive detail.
- Require confirmation before persisting an inference, replacing an explicit preference, resolving a consequential conflict, or retaining information whose sensitivity creates material privacy, safety, or misuse risk.
- Preserve household-member attribution and do not generalize one person's preference to another.
- If a record is unavailable, ambiguous, or partially writable, preserve uncertainty and provide a clearly labeled proposed update. Never imply that a read, refresh, or write succeeded when it did not.

## Return the result

Answer retrieval requests with the smallest sufficient set of relevant current context and source identity. After a write, summarize the topic, record identity, fields changed, provenance, freshness or history effects, and anything that remains proposed or unresolved without reproducing the complete personal record.
