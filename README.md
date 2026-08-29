<!-- catalog:start -->
| Name | Type | Link | Description |
| --- | --- | --- | --- |
| meal-planner | plugin | [plugins/meal-planner](plugins/meal-planner) | Safe household meal planning with durable plan history, recipe ratings, preference memory, grocery consolidation, and cost estimation.<br><br>• [meal-planner](plugins/meal-planner/skills/meal-planner/SKILL.md) - Coordinate and preserve safe household meal plans<br>• [personal-chef](plugins/meal-planner/skills/personal-chef/SKILL.md) - Select recipes and maintain ratings and preferences<br>• [personal-shopper](plugins/meal-planner/skills/personal-shopper/SKILL.md) - Build store-prioritized grocery lists and costs |
| work-smarter | plugin | [plugins/work-smarter](plugins/work-smarter) | Evidence-grounded research and interactive teaching, reliable instruction design, and durable personal-context indexing with authoritative record routing.<br><br>• [remember-me](plugins/work-smarter/skills/remember-me/SKILL.md) - Maintain a durable personal context index<br>• [research-briefing](plugins/work-smarter/skills/research-briefing/SKILL.md) - Evidence-grounded research with citations<br>• [superb-skills](plugins/work-smarter/skills/superb-skills/SKILL.md) - Design and test reliable skills and plugins<br>• [teach-me](plugins/work-smarter/skills/teach-me/SKILL.md) - Learn concepts through adaptive dialogue |
| career-coach | plugin | [plugins/career-coach](plugins/career-coach) | Evidence-grounded career direction, opportunity fit and lifecycle tracking with durable records, and resume tailoring from verified evidence.<br><br>• [career-direction](plugins/career-coach/skills/career-direction/SKILL.md) - Clarify executive career direction<br>• [evaluate-opportunity](plugins/career-coach/skills/evaluate-opportunity/SKILL.md) - Assess and track two-way opportunity fit<br>• [update-resume](plugins/career-coach/skills/update-resume/SKILL.md) - Tailor resumes using verified evidence |
| research-briefing | skill | [skills/research-briefing](skills/research-briefing/SKILL.md) | Standalone research and briefing skill for answering substantive questions objectively using the strongest available evidence, current verification when warranted, quantitative results, explicit uncertainty, and direct citations. Use when the user invokes research-briefing or asks for an evidence-based investigation, fact-check, literature review, source-supported technical explanation, comparison of competing claims, or assessment of a current, uncertain, niche, or high-stakes topic. |
| teach-me | skill | [skills/teach-me](skills/teach-me/SKILL.md) | Standalone teaching skill for helping users learn, think through, and practice concepts through source-grounded, adaptive dialogue that checks and develops understanding. Do not use for a simple direct answer or content transformation without a learning goal. |
<!-- catalog:end -->

## v2.1.0

### New: Teach Me

Added `teach-me`, an interactive learning skill that helps users develop and test genuine understanding through adaptive dialogue.

- Researches source-sensitive topics before substantive teaching begins.
- Supports modular teaching personalities.
- Includes `nicer-socrates`, a supportive Socratic style focused on purposeful questions, concise feedback, and learner-generated connections.
- Challenges questionable premises and avoids reflexive or sycophantic agreement.
- Increases scaffolding or explains directly when questioning stops being productive.
- Is available within the Work Smarter plugin and as an independent standalone skill.
- Can optionally retrieve relevant learning preferences from `remember-me` in the Work Smarter plugin without persisting lesson transcripts or inferred ability.

### Work Smarter 1.5.0–1.6.0

- Added canonical handoffs between `teach-me`, `research-briefing`, and `remember-me`.
- Added stronger memory lifecycle and loss-controlled audit rules.
- Prioritized reliable recall before context-token reduction and retrieval speed.
- Improved canonical record identity using provider identifiers, immutable references, and permalinks.
- Required evidence for comparative language such as “best” or “unusual,” unless clearly presented as subjective judgment.
- Expanded research, memory, teaching, and routing evaluations.

### Packaging and quality

- Added `teach-me` to the public catalog.
- Mirrored the standalone teaching workflow, personality, metadata, and icons.
- Added standalone-isolation and synchronization checks.
- Expanded structural, behavioral, routing, handoff, and marketplace test coverage.
