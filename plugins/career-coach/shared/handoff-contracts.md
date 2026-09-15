# Shared records and handoff contracts

This file is the canonical authority, ownership, and coordination contract for the career-coach skills. Read it from the plugin-level path; do not copy it into a skill folder. Read [career-direction-records.md](career-direction-records.md) for career-direction record procedures, [opportunity-records.md](opportunity-records.md) for opportunity record procedures, and [record-audits.md](record-audits.md) only when a lifecycle trigger is due or structural maintenance is proposed.

## Capability responsibility model

Career Coach has five primary capabilities with distinct owners:

- `career-direction` owns reusable career goals, constraints, preferences, positioning, target roles, career hypotheses, and high-level development priorities. It answers what matters and why.
- `professional-development` owns the execution layer for capability gaps, development goals, credentials, courses and resources, sequencing, progress, completed evidence, and next actions. It answers what the user is doing about a career-direction priority.
- `evaluate-opportunity` owns bidirectional fit for a specific opportunity, pursuit decisions, role-specific risks and unknowns, compensation/location/travel considerations, employer and role due diligence, and opportunity records.
- `prepare-interview` owns candidate preparation: what the candidate needs to communicate, demonstrate, explain, or practice for an interview. It may use opportunity context but does not own opportunity records.
- `update-resume` owns evidence-grounded resume and profile tailoring and artifact production. It does not own interview preparation or establish candidate evidence from plans or intentions.

Keep these boundaries explicit:

- Career Direction owns the strategic reason for development; Professional Development owns detailed execution and progress.
- Evaluate Opportunity owns what the candidate needs to learn about the employer, role, manager, team, or opportunity; Prepare Interview owns what the candidate needs to communicate, demonstrate, explain, or practice.
- Update Resume may use current direction and development context to guide emphasis, but planned courses, certifications, capabilities, or experience are not completed candidate evidence.

Each cross-skill handoff must use a contract below. Do not invoke another capability merely because its subject matter is adjacent, and do not create skill-local copies of shared rules or canonical records.

## Shared source discovery

At the start of each skill workflow, search accessible library and project sources for:

- `career_direction_record.md` or a clearly equivalent working file containing the user's current reusable career direction;
- `career_direction_history.md` or a clearly equivalent historical companion, but do not read its contents by default; and
- when development context could materially affect the task, `professional-development.md` or a clearly equivalent current execution record; and
- `opportunities-current.md` or a clearly equivalent working file containing active opportunities and their current state;
- `opportunities-history.md` or a clearly equivalent historical companion, but do not read its contents by default; and
- an accessible Google Drive folder named `opportunity descriptions`, `job descriptions`, or a clearly equivalent name, containing canonical captured postings when available; otherwise canonical captured postings stored directly in the selected library location; and
- `career-coach-preferences.md` or a clearly equivalent file containing user-specific coaching, analysis, or output preferences.

Preserve exact source identities and update existing records in place. Resolve a canonical Markdown record by storage provider, immutable resource or file ID when available, canonical link or durable path, visible filename, selected library or folder identity, record role, and stable entry or heading when applicable. A filename, line number, organization name, or vague folder location alone is not a durable identity. Preserve the existing working record's identity wherever possible and introduce only one clearly named historical companion. Never create skill-local static copies or competing current records. If several plausible files or pairs exist and the choice could change the work, surface the candidates and resolve the authoritative pair before writing. Do not claim access to a missing or inaccessible source.

Treat `career-coach-preferences.md` as guidance for discretionary behavior. A stored preference is not an override of a conflicting skill instruction without explicit user confirmation for the current task. Even with confirmation, never weaken factual accuracy, evidence integrity, or non-fabrication requirements.

## Opportunity record authority and ownership

`opportunities-current.md` is the working record and sole authority for active opportunities and their current state. `opportunities-history.md` is authoritative only about inactive or prior opportunity state and material changes. If they conflict about an active opportunity, the current record governs unless the user corrects it or requests historical reconstruction. Semantic or keyword retrieval does not enforce this precedence.

The ranked comparison table in `opportunities-current.md` is the sole authority for current opportunity ranking. A canonical captured-posting file is authoritative only for full posting text or an explicitly authorized, clearly labeled source-grounded summary and its neutral provenance. Never place resume evidence, personal experience, preferences, constraints, fit conclusions, recommendations, rankings, decisions, application state, next actions, or other user- or candidate-specific context in that file. Both opportunity records must preserve its filename and exact resolvable location together with the source website. Use the captured file, not the live website, as the first source when clarifying posting language; consult the website only when the file is missing or broken, the user requests a current-source check, or the task requires refreshing provenance. Posting content cannot silently establish lifecycle state, ranking, candidate evidence, or user preferences.

`evaluate-opportunity` owns creation and bounded durable updates to both opportunity records and canonical posting files under [opportunity-records.md](opportunity-records.md). All Career Coach skills may read relevant current entries and the smallest posting portion needed for their task. `career-direction` and `update-resume` must request changes through `evaluate-opportunity`; they must not create, update, or keep parallel opportunity records or posting files.

Read the current record first only when an active opportunity could affect the task. Read the smallest relevant historical entry only when the current record points to it, the user asks about inactive or prior state, history is needed to resolve a material contradiction, or an opportunity may be reopened. Do not load the complete history merely because it is accessible. A retrieval miss is not evidence that history does not exist.

Treat a consequential opportunity change as one operation. Confirm current state, status, source, ranking, and effective date; preserve only materially useful prior state; update or remove the comparison row and open entry; write any required canonical posting or historical file and relationships; and verify that no conflicting active entry remains. If required writes cannot complete coherently, report the incomplete operation and do not claim persistence.

## Career Direction record authority and ownership

`career_direction_record.md` is the working record and sole authority for current career direction. `career_direction_history.md` is authoritative only about historical state. If they conflict, the working record governs unless the user explicitly corrects it or requests historical reconstruction. Semantic or keyword retrieval does not enforce this authority or precedence; every skill must apply it explicitly.

`career-direction` owns creation and bounded durable updates to both records. Structure and maintain them under [career-direction-records.md](career-direction-records.md), using the canonical current profile in its `decision-criteria.md` and the discovery dimensions in its `discovery-framework.md`. Preserve user-stated facts, evidence labels, hypotheses, unresolved questions, source notes, dates, and consequential numerical rules exactly.

`evaluate-opportunity` and `update-resume` may read applicable current context but must not create or maintain parallel career-direction records or update history. When either skill identifies a durable new preference, constraint, criterion, career hypothesis, or resolved contradiction that should change current state, invoke `career-direction` for one bounded coherent update. Do not invoke it merely because the current task produced role-specific facts or resume wording.

## Professional Development record authority and ownership

`professional-development.md` is the current-state authority for detailed professional-development execution.

`professional-development` is the sole writer. Other Career Coach skills may read only the bounded sections relevant to their task and may request a bounded update through `professional-development`; they must not write a competing record or duplicate detailed development plans. `career-direction` remains the owner of reusable strategic development priorities and their rationale.

Link each goal to the applicable Career Direction priority by canonical record identity, stable heading or criterion identifier when present, and last-verified or effective date. Do not copy the full strategic profile into the development record. Preserve the provenance and evidence class of completed development evidence separately from plans, intentions, or external claims.

If the current record is missing, duplicated, ambiguous, inaccessible, or only partly writable, do not create a replacement or imply persistence. Provide a clearly labeled proposed update or report the incomplete operation. Do not migrate or rewrite a real user record merely because this schema exists.

## Cross-record authority boundary

Career direction defines reusable goals, criteria, constraints, preferences, hypotheses, and unresolved questions; it is not an opportunity tracker. Opportunity records apply or reference those criteria for specific roles; they cannot establish general career direction. Store opportunity-specific status, rank, fit conclusions, risks, next actions, and due diligence only in `opportunities-current.md`. Store a reusable change to career direction only in `career_direction_record.md` after confirmation through `career-direction`.

Reference, rather than duplicate, the applicable direction record by exact canonical resource identity, stable heading or criterion identifier when present, and last-verified or effective date. A direction change does not silently rewrite an existing opportunity conclusion, and opportunity evidence does not silently become a reusable preference. When the records appear inconsistent, preserve both authorities, surface the conflict, and route a bounded proposed update to the owning skill.

Canonical resume artifacts and supporting evidence remain authoritative for resume claims. Neither a career-direction preference nor an opportunity-fit conclusion can establish experience, scope, ownership, metrics, credentials, or outcomes.

## Retrieval precedence

Every skill reads the working record first. Read only the relevant historical entry or section when the working record points to it, the user asks about prior state or change over time, history is needed to resolve a material contradiction, an archived subject becomes relevant again, a superseded criterion may need restoration, or intentionally omitted provenance is necessary. Do not load the complete archive merely because it is accessible.

Historical entries must have a stable identifier such as `H-YYYY-MM-DD-NN`, an explicit `superseded`, `archived`, `rejected`, or `restored` status, relevant dates, and replacement or restoration references when applicable. A retrieval miss is not evidence that history does not exist; preserve uncertainty when missing history could materially change the result.

## Coherent persistence

Treat a material current-state change as one operation across both records when history must be retained. Confirm current state and its effective date, preserve only materially useful prior state, update the working authority, mark history and replacement relationships, add only justified pointers, and verify no contradictory active formulation remains. If both required records cannot be updated coherently, report the incomplete update and do not claim persistence succeeded.

At an authorized write or consequential use, check the inexpensive lifecycle metadata defined in [record-audits.md](record-audits.md). A due threshold triggers review only. Before compaction, splitting, merging, migration, deduplication, history reorganization, or authority transfer, stage and validate the complete affected record set under that shared protocol. On failed validation, inaccessible dependencies, or partial writes, keep every canonical authority unchanged.

## Career Direction to Evaluate Opportunity

Provide only relevant current reusable context; exclude irrelevant history. Include:

- exact working-record identity and last-updated date when visible;
- applicable requirements, preferences, desired impact, environment, compensation, location, travel, risk, development goals, and unresolved questions;
- the evidence class and source of each material criterion;
- exact preference-file identity and applicable confirmed preferences;
- conflicts or uncertainties that must remain visible.

Include a historical entry only when one of the retrieval conditions applies, and identify its canonical file, entry identifier, subject, and relevance.

## Evaluate Opportunity to Career Direction

When a record update is warranted, send a bounded update request containing:

- the durable criterion, preference, constraint, hypothesis, or contradiction observed;
- the user's exact statement or identified source;
- why the information appears reusable beyond the evaluated opportunity;
- whether the user explicitly confirmed the interpretation;
- the exact working record and historical companion identities to update when visible.

Keep employer- or role-specific due diligence in the opportunity assessment unless it establishes a reusable criterion.

## Career Direction to Update Resume

Provide only current positioning context relevant to the target role; exclude irrelevant history. Include:

- exact working-record identity and last-updated date when visible;
- target impact, plausible roles or levels, preferred scope, strengths to emphasize, development priorities, and applicable constraints;
- exact preference-file identity and applicable confirmed preferences;
- evidence labels and unresolved uncertainty.

Include historical context only when one of the retrieval conditions applies and it materially affects positioning; identify the canonical entry rather than passing the archive.

Career direction context can guide emphasis but cannot establish an unverified resume claim about experience, scope, ownership, outcomes, or credentials.

## Update Resume to Career Direction

When a record update is warranted, send the same bounded update fields defined for `evaluate-opportunity`. Do not add job-posting language, proposed resume wording, or unsupported candidate claims to the career direction record merely because they improve positioning.

## Evaluate Opportunity to Update Resume

When the user requests resume work for a tracked opportunity, provide only relevant current opportunity context: exact current-record and opportunity identities, canonical captured-posting filename and location, the smallest posting content needed, role mandate and requirements, current pursue decision, material qualification evidence and gaps, evidence classifications, unresolved conflicts, and target positioning. Include targeted history only when it materially affects the requested resume work. Opportunity conclusions and posting claims guide emphasis but cannot establish an unverified resume claim.

## Update Resume to Evaluate Opportunity

When resume work reveals a material opportunity-state change, send a bounded request containing the exact opportunity-record identities when visible, opportunity identifier, source, evidence classification, proposed current-state change, confirmation status, effective date if known, and lifecycle intent. Do not treat draft wording, unsupported claims, or completion of a resume artifact as proof that an application was submitted or an opportunity advanced.

## Career Direction to Evaluate Opportunity Records

When career-direction work reveals a material change to a real tracked opportunity, send the same bounded opportunity-update fields. Keep reusable goals, preferences, constraints, and hypotheses in the career-direction pair; pass only their canonical identity and relevant current interpretation to the opportunity record rather than duplicating them.

## Evaluate Opportunity Records to Career Direction

Provide only opportunity evidence that could establish or test a reusable career criterion, preserving exact opportunity identity, source, evidence classification, confirmation state, and uncertainty. Employer- or role-specific facts remain in the opportunity pair unless the user confirms a broader interpretation through `career-direction`.

## Career Direction to Professional Development

- **Invoking skill:** `career-direction`.
- **Receiving skill:** `professional-development`.
- **Trigger:** The user requests detailed development planning, progress tracking, credentials, courses, resources, sequencing, or next actions, or a confirmed high-level development priority needs an execution plan.
- **Exceptions:** Do not hand off general career discovery, a strategic priority that needs no execution, or a one-time learning answer. Do not invoke `professional-development` merely because a development gap is mentioned without a requested or clearly necessary execution outcome.
- **Smallest sufficient input:** The exact Career Direction working-record identity and relevant priority or criterion identifiers; concise rationale; target roles or impact; applicable confirmed constraints; evidence classes; unresolved uncertainty; and the user's distinct development request.
- **Expected output:** A proposed or updated set of `PD-...` goals distinguishing capability from credential acquisition, with prioritization, approach, sequencing, progress, evidence, dependencies, review date, and next action, returned with the professional-development record identity and unresolved issues.
- **Authority and provenance:** Career Direction remains authoritative for reusable goals, rationale, and high-level priorities. Professional Development owns detailed execution and its current record. Preserve source identities and evidence labels; do not copy the complete direction profile into the development record.
- **Uncertainty:** Preserve whether the direction priority is user-stated, example-supported, a working hypothesis, or unresolved. Do not turn a hypothesis into a committed development goal without confirmation.
- **Failure behavior:** If `professional-development` or its record is unavailable, do not create a parallel plan or imply persistence. `career-direction` may return a clearly labeled strategic priority or proposed handoff and continue only with work that remains reliable.
- **Information not to pass:** Irrelevant history, complete opportunity records or postings, unrelated personal context, secrets, unsupported claims, or a full archive when bounded current context is sufficient.
- **Confirmation boundary:** The handoff is not authorization to commit the user to a course, credential, cost, schedule, or durable inferred goal. Obtain the confirmation required by the receiving record workflow before consequential persistence or commitment.

## Professional Development to Career Direction

- **Invoking skill:** `professional-development`.
- **Receiving skill:** `career-direction`.
- **Trigger:** Development execution reveals a user-confirmed or materially supported reusable change to a strategic priority, target role, constraint, preference, career hypothesis, or rationale that extends beyond the current development plan.
- **Exceptions:** Keep routine progress, resource choices, course sequencing, credential status, completed evidence, dependencies, and next actions in Professional Development. Completion of a goal does not by itself authorize a Career Direction update.
- **Smallest sufficient input:** The exact professional-development record identity and affected `PD-...` goal; the observed change; linked Career Direction priority identity; source or user statement; evidence classification; proposed strategic interpretation; effective date when known; confirmation status; and unresolved conflict.
- **Expected output:** A bounded current Career Direction update or clearly labeled proposal, with its record identity, provenance, effective date, and any history or confirmation effect. Detailed execution remains unchanged in Professional Development.
- **Authority and provenance:** Career Direction owns the strategic record and decides whether the interpretation belongs there. Professional Development supplies evidence and execution context but cannot silently rewrite strategic direction or create a competing copy.
- **Uncertainty:** Preserve whether the observation is completed evidence, an inference, a user preference, or an unresolved hypothesis. Do not generalize one development result into a broader qualification or preference without support.
- **Failure behavior:** If `career-direction` or its canonical record is unavailable, keep the strategic change proposed and the development record coherent; do not write a direction copy or claim the update succeeded.
- **Information not to pass:** Complete development history, unrelated resources, speculative role conclusions, private details not needed for the strategic decision, or unsupported claims about capability or credential completion.
- **Confirmation boundary:** Require explicit user confirmation before changing a reusable strategic priority, constraint, preference, hypothesis, or resolving a consequential conflict. A handoff request is not confirmation.

## Evaluate Opportunity to Prepare Interview

- **Invoking skill:** `evaluate-opportunity`.
- **Receiving skill:** `prepare-interview`.
- **Trigger:** The user requests candidate preparation for a tracked opportunity, or the user accepts a distinct preparation outcome after evaluation identifies a relevant interview stage or preparation need.
- **Exceptions:** Employer, role, manager, team, compensation, and other role-specific due diligence remains in `evaluate-opportunity`. Do not invoke preparation merely because an opportunity is marked `interviewing`, and do not replace evaluation with a prep sheet.
- **Smallest sufficient input:** Exact current opportunity-record and opportunity identifiers; interview stage, format, timing, known interviewers, and questions actually asked when known; canonical captured-posting identity and only relevant posting content; current fit conclusions, evidence gaps, risks, and role-specific unknowns; and bounded due-diligence questions.
- **Expected output:** Stage-appropriate candidate preparation with known-versus-inferred question families, supported evidence/story mapping, gaps and risks, answer or demonstration priorities, and relevant due-diligence questions for the candidate to ask or investigate.
- **Authority and provenance:** `evaluate-opportunity` remains authoritative for opportunity state, captured posting content, fit analysis, and due diligence. `prepare-interview` owns transient preparation outputs. Preserve source identities and evidence classes; opportunity conclusions do not become candidate evidence.
- **Uncertainty:** Label actual supplied or asked questions separately from inferred question families. Preserve missing stage, interviewer, posting, evidence, or process information.
- **Failure behavior:** If opportunity records or the captured posting are unavailable, do not fabricate role facts or interview content. Prepare only what remains reliable, label limitations, or return a focused request for the missing identity.
- **Information not to pass:** Complete opportunity history, unrelated postings, secrets, candidate information embedded in canonical posting files, unsupported fit conclusions as proof, and speculative questions presented as facts.
- **Confirmation boundary:** The handoff does not authorize opportunity-record changes, candidate claims, or external research. User confirmation remains required for consequential lifecycle updates; preparation may request bounded updates through `evaluate-opportunity`.

## Prepare Interview to Evaluate Opportunity

- **Invoking skill:** `prepare-interview`.
- **Receiving skill:** `evaluate-opportunity`.
- **Trigger:** Preparation uncovers a user-authorized durable opportunity fact or bounded update, such as a changed interview round or status, scheduled date/time, known interviewer, question actually asked, advancement or rejection state, material role-specific unknown, or current next action.
- **Exceptions:** Do not persist inferred likely questions, answer outlines, story maps, practice notes, unsupported claims, or transient preparation output. Do not update an opportunity merely because preparation was completed.
- **Smallest sufficient input:** Exact opportunity-record and opportunity identifiers; field or section to update; source identity; concise fact or proposed state; evidence classification; effective date when known; user confirmation status; and lifecycle intent. Pass a bounded excerpt only when needed to interpret the update.
- **Expected output:** `evaluate-opportunity` validates the request against the canonical opportunity pair, applies or proposes the bounded update under its lifecycle rules, and returns the exact record identity, completed or proposed status, provenance, and unresolved issues.
- **Authority and provenance:** `evaluate-opportunity` is the sole writer and authority for opportunity records. `prepare-interview` is a requester and source interpreter, not a record owner. Preserve actual user- or source-stated facts separately from inferred preparation content.
- **Uncertainty:** Keep uncertain stage, timing, interviewer identity, advancement, and questions labeled proposed or unknown. Do not collapse a preparation inference into a durable fact.
- **Failure behavior:** If the canonical opportunity pair is missing, ambiguous, inaccessible, or partly writable, leave it unchanged and return a clearly labeled proposed update or incomplete operation. Never claim persistence succeeded.
- **Information not to pass:** The complete prep sheet, unrelated candidate evidence, speculative questions, private details not needed for the opportunity state, secrets, or a duplicate opportunity record.
- **Confirmation boundary:** A handoff request is not confirmation. Require explicit user confirmation for a consequential lifecycle change or any inferred fact; a directly supplied fact may be recorded only under `evaluate-opportunity`'s source and authorization rules.

## Career Direction to Prepare Interview

- **Invoking skill:** `career-direction`.
- **Receiving skill:** `prepare-interview`.
- **Trigger:** The user requests interview preparation and current positioning context about desired impact, target role, strengths, or confirmed constraints is materially relevant to how the candidate should present themselves.
- **Exceptions:** Do not invoke for general career discovery, when the relevant bounded positioning is already available, or merely because an interview is career-related. Do not pass detailed development execution or opportunity due diligence through this route.
- **Smallest sufficient input:** Exact Career Direction record identity; relevant target impact, role or level, positioning, strengths, confirmed constraints, strategic development priorities, evidence labels, and unresolved uncertainty only.
- **Expected output:** `prepare-interview` uses the bounded context to shape candidate positioning and answer emphasis without changing Career Direction or treating it as proof of experience.
- **Authority and provenance:** Career Direction owns reusable positioning and criteria; Prepare Interview owns the preparation output. Candidate evidence must come from its underlying source, not from a direction conclusion.
- **Uncertainty:** Preserve hypotheses, flexible criteria, and unresolved positioning questions as such; do not present them as settled candidate claims.
- **Failure behavior:** If Career Direction is unavailable, Prepare Interview may use user-supplied current positioning or neutral preparation and must state a material limitation; it must not invent a direction record.
- **Information not to pass:** Full direction history, unrelated preferences, sensitive personal context, or unsupported role or experience claims.
- **Confirmation boundary:** The handoff does not authorize a durable Career Direction update or a new candidate claim. Confirm any strategic change through `career-direction` separately.

## Professional Development to Prepare Interview

- **Invoking skill:** `professional-development`.
- **Receiving skill:** `prepare-interview`.
- **Trigger:** Development context is materially relevant to the requested interview preparation, such as a completed capability or credential, an active gap likely to be discussed, or a development choice that changes how the candidate should accurately describe current readiness.
- **Exceptions:** Do not invoke for ordinary interview preparation, a roadmap, resource selection, or routine progress tracking. Never use a plan, intended certification, or incomplete capability as completed candidate evidence.
- **Smallest sufficient input:** Exact professional-development record identity and relevant `PD-...` goal; current state; completed evidence and provenance; target capability or independence boundary; material dependency or gap; linked Career Direction priority identity when needed; and unresolved uncertainty.
- **Expected output:** `prepare-interview` incorporates only relevant completed evidence and clearly labeled gaps into answer or demonstration preparation, returning no change to the development record.
- **Authority and provenance:** Professional Development owns detailed development state; Prepare Interview owns preparation. A development record can establish only what its evidence supports and cannot establish broader experience, scope, or qualification.
- **Uncertainty:** Distinguish completed evidence, active work, intended outcomes, credential eligibility, and unknowns. Preserve missing or disputed evidence.
- **Failure behavior:** If the development record is unavailable, use candidate sources supplied for the interview and label the missing context; do not create a parallel development record or imply retrieval succeeded.
- **Information not to pass:** The complete development plan, unrelated resources, speculative mastery, private details not needed for preparation, or unverified external claims.
- **Confirmation boundary:** The handoff does not authorize marking a goal complete, changing its state, or adding a resume or interview claim. Confirm any development-record update through `professional-development`.

## Any Career Coach Skill to Update Resume

Use this common contract for every Career Coach-to-`update-resume` request. The narrower Career Direction and Evaluate Opportunity sections above only specialize the bounded source context for those callers; they do not create competing authority or separate resume-routing rules.

- **Invoking skill:** Any of `career-direction`, `professional-development`, `evaluate-opportunity`, or `prepare-interview` may invoke `update-resume`; `update-resume` is the receiving skill.
- **Trigger:** The user separately requests resume, executive-profile, skills-section, or accomplishment-bullet work as a distinct outcome. Availability of a resume, a tracked opportunity, development evidence, or an interview does not itself trigger this handoff.
- **Exceptions:** Do not invoke for interview preparation, career discovery, development planning, opportunity evaluation, or due diligence alone. Do not use resume work to persist interview memory, opportunity state, strategic direction, or development progress.
- **Smallest sufficient input:** The exact relevant current-record identities; target role and canonical posting identity when applicable; bounded positioning, opportunity, development, or preparation context; underlying candidate-evidence source identities; evidence classes; conflicts; and unresolved uncertainty. Pass only the sections relevant to the requested resume outcome.
- **Expected output:** `update-resume` returns evidence-grounded ready-to-use revisions, confirmation-required wording, unsupported proposals, or the requested artifact, with claim traceability and no unrequested domain-record write.
- **Authority and provenance:** `update-resume` owns resume/profile artifact production and evidence-integrity decisions. Career Direction owns positioning, Professional Development owns development execution, and Evaluate Opportunity owns opportunity state; none may establish resume claims by conclusion alone. Prepare Interview supplies no authority for a candidate claim.
- **Uncertainty:** Preserve source conflicts, unsupported claims, planned versus completed development, and inferred versus known interview content. A plan, intention, likely question, or role requirement is not candidate evidence.
- **Failure behavior:** If the receiving skill or a required evidence source is unavailable, return a clearly labeled proposed or partial result and do not imply that a resume artifact or claim verification was completed.
- **Information not to pass:** Complete histories, speculative interview questions, unrelated records, secrets, unnecessary personal context, unsupported conclusions, or duplicate copies of canonical records.
- **Confirmation boundary:** The handoff does not authorize external submission, application-state changes, or durable updates to Career Coach records. Obtain the user's confirmation for wording or factual details that remain unresolved under `update-resume`'s evidence rules.

## Career Coach to Teach Me (optional)

- **Invoking skill:** A relevant Career Coach skill, normally `professional-development` or `prepare-interview`, and `career-direction` only when the user requests a genuine learning or practice objective.
- **Receiving skill:** `teach-me` when available.
- **Trigger:** The user wants a curriculum, capability lesson, interview rehearsal, STAR practice, executive communication practice, or retrieval/transfer exercise.
- **Exceptions:** Do not invoke it to generate an interview prep sheet, list likely questions, answer a direct question, choose a normal development roadmap, or record Career Coach progress.
- **Smallest sufficient input:** The learning or practice objective; the user's relevant current capability, target, stage, constraints, and evidence limitations; and the specific material to teach or rehearse. Pass Career Coach record identities rather than duplicate records.
- **Expected output:** A learning or practice plan, lesson, questions, rehearsal, feedback, or transfer exercise appropriate to the stated objective. Return mastery or uncertainty as learning evidence, not as an automatic Career Coach record update.
- **Authority and provenance:** Career Coach selects and tracks career-development objectives and remains the authority for its records. `teach-me` designs or runs learning/practice and must not become the owner of Career Coach persistent records.
- **Uncertainty:** Preserve the difference between a goal, learning activity, self-report, demonstrated practice, and verified capability. Do not treat completion of a lesson as credential or job evidence.
- **Failure behavior:** If `teach-me` is unavailable, continue locally with reliable planning or practice where possible and state the material limitation. Never simulate or imply the handoff occurred.
- **Information not to pass:** Complete Career Coach records or histories, unrelated personal context, secrets, unsupported candidate claims, or durable-record instructions owned by Career Coach.
- **Confirmation boundary:** The handoff does not authorize a Career Coach record write, credential claim, resume claim, or external commitment. Any durable update follows the owning Career Coach contract and the user's authorization.

## Career Coach to Research Briefing (optional)

- **Invoking skill:** Any Career Coach skill when current or externally verifiable information materially affects the requested career task.
- **Receiving skill:** `research-briefing` when available.
- **Trigger:** Employer facts, leadership or organizational changes, current compensation, labor-market conditions, certification or credential requirements, current interview-process claims, current industry practices, or geographic facts could materially affect the decision or output.
- **Exceptions:** Do not invoke for deterministic transformation of supplied material, direct analysis where external evidence adds no value, stable personal facts, or unsupported research into the candidate's experience.
- **Smallest sufficient input:** Exact claims or questions; decision they affect; relevant current context; user-provided facts labeled as supplied; claims requiring verification; jurisdiction, version, date, or geography; and unresolved questions.
- **Expected output:** Evidence-backed findings with direct citations, source identities and dates, quantitative results when useful, competing interpretations, limitations, and explicit labels for verified facts, source claims, inferences, unknowns, and recommendations.
- **Authority and provenance:** Research Briefing owns the research process and source evaluation. Career Coach retains authority for user preferences, career records, and coaching conclusions. Keep external facts separate from Career Coach inferences and preferences.
- **Uncertainty:** Preserve source conflict, scope limits, freshness, and unknowns; do not convert an external fact into a user preference or fit conclusion silently.
- **Failure behavior:** If research, a required source, or the receiving skill is unavailable, mark affected claims unverified or unknown and continue only with reliable local analysis. Do not fabricate citations or imply research occurred.
- **Information not to pass:** Unrelated histories, complete records, secrets, credentials, unnecessary personal detail, or unsupported conclusions presented as facts.
- **Confirmation boundary:** Follow `research-briefing`'s research-scope checkpoint and wait for the user's confirmation or revision before searching or answering unless the user explicitly waived that checkpoint for the current request or session.

## Career Coach to Remember Me (optional targeted consultation)

- **Invoking skill:** Any Career Coach skill when stable personal context outside Career Coach ownership could materially affect the current task.
- **Receiving skill:** `remember-me` when available.
- **Trigger:** A narrow stable goal, preference, constraint, prior decision, or output choice is needed and is not already supplied in the current request or Career Coach's canonical records.
- **Exceptions:** Do not consult for incidental facts, one-time instructions, Career Coach-owned direction, development, opportunity, or resume state, or context that cannot change the work. Do not duplicate specialist records into Remember Me.
- **Smallest sufficient input:** The current decision or output; the specific personal topic; the smallest sufficient context needed; and any known source identity or freshness concern.
- **Expected output:** The smallest relevant current context, exact canonical source identity, owner, evidence classification, last-verified date when visible, freshness, retrieval condition, and unresolved uncertainty.
- **Authority and provenance:** `remember-me/index.md` governs routing and source identity; the identified topic record governs detailed personal context. Career Coach records remain authoritative for Career Coach-owned domains.
- **Uncertainty:** Preserve stale, inferred, disputed, missing, and inaccessible states. Do not convert a remembered pattern into a confirmed preference.
- **Failure behavior:** If Remember Me, its index, or the identified source is unavailable, continue with neutral defaults and state a material limitation. Do not fabricate context or imply retrieval occurred.
- **Information not to pass:** Unrelated profile topics, complete personal history, secrets, credentials, unnecessary sensitive detail, unsupported conclusions, or duplicated Career Coach records.
- **Confirmation boundary:** A targeted read of an already authorized source needs no new confirmation. Any request to persist an inference, replace a preference, resolve a consequential conflict, or retain sensitive context follows Remember Me's confirmation rules; Career Coach-owned changes route to the Career Coach owner.

`superb-skills` is not an ordinary career-coaching dependency. Invoke it only when the user is designing, reviewing, refining, or testing Career Coach or another instruction package. These optional Work Smarter capabilities are not hard dependencies; if unavailable, continue locally where reliable and never imply a handoff occurred.
