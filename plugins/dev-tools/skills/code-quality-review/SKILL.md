---
name: code-quality-review
description: Review code for correctness and material maintenance risks when requested or accepted; ordinary implementation and coding-preference work do not acquire a reviewer prerequisite.
---

# Code Quality Review

Use this skill only for a requested code-quality review or after the user accepts a review recommendation. Do not add a review gate to ordinary implementation or coding-preference work.

Read [the private reviewer guide](references/reviewer.md) for target capture, evidence, findings, delegation, and optional convention consultation. When invoked by another skill, follow the public [caller contract](../../shared/handoff-contracts.md#caller-to-code-quality-review-bounded-review-request); it defines the request and result boundary, not this skill's private review procedure.

Keep reviews read-only. Do not edit the target, install dependencies, change persistent preferences, commit, or ship. A no-tool request uses supplied content only: do not read files, run commands, retrieve preferences, or spawn a reviewer. Report the reviewed scope and limits; do not imply checks or coverage that did not occur.
