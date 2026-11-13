---
name: coding-preferences
description: Apply relevant portable coding preferences to implementation, code review, explanation, and engineering prose. Use when reusable coding conventions could affect the result; do not use to manage general personal or writing preferences.
---

# Coding Preferences

Apply portable coding preferences to useful engineering work without taking over repository policy, general writing preferences, or the user's requested operation.

## Resolve the requested operation

Use this skill for code implementation, code review, explanation of code or engineering behavior, and engineering prose such as technical plans or documentation. Do not use it for general prose or reusable instruction-package design.

Respect the requested mode throughout the task. A no-tool request permits no reads, commands, tests, or writes. Review-only and explanation-only requests remain read-only. Do not turn a request for a code change into a preference-record update. A durable preference change requires explicit authorization for its values and scope.

## Apply relevant preferences

Read [coding workflow](references/coding-workflow.md) for an implementation, review, explanation, or engineering-prose task. Retrieve a coding preference only when it could materially change a discretionary choice and is not already settled by the current request or repository guidance. Read [record management](references/record-management.md) when resolving, saving, or changing a durable preference authority.

For requested engineering prose, use the public [handoff contract](../../shared/handoff-contracts.md#dev-tools-to-remember-me-targeted-consultation) only when relevant general writing context is missing and could materially change the result. Do not load a complete profile or copy writing values into the coding record.

Apply the relevant rules in this order, subject to higher-priority host instructions:

1. Explicit instructions for the current task.
2. Applicable repository instructions and conventions.
3. Verified, relevant portable coding preferences.
4. An ordinary, disclosed default where a choice remains.

If the user gives an exact preference value in the current request and asks you to apply it, treat that value as a task instruction for this task even when no canonical record is available. Do not claim the stored record was read or verified, and do not persist the value unless separately authorized.

A task-specific override applies only to that task unless the user explicitly authorizes a durable preference update. If a request materially conflicts with a repository convention, identify the conflict and follow the user's explicit scope where permitted. Do not silently change formatter or linter configuration to make the result appear consistent.

If the selected record or a required tool is unavailable, keep the uncertainty visible and continue with supplied instructions and reliable repository guidance. Use a neutral default only for an unresolved discretionary choice. Never claim a preference was read, saved, or reused without evidence.

## Keep preference storage separate

The user's selected Markdown record is the only coding-preference value authority. Do not put user preferences in this skill, another package file, an unselected store, or a second YAML profile. General writing preferences remain with their established owner; do not copy their values into the coding record.

Use [record management](references/record-management.md) for bounded discovery, exact identity, authorization, updates, readback, and recovery. A record write and a persistent pointer that makes it discoverable in a later session are separate changes. Never edit user or project instructions to add a pointer unless that exact change is authorized.

Report only material preference use or limits, the requested work, and actual check outcomes. Keep code review findings separate from changes, and do not imply that static instruction checks demonstrate runtime behavior.
