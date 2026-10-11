# Preferences and verified lessons

Read this reference when designing a target skill whose execution changes with personal preferences, project settings, task-specific overrides, or operational mistakes that may have a reusable remedy. It governs how Superb Skills designs those mechanisms; it does not create a Superb Skills user profile and it does not replace the target's own runtime records.

## Keep authorities separate

For every target, classify each value before writing instructions:

- **Personal workflow preference:** When an available personal-context owner such as `remember-me` is relevant, request the smallest sufficient targeted context through the canonical [handoff contract](../../../shared/handoff-contracts.md#bundled-skills-to-remember-me-targeted-consultation). Do not copy its index, topic schema, retrieval procedure, or history into the target. If the owner is unavailable, preserve uncertainty and continue with supplied facts, neutral defaults, or a focused question when reliable.
- **Project setting:** Keep the target's operational settings in a project-owned readable/writable Markdown or YAML authority outside installed caches. Specify the owner, durable path, format, identity, permitted readers and writers, precedence, and behavior when the record is missing, stale, ambiguous, inaccessible, or partially writable. Keep defaults separate from user-specific values.
- **Task override:** Treat an explicit current-task instruction as a temporary override with a recorded precedence decision. Do not silently convert it into a project setting or personal preference.
- **Verified lesson:** Keep an applicable remedy with the target project or workflow that owns the failure. A lesson is evidence about a remedy, not a permission, preference, current instruction, or personal profile.

One authority owns each persistent value. A standalone target must preserve the same boundaries with its own available records when a companion personal-context skill is absent; do not make `remember-me` a mandatory dependency merely to use this guidance.

State the record owner explicitly inside the delivered target instructions, alongside the canonical path. Distinguish who owns and authorizes the settings from the skill or workflow permitted to maintain them; a path or write-permission rule alone does not identify an owner. Use the supplied owner, or identify the user as owner when the user has designated their record as canonical and no separate owner is supplied. Do not invent another person or service.

Read mutable settings from the current canonical record. Label supplied initial values as fixture data or examples, rather than repeating them as permanent operating rules. After a verified authorized update, subsequent tasks use the updated record; task-only overrides remain temporary.

## Design focused intake

When a missing value can change execution, design the target to:

1. Reuse an explicit value supplied in the current request before consulting or asking for anything else.
2. Read the identified canonical record only when its topic and freshness could affect the current decision. Ask one focused question for the smallest missing decision; do not conduct a broad interview.
3. Apply the declared precedence among task overrides, project settings, personal context, and defaults. State which value won when the distinction matters.
4. Continue directly when valid configuration is available. If configuration is absent or an optional record is unavailable, state the precise limitation and either use a declared neutral fallback or return a `needs_focused_input` result for unattended work. Never invent a preference, treat a default as approval, or create an empty authority as a substitute for intake.
5. Keep persistence separately authorized. If a write is not requested or authorized, retain the value only for the current task.

The target design must describe the supplied, missing, unavailable, override, and partial-write branches. A partial write retains the last verified authority or marks the new state uncertain, reports what failed, and never claims persistence. Bound retries and retry only when current authorization explicitly covers the retry; request fresh authorization when it does not.

## Maintain verified lessons

Use this lifecycle only when an observed mistake has a potentially reusable operational remedy or when repeated, material failures make a lesson store useful. Do not add durable lesson storage to a target that has no such need.

1. **Recognize:** distinguish one observed mistake, a repeated material failure, a transient error, a user correction, and ordinary task variation. One occurrence is not proof of a recurring pattern. A single observation may support a *preventive* lesson only after a target-relevant remedy has been verified; describe it as based on one observation, not as recurring.
2. **Diagnose:** record the observed symptom separately from a proposed cause. Label unresolved diagnoses and do not state them as facts.
3. **Verify:** test the remedy against the applicable target, configuration, and authorization. Preserve the evidence and limitations. A plausible explanation or an untested recommendation is not a verified remedy.
4. **Record:** only after verification, store the remedy in the target-owned authority with a stable lesson ID, observed mistake, verified remedy, applicability, evidence reference, date, owner, status, and permission limits. Do not store a transcript or unnecessary sensitive detail. Keep a preventive lesson's scope and single-observation basis explicit.
5. **Retrieve:** look for an applicable verified lesson before similar work, while checking target identity, version, freshness, and scope. Apply only what remains compatible.
6. **Revise or retire:** when applicability changes, revise the scope or mark a stale, contradicted, superseded, or inapplicable lesson retired. Preserve the reason and evidence; do not silently promote it back to current authority.

Lessons never authorize a benchmark rerun, external write, reviewer transmission, or other action. Existing confirmation and permission boundaries remain authoritative. If lesson storage is unavailable, return the current-task result with an explicit limitation; do not simulate persistence or create a competing cache.

## Require target evidence

For a preference-dependent target, include design cases for supplied values, missing decisions, unavailable personal or project records, task overrides, partial writes, stale or conflicting lessons, and an ordinary target that needs none of these mechanisms. Inspect the target's actual instructions and records separately from the designer's guidance. Acceptance requires that the target can explain its owner, precedence, intake, fallback, persistence authorization, and lesson lifecycle without relying on the designer's conversation history.

Do not add preference intake, durable lessons, or a record layer to a simple target whose user goal and deterministic acceptance checks do not need them.

Before delivery, check the target artifact itself for an explicit owner and canonical path, permitted readers and writers, override precedence, specific persistence permission, and unavailable or partial-write behavior. Verify that updating a canonical setting changes subsequent behavior without editing a second copy in the instructions.

## Decide target persistence

For a reusable preference-dependent target, make the persistence decision explicit. When the target should reuse household preferences, design one optional target-owned canonical record even if it is standalone; state its owner and path, permitted reads and writes, task-override precedence, and missing, unavailable, or partial-record behavior. If existing data is inaccessible or partly readable, never create a second record, overwrite unknown fields, or write until its canonical path and latest state are verified; initialize only a confirmed-missing record at the user-designated path after exact save authorization. Require exact authorization for each update, preserve unrelated values, and verify authorized changes. Keep values task-only when that is the intended scope, and explain why. For food-planning targets, design focused intake for allergies or medical restrictions and serving count before recommendations. Translate these requirements into observable validation cases, including unauthorized and authorized updates when persistence is in scope.
