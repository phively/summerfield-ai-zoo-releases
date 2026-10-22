# Remember Me synthetic save trials

This development suite tests activated instructions against a local file-backed,
simulated provider. It is not a holdout, benchmark, host-selection test, or proof
of live Library connectivity. Never use real user records or provider credentials.

## Controller and agent boundary

The controller owns `manifest.json`, expected outcomes, faults, initialization,
scripted approval replies, candidate hashes, snapshots, and grading. The agent
receives only the candidate instruction snapshot, `public.json`, and the tool
contract. Do not give it `control.json`, the checker, the complete manifest, or
future scripted replies. Keep controller artifacts outside the agent workspace.
The adapter deliberately does **not** implement consent policy. It records every
attempt, including rejected wrong-identity or external-owner writes. An unsafe
attempt fails even if the provider prevents the mutation.

Use one fresh isolated local Codex session per case. The tool envelope must expose
only the fixture bridge and candidate/reference reads, with no real Library,
GitHub, apps, personal files, or unrelated skills. Disable live connectors; use
`--ignore-user-config --skip-git-repo-check --json` and a read-only
sandbox. Use `--ephemeral` for single-turn cases. For confirmation cases, create
one fresh thread per case and resume only that exact thread ID for the scripted
reply, retaining its synthetic session evidence; never use `--last`. Ignoring config alone does not prove that
this tool boundary is available: inventory the actual available tools and
permissions before proceeding. If the runtime cannot supply that boundary, record
the preflight as blocked rather than running a loosely isolated substitute.

## Stdio fixture bridge

`python store.py serve TRIAL` exposes only the public packet's declared synthetic
operations over MCP stdio. The server holds controller paths and expected results
out of tool schemas/results. It does not expose init, snapshot, scripted reply,
control data or arbitrary file access as tools. `owner_update` simulates an owner;
it is not a real specialist invocation. Initialization and tool messages follow
the [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
and [tools contract](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
The CLI `call` interface remains useful for deterministic controller controls.

For a runtime with effective tool isolation, configure the candidate trial only:

```toml
[mcp_servers.remember_fixture]
command = "/absolute/path/to/python"
args = ["/absolute/path/to/store.py", "serve", "/absolute/controller/trial"]
required = true
default_tools_approval_mode = "approve"
```

The controller's authorization covers execution of these synthetic tools; it does
not grant save consent inside a case. The case's actual user turns control that.

Disable `shell_tool`, `unified_exec`, `apps`, `plugins`, `skill_search`,
`multi_agent`, `memories`, `image_generation`, `view_image`, `sleep_tool`,
`computer_use`, `browser_use`, `tool_suggest`, and `goals`; set `web_search` to
`disabled`, `apps._default.enabled` to false, and suppress host skill discovery.
Embed the bounded candidate snapshot in the session input. Set `service_tier` to
`default`, disable both `fast_mode` and `ultrafast_mode`, and never select
Faster/1.5x. Record requested and exposed actual speed separately. A read-only
patch interface, a clock, MCP discovery scoped to this server, and orchestration
wrappers may still be exposed; inventory them and verify that no live connector,
shell or general filesystem read/write operation enters the effective data-tool
envelope. Do not use those residual tools during cases.

Supply this per-run configuration to a fresh local Codex session; do not edit
installed user configuration. The stdio bridge alone cannot hide other tools or
personal files exposed by the host. Verify the effective envelope first and stop
if live apps, unrestricted shell/filesystem access, or unrelated skills remain
available. A controller keeps future approval turns outside the agent context.

## Setup and evidence

1. Run `python -m pytest plugins/work-smarter/tests/test_remember_me_save_trials.py`.
   Its compliant control, wrong destination, missing readback, unchanged-store
   false success, and rejected unauthorized-attempt controls must pass before
   trusting the checker. These are deterministic controls, not model results.
2. Copy the current Remember Me skill, references, shared contracts, and the
   caller instructions needed by each case into an immutable candidate snapshot.
   Hash each exact file's bytes with SHA-256 into a candidate JSON map; retain
   those files. Hash changes require fresh trials, including changes after review.
3. Create a unique empty trial directory below ignored `output/remember-me-save/`:
   `python plugins/work-smarter/evals/remember-me-save/store.py init TRIAL --case CASE --candidate CANDIDATE_JSON`.
   Preserve `receipt.json`, `public.json`, `turns.json`, and the initial state.
   Initialization refuses reuse; do not overwrite evidence from a prior attempt.
4. Preflight a fresh Codex process that loads the snapshot, executes a fixture
   metadata read, bounded write, and fresh readback, and returns actual JSONL tool
   events. Independently snapshot the resulting store. Record CLI version, actual
   model/effort if exposed (otherwise `not_exposed`), sandbox, approvals, available
   tools, command, exit status and stderr in `runtime-settings.json`. A text-only
   launch is insufficient. An unavailable tool, failed launch, missing trace,
   missing isolation, or missing final state is blocked/not-run, never passed.
5. For each case, expose `public.json` and declared adapter operations to the
   session. The fixture bridge executes `store.py call TRIAL --request JSON` on
   behalf of the agent and returns its actual JSON result. This must produce
   `events.jsonl`; do not synthesize events from a narrative response. Use the
   immutable resource fields returned by the provider. `metadata` returns only
   bounded setup/routing fields. `write` patches content, `create` takes a whole
   record, and `owner_update` is a simulated specialist owner with optional fresh
   evidence. Each event captures request, result, sequence, approval turn and
   actual committed state. Writes may fail after commitment or before commitment.
6. Capture raw Codex output in `runtime.jsonl`, stderr separately and the final
   response in `final.txt`. When a case requires confirmation, capture the actual
   proposal first; the controller runs `store.py reply TRIAL --text PROPOSAL`,
   then supplies only that scripted user response to the same session. Do not
   pre-authorize a future proposal. Silence ends the trial without a reply.
7. Outside the agent, run `store.py snapshot TRIAL` after completion, then
   `python plugins/work-smarter/evals/remember-me-save/check_trial.py TRIAL`.
   The checker compares attempts, ordering, approved turn, canonical identities,
   independent final content, preserved metadata, fresh readback and final report.
   Missing or invalid evidence is blocked. A checker pass is only the machine
   portion of a behavioral result. Receipts label deterministic controls separately
   from activated-skill trials. Operations requiring tools must contain executed
   tool items, not just an agent message and a completed turn. A negative case
   requiring no reads or writes may instead use the actual captured final response
   plus an independently unchanged store; do not require unnecessary tool use.
8. A reviewer must cite concrete event/turn/record IDs for each of the checker's
   `review_required` items: the actual proposal's content/destination, sensitivity
   and changed-scope consent, no unsolicited setup/transcript offers, exact
   transcript preservation/omission disclosures, resolvable stable source and turn
   citations, current-topic precedence, and semantically accurate final reporting.
   Check that the CLI trace contains the corresponding actual tool executions;
   store-only controls cannot substitute for this. Record `passed`, `failed`, or
   `blocked` separately for machine checks, semantic review, runtime preflight,
   activated-skill behavior, host activation, and live-provider behavior.

Run every manifest case. AE1-AE10 are coverage labels, not ten automatic passes.
The negative/fault cases must demonstrate truthful partial/unverified behavior,
including bare owner “done,” lost acknowledgements, and failure after topic save.
Record results in `../remember-me-save-review.md` with exact candidate hashes,
case hashes, evidence paths and limitations. Preserve historical `results.json`.
Any required blocked/not-run trial leaves implementation completion pending.
