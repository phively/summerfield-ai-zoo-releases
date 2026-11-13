# Reviewer Guide

Use this procedure only for a requested code-quality review or after the user accepts a review recommendation. It is a read-only review, not an implementation, test gate, or general coding assistant.

## Capture the request and target

Before drawing conclusions, identify:

- the review question and intended behavior;
- the exact target and scope;
- applicable repository instructions, public module contracts, relevant tests, and any check evidence already available;
- allowed operations, including whether tools and independent review are allowed or required;
- any resolved convention that could affect the conclusion, with its source and uncertainty.

Bind the review to the actual input. For a clean repository target, identify the repository and base/head commits or reviewed commit, plus the included paths. For dirty work, identify the captured staged and unstaged changes, included untracked files, and a digest or equally precise identity for the captured contents; a branch name or revision alone does not identify dirty work. For supplied material, name the supplied artifact and the exact content or excerpt reviewed. Do not build a reusable snapshot system. If you cannot identify the reviewed input precisely, narrow the conclusion or report that the review could not be bound to a stable target.

If the target changes after capture, keep findings attached to the captured identity and say that the new contents were not reviewed. Do not silently transfer findings to a changed diff.

## Review the bounded scope

Read applicable task and repository guidance before judging conventions. Trace affected behavior through the relevant public interfaces and nearby tests; avoid expanding into unrelated files. Look for supported risks in correctness, module boundaries and encapsulation, focused scope, maintainability, meaningful behavioral coverage, and repository formatting conventions.

Apply convention precedence in this order: current task instructions, repository instructions and conventions, verified relevant portable coding preferences, then an ordinary disclosed default. A project rule or public interface overrides generic taste. Do not present a stylistic preference as a defect. If a material portable convention remains unresolved after checking task guidance, repository rules, and public interfaces, use the public [Coding Preferences consultation](../../../shared/handoff-contracts.md#code-quality-review-to-coding-preferences-optional-convention-consultation) only when that skill is available. Pass the smallest relevant context and retain the returned convention's authority and provenance. Do not read preference records directly, send unrelated personal context, or write a preference. If consultation is unavailable, use a reliable project rule or disclosed neutral default and mark any material uncertainty.

Judge tests by whether they exercise externally meaningful behavior or only repeat the implementation. Recommend a red/green check only when it would resolve a concrete uncertainty or demonstrate a supported failure. Do not require a regression test for every change, especially a cosmetic or documentation-only change. Distinguish checks actually observed from checks proposed, unavailable, or not run; a missing check is not a pass.

No-tool is a strict boundary: use only content supplied in the request. Do not read repository files, inspect preferences, retrieve external information, run commands or tests, or delegate. State any resulting scope limit.

## Optional bounded delegation

When tools and delegation are allowed and the host can delegate, use one separate generic host child agent for an independent review pass. Do not dispatch nested agents or require a custom-agent registration. Give the child only the captured target identity and in-scope content or paths, intended behavior and review questions, applicable repository guidance and public contracts, relevant tests and observed checks, verified conventions with provenance, and the allowed-operation limits. Ask it to return only supported findings with locations, evidence, consequences, bounded remedies, optional suggestions, checks actually observed, and uncertainties. The child must not edit files, install dependencies, commit, ship, or delegate further.

A native child inherits the parent task's permissions; a read-only prompt is not a separate sandbox. Honor all inherited and user-stated limits. If delegation is unavailable or forbidden, label the route as same-agent. If independence was explicitly required, report that requirement unmet even if you can still provide clearly labeled same-agent observations. If a child fails or returns incomplete work, disclose the incomplete pass and use only verified partial observations; do not silently retry or call it a completed independent review. Any useful same-agent continuation must remain labeled as such.

When tools are prohibited, do not spawn a child. A normal review may use the supplied content in the same agent, with that route disclosed. If independent review is required, say it remains unmet.

## Return the review

Identify the reviewed target, captured identity, included scope, and route (delegated, same-agent, or incomplete). Order findings by correctness and material maintenance consequence. Each finding must name a location and include:

- the evidence in the captured target or applicable contract;
- the resulting consequence and why it matters;
- a bounded remedy that addresses the supported issue.

Use priority labels only when they reflect the relative consequence. Keep optional style or cleanup suggestions in a separate section. If no supported finding remains, say that none was found in the stated scope; do not imply the code is defect-free or fully validated.

Report observed checks separately from proposed checks, checks not run, unavailable evidence, and any incomplete reviewer pass. Tie each conclusion to its evidence and target identity. Do not modify files, install dependencies, change preferences, commit, or ship as part of the review.
