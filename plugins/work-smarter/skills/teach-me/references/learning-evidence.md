# Learning evidence

This is the current evidence authority for the `teach-me` learning philosophy. Read it only when evidence behind the pedagogy, candidate literature, or maintenance of the framework is relevant. It supports but does not override `learning-philosophy.md`, current user instructions, or evidence about the lesson's subject matter.

## Record metadata

- Owner: `teach-me` design-maintenance workflow
- Current authority: this file
- Initial comprehensive review: 2026-09-06
- Last targeted AI-learning review: 2026-09-06
- Next targeted AI-learning review due: 2026-12-06
- Next comprehensive review due: 2027-09-06
- Initial provenance: source-level audit contained in the user-supplied `teach-me` research and architecture transcript
- Implementation note: the 1.7.0 implementation captured that audited synthesis but did not independently repeat its web research
- History: Git; do not create a separate history file until current retrieval or auditability materially benefits from separation

## Current synthesis

### Strong general support

- Retrieval practice and distributed practice support retention; useful schedules depend on material, learner, and desired retention interval.
- Assisted fluency, recognition, and immediate task performance are not sufficient evidence of durable or transferable capability.
- Scaffolding should vary with prior knowledge and task complexity. Worked examples can help learners without a usable schema, while excessive guidance can become redundant as expertise grows.
- Feedback is heterogeneous; feedback that explains evidence, reasoning, or corrective action is generally more instructionally useful than a bare correctness signal.

### Supported with important conditions

- Generation, prequestioning, and problem solving before instruction can help, but their benefit depends on prior knowledge, task design, later instruction, and what is measured.
- Interleaving is most defensible when learners must discriminate among confusable categories or select among strategies; it is not a universal replacement for blocked practice.
- Errors become useful learning material when learners can interpret, compare, and correct them without overload.
- Confidence judgments become useful when compared with subsequent performance; felt fluency alone is a poor mastery measure.

### Emerging AI-specific evidence

- LLM assistance can improve work while available without producing corresponding independent learning and can sometimes reduce later unaided performance.
- Interaction design matters: learner generation before assistance, guarded tutoring, active note-taking, and corrective feedback can preserve more target processing than unrestricted answer provision.
- Machine advice can teach both correct and incorrect patterns. Learners therefore need practice detecting commission errors, omission errors, and unverified recommendations.
- Current LLM-specific evidence is much stronger for immediate or short-delay performance and transfer than for long-term retention.

### Do not use as foundations

- generalized claims that AI use necessarily causes cognitive decline or irreversible skill loss;
- EEG findings from small LLM-writing studies as proof of broad learning harm;
- mathematical tipping-point models as observed causal effects;
- universal human-first, AI-first, generation-first, delayed-feedback, or interleaving rules; or
- learner satisfaction, model agreement, or one successful attempt as proof of mastery.

## Principle-to-evidence map

| Principle | Evidence position | Main limitations |
| --- | --- | --- |
| Assess capability beyond assisted performance | Strong general evidence; growing direct AI evidence | Long-term LLM-specific evidence remains limited |
| Use retrieval and distributed revisiting | Strong across many learning settings | Timing and task implementation vary |
| Adapt examples and generation to prior knowledge | Supported by worked-example, expertise-reversal, and PS-I research | Effects vary by age, domain, and task complexity |
| Prefer explanatory correction and reconstruction | Broad feedback evidence plus emerging machine-mentoring evidence | Feedback effects are heterogeneous |
| Preserve target cognition while delegating supporting work | Design synthesis supported by automation and active-encoding research | Not a single experimentally established universal law |
| Train critical evaluation of AI advice | Supported by automation-bias and machine-mentoring studies | Mitigations reduce but do not eliminate over-reliance |
| Use contrast and interleaving for discrimination | Supported conditionally | Domain differences are substantial |
| Treat the tutor as fallible | Safety and transfer implication from automation evidence | Exact exercise design requires domain judgment |

## Initial source register

`verified` below means that the supplied 2026-09-06 audit reported checking the source and the summarized result. Preserve that provenance until a future maintenance review independently verifies it again.

| ID | Status | Source | Contribution and constraint |
| --- | --- | --- | --- |
| LE-001 | verified | [Dunlosky et al. (2013)](https://doi.org/10.1177/1529100612453266) | Comparative review; supports practice testing and distributed practice strongly, with self-explanation and interleaving more conditionally. |
| LE-002 | verified | [Cepeda et al. (2006)](https://pubmed.ncbi.nlm.nih.gov/16719566/) | Large distributed-practice synthesis; spacing depends on the desired retention interval. |
| LE-003 | verified | [Pan and Rickard (2018)](https://pubmed.ncbi.nlm.nih.gov/29733621/) | Retrieval-practice transfer meta-analysis; supports testing as learning beyond exact repetition. |
| LE-004 | verified | [Bertsch et al.](https://pubmed.ncbi.nlm.nih.gov/17645161/) | Generation-effect synthesis; largely memory-paradigm evidence, not justification for unguided complex problem solving. |
| LE-005 | verified | [Sinha and Kapur (2021)](https://journals.sagepub.com/doi/abs/10.3102/00346543211019105) | Meta-analysis of problem solving before instruction; Productive Failure is a narrower design within that family. |
| LE-006 | verified | [Schwonke et al.](https://www.sciencedirect.com/science/article/pii/S0747563208002161) | Faded worked examples in tutoring; supports example-first instruction and gradual completion. |
| LE-007 | verified | [Tetzlaff et al. (2025)](https://doi.org/10.1016/j.learninstruc.2025.102142) | Expertise-reversal meta-analysis; supports adapting assistance to prior knowledge, with domain and population heterogeneity. |
| LE-008 | verified | [Interleaving meta-analysis](https://pubmed.ncbi.nlm.nih.gov/31556629/) | Supports conditional use, particularly when discrimination among similar categories matters. |
| LE-009 | verified | [Wisniewski et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6987456/) | Broad feedback meta-analysis; effects are heterogeneous and information content matters. |
| LE-010 | verified | [Koriat and Bjork](https://pubmed.ncbi.nlm.nih.gov/16938051/) | Foresight bias; visible study cues can inflate judgments of later retrievability. |
| LE-011 | verified | [Dieterich, Rumann, and Rodemer (2025)](https://doi.org/10.1007/s10648-025-10071-x) | Erroneous-example review; usefulness depends on comparison, prompts, feedback, prior knowledge, and load. |
| LE-012 | verified | [Wong and Qiu (2026)](https://link.springer.com/article/10.1007/s10648-026-10118-7) | Regulated think-first-then-AI interaction improved subsequent unaided creative performance; establishes near-term transfer, not long-term retention. |
| LE-013 | verified | [Bastani et al. (2025)](https://doi.org/10.1073/pnas.2422633122) | Unrestricted GPT improved practice but reduced later unaided performance; guarded tutoring mitigated harm without proving superiority to control. |
| LE-014 | verified | [Kreijkes et al.](https://www.sciencedirect.com/science/article/pii/S0360131525002829) | Note-taking outperformed LLM-only learning after three days; 405 enrolled and 344 analyzed. |
| LE-015 | verified | [Fan et al.](https://doi.org/10.1111/bjet.13544) | Better assisted essays without significant corresponding knowledge or transfer gains; proposed mechanism should not be treated as demonstrated. |
| LE-016 | verified | [Darvishi et al.](https://www.sciencedirect.com/science/article/pii/S0360131523002440) | AI-supported peer-feedback field evidence; distinguishes relying on assistance from learning the underlying reviewing behavior. |
| LE-017 | verified | [Memmert et al.](https://link.springer.com/article/10.1007/s12599-025-00974-y) | Separates combined human-AI output from ideas generated by the human; results do not justify universal homogenization claims. |
| LE-018 | verified | [Goddard et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3240751/) | Automation-bias review; presentation, workload, trust, and task structure affect reliance, while mitigation evidence is mixed. |
| LE-019 | verified | [Endsley and Kiris](https://journals.sagepub.com/doi/pdf/10.1518/001872095779064555) | Out-of-the-loop performance and situation-awareness evidence; retained human control affects degradation. |
| LE-020 | verified | [Skitka et al.](https://www.sciencedirect.com/science/article/pii/S1071581999902525) | Supports distinct commission and omission errors and cautions against treating warnings as complete protection. |
| LE-021 | verified | [Casner et al.](https://journals.sagepub.com/doi/10.1177/0018720814535628) | Automation affected cognitive aviation skills differently from manual control skills; task-specific rather than universal. |
| LE-022 | verified | [Machine-mentoring experiment](https://www.sciencedirect.com/science/article/pii/S107158192500031X) | Faulty machine advice transferred into later unaided decisions alongside some useful learning. |
| LE-023 | verified | [Machine-mentoring follow-up](https://www.sciencedirect.com/science/article/pii/S1071581926001308) | Corrective feedback about learner and machine decisions produced learning where advice or confidence information alone did not. |
| LE-024 | watchlist | [Solé et al. (2026)](https://arxiv.org/abs/2609.03344) | Conceptual mathematical model; useful framing but not empirical evidence of cognitive dependence or tipping points. |
| LE-025 | watchlist | [Kosmyna et al.](https://arxiv.org/abs/2506.08872v2) and [methodological critique](https://arxiv.org/abs/2601.00856) | Preliminary LLM-writing, recall, ownership, and EEG findings with substantial methodological limitations; do not use as a foundation. |

## Candidate-source intake

Add a source without changing the synthesis when it has not been evaluated. Use a stable `LE-###` identifier and record:

- status: `candidate`, `verified`, `watchlist`, `excluded`, or `superseded`;
- full citation and persistent link;
- date added and provenance;
- evidence type, population, task, comparison, delay, and transfer distance;
- finding relevant to an existing or proposed principle;
- limitations, disagreement, corrections, or retractions;
- decision impact: changed philosophy, changed workflow, corroborated, constrained, or no material effect; and
- verification date and reviewer or workflow.

User-supplied claims remain attributed and `candidate` until evaluated. Promotion to `verified` requires checking the source itself and confirming that it supports the recorded claim. Mark unsuitable evidence `excluded` with a short reason rather than silently deleting it when the exclusion remains useful for later decisions.

## Maintenance

Review the fast-moving AI-learning literature quarterly and the broader framework annually. These intervals are maintenance heuristics, not empirical learning prescriptions. A due date means review is due; it does not authorize research, an external write, or an autonomous reminder.

Also review when:

- a user supplies a potentially framework-changing source;
- credible evidence materially conflicts with an active principle;
- a source is corrected or retracted;
- an active claim lacks a resolvable source;
- bounded retrieval repeatedly misses relevant current evidence;
- the file exceeds 16 KiB or grows by 25 percent since its last structural review; or
- a split, compaction, schema migration, or authority transfer is proposed.

For a material update, preserve the existing file, inventory current principles and sources, stage the revision, map each changed item to retained, revised, added, excluded, or superseded, check links and active contradictions, and replace the current authority only after review. Git history is sufficient while the record remains understandable and easy to retrieve; add a separate history only when meaningful superseded conclusions make the current file materially harder to use.
