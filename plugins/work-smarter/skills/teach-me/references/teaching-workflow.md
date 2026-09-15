# Adaptive teaching workflow

Use this file as the operational authority for lessons and learning plans. The selected personality controls delivery style, not instructional decisions.

## Choose the interaction mode

Choose the interaction mode before selecting a teaching move. Treat the mode as current conversational context, not as durable learner state. Subject to higher-priority instructions, apply these rules in order:

1. Honor an explicit current user instruction for its stated scope. Requests such as “answer this directly,” “just tell me,” “teach me,” “help me understand,” “let’s explore,” “quiz me,” or “work through this with me” establish the requested mode. If the same request asks for both learning and a direct answer, answer the specified sub-scope directly while preserving the surrounding mode.
2. An explicit request to use teach-me for learning establishes **LEARNING** mode unless the same request asks for direct delivery. Mentioning, reviewing, or editing teach-me does not itself establish a learning goal.
3. Once **LEARNING** mode is established, preserve it across ordinary follow-up questions, hypotheses, requests for clarification, and requests such as “why?”, “what about X?”, “isn’t that Y?”, or “can you explain that?” A content question does not by itself end the lesson.
4. Within **LEARNING** mode, provide a direct fact, explanation, example, correction, or supporting task when it is appropriate scaffolding or the user requests it for a local scope. That teaching move does not end **LEARNING** mode; continue the adaptive workflow when the surrounding learning objective remains active.
5. When no current explicit instruction or established conversational mode settles the choice, apply a relevant project learning default. Without one, explicit learning or exploration intent establishes **LEARNING** mode; ordinary informational, analytical, evaluative, and task-completion requests use **DIRECT** mode.
6. If the initial intent remains materially ambiguous and the choice would change the response, ask one concise mode question such as “Would you like the answer directly, or would you like to work through it?” Do not ask that question when explicit instructions, an established mode, or a relevant project default settles the choice. If the missing information is the subject or referent rather than the interaction mode, ask only for that information.
7. A direct override applies only for the turn or scope stated by the user unless they explicitly say to remain direct. An explicit request to stop or switch modes exits **LEARNING** mode. Complete a temporary supporting task directly and retain an unfinished lesson's context; handle an unrelated new task on its own terms and restore the lesson only if the user returns to it without an explicit mode change. A learning-plan request is a deliverable and does not require an interactive lesson when sufficient information is available.

## Define the target

Identify the capability, practical context, desired retention and transfer, relevant prior knowledge, and appropriate independence boundary. Ask only when a missing answer would materially change the approach; otherwise infer a limited answer and state it when consequential.

Separate:

- **target cognition:** perception, representation, generation, reasoning, judgment, or checking the learner is trying to acquire;
- **supporting cognition:** work that may be delegated without displacing the target;
- **independent capability:** what the learner should understand or perform without assistance; and
- **tool-augmented capability:** what competent practice may appropriately accomplish with tools.

For task-completion requests without a learning goal, leave this workflow. For mixed requests, apply it only to the learning component.

## Select an acquisition strategy

Choose from observed knowledge and task complexity rather than applying one teaching method universally.

Use an **example-first** progression when the learner lacks a usable schema: worked example, active explanation or prediction within it, partial example, completion, supported performance, then fading.

Use a **generation-first** progression when the learner can attempt productively: retrieve or attempt, make a provisional commitment, receive feedback and comparison, revise, then apply independently.

Commitment may be small. Do not require a complete unaided solution when prediction, classification, explanation of one step, or identification of an error exercises the target operation.

## Run the adaptive loop

For each meaningful exchange:

1. **Elicit:** Ask the learner to retrieve, predict, explain, discriminate, complete, judge, or attempt; or present an example and elicit active processing within it.
2. **Diagnose:** Determine correctness, reasoning, omissions, misconceptions, confidence when useful, and whether the difficulty remains productive. A chain of reasonable answers can still drift from the underlying concept.
3. **Scaffold:** Provide the least substitutive assistance sufficient for useful progress. Depending on need, use a cue, targeted question, error location, hint, partial example, principle, worked example, direct explanation, or solution. This is a menu, not a mandatory sequence.
4. **Correct:** Connect the learner's reasoning to evidence, principles, and outcomes. Prefer ground truth over agreement with the assistant; preserve legitimate alternatives and uncertainty.
5. **Reconstruct:** After consequential feedback, ask for a restatement, corrected step, new example, near-transfer application, or explanation of the earlier error when that would materially strengthen learning. Do not make the learner rediscover an explanation they just requested unless practice is itself the goal.
6. **Fade or restore:** Reduce support after reliable success. Restore enough support when fading produces guessing, repeated unrefined errors, overload, or inability to use feedback.
7. **Vary and transfer:** When useful, add contrasts, confusable alternatives, erroneous examples, boundary cases, changed contexts, or novel applications. Interleave only when discrimination or strategy selection is part of the target.
8. **Retrieve later:** For material intended to persist, recommend or schedule later retrieval with cues removed, followed by checking and correction. Do not imply autonomous follow-up or cross-session adaptation without an available mechanism and authorized state.

Ask a question only when its answer could reveal a misconception, distinguish important interpretations, connect ideas, surface a prerequisite, exercise target cognition, test transfer, or otherwise materially increase understanding. Do not question for its own sake or force the lesson into a quiz.

## Protect independent search and judgment

When judgment or critique is a target, often let the learner construct an initial interpretation before showing the assistant's. Ask the learner to identify possible errors, alternatives, tests, or counterarguments before receiving a review when that search is itself part of the capability.

Teach both forms of automation failure:

- **commission:** accepting faulty advice; and
- **omission:** failing to find a problem because the assistant did not flag it.

Do not present an AI review as exhaustive. When useful, have the learner challenge a model claim, inspect evidence, compare solutions, or diagnose a deliberately faulty example.

## Use difficulty and errors conditionally

Productive difficulty exercises relevant processing at a manageable level. Random guessing, repeated identical errors, missing prerequisites, irrelevant workload, or inability to use feedback indicate that the task needs simplification or stronger scaffolding.

Treat interpretable errors as material for diagnosis, contrast, correction, and renewed application. Error production is not itself a goal.

## Build learning plans

For a curriculum or training recommendation:

1. read `learning-philosophy.md` and any applicable domain reference;
2. define observable target capabilities and independence boundaries;
3. sequence prerequisites, examples, supported practice, fading, independent practice, and transfer;
4. include retrieval and revisiting appropriate to the desired retention period;
5. define evidence of progress without creating unsupported mastery claims; and
6. identify which activities use tools and which assess independent performance.

Provide a schedule or reminder plan when useful, but distinguish a recommendation from a reminder that has actually been created.

## Conclude from demonstrated capability

Do not claim mastery from agreement, fluency, recognition, satisfaction, assisted output, visible cues, or a single correct answer. Stronger evidence includes independent reconstruction, delayed retrieval, discrimination among alternatives, transfer to a changed case, and self-detection of errors.

Conclude when the requested learning objective is met, the user asks to stop, or the interaction changes direction. State remaining uncertainty or misconceptions plainly and preserve learner control throughout.
