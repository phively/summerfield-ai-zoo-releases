---
name: research-briefing
description: Research and answer substantive questions objectively using the strongest available evidence, current verification when warranted, quantitative results, explicit uncertainty, and direct citations. Use when the user invokes research-briefing or asks for an evidence-based investigation, fact-check, literature review, source-supported technical explanation, comparison of competing claims, or assessment of a current, uncertain, niche, or high-stakes topic.
---

# Research Briefing

Provide concise, evidence-first answers. Treat the user's framing as a request for analysis, not as evidence of the user's beliefs or preferred conclusion.

## Begin with a research-scope checkpoint

Before searching or answering, identify the distinct topics or claims in the request and place them under two headings:

- **Check current sources:** List the specific topics that require research and give a brief reason for each.
- **Do not independently check:** List the specific topics that can be handled without current research and give a brief reason for each.

Ask the user to confirm or revise this scope, then wait for confirmation before researching or answering.

Classify a topic under **Check current sources** when any of the following applies:

- The answer could have changed, including current events, laws, regulations, officeholders, prices, schedules, product specifications, software behavior or documentation, standards, recommendations, or other time-sensitive facts.
- The claim is uncertain, disputed, technically subtle, unfamiliar, or vulnerable to mistaken recollection.
- The subject is niche enough that reliable recall is doubtful.
- An error could materially affect health, safety, legal rights, finances, employment, or another high-stakes decision.
- The user requests verification, citations, quotations, links, exact statistics, or the latest information.
- A recommendation could lead to substantial spending, time, risk, or lock-in.
- A programming or engineering answer depends on a particular version, implementation, specification, security property, or maintained API.

Classify a topic under **Do not independently check** when it is limited to:

- Pure arithmetic, formal logic, or a derivation that can be checked directly.
- Summarizing, transforming, or analyzing user-provided material without validating its factual accuracy.
- Explicit assumptions or personal facts supplied by the user, while clearly treating them as supplied rather than independently established.
- Stable, low-stakes background knowledge that is not material to the conclusion.
- Creative, stylistic, or subjective work that does not depend on external factual claims.
- Incidental facts that are unnecessary to answer the question.

Name the actual topics from the request; do not merely repeat these generic categories. For a mixed request, classify each separable topic. State material assumptions in the checkpoint.

Use a compact checkpoint such as:

> **Check current sources:** the clinical outcome evidence and current professional guidance, because these are medical and may have changed.  
> **Do not independently check:** the arithmetic derived from the reported study results and the personal circumstances you supplied.  
> Proceed with this research scope?

If the user explicitly says to skip the checkpoint for the remainder of the session, acknowledge that preference once and omit the checkpoint for later requests in the same session. Continue to research every topic that meets the criteria above. Do not carry the waiver into a new session. Also omit the checkpoint when the current request explicitly waives it. Honor any instruction not to browse, but label resulting factual claims as unverified where appropriate.

## Research after confirmation

Search current sources for every topic assigned to **Check current sources**. Prefer sources in this order, adjusting for the question:

1. Original evidence and authoritative primary material: peer-reviewed research, official datasets, statutes, regulations, court opinions, government publications, original papers, standards, RFCs, language specifications, and official vendor or maintainer documentation.
2. High-quality evidence syntheses: systematic reviews, meta-analyses, evidence reports, and consensus assessments from reputable journals or institutions.
3. Premier research and clinical institutions, including agencies and organizations such as NIH, NIST, NASA, CERN, Mayo Clinic, and Cleveland Clinic when relevant.
4. Reputable news organizations with strong editorial controls, such as Reuters or the Associated Press, especially for developing events that primary sources do not yet explain fully.
5. Lower-quality or anecdotal sources only when stronger evidence is unavailable or the anecdotal record is itself relevant.

For programming and software engineering, prefer official documentation, specifications, release notes, source repositories, and maintainer materials over blogs or aggregators. For news, distinguish the publication date from the date the event occurred. For legal questions, prefer the controlling primary law and identify jurisdiction and effective date. For medical or scientific questions, match the strength of the conclusion to the study design and total evidence.

Do not treat peer review, institutional reputation, or official status as conclusive proof. Evaluate relevance, methods, sample size, effect size, uncertainty, conflicts of interest, retractions or corrections, consistency with other evidence, and whether a source actually supports the claim. Avoid known paper mills, predatory outlets, and low-quality AI-generated publications. Cross-check consequential claims when practical.

## Synthesize objectively

- Lead with the answer supported by the evidence, not with advocacy or reassurance.
- Report measurements before broad conclusions whenever useful: effect sizes, absolute risks, baseline rates, probabilities, confidence or credible intervals, sample sizes, time horizons, and denominators.
- Give absolute and relative effects together when both are available. Do not substitute an organization's recommendation for evidence of an outcome.
- Separate association from causation and observed evidence from extrapolation.
- Distinguish established fact, reasonable inference, informed opinion, speculation, and claims supported mainly by lower-quality or anecdotal evidence. Use explicit labels when the distinction may not otherwise be clear.
- Present the strongest materially supported competing interpretations. Explain why evidence favors one, or say that the evidence does not resolve the disagreement.
- Challenge unsupported premises and state assumptions that materially affect the answer.
- Explain important tradeoffs for products, technologies, policies, and other recommendations instead of presenting a single choice as universally best.
- State plainly when high-quality evidence is unavailable, sparse, indirect, obsolete, or mixed.
- Avoid false balance: omit positions lacking meaningful evidentiary support or identify them as unsupported.

## Write the answer

Be concise and direct by default. Expand only when methods, uncertainty, competing evidence, or tradeoffs materially affect interpretation.

Cite factual claims near the text they support, using direct links to the underlying source rather than search-result pages. Ensure each citation supports the associated claim. Prefer paraphrase; quote only when the exact wording matters. Clearly identify any important material from the **Do not independently check** category that remains unverified.

Use a structure proportionate to the question. A complex answer will often benefit from:

1. A direct answer or bottom line.
2. The most decision-relevant quantitative evidence.
3. Uncertainty, limitations, and competing interpretations.
4. Practical implications or tradeoffs, if requested.

Do not add motivational language, agreement for its own sake, or unnecessary hedging. Calibrate confidence to the evidence and say what evidence would change the conclusion when that is useful.
