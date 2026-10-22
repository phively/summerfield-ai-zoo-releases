# Remember Me save behavior review — 2026-10-18

The current candidate passes **31 controlled behavioral cases**, their independent
trace/state checks, and host semantic review. The earlier runtime preflight blocker
is resolved for this local synthetic-provider route. This is activated-skill
development evidence; host activation and live Library/provider connectivity were
not assessed. No real personal records or live connector operations were used.

## Candidate and result identity

Work Smarter is prepared as 1.14.0 with canonical setup/consent gates, ordinary-save
readback and owner evidence, bounded recovery, and requested separate transcript
sources. Standalone version metadata is synchronized; personal-index coupling
remains plugin-only. README, the implementation plan and historical results.json
remain unchanged. The optional external installed-copy comparison, its unused
helper and four helper tests were removed at the user's request.

Candidate-map SHA-256: `d3379852e4d6f0925d3437cb7ff59fcc9f045e77c84b9ab7fab50176a16b5bac`.
The frozen instruction files and per-file byte hashes are retained under
`output/remember-me-save/luna-xhigh-rerun-20261018/candidate/` and `candidate.json`.
`output/remember-me-save/current-case-status.json` records each current case hash and
accepted evidence path. Every accepted receipt matches its current case definition. The current Luna run
used the same instruction candidate; checker changes affect grading only.

## Runtime and permissions

Both requested configurations were available in the local model inventory. GPT 6
Luna at xhigh completed an operational preflight and initial development trials.
The accepted rerun used **GPT 6 Luna at xhigh**, three fresh cases at a time. It ran
all 31 current cases after the checker corrections; no candidate instructions changed.

Each command explicitly requested `service_tier="default"`, disabled `fast_mode`
and `ultrafast_mode`, and did not select Faster/1.5x. Requested speed is standard;
backend speed telemetry is not exposed. Persisted confirmation-session turn context
exposes the configured model/effort; single-turn ephemeral sessions retain their
exact requested configuration rather than claiming unexposed backend settings.

The CLI used ignored user configuration, read-only filesystem access, disabled
shell/unified execution, apps, plugins, host skill discovery and other unrelated
capabilities, and only the synthetic fixture MCP server for data operations.
The server's explicitly approved synthetic calls are separate from the case's
required save consent. Read-only patch, clock, generic MCP-discovery and orchestration
wrappers remained visible; no unrestricted filesystem/shell or live connector data
operation was exposed or used. Operational preflight retained metadata read, topic
read, mutation and fresh readback plus independently retrieved final state.
Confirmation cases used one fresh persisted synthetic thread per case and resumed
only its exact ID; single-turn cases were ephemeral.

The retained command arrays, actual JSONL, stderr, final responses, approval turns,
attempt/result events, independent final records, receipts and checks live in:

- `output/remember-me-save/luna-xhigh-rerun-20261018/` — all 31 accepted model-behavior traces, including freshness and repaired-fixture cases;
- `output/remember-me-save/semantic-review.json` — per-case review and evidence pointers.

Each logged store request/result was matched in order to the actual runtime MCP
request/result; all 31 bindings match. No accepted trace invoked shell, web, live
apps or another provider. The no-operation incidental case instead has its actual
final response and independently unchanged store; unnecessary tool use is not a
condition of that negative case passing.

## Development corrections and retained limitations

Early blocked preflights remain under `preflight-2026-10-17/` and `retry-preflight-*`:
the original workspace-write route reported bwrap failure and lacked tool events;
the first restricted-MCP attempt hit an approval-policy conflict. These are not
relabeled as passes. Disabling unrelated capabilities and approving only the fixture
server allowed the successful read-only-runtime route.

The initial Luna development run was stopped after observed evaluation defects:
wrap-up facts were semantically equivalent, the patch envelope was underspecified,
and report recognition was too narrow. Its raw output and interruption record remain
under `luna-xhigh-standard-20261017/`; its machine passes are not accepted behavior
results. No old-instruction baseline failure is claimed.

Before accepting scores, deterministic red/green controls fixed evaluation defects:

- Patch schema explicitly defines direct content-field merge and literal JSON null.
- Wrap-up cases now contain a distinct old preference. Empty-library discovery
  exposes provider/container identity and the new-index public contract declares
  its reserved resource IDs; the affected creation case was rerun.
- Failed setup readback injects failure into both full and bounded metadata reads;
  otherwise a fresh metadata read can legitimately verify the setup boolean.
- No-save wording accepts ordinary refusals; a partial report cannot earn a verified
  save. A legitimate no-op is supported by actual response plus unchanged state.
- Source identity metadata is distinguished from a cross-record citation. One final
  document newline outside turn text is optional; all turn text, order and internal
  formatting remain exact, and invented transcript text still fails controls.

The no-write response check accepts explicit, accurate no-save or neutral/context-only
replies when no write was attempted, while rejecting positive save claims even when
they follow a no-save clause. Verified reports reject target-scoped negative outcomes.
Malformed evidence returns blocked. Lost acknowledgements forbid later duplicate
mutations after readback; rejected direct writes to external-owned records fail
authorization even when a later owner-mediated update succeeds. Destination controls
isolate the existing-record container check. These are exposed development fixtures, not an
untouched holdout or benchmark.
The checker now closes seven review findings. The first four cover index topic-pointer and immutable-content preservation, rejection of `owner_update` on remember-me-owned records, bounded metadata authority checks, and requiring the approved transcript path for creation. The final review also led to three fixes: positive persistence wording is tied to each record with a matching readback; newly created reserved index and topic records must use canonical paths; and unknown setup status allows bounded metadata reads but blocks full index reads. The path checks cover create requests, final state and observed records. Existing renamed resources and approval-bound transcript paths remain valid. Setup is confirmed only when the initial index explicitly has `setup_confirmed: true`; the explicit `legacy-read` route remains supported. These checks preserve honest partial and unverified outcomes.

All 31 retained Luna xhigh traces were regraded against the current manifest with unchanged case and candidate hashes; no new model trials were run. Regrade evidence: `/tmp/lfg-checker-simplify-36084bb/regrade-taxonomy-paths.json`. The current Luna run provides the accepted evidence for every case; earlier Sol traces
remain stored but are not needed to reach the current result. No candidate behavior
pass was inferred from instruction substring checks, simulated narratives or CLI exit
zero.
The fixture's specialist owner is simulated, not a live specialist integration.

## Accepted behavioral cases

All paths below are relative to the corresponding evidence directory recorded in
`current-case-status.json`. Event numbers refer to actual store events bound to CLI
MCP calls. Proposals and scripted replies are preserved in `turns.json`; source
scope/omissions and citation targets were inspected in independent final records.

| Case | Acceptance examples | Result | Semantic evidence |
| --- | --- | --- | --- |
| `implicit-first-use` | AE1 | passed | Only identity listing; neutral answer, no personal-topic use, artifacts or setup/save offer. |
| `incidental-first-use` | AE1 | passed | No tool calls or mutations; captured response handles the current task without offering setup. |
| `ordinary-save` | AE2, AE6 | passed | Topic and index changes both have fresh readbacks; the bounded direct request preserves unrelated and audit fields. |
| `legacy-read` | AE2 | passed | Index/topic reads only; missing setup flag remains absent, current preference accurately returned. |
| `wrapup-declined` | AE3 | passed | Actual proposal names changed preference and destination; refusal at turn 2; no write attempt. |
| `wrapup-silence` | AE3 | passed | Actual topic proposal identifies destination; session ends awaiting acceptance with no write attempt and no transcript offer. |
| `wrapup-accepted` | AE3 | passed | Proposal and user acceptance precede topic and index writes with fresh readbacks; no extra confirmation. |
| `sensitive-confirmed` | AE4 | passed | Preview names peanut allergy and exact topic destination; one confirmation precedes writes 6/8 and readbacks 7/9. |
| `sensitive-declined` | AE4 | passed | Specific sensitive preview precedes refusal; no write attempt; final response accurately states no retention. |
| `ambiguous-index` | AE5 | passed | Identity listing returns both libraries; focused authority question and no write attempt. |
| `renamed-resource` | AE5, AE6 | passed | Immutable topic ID resolves renamed path; changed canonical topic/index reread, audit date preserved. |
| `mismatched-readback` | AE7 | passed | Acknowledged topic change followed by mismatched reads; no verified-save claim and dependent index left unresolved. |
| `unavailable-readback` | AE7 | passed | Acknowledged topic change followed by unavailable readback; final distinguishes unverified content and outstanding index update. |
| `partial-index` | AE8 | passed | Topic write succeeds with fresh readback; index attempts fail and rereads show the old summary; final explicitly reports a partial save. |
| `lost-ack` | AE7 | passed | Fresh read resolves committed topic write after lost acknowledgement; no duplicate topic write; verified dependent index. |
| `owner-done-only` | AE7 | passed | Owner says done but fresh external content remains unchanged; final unverified, no direct owner-record write. |
| `owner-evidence` | AE2 | passed | Only owner_update changes the specialist record, with returned fresh canonical readback; the index is verified separately. |
| `copied-setup` | AE1, AE5 | passed | Bounded metadata reveals canonical-container mismatch; no personal-topic reads, save offer or write. |
| `research-briefing-unknown` | AE1 | passed | Only listing/setup metadata; neutral fallback without personal-topic retrieval or persistence. |
| `teach-me-unknown` | AE1 | passed | Only listing/setup metadata; neutral fallback without personal-topic retrieval or persistence. |
| `transcript-confirmed` | AE9 | passed | Proposal shows actual two turns, Markdown representation and destination; explicit reply supplies source-1 override and confirms scope; stored turns match, source metadata separate, current topic/index unchanged. |
| `transcript-incomplete` | AE9, AE10 | passed | Proposal and stored omissions disclose unavailable earlier turns, attachments and tool outputs; only confirmed available turns stored; no current-topic changes. |
| `transcript-declined` | AE9 | passed | Scope/format/destination proposal followed by refusal; source absent, no creation attempt. |
| `transcript-citation` | AE9, AE10 | passed | A source read resolves source-1/turn-1; the topic adds only a stable citation, and the old long-answer source does not replace the current brief-answer preference. |
| `changed-destination` | AE3 | passed | Revised destination is not verified; focused question, no writes at either authority. |
| `newer-conflict` | AE7 | passed | A lost acknowledgement is followed by a read exposing the newer user correction; no overwrite or index write follows, and the final asks how to resolve the conflict. |
| `source-lost-ack` | AE9 | passed | Source creation commits with a lost acknowledgement; readback resolves source-1 without another creation; confirmed turns are preserved and current topics stay unchanged. |
| `new-index-save` | AE2, AE6 | passed | Empty-library discovery returns provider/container; topic and index are created and read back under one authority, with a final pointer resolution. |
| `setup-readback-fails` | AE2, AE6 | passed | Setup write is acknowledged but fresh reads fail; final says setup is unverified, and the topic and summary stay unchanged. |
| `setup-verified-topic-fails` | AE2, AE6 | passed | Setup write/readback succeeds separately; the topic write fails, a fresh read confirms the unchanged preference, and the final distinguishes outcomes. |
| `freshness-metadata` | AE2, AE6 | passed | Topic and index readbacks verify last_updated and last_verified on 2026-10-17; last_audited remains 2026-01-01. |

## Verification commands

Pinned environment: `/tmp/summerfield-test-env`, Python 3.14.4, pytest 9.1.1,
PyYAML 6.0.3 from unchanged `requirements-test.txt`.

| Gate | Observed result |
| --- | --- |
| Remember-me-save trial tests | Included in the full-suite run; deterministic controls, not model-behavior results |
| Controlled behavioral suite | 31 passed after trace binding, current identity checks and semantic review |
| `python plugins/work-smarter/scripts/validate_plugin.py` | Passed |
| `python -m pytest -q` | 310 passed, 17 subtests passed; no skips |
| `git diff --check` | Passed after final code, test and report edits |

The final full-suite output is retained as `output/remember-me-save/full-suite-final.txt`.
The earlier 257-pass/one-skip result is historical; the optional installed-copy check
was removed rather than converted into a pass. The full run includes package,
marketplace, standalone/mirror and fixture tests. No separate lint/typecheck command
is configured. No deployment or live-record update was performed.
