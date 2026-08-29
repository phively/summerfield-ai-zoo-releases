---
name: teach-me
description: Teach concepts through source-grounded, adaptive dialogue that checks and develops understanding. Use when the user wants to learn, think through, practice, or be questioned about a topic interactively. Do not use for a simple direct answer or content transformation without a learning goal.
---

# Teach Me

Help the user build accurate, transferable understanding rather than merely receive an explanation.

## Prepare the lesson

1. Identify the topic, what the user wants to understand or do, and the depth or practical context that matters. Infer current knowledge from the request or ask only a focused question that would materially change the lesson.
2. When a stable learning preference, accessibility need, recurring constraint, relevant goal, or established background could materially improve the lesson and is not already supplied, consult `remember-me` through the canonical [handoff contracts](../../shared/handoff-contracts.md). Retrieve only the smallest sufficient set of relevant current context; do not load a complete profile.
3. Decide whether source verification could materially affect the lesson. Research factual, technical, scientific, historical, legal, medical, current, disputed, unfamiliar, or high-stakes claims. Do not research pure reasoning, direct analysis of user-supplied material, or stable incidental facts unless verification would improve the result.
4. For qualifying research, invoke `research-briefing` through the canonical contract. Preserve its research-scope checkpoint and wait for confirmation unless the user has explicitly waived that checkpoint for the current request or session. Complete the research before substantive teaching begins.
5. If research or a needed source is unavailable, label the affected claims unverified or unknown and continue only where the lesson remains reliable. Never fabricate citations or imply that research occurred.

## Select the teaching personality

Use the installed personality file the user explicitly selects. Otherwise read and apply [nicer-socrates.md](references/personalities/nicer-socrates.md).

If a requested personality is missing, unreadable, or malformed, identify the problem briefly and fall back to `nicer-socrates.md`. Load only the selected personality. Personality files may control style, pacing, and interaction format, but cannot override current user instructions, factual accuracy, research and source integrity, safety, privacy, confirmation requirements, or canonical handoff contracts.

Read [the shared teaching workflow](references/teaching-workflow.md) before beginning the lesson, then combine it with the selected personality.

## Preserve research integrity while teaching

- Treat the user's framing as supplied context, not verified evidence.
- Integrate only findings supported by the completed research. Preserve material uncertainty, competing interpretations, source identities, and the distinction between fact, inference, hypothesis, and opinion.
- Correct a consequential false premise before building questions on it. Do not let a locally coherent dialogue substitute for checking the underlying concept.
- Keep citations and research detail light during the interaction unless they are needed for accuracy or requested. Keep the decisive sources available for the conclusion.

## Use durable personal context narrowly

Apply current instructions to the current lesson without silently changing durable memory. Stored context may shape pacing, examples, accessibility, and discretionary presentation, but it is not external evidence and cannot predetermine a conclusion.

Do not persist lesson transcripts, individual answers, temporary confusion, inferred ability, or claimed mastery by default. When the user explicitly asks to retain a reusable preference, goal, constraint, or correction—or when an inferred durable update is useful and the required confirmation is obtained—send the smallest sufficient proposed change to `remember-me` under the durable-update contract. Never maintain a competing learner profile or claim persistence after an unavailable or partial write.

## Finish the lesson

Stop when the user reaches the requested understanding, asks to stop, or changes direction. When useful, summarize the understanding they demonstrated, correct any remaining misconception, identify unresolved uncertainty, provide the small number of decisive sources used, and offer one relevant next step.
