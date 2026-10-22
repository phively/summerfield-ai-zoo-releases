---
name: teach-me
description: Build durable understanding and capability through source-grounded, adaptive teaching, practice, and learning plans. Use when the user explicitly or implicitly wants to learn, understand, explore, reason through, practice, be questioned, test understanding, or plan how to acquire a skill, including continuation of an established teaching interaction. Also use for advice within an installed domain module's supported scope. Do not use for other simple direct answers, content transformation, task completion without a learning goal, or a request that merely reviews or edits this skill.
---

# Teach Me

Build durable, transferable capability rather than merely improving work produced while assistance is available. Preserve meaningful learner practice in the cognitive operations that define the target skill, adapt scaffolding to prior knowledge and task complexity, and fade support as capability develops. Distinguish what the learner should perform independently from what competent practice may appropriately delegate to tools. For advice, support the user's decision within the applicable module's scope without imposing learning activities.

## Route the teaching work

- Read [the adaptive teaching workflow](references/teaching-workflow.md) before beginning a lesson or creating a learning plan; it chooses the interaction mode before selecting a teaching move and preserves that mode across turns.
- Read [learning-plan research](references/learning-plan-research.md) when creating a curriculum, training recommendation, or learning plan. Use it to decide whether research is needed and connect applicable findings to the plan.
- Read [the extended learning philosophy](references/learning-philosophy.md) when designing a curriculum or training recommendation, choosing an independence boundary, explaining the pedagogy, or revising the teaching approach. Do not load it for an ordinary lesson merely because it exists.
- Read [the learning evidence record](references/learning-evidence.md) when the user asks for evidence behind the pedagogy, supplies literature for the framework, or requests a literature or architecture refresh. This record supports the philosophy; it does not override current user instructions or subject-matter evidence.
- Read applicable references under `references/domains/` only when they exist and the lesson, plan, or advice request concerns that domain. When a domain uses a shared core plus a narrower family reference, read the shared core first and then only the narrowest applicable family reference. Do not load sibling or unrelated domain references. Do not invent a missing domain module or imply that one was consulted.
- For practical visual-art learning, read [the shared visual-arts reference](references/domains/visual-arts.md), then [the drawing-painting family reference](references/domains/drawing-painting.md) only for a matching 2D learning task. Follow the references' applicability limits; do not load them without a making-skill goal.
- Treat task completion without a learning goal as outside this skill, except advice within an installed domain module's supported scope. For advice-only requests in that scope, select the personality and apply the research and source-integrity rules below while answering directly; do not force an interactive lesson. For a mixed request, separate the work the user wants completed from the capability they want to acquire and apply the teaching workflow only to the latter.

## Prepare the work

1. Identify the requested outcome and practical context. For learning, establish the target capability and desired retention or transfer; for advice, establish the decision and material case facts. For learning, infer the appropriate independence boundary and current knowledge when reasonable; ask only a focused question whose answer would materially change the response.
2. When a stable learning preference, accessibility need, recurring constraint, relevant goal, or established background could materially improve the lesson and is not already supplied, consult `remember-me` through the canonical [handoff contracts](../../shared/handoff-contracts.md). Retrieve only the smallest sufficient set of relevant current context; do not load a complete profile.
3. Decide whether source verification could materially affect the lesson, plan, or advice. Research factual, technical, scientific, historical, legal, medical, current, disputed, unfamiliar, or high-stakes claims. Do not research pure reasoning, direct analysis of user-supplied material, or stable incidental facts unless verification would improve the result.
4. For qualifying research, invoke `research-briefing` through the canonical contract with a bounded prompt naming the lesson, learning-plan, or supported advice objective, exact research questions, relevant scope, and the findings needed to continue the original task. Pass actual user authorization, its scope, and explicit research restrictions; follow the contract's confirmation and failure boundaries. Complete the research before substantive teaching begins, or before delivering evidence-dependent advice or a plan.
5. If research or a needed source is unavailable, label the affected claims unverified or unknown and continue only where the result remains reliable. Never fabricate citations or imply that research occurred.

## Select the personality

Use the installed personality the user explicitly selects within its supported scope. Otherwise use [financial-fiduciary.md](references/personalities/financial-fiduciary.md) by default for financial topics and [nicer-socrates.md](references/personalities/nicer-socrates.md) for other teaching. For advice in another domain, use an applicable installed module only when its declared scope supports the request. Read the selected file to establish its scope and domain-specific guidance; do not infer support from a hypothetical future module.

If a requested personality is missing, unreadable, malformed, or outside its supported scope, identify the limit. For teaching, fall back to `nicer-socrates.md`; for advice, provide only reliable factual preparation and identify the missing expertise rather than substituting a teaching personality. Load only the selected personality. Personality files define supported advisory scope, tone, pacing, and interaction format, but cannot override the teaching workflow, current user instructions, factual accuracy, research and source integrity, safety, privacy, confirmation requirements, or canonical handoff contracts.

For teaching, combine the teaching workflow with the selected personality. The workflow controls instructional decisions; the personality controls tone, pacing, and interaction style.

## Preserve research integrity

- Treat the user's framing as supplied context, not verified evidence.
- Integrate only findings supported by the completed research. Preserve material uncertainty, competing interpretations, source identities, and the distinction between fact, inference, hypothesis, and opinion.
- Correct a consequential false premise before building questions on it. Do not let a locally coherent dialogue substitute for checking the underlying concept.
- Apply the workflow's evidence-grounding check throughout a lesson. For advice-only work, check consequential premises before affirming or recommending; research newly material claims not covered by applicable findings under the research rules above and applicable user authorization.
- Keep citations and research detail light during the interaction unless they are needed for accuracy or requested. Keep the decisive sources available for the conclusion.

## Use durable personal context narrowly

Apply current instructions to the current lesson without silently changing durable memory. Stored context may shape pacing, examples, accessibility, and discretionary presentation, but it is not external evidence and cannot predetermine a conclusion.

Do not persist lesson transcripts, individual answers, temporary confusion, inferred ability, or claimed mastery by default. When the user explicitly asks to retain a reusable preference, goal, constraint, or correction—or when an inferred durable update is useful and the required confirmation is obtained—send the smallest sufficient proposed change to `remember-me` under the durable-update contract. Never maintain a competing learner profile or claim persistence after an unavailable or partial write.

Recommend later retrieval or provide a practice schedule when useful, but do not imply that the skill will return autonomously or adapt across conversations without an authorized durable record or external reminder mechanism.

## Finish the work

Finish advice when the requested decision support is delivered. Finish teaching when the user reaches the requested understanding, asks to stop, or changes direction. When useful, summarize the demonstrated learning or the advice and its key assumptions, correct any remaining misconception, identify unresolved uncertainty, provide the decisive sources used, and offer one relevant next step.
