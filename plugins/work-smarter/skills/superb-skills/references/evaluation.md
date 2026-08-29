# Evaluation and architecture comparison

Use this reference to design tests, compare architectures, validate implicit activation, diagnose observed failures, or determine whether a revision improves performance.

## Build the evaluation set

Include representative cases for:

- explicit invocation;
- indirect requests expressing the intended goal;
- incomplete inputs requiring a focused question;
- adjacent requests that must not activate the skill;
- ambiguous vocabulary shared by multiple skills;
- mixed workflows that may require coordination;
- unavailable tools or references;
- likely fabrication, authority, or compatibility failures; and
- unsupported explicit and implicit comparisons, supported comparisons with a named reference set, and clearly labeled subjective comparisons; and
- regressions in existing triggers and outputs.

For every case define the input, intended activation and behavior, observable success criteria, and failure criteria. Do not encode only ideal outputs; evaluate process requirements such as confirmation, source use, file preservation, and prohibited actions.

## Compare architectures

Use the same prompt set, environment, model configuration, permissions, and scoring rules for each candidate. Measure when observable:

1. activation precision and recall;
2. false-positive and missed activation rates;
3. number of skills and references loaded;
4. relevant versus irrelevant instruction volume;
5. clarification turns;
6. completion of task-specific requirements;
7. contradictions or constraints lost across handoffs;
8. unsupported claims or actions;
9. end-to-end latency; and
10. maintenance surface, including duplicated rules and contracts.

Prefer high precision on negative and adjacent prompts before marginal recall gains. Accept a more modular design only when it produces a meaningful behavioral improvement without a disproportionate rise in multi-skill activation, handoff failures, or duplicated authority.

## Test sequence

1. Establish a baseline before revising the architecture.
2. Change one architectural or metadata variable at a time when practical.
3. Run deterministic structural checks and the targeted prompt set.
4. Forward-test judgment-heavy workflows in clean contexts without revealing expected answers or suspected defects.
5. Compare observed behavior with the predefined criteria.
6. Revise only where evidence identifies a problem.
7. Rerun affected cases and a suitable regression set.

Treat simulated or clean-context trials as evidence about behavior, not proof of live marketplace activation, production latency, or tool availability.
