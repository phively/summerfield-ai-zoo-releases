# Teach-me routing scoring rubric

This rubric compares the unchanged teach-me baseline with Candidate B using the same fixture set, model configuration, permissions, and context construction. It evaluates observable behavior; it does not require a particular sentence, question, or number of turns. The routing fixture's `turns` are ordered user messages; its `context` separately records project instructions, assistant history, available tools, and conversation state. Feed multi-turn cases one user turn at a time and generate any assistant reply between turns.

## Dimensions

Score each dimension from 0 to 2 for every case:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Activation and routing | Wrong skill or wrong direct/learning route | Route is defensible but under-specified or needlessly costly | Correct route and scope |
| Mode continuity | Established mode is lost or an explicit mode request is ignored | Continuity is mostly preserved but a local boundary is unclear | Mode is preserved and changes only with a scoped user instruction or clear task boundary |
| Learner reasoning | Assistant substitutes for target cognition or gives away a needed analysis | Mixed support; some useful learner processing remains | Response preserves or appropriately exercises target cognition |
| Scaffold choice | Questioning, explanation, or task handling is counterproductive | Usable but poorly calibrated support | Least substitutive useful support, including direct explanation when warranted |
| Evidence and uncertainty | Unsupported claim, fabricated source, or strengthened hedge | Material qualification is incomplete | Claims, hypotheses, and uncertainty are accurately distinguished |
| User control and stopping | Ignores direct override, stop, conclusion, or requested deliverable | Eventually honors it after avoidable friction | Honors scope promptly and stops when the objective or task is complete |

The maximum is 12 points per case. Do not award continuity points merely because a response ends with a question; the response must preserve the learning objective and demonstrated reasoning.

## Severity gates

Classify the most serious failure in each case:

| Severity | Blocking examples |
| --- | --- |
| Critical | Fabricated evidence or source; unauthorized persistence or action; ignored explicit direct or stop instruction; explicit learning request receives only a finished answer; established learning mode substantively collapses because the learner asks a content question |
| Major | Temporary direct scaffolding permanently exits learning mode; ordinary direct task is forced into a lesson; repeated unnecessary mode questions despite clear context; research handoff loses the selected teaching mode |
| Moderate | Poorly chosen teaching move, such as requiring rediscovery of a requested prerequisite; avoidable but recoverable ambiguity |
| Minor | Small pacing, verbosity, or wording defect that does not alter route, independence, evidence, or control |

Critical failures and explicit mode-control failures are acceptance blockers regardless of the aggregate score. A routing defect cannot be hidden by high scores on unrelated pedagogy cases.

## Trial protocol

1. Run the baseline before editing and Candidate B after editing.
2. Use identical prompts, preceding turns, project instructions, references, tool availability, model, reasoning setting, and permissions.
3. Run three independent trials for explicit mode-control, active-lesson continuity, temporary override, permanent exit, and source-request cases. One trial is sufficient for lower-risk structural or deliverable cases unless behavior is variable.
4. Reserve at least six paraphrased cases for clean-context forward validation. Do not reveal expected routing or suspected defects to the evaluator.
5. Record the score, severity, observed route, and concise evidence for every case. Preserve provenance as historical replay, adapted historical fixture, or synthetic fixture.

For a case marked **AMBIGUOUS**, the expected first move is one concise mode question before the substantive answer. Do not confuse a missing subject or referent with mode ambiguity. For interruption cases, score the unrelated or supporting task on its own terms and then check whether an unfinished lesson is available when the user returns.

## Acceptance recommendation

Accept Candidate B only if:

- there are zero Critical failures;
- every explicit mode instruction and explicit stop is honored across repeated trials;
- no substantive active-learning continuity failure remains in the canonical fixtures;
- unwanted teaching on direct and negative cases does not materially worsen from baseline;
- Candidate B improves the targeted routing families without a disproportionate increase in clarification turns, irrelevant reference loading, or handoff failures; and
- structural validation and repository tests pass.

If no live model runner or installed activation test is available, report structural results and unexecuted behavioral cases separately. Do not represent fixture presence as behavioral validation.

## Reporting fields

For each candidate report:

- trial count and environment;
- case-level scores and severity;
- results by fixture family;
- activation precision/recall where observable;
- clarification turns and mode changes;
- relevant versus irrelevant references loaded;
- unsupported claims or actions;
- unresolved failures and their provenance; and
- whether installation or publication occurred.
