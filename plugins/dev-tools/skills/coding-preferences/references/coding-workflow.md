# Coding workflow

Read this reference for implementation, code review, explanation, or engineering prose when coding preferences may affect the result.

## Preserve the requested mode

Resolve what the user asked for before reading records or running commands.

- **Implementation:** make the smallest complete change that satisfies the request.
- **Review-only:** report supported findings with relevant evidence and impact. Do not edit files unless the user also requested fixes.
- **Explanation-only:** answer the question. Do not edit files, run an evaluation, or start a benchmark unless requested.
- **Engineering prose:** produce the requested design, plan, documentation, or status text. Do not turn prose into a code change.
- **No-tool:** use only information already supplied in the conversation. Do not read files, search records, run commands, or write anything.

Keep this skill out of general prose and instruction-package design. A request to save a preference is not implied by following one during a task.

## Resolve applicable conventions

Use explicit task instructions, applicable repository instructions and conventions, verified relevant coding preferences, then ordinary disclosed defaults. Host instruction priority still governs. Read repository guidance and the affected code before choosing a style when those sources can change the result. Do not search for a preference record when the task and repository already settle the choice.

When a user asks for a one-time override, apply it only to the current task. When an explicit request materially conflicts with a repository convention, call out the conflict at the point it affects the work. Follow the user's requested scope where permitted, but do not silently change formatter, linter, or project configuration. Ask a focused question only when the conflicting instructions make the requested result genuinely unclear.

Use only preference entries that apply to the language, repository, artifact, and task. An unavailable or uncertain record does not justify guessing a personal preference. Continue with explicit task instructions, reliable repository rules, and a neutral default; disclose a material limitation.

## Preserve module boundaries

Use another module through its documented public interface. Do not expose or depend on its private implementation details; keep those details inside their owning module.

## Implement and verify proportionately

Inspect the smallest relevant area and existing test or formatting conventions. Make a focused change; avoid speculative abstractions, unrelated restyling, and opportunistic cleanup. Add a meaningful regression check when a behavior defect is small and feasible to reproduce. When a check is warranted and feasible, observe it fail on the unfixed behavior, then pass it after the correction; confirm the failure concerns the requested behavior rather than a syntax or setup error. If the check or either run is unavailable, report the sequence as unverified instead of claiming red/green proof. Do not add tests that only restate the implementation.

Run the repository's applicable formatting, linting, and tests for the changed work. Report which checks actually ran and their results. If a tool or test is unavailable, distinguish that limit from a failing check. Do not claim broader validation than the evidence supports.

For a review, explanation, or prose-only task, apply relevant preferences to the response and keep the operation read-only. A saved preference never authorizes edits, extra research, benchmark trials, or a broader task.
