---
name: fixture-preference-planner
description: Fixture target for testing preference intake, editable project settings, task overrides, and verified operational lessons.
---

# Fixture preference planner

Use the project-owned settings file for current project preferences. Ask only for missing decisions that change the requested plan. Treat a task-specific instruction as a current-task override and do not silently write it to project settings.

Read lessons only when they are marked verified and applicable. A stale or uncertain lesson is evidence to review, not authority to apply. Keep authorization separate from lesson retrieval.

When personal context is unavailable, state that limitation and continue with supplied project settings or focused questions. Never invent a preference or create a competing personal record.

For unattended work, missing settings produce `needs_focused_input` with no persistent write. A task-specific preference remains a current-task override. If a `partial-write` partially fails, retain the last verified value or mark the new value uncertain, report the failed persistence check, and never claim success or retry beyond the currently authorized bound.

Do not apply a stale lesson as current guidance. Preserve the task result while recording that verification is required before the lesson can become applicable again.
