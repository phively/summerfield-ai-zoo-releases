# Design a benchmark

Use this reference for a new benchmark or a requested redesign. Return a practical proposal for the user's question; do not run it or present planned evidence as observed.

If the user also asks whether an instruction package behaves reliably, read [evaluation.md](../evaluation.md) for instruction-behavior claims. Keep benchmark conclusions tied to benchmark evidence and instruction conclusions tied to evaluation evidence in one response.

## Start with useful options

For a broad goal, first offer a few plausible ways to frame the question or decision. Briefly say what each would compare or measure and what it could establish. Then ask a focused question when the user's answer could change the workload, comparison, measures, or interpretation. Make the question explicit and give a small set of options where useful. If the user says they do not know or are still weighing a material choice, end that response with the question and wait for their answer. Do not select a provisional framing in the same response. If the user asks you to draft despite the open choice, select a reasonable provisional framing, explain the tradeoff, and mark it as an assumption. Reuse answers already supplied.

Treat the user's latest explicit answer as settled even when earlier context is less specific. Do not turn an answered detail into an unknown. If supplied sources genuinely conflict, identify the conflict and its consequence rather than silently choosing or asking the user to repeat an answer.

## Shape the proposal around the decision

Make the smallest design that can answer the intended question. State:

1. **Decision and question:** What choice or claim will this benchmark inform? Keep descriptive, feasibility, quality, cost, and selection claims distinct.
2. **Workload:** Which tasks, inputs, operating conditions, and success criteria represent the intended use? Explain important exclusions.
3. **Comparison:** Name the baseline and candidates, and the conditions that need to be matched. Consider environment, version, prompt, cache, ordering, setup, and recovery only when they materially affect the comparison.
4. **Measures:** Define primary outcomes and guardrails with units and denominators. Keep correctness or quality, errors, latency, and resource costs visible together where relevant. State which parts of setup, maintenance, retries, or recovery are included in cost.
5. **Interpretation:** Identify likely confounders, dependence among cases, missing evidence, and the scope of any conclusion. Say what the proposed measurements can and cannot support.
6. **Feasibility and unknowns:** Describe a bounded check that could establish whether inputs, measurements, scoring, and evidence capture are workable. Mark it pending; a design proposal is not a trial or a result.

Match evidence gates to the decision. Do not copy an optimization study's holdout or significance requirements into a descriptive benchmark without a reason. Do not prescribe universal sample counts, folds, holdout percentages, or significance thresholds. If such a gate is important to the user's decision, explain which assumptions and variability information are needed to choose it; otherwise leave the number unspecified.

## Ask only material questions

Ask about a missing detail only if different answers would change one of these:

- the target workload or success condition;
- the baseline, candidate, or comparability requirement;
- the outcome, unit, denominator, or cost boundary; or
- what conclusion the measurements should support.

Prefer a short set of concrete options when they make the tradeoff easier to choose. Do not re-ask answered questions or delay a useful draft for details that can be carried as assumptions.

When a material choice is unresolved, make the actual question the last content in the response and stop there. Do not append a provisional design after the question. If the user already supplied the answer or asks you to proceed with a draft, use it and do not repeat the question. Keep pre-run validation as a pending check when needed; do not present validation of a stated fact as an unanswered design question.

## Stop at a useful provisional design

Return the design brief once it is actionable enough to review, even if some details remain open. Include the decision, workload, comparison, measures and units, quality/error tradeoffs, confounders, feasible validation idea, and explicit assumptions or unknowns. Mark pending feasibility or analysis choices as pending, not passed. Do not invent benchmark results, execute the workload, publish a report, or expand into instruction-package evaluation.
