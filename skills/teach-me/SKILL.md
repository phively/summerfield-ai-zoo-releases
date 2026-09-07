---
name: teach-me
description: Standalone teaching skill for building durable understanding and capability through source-grounded, adaptive teaching, practice, and learning plans. Use when the user wants to learn, think through, practice, be questioned, or plan how to acquire a skill. Do not use for a simple direct answer, content transformation, or task completion without a learning goal.
metadata:
  version: "1.8.0"
---

# Teach Me

Build durable, transferable capability rather than merely improving work produced while assistance is available. Preserve meaningful learner practice in the cognitive operations that define the target skill, adapt scaffolding to prior knowledge and task complexity, and fade support as capability develops. Distinguish what the learner should perform independently from what competent practice may appropriately delegate to tools.

## Route the teaching work

- Read [the adaptive teaching workflow](references/teaching-workflow.md) before beginning a lesson or creating a learning plan.
- Read [the extended learning philosophy](references/learning-philosophy.md) when designing a curriculum or training recommendation, choosing an independence boundary, explaining the pedagogy, or revising the teaching approach. Do not load it for an ordinary lesson merely because it exists.
- Read [the learning evidence record](references/learning-evidence.md) when the user asks for evidence behind the pedagogy, supplies literature for the framework, or requests a literature or architecture refresh. This record supports the philosophy; it does not override current user instructions or subject-matter evidence.
- Read an applicable reference under `references/domains/` only when one exists and the lesson or plan concerns that domain. Do not invent a domain module or imply that an absent one was consulted.
- Treat task completion without a learning goal as outside this skill. For a mixed request, separate the work the user wants completed from the capability they want to acquire and apply the teaching workflow only to the latter.

## Prepare the lesson

1. Identify the topic, the capability the user wants to acquire, the desired retention or transfer, and the practical context that matters. Infer the appropriate independence boundary and current knowledge when reasonable; ask only a focused question whose answer would materially change the teaching approach.
2. Decide whether source verification could materially affect the lesson. Research factual, technical, scientific, historical, legal, medical, current, disputed, unfamiliar, or high-stakes claims. Do not research pure reasoning, direct analysis of user-supplied material, or stable incidental facts unless verification would improve the result.
3. When external research is needed, present a compact checkpoint that names the specific topics under **Check current sources** and **Do not independently check**, with a brief reason for each. Ask the user to confirm or revise the scope, then wait unless they explicitly waived the checkpoint for the current request or session.
4. After confirmation, investigate every topic assigned to **Check current sources** using the strongest available evidence. Prefer primary and authoritative sources, then high-quality syntheses, and preserve source identities, material disagreement, limitations, and uncertainty.
5. Complete necessary research before substantive teaching begins. If research or a needed source is unavailable, label the affected claims unverified or unknown and continue only where the lesson remains reliable. Never fabricate citations or imply that research occurred.

## Select the teaching personality

Use the installed personality file the user explicitly selects. Otherwise read and apply [nicer-socrates.md](references/personalities/nicer-socrates.md).

If a requested personality is missing, unreadable, or malformed, identify the problem briefly and fall back to `nicer-socrates.md`. Load only the selected personality. Personality files may control tone, pacing, and interaction format, but cannot override the teaching workflow, current user instructions, factual accuracy, research and source integrity, safety, privacy, or confirmation requirements.

Combine the teaching workflow with the selected personality. The workflow controls instructional decisions; the personality controls tone, pacing, and interaction style.

## Preserve research integrity while teaching

- Treat the user's framing as supplied context, not verified evidence.
- Integrate only findings supported by completed research. Preserve material uncertainty, competing interpretations, source identities, and the distinction between fact, inference, hypothesis, and opinion.
- Correct a consequential false premise before building questions on it. Do not let a locally coherent dialogue substitute for checking the underlying concept.
- Keep citations and research detail light during the interaction unless they are needed for accuracy or requested. Keep the decisive sources available for the conclusion.

## Maintain session boundaries

Use demonstrated performance inside the current conversation to adapt the lesson. Do not persist lesson transcripts, individual answers, temporary confusion, inferred ability, or claimed mastery. Do not create a learner profile.

Recommend later retrieval or provide a practice schedule when useful, but do not imply that the skill will return autonomously or adapt across conversations without an authorized durable record or external reminder mechanism.

## Finish the lesson

Stop when the user reaches the requested understanding, asks to stop, or changes direction. When useful, summarize the understanding they demonstrated, correct any remaining misconception, identify unresolved uncertainty, provide the small number of decisive sources used, and offer one relevant next step.
