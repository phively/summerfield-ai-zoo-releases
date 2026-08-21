# Working memory and historical records

Use this reference only after the working-memory gate in `SKILL.md` passes.

## Contents

- [Record model](#record-model)
- [Authority and retrieval](#authority-and-retrieval)
- [Pointers](#pointers)
- [Coherent updates](#coherent-updates)
- [Lifecycle rules](#lifecycle-rules)
- [Lifecycle review triggers](#lifecycle-review-triggers)
- [Loss-controlled audits](#loss-controlled-audits)
- [Progressive disclosure](#progressive-disclosure)
- [Identity and ownership](#identity-and-ownership)
- [Coherence checks](#coherence-checks)
- [Design objective](#design-objective)

## Record model

Use two complementary record types only when active state and meaningful history both exist.

### Working briefing

Make the working briefing the default, authoritative source for routine decisions and handoffs. Keep it concise, structured, and understandable without the archive. Include the active goals, decisions, constraints, preferences, requirements, hypotheses, unresolved issues, and other frequently reused state needed for execution.

### Historical record

Use a historical record for superseded criteria, archived decisions, prior versions, detailed provenance, rejected alternatives, and examples that retain explanatory, evidentiary, audit, or restoration value. Do not load it by default or let it silently override current state. It is authoritative about what was recorded previously, not what is current.

Use one file while the record is small, predominantly current, and free of meaningful historical complexity. Split it only when separation materially improves signal density, retrieval, maintenance, auditability, or reliability.

## Authority and retrieval

- Designate exactly one source as authoritative for current state.
- Use the working briefing when it conflicts with history unless the user corrects it or requests historical reconstruction.
- Avoid uncontrolled duplicate formulations of an active fact or rule.
- Distinguish current facts, user-stated preferences, evidence-supported patterns, working hypotheses, unresolved issues, and superseded information.
- Preserve exact active thresholds, formulas, eligibility rules, safety constraints, and other consequential details.

Treat reliable recall as successful retrieval of the complete relevant current state for the task, including consequential detail and uncertainty. It does not require loading unrelated topics or history. Start with the smallest likely-sufficient current section, then expand retrieval when an index, summary, or initial section is incomplete, stale, ambiguous, conflicting, or points to required detail.

Read the working briefing first. Retrieve the smallest relevant historical or supporting section only when:

- the briefing points to a historical entry;
- the user asks about an earlier decision, prior reasoning, or change over time;
- provenance is needed to resolve ambiguity or contradiction;
- an archived subject becomes relevant again;
- a superseded rule may need restoration or reconsideration; or
- required evidence or detail was intentionally omitted from the briefing.

Do not load an archive merely because it exists. For large records, support targeted retrieval with descriptive headings, stable identifiers, a table of contents, metadata, or documented search patterns.

## Pointers

- Give material historical entries stable identifiers such as `H-YYYY-MM-DD-NN`.
- Include the canonical file identity, entry identifier, subject, and condition for consulting it.
- Do not use line numbers or a filename alone as durable pointers.
- Keep references shallow and link core instructions directly to each potentially needed resource.
- Resolve pointers to canonical records; never create skill-local copies or parallel authorities.
- Add a pointer only when history could materially affect later interpretation.

Example:

> For the rationale and superseded alternatives behind the current compensation rule, consult `Career_Direction_History.md`, entry `H-2026-08-12-03`, only when reviewing or changing that rule.

## Coherent updates

Treat a material change as one transaction:

1. Confirm the revised current state.
2. Preserve the previous material state in history only when it retains explanatory, evidentiary, audit, or restoration value.
3. Update the working briefing with the authoritative formulation.
4. Mark the historical entry `superseded`, `archived`, `rejected`, or `restored`.
5. Record effective dates, provenance, and replacement identifiers when useful.
6. Add or revise pointers only when later access to the history would help.
7. Verify that no contradictory active formulation remains elsewhere.

Do not archive trivial wording changes, transient task state, or routine process events unless they explain a consequential decision. Do not allow append-only logging to turn the archive into a transcript.

Update only affected sections and justified pointers when that preserves a coherent, complete current authority. If a narrow edit would omit a dependent constraint, leave stale summaries, or create a contradiction, widen the transaction enough to protect recall before minimizing update tokens.

## Lifecycle rules

- **Promote** archived information only when it becomes active and decision-relevant again.
- **Demote** information when it is no longer needed routinely but retains historical value.
- **Remove** information when it is incorrect, valueless duplication, transient, or no longer useful even for provenance.
- Retain infrequently discussed stable requirements when they remain decision-relevant.
- Base placement on expected reuse and decision relevance, not recency or file size alone.

## Lifecycle review triggers

Every persistent-memory design must define at least one measurable elapsed-time, byte-size, token-estimate, or material-change-count threshold. Check it at an inexpensive workflow boundary such as an authorized write, explicit audit, or consequential use; do not repeatedly load full records merely to test the trigger. A threshold makes an audit due. It never decides the lifecycle action by itself.

When domain evidence supplies no better threshold, use this conservative default design heuristic and label it as a heuristic rather than a research finding:

- review when the routing or current-state file exceeds 8 KiB, any detailed current file exceeds 16 KiB, or 180 days have elapsed since its recorded audit;
- audit before every compaction, split, merge, archive migration, or authority transfer regardless of size or age; and
- if a due audit is not authorized or cannot run safely, report it as due and continue read-only with explicit uncertainty rather than silently rewriting memory.

Choose the resulting action from retrieval quality, decision relevance, provenance needs, ownership, and observed failure modes. A stable oversized file may remain intact; a smaller file may need repair when it is contradictory or hard to retrieve accurately.

## Loss-controlled audits

Treat a maintenance rewrite as a staged transaction:

1. Resolve the canonical current authority and all dependent indexes, topic files, histories, and pointers.
2. Preserve a recoverable pre-audit snapshot and record complete file identities, byte sizes, and SHA-256 hashes.
3. Inventory semantic items before drafting: active facts, exact constraints, numerical rules, provenance, stable identifiers, required pointers, meaningful history, uncertainty, and ownership metadata. Classify disposable formatting, transient text, and valueless duplication separately.
4. Build the proposed state outside the canonical location. Compare the complete before and after file sets and create a bidirectional ledger mapping every pre-audit item to retained, moved, reworded, updated, archived, or justified removal, and every post-audit item to its origin or an authorized addition.
5. Preserve exact constraints, numerical values, provenance, and stable identifiers byte-for-byte during compaction or splitting. Preserve pointer targets and entry identifiers; revise a pointer path only in the staged ledger with justification and verified resolution. Require explicit authorization for a factual update and an explicit semantic-equivalence review for rewording other protected information. Never classify protected information as disposable.
6. Use `../../../scripts/validate_memory_audit.py` when the records are accessible as files. Treat a failed file inventory, hash, item mapping, semantic review, authority check, or pointer check as a failed audit.
7. Inspect the raw file diff in both directions, verify that current state remains understandable without history, and verify that history can reconstruct every retained prior state.
8. Replace the canonical state only after every check passes. Use a recoverable or atomic replacement when supported, verify the written hashes, and retain the snapshot until post-write verification succeeds. On any failure, leave the original authoritative state unchanged and report the failed check.

This process proves structural and declared semantic coverage; deterministic hashes and ledgers cannot independently prove that two differently worded statements mean the same thing. Preserve that limitation by requiring a recorded semantic review rather than claiming automated semantic certainty.

## Progressive disclosure

- Keep skill instructions focused on core workflow, authority, safeguards, and resource-selection logic.
- Put schemas, rubrics, examples, history, templates, and domain detail in purpose-specific references.
- State precisely when each reference must be read.
- Do not duplicate a rule across a skill body, working briefing, and archive.
- Use scripts for repeated deterministic transformations or validation.
- Pass downstream skills only relevant current context, evidence classifications, source identities, and unresolved issues—not the entire history.

## Identity and ownership

For each persistent record, define:

- canonical filename or resource identity;
- owning skill or workflow;
- current-state authority;
- permitted readers and writers;
- update conditions;
- archive relationship;
- conflict-resolution rule; and
- behavior when the record is missing, duplicated, ambiguous, or inaccessible.

Preserve an existing canonical file's identity and update it in place. Do not create a replacement or competing copy because access is inconvenient. Resolve the authoritative source before writing when multiple plausible records could change the result. If the authority is missing or inaccessible, do not imply persistence; provide a clearly labeled proposed update when useful.

## Coherence checks

After consequential updates and at suitable intervals, verify that:

- every active rule appears in the working briefing;
- superseded rules are not presented as current;
- no active rule has conflicting formulations;
- pointers resolve to intended entries;
- archived material has explicit status and dates;
- numerical rules and constraints remain exact;
- historical examples have not become unsupported current rules;
- downstream skills use the working briefing by default; and
- the briefing remains understandable without the archive.

## Design objective

Apply this strict priority order:

1. Preserve reliable recall of all information relevant to the task.
2. Minimize the tokens required to read and update that memory context.
3. Minimize the time required to retrieve it.

Never improve a lower-ranked objective by weakening a higher-ranked one. Keep the smallest complete set needed for routine decisions in the working briefing, use targeted sections and narrow coherent updates to reduce token use, and add stable retrieval aids to improve speed. Preserve only history with continuing explanatory, evidentiary, audit, or restoration value. Most tasks should use current state alone; exceptional tasks should recover relevant history without ambiguity or uncontrolled duplication.
