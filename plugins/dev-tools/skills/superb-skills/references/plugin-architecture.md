# Plugin architecture

Use this reference for multi-skill plugins, manifests, shared contracts, cross-skill state, packaging, and publication readiness.

## Architecture workflow

1. Inventory recognizable user goals. Give each skill a focused workflow boundary with distinct triggers, expected inputs, outputs, success criteria, and failure behavior.
2. Do not create separate skills merely because the domain contains separate nouns. Split only when different workflows are likely to improve activation precision, reduce irrelevant instruction loading, use materially different tools or inputs, or require different success criteria.
3. Keep cross-cutting design rules in one coordinating skill or canonical plugin-level contract. Name the owner and replace duplicated rules in consuming skills with references; independently usable skills retain their own procedures and can reference a packaged shared contract. Do not preserve synchronized prose copies as a substitute for single ownership. Put task-specific detail in conditional references before creating additional skills.
4. Invoke `skill-creator` for each skill created or revised. Treat it as authoritative for current skill scaffolding, metadata, validation, installation, and packaging conventions.
5. Inspect current supported plugin conventions before adding or changing a manifest. Do not invent dependency fields, APIs, or capabilities.
6. Define every permitted handoff in one canonical contract. Specify the invoking and receiving skills, trigger, required input, expected output, authority and provenance, uncertainty, failure behavior, prohibited information, and confirmation boundary.
7. Pass the smallest sufficient set of relevant current context, source identities, evidence classifications, and unresolved issues. Expand the handoff when a bounded summary would omit consequential information; do not pass complete histories or create competing copies of authoritative records by default.
8. Keep each skill independently useful unless the user goal inherently requires coordination. Avoid circular or unconditional handoffs.

## Coordination and delivery

- Keep the coordinator responsible for routing, decomposition, authority, user-facing decisions, and evidence synthesis. Delegate only bounded work with explicit inputs, outputs, limits, and confirmation boundaries.
- Let scripts own repeated deterministic transformations, validation, and provenance capture. Let skills own judgment, clarification, and handoffs; do not duplicate script logic in instructions.
- Decompose only when separate outputs, tools, constraints, or success criteria justify it. Keep simple target work simple, and require evidence for each consequential design decision.
- For raster icons, require legibility at 32×32 and dimensions no larger than 128×128. Dimension checks are structural evidence; include visual review when legibility matters. Preserve suitable SVG assets unless visual review identifies a defect.
- Before releasing a target package, check its version decision, supported manifest fields, required assets, and any applicable mirrored metadata under that target repository's conventions. Do not hard-code this repository's mirror names into general guidance.

## Decomposition decision

Compare a unified and split architecture using [evaluation.md](evaluation.md) when the performance effect is uncertain. Prefer a split only when tests show a meaningful improvement in activation, output quality, context use, or reliability that exceeds added routing and handoff failures.

In the written comparison plan, explicitly hold prompts, environment, model and reasoning configuration, permissions, dependency availability, and scoring rules constant across alternatives. Measure behavior, clarity, maintenance, and routing/handoff failures, including unavailable dependencies. State that an unexecuted comparison is provisional.

Do not use file length alone as the decision rule. A concise unified skill may outperform several overlapping skills; a longer skill may still benefit from conditional references rather than new activation boundaries.

## Completion checks

- Every skill has a precise, non-conflicting description.
- Shared rules have one authority.
- All references and assets resolve.
- Handoffs preserve authority, uncertainty, and confirmation requirements.
- The manifest uses supported fields and paths.
- Direct, indirect, ambiguous, mixed, and negative routes are evaluated.
- Structural validators and affected regressions pass.
- Unverified runtime, marketplace, or publication behavior is reported rather than inferred.
