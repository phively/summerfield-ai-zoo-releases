---
name: prepare-interview
description: Prepare a candidate for a specific interview by mapping supported evidence and stories to inferred question families, stage-appropriate demonstrations, risks, and practice. Use for recruiter screens, behavioral, hiring-manager, executive, panel, later-round, or strategy/case-style preparation; do not use for employer due diligence as the primary task or resume rewriting.
---

# Prepare Interview

Help the candidate communicate, demonstrate, explain, and practice what matters for an interview without inventing interview content or candidate evidence.

## Evidence and ownership

- Read the canonical [shared records and handoff contracts](../../shared/handoff-contracts.md) before coordinating with another Career Coach skill.
- `evaluate-opportunity` owns opportunity records, captured postings, fit analysis, interview due diligence, and what the candidate needs to learn about the employer, role, manager, team, or opportunity. `prepare-interview` owns candidate preparation: what the candidate needs to communicate, demonstrate, explain, or practice.
- Treat the captured posting and current opportunity record as source-specific context, not proof of candidate experience. Retrieve relevant resume and supporting evidence separately, preserving source identity and evidence class.
- Do not create `interview-prep.md`, an interview history, a story-bank record, or any other persistent interview layer. Do not persist speculative likely questions as facts. Request bounded opportunity-record updates through `evaluate-opportunity` when authorized and needed.
- Require explicit user confirmation before treating an inferred interview fact, unsupported candidate claim, or consequential opportunity-state change as current.

## Workflow

1. Resolve the opportunity identity, interview stage, date or timing, format, known interviewers, and requested preparation scope. If the opportunity is not identifiable, preserve the ambiguity and ask only for the missing detail that changes the work.
2. Retrieve the canonical captured posting when available, then the relevant current opportunity-fit analysis and current role-specific unknowns. Use the captured posting before the live source when clarifying role language.
3. Retrieve candidate evidence needed to support answers, such as a resume, project summaries, reviews, promotion materials, or other user-provided sources. Never treat career-direction or opportunity conclusions as evidence of experience, scope, ownership, outcomes, metrics, or credentials.
4. Identify likely question families and stage-appropriate demonstrations from the available role and stage context. Label inferred families and possible questions as inferred; distinguish them from questions actually supplied or previously asked.
5. Map supported evidence and reusable stories to question families. Use STAR as one structure for behavioral answers, not as the whole preparation method. Mark missing evidence, weak coverage, unsupported claims, and material risks for confirmation or practice.
6. Include relevant due-diligence questions from `evaluate-opportunity` as questions for the candidate to ask or investigate; do not turn role-specific unknowns into candidate-preparation facts.
7. Produce preparation proportional to the request: a concise sheet, evidence/story map, answer outlines, opening narrative, question plan, practice set, or stage-specific strategy. Keep ready-to-use wording separate from confirmation-required content.
8. Invoke `teach-me` only when the user has a genuine learning or practice objective, such as rehearsal, STAR practice, executive communication practice, or retrieval/transfer exercises. Do not invoke it merely to list questions or generate a prep sheet. Continue locally if it is unavailable and do not imply the handoff occurred.

## Supporting capabilities

- When available, invoke `research-briefing` only when current external facts materially affect employer, role, compensation, industry, geography, or interview-process claims. If it is unavailable, label affected claims unverified or unknown. Keep researched facts separate from opportunity records and Career Coach inferences.
- When available, use `remember-me` only for narrow stable personal context not owned by Career Coach that materially affects preparation. If it is unavailable, continue with neutral defaults.
- Do not invoke `update-resume` merely because a resume is available. Invoke it only when resume work is a distinct requested outcome.

## Output

Distinguish known interview content, inferred question families, candidate-supported evidence, confirmation-needed claims, due-diligence questions, practice priorities, and unresolved unknowns. Do not persist preparation artifacts unless a separate authorized owner and workflow explicitly applies.
