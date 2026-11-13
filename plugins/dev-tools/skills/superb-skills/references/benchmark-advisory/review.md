# Critique and explain benchmarks

Use this reference for an existing benchmark design, comparison, or result. Keep the requested mode: a critique assesses the benchmark; an explanation makes its design or evidence understandable. Neither mode redesigns, runs, or publishes the benchmark unless the user separately requests a design proposal; execution and publication remain outside this skill.

If the user also asks whether an instruction package behaves reliably, read [evaluation.md](../evaluation.md) for instruction-behavior claims. Keep benchmark conclusions tied to benchmark evidence and instruction conclusions tied to evaluation evidence in one response.

## Critique an existing benchmark

Start with the benchmark's stated question and intended decision. Assess whether its workload, comparator, measures, and evidence can answer that question. Do not silently replace the user's decision with a stronger one.

Check only the dimensions material to the claim:

- **Question and decision:** Is the benchmark descriptive, checking feasibility, comparing quality or cost, or selecting an option? Are recommendations limited to that decision?
- **Workload and comparison:** Are the tasks and conditions relevant and comparable? Check baseline, candidates, hardware, software/model versions, prompts, cache state, ordering, and other factors only when they can change the interpretation. Identify mismatches and confounders.
- **Measures:** Are outcomes defined with units and denominators? Consider quality, correctness, failures, and resource costs together. Clarify whether latency or cost covers a task, a turn, recovery, setup, or maintenance when that boundary affects the claim.
- **Coverage and evidence:** Identify what was measured, what was omitted, how many observations were retained, and whether observations are repeated, paired, clustered, or otherwise dependent when that changes uncertainty. Preserve failed, interrupted, missing, or blocked measurements as such.
- **Evidence gate:** Match evidence to the decision. A descriptive result does not need to select a winner; a selection claim needs evidence that supports selection. Do not impose a universal holdout, significance test, sample count, or fold count. Explain what stronger claim would require if the current evidence is narrower.

Prioritize recommendations by decision impact and feasibility. Tie each one to a supplied source or an identified gap. Separate required corrections to support the stated claim from optional ways to strengthen a future study. Do not claim a change was implemented or validated.

## Explain a design or result

Lead with the question the benchmark addressed and what the supplied evidence says. Explain task, comparison, measure, unit, and denominator in plain language when they are needed to understand the result.

Keep each evidence level clear:

- **Observation:** What the supplied record directly reports, including its source identity and scope when known.
- **Inference:** What that observation may support, with the reasoning and reference comparison stated.
- **Unknown or limitation:** What the record cannot establish, placed next to the claim it limits.

Explain quality and correctness alongside cost. Keep unlike stages, prompts, workloads, scoring rules, or populations separate unless the evidence supports comparison. Distinguish unavailable values from zero; do not impute missing totals, infer unreported settings, or treat a blocked or unfinished run as a pass. A single aggregate, such as one timing value without repeat observations or quality measures, supports a bounded description of that observation only. It does not by itself establish variability, statistical significance, general superiority, or successful-task efficiency.

If raw observations or context are absent, explain only what can be concluded from the supplied summary and name the missing evidence. Do not turn an explanation request into an interview or a redesign. Offer a separate design proposal only if the user asks for one.
