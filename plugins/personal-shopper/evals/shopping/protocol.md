# Personal Shopper acceptance and live access protocol

This suite has three distinct evidence levels: deterministic checker controls,
activated synthetic behavior, and live canonical-provider access. A result at one
level never stands in for a later level. The fixture text describes expected
behavior; it does not prove that the skill ran.

## Candidate and isolated activation

Before a run, compute the candidate SHA-256 using `check_trial.py`. For every
local package, `candidate.packages[*].source_root` and `files` in
`manifest.json` are the single declaration used to stage package contents,
build the aggregate candidate identity, and compare a retained profile's
installed local-file hashes with the current source. Add required transitive
contracts to that package's `files` list so each run contains the instructions
its behavior depends on. Runtime provider packages are resolved and checked by
their installed plugin identity and version; they are not treated as local
candidate files. Freeze the exact local candidate until the run ends. Any change
to a declared identity file makes an earlier receipt stale. Compute and record
the separate suite SHA-256 from the evaluator identity patterns in `manifest.json`;
this covers the fixtures, protocol, collector, runner, synthetic store and
scoring rubric. A candidate or suite identity change invalidates affected
evidence.

Before creating the isolated workspace, the runner checks Markdown links in each
staged local package. Relative links must resolve to files inside that package
and those targets must also be declared for staging. Missing, undeclared,
symlinked, or escaping targets fail preflight before the workspace is created.
External provider packages do not use this local-package check.

Run activated behavior only through the host's supported skill activation route.
Use a fresh isolated context with only the candidate package, declared fixture or
provider tools, and explicit case input. Keep the active workspace outside this
repository and outside any ancestor containing repository instructions. Do not
expose sibling packages, broad filesystem access, unrelated connectors, or private
personal records to a synthetic trial. Record the actual available tool and
permission envelope before running. If the host cannot provide the required
boundary or activation route, mark the case blocked/not-run; do not substitute a
direct connector check or a model-written trace.

The Codex CLI adapter installs the profile packages from a disposable local
marketplace into a temporary `CODEX_HOME` and invokes the qualified skill ID in
a fresh JSONL session. Sessions are ephemeral by default. The dedicated
`B10-AE12-new-plan` profile alone enables multi-agent delegation and retains its
session long enough to copy the invoked parent and directly related child
rollouts. The runner copies only those rollout files into private evidence,
records their hashes and thread relationship, then deletes the temporary home.
It never copies authentication files or unrelated sessions. The delegated
profile keeps shell, unified execution, app, browser and provider tools disabled;
the isolated workspace uses a read-only sandbox and has no general filesystem
MCP server. Only the case's allowlisted synthetic fixture and exact
installed-contract reader are registered. For AE12, the child reader exposes the
declared grocery workflow, receiver, record-management, store-preference, and pricing
resources. Other profiles remain ephemeral and do not enable
multi-agent delegation. The host stream and installed-package and evaluator
identities are recorded before and after the run. For the AE12 new-plan case,
the caller's frozen reader also exposes its Meal Planner skill and shared
handoff, record-management, and grocery-integration contracts; scoring requires
all four reads to complete before packet construction. The actual smoke invocation
must confirm the discovered skill is present and the host stream is complete
before any behavioral panel starts. The runner's `runtime-settings.json`
records the profile, tool policy, filtered environment names, plugin
suppressions and identity check outcomes; prompt, trace, task, runtime profile
and delegated rollouts remain private.

The connected Google Drive app exposes account-scoped tools, not a per-resource
permission filter. For R25, pass only the current runtime-selected locator to the
activated skill and require the checker to bind every captured provider call to
the independently resolved canonical identity. Any captured call targeting a
different identity invalidates the run; the profile must not probe unrelated
account files. Synthetic trials use only the local fixture provider, which
rejects out-of-scope spreadsheet IDs before reading or changing fixture state.

Use the AE1–AE12 fixtures for case inputs and the B1–B12 groups in the plan as the
behavior matrix. Fixtures cover controlled examples, including the integration
and fallback edge cases. A semantic reviewer must inspect product fit, evidence
quality, recipe preservation, and truthful per-target persistence claims against
actual invocation and tool evidence. A phrase match, deterministic control, or
hand-authored expected response is not an activated-skill result.

The two AE12 B10 subcases use synthetic fixture data only. The new-plan child may use
read-only synthetic workbook metadata and range tools; only the parent uses plan tools.
The new-plan case has a dedicated profile that enables Codex multi-agent delegation while keeping
shell, filesystem, browser, app and provider tools disabled. The caller must invoke the
installed Personal Shopper as a child agent, return the complete packet through the
observation tool, and save/read back the plan only after that return. The scorer binds
the child request and completed response to the recorded packet and subsequent save;
the observation tool does not generate a grocery result. The second case stays on the
standard single-agent profile and checks the existing-plan missing-identity boundary.
The runner exposes only the declared installed Markdown resources for these two cases
through a read-only, path-and-digest allowlisted local reader. The scorer requires the
declared contract reads and checks their returned bytes against installed identities. For
the new-plan case, it reads the persisted parent and child rollouts, requires the caller's
own Meal Planner skill and grocery integration reads before packet construction, then
requires the complete caller packet as the last parent assistant message before
delegation. It matches that message ID and content in the child's inherited history and
counts only calls with the child's own thread ID as child activation. The child must read
the installed Personal Shopper skill and all declared grocery workflow resources before
work. Repeated completion notifications for one child thread remain bound to that one
activity, using its last completion position. It may use only read-only synthetic
spreadsheet metadata and range tools, and only with the workbook identity in the packet.
Each such tool response carries a fixture event ID that is matched
to the same tool, arguments, and result in the fixture ledger. The child cannot record the
grocery result, inspect or save plans, or write the workbook. The recorded object is the
exact top-level `grocery-handoff/v1` result packet; the fixture does not require a nested
`grocery_result` field. The parent records that exact terminal child JSON return after
captured child completion, then saves and reads back the plan. These controls verify a
synthetic handoff and plan save; they do not access a
provider or establish B12 preservation. Existing case results and their denominators
remain tied to their original candidate and suite identities.

The supplemental B7 role-map case activates Personal Shopper against a legacy
workbook with `Price History`, `Shopper Preferences`, and `Change History` tabs,
no `Record Index`, reordered fields, and stable keys at the end of each row. The
scorer requires successful metadata and role-tab reads, the reviewer checks the
reported order against those rows, and every write attempt fails acceptance.

Run one synthetic subcase at a time with `run_trial.py --profile <profile>
--subcase <subcase-id> --output-dir <ignored-private-path>`. The runner exposes only
that subcase's declared tools from the local synthetic MCP fixture. Its automatic
approval applies only to those private, allowlisted fixture tools; it does not enable
provider connectors. The fixture stores task-visible workbook rows separately from
hidden controller assertions, logs every tool call, and retains final state. After a
completed run, invoke `score_trial.py <private-trial-directory>`. Machine-ready
evidence must still be reviewed using `rubric.md`; the scorer intentionally leaves
semantic review pending and never accepts a case by itself.

For a CLI using file-based ChatGPT authentication, an empty temporary home may
have no usable login. The optional `--use-existing-cli-auth` flag links the
controller's existing private CLI `auth.json` into that temporary home. The
runner checks its private-file permissions without reading its contents. It
copies no credentials, global configuration, sessions, or provider connection
state. The flag is allowed only for profiles without provider apps. Provider
apps use the account's broader access, and the runner cannot enforce a workbook
and range allowlist before each provider call; it rejects auth linking for
provider-enabled profiles, including `r25` and `native-sheets-preservation`.
The candidate still has no shell or general filesystem tool; the source and
installed-resource readers cannot read the credential cache. The alias is
removed with the temporary home, while the CLI may refresh its normal login
cache during use. The runtime settings record whether the flag was used.
Missing private-cache access or unavailable symlink support blocks that route;
do not print or put authentication files in captures or the source checkout.

## Source-retrieval research cases

The thirteen B13–B18 subcases extend the synthetic matrix without changing the
historical B1–B12 definitions or denominators. Each uses `shopper-alone` and its
declared installed-resource reader. The shopper-only reader exposes hashed
Markdown instructions within the installed candidate's skill directories so
the skill can follow relevant package-local links. Required instruction reads
remain the case's minimum; other packages, credentials, arbitrary files and
changed bytes remain inaccessible. Delegated legacy readers keep their exact
declared resource boundaries. Older shopper-only subcases without a required
resource list receive the same installed reader, with the main skill as the
minimum read, so linked workflows remain available when filesystem tools are
disabled. This changes no fixture request, expected answer or research-source
allowlist. B13–B17 and the task-only B18 case permit
only public-context and case-allowlisted synthetic source reads. The partial-save
B18 case additionally permits the existing synthetic workbook tools for its
explicit current-row and history targets. None enables real providers, web
access, purchases, contractor contact, applications, or bookings.

The task-visible `source_index` supplies source IDs, kinds, titles, and locators.
Source bodies are absent from the prompt and `get_case_context`; only
`retrieve_source(source_id)` returns them. Each fixture's controller file keeps
its typed sources and expected judgments separate from public context. A
retrieval returns source identity, applicability, effective/check dates, the
actual content, and its digest, or an explicit unavailable result. Unknown IDs,
extra selectors, malformed envelopes, and sources from another case cannot
supply evidence. These fixture sources and amounts are controlled synthetic
inputs, never current real-world claims.

The scorer binds each research call's arguments, returned bytes and fixture
event ID to the host capture, checks source bytes and controller expectations
against the frozen fixture, requires declared successful and unavailable-source
observations, and confirms read calls preserve shopping state. Missing reads
fail even when the final prose resembles the expected answer. The manufacturer
cases require the primary lookup before secondary listings. The partial-save
case requires the confirmed current correction and its later readback, one
linked history row with observed failed verification, and unchanged grocery
records. Machine reconciliation still leaves semantic review pending.

Before activation, record the final candidate and suite digests, the exact new
and affected-baseline cases, one explicit attempt budget, permitted tools and
stop conditions. Finalize package metadata first. Source retrieval controls
must pass before a trial; neither a historical result nor a failed attempt
authorizes replay. Any identity-bearing change after the freeze requires impact
and evidence reconciliation before claiming current acceptance. Raw captures,
machine scores and semantic review working files belong under ignored root
`output/`; curate only the necessary results, identities and limits in internal
acceptance documentation. Public-source smoke runs, when authorized, are
separate evidence and never substitutes for installed synthetic behavior or
native-provider preservation.

Review every required case with the source-retrieval criteria in `rubric.md`.
The controlled twenty-project example uses final/original-base ratios and
nearest rank `ceil(p × n)`: independently recompute both quantiles, unit prices,
permit calculations and included allowances. A correct trace with incorrect
math fails semantic review. Thin or incompatible observations cannot establish
a reference-class distribution; missing jurisdiction or specification inputs
must remain explicit.

## R25 private inputs

The runtime supplies the current locator; the test controller separately holds
the expected canonical native identity. Keep both out of source, tests, fixtures,
plan text, command history, and public reports. The candidate may receive the
locator through its private task input or runtime context; keep the expected
identity, receipt key, and hidden assertions controller-side. The private prompt
and host capture may therefore contain the locator and bounded row results. Store
them only in the protected evidence directory and never publish them. Configure
these private runtime inputs only for the live gate:

- `SHOPPING_CANONICAL_GROCERY_LOCATOR`: the current runtime-selected locator.
- `SHOPPING_LIVE_CONFIG`: private JSON containing `{"schema_version": 1,
  "expected_resource": {"provider": "google-sheets", "native_id": "..."}}`.
- `SHOPPING_LIVE_RUN_ID`: a fresh opaque run nonce shared with the host invocation.
- `SHOPPING_LIVE_RECEIPT_KEY`: a private HMAC key of at least 32 characters. This
  attests to receipt integrity; it is not a provider credential.
- `--shopping-live-receipt`: a private JSON receipt path.

The controller must resolve the expected identity from the current private
authority routing, not a fixture or stale URL. Keep the config, receipt, raw host
trace, and any private evidence under ignored `output/shopping/<run-id>/` or
another private location outside the repository. Check that the path is ignored
before writing evidence. Do not put raw rows, account identifiers, credential
values, or response text into the receipt. The actual bounded content stays in
the private host trace; the receipt carries counts and digests only.

The receipt uses `personal-shopper-live-receipt/v2` and is HMAC-SHA256 signed over
all fields except `attestation`. It must include:

- `evidence_kind: "host-activation"`, the current `run_id`, the exact candidate
  and evaluator suite hashes, and a hash of the supplied runtime locator.
- The private resolved resource identity, plus a current activation record for
  `personal-shopper:personal-shopper`, its session, candidate hash, and UTC start
  and completion times.
- Actual host preflight fields for connected Google Sheets tool availability,
  read credentials, a read-only envelope, and a digest of the captured tool
  trace. The trace must identify the actual connected tool calls, not narrative
  claims. Native Sheets API calls exposed through the connected Drive provider
  are eligible. When a runtime Sheets URL must be resolved through Drive's
  `get_file_metadata`, count it only as identity resolution inside the activated
  skill: its returned file ID and Sheets MIME type must match the independently
  held expected identity. It does not replace spreadsheet metadata or content
  reads. A Drive search, file fetch, metadata lookup, or direct connector check
  outside the activated skill is not an equivalent content read.
- Ordered operation receipts for native identity resolution, spreadsheet
  metadata/routing, bounded relevant grocery-content reads, and a post-read
  state check. Every operation carries the same run and session, a host tool-call
  ID, timestamp, provider, and native resource identity. The receipt's tool-event
  count must equal the full captured host tool trace count.
- Native sheet IDs and the actual headers with the logical field-to-column map.
  A relevant content read must contain at least one row, include a stable key
  mapping that is not assumed to be column A, and stay within 1,000 cells. The
  route must resolve to a sheet discovered in the same-run native metadata. If
  the workbook has a routing table, capture its bounded header/key/role/tab read;
  otherwise bind the route to the actual grocery-content header map. Do not
  require a fixed tab name or column order. One additional bounded workbook
  context read may be recorded separately; it cannot replace routing or grocery
  content evidence.
- A read-only state check tied to the content-read event, with equal before/after
  digests and `write_count: 0`. The post-read digest must come from a second
  actual bounded native read event for the same resource, sheet, and range.

The checker rejects mismatched identity, locator, run, session, candidate,
resource, invalid signature, missing credentials, stale activation, missing
content rows, metadata-only access, incomplete native routing, unbounded reads,
any write attempt (including one the provider rejects), any conflicting resource
identity in a captured request or result, or changed post-read state. It returns
only stable issue codes; it does not echo private IDs or paths.
The HMAC establishes that the receipt was not changed after the controller
created it. The host runner must create a `host-activation` receipt only from the
actual skill activation and captured tool trace. Deterministic controls use
`evidence_kind: "deterministic-control"` and can never satisfy R25.

## B12 native preservation inputs

B12 requires Google Sheets only. The user removed Excel from this acceptance
gate on 2026-10-26; an unavailable Excel connection does not block completion.
The skill's guidance for optional Excel use is unchanged.

Use the `native-sheets-preservation` profile only with a controller-created
disposable workbook seeded with synthetic records. The live canonical grocery
workbook is never a B12 target. The controller privately stores the expected
native spreadsheet ID, sheet IDs and titles, target coordinates and before/after
values, formula, validation rule, Record Index range, and verification ranges in
the JSON supplied through `--shopping-native-config`. Keep the complete host
capture in a separate private directory supplied through
`--shopping-native-capture`; both paths must be protected and outside the source
checkout.

For the Codex CLI route, the capture must show one activated Personal Shopper
run, metadata resolution, a bounded Record Index read, matching native CellData
reads before and after the update, and exactly one authorized update to the
configured target cell. The checker binds captured provider calls to the
controller-approved test workbook and reconciles the native before/after values,
formula, validation, and history. A successful write response without saved
source readback does not pass.
The isolated native-sheets profile enables only its declared Google Drive
tools and sets `approval_mode = "approve"` only for `batch_update_spreadsheet`;
the checker verifies the captured effective config and rejects approval
overrides on other tools.
The CLI installs the frozen candidate through its local marketplace. A local,
read-only MCP resource reader exposes only that installed skill's allowlisted
Markdown files; it cannot read workbooks or call a provider. B12 requires captured
reads of `SKILL.md` and the record-management contract before the write, with
returned bytes matching both the installed file digests and current source.
The original CLI events remain unchanged. These resource reads establish loaded
instructions alongside installation/discovery evidence; they never replace
native Google Sheets observations.

### ChatGPT Work browser captures

The Work UI does not expose the full provider read-call ledger. A browser run
can still pass B12 when the private capture includes the original conversation
DOM, the uploaded candidate archive, the visible one-cell provider request and
success result, and a direct native Sheets UI review of the saved source and its
prior revision. The review must reconcile the same workbook and target, stable
key, before/after values, neighboring formula, validation rule, existing
history, and the single changed cell. The Work activity and response must show
the installed Personal Shopper skill and the bounded metadata/read/write
operations.

Run `capture_work_browser.py` to hash and check these original artifacts. The
adapter records that raw provider read events are unavailable; it does not
invent event IDs, timestamps, request fingerprints, or Codex CLI JSONL. Missing
per-call bookkeeping does not block acceptance when the visible authorized
write and direct native source review establish the same B12 assertions.
Screenshots of the Work reply or a success claim alone do not pass. If direct
native source and prior-revision observations are absent or disagree, the
browser capture remains blocked.

Unavailable Google Sheets access remains **NOT RUN** or **BLOCKED** and cannot
be replaced by fixture evidence. Excel is outside B12's required denominator.

Run the required Google Sheets preservation gate with:

```text
python -m pytest plugins/personal-shopper/tests/test_native_provider_preservation.py \
  --require-shopping-native --shopping-native-config <private-config.json> \
  --shopping-native-capture <private-capture-directory>
```

## Run and report

Run deterministic controls and the package validator separately from live
acceptance. Default offline pytest marks R25 **NOT RUN** when no private live
inputs were supplied. If any live input is supplied but incomplete or invalid,
the test fails closed. Release acceptance must run:

```text
python -m pytest plugins/personal-shopper/tests/test_live_canonical_access.py \
  --require-shopping-live --shopping-live-receipt <private-receipt.json> \
  --shopping-host-capture <private-capture-directory>
```

`--require-shopping-live` converts missing inputs or unavailable host activation
into a failing **BLOCKED / NOT ACCEPTED** gate, never a skip or fixture pass. Run
all applicable behavior groups against the frozen final candidate and preserve
each case's numerator and denominator. Use disposable native workbooks for any
separate authorized write tests; R25 is read-only.

The tracked benchmark report is a concise, redacted status summary. It separates
offline controls, activated synthetic cases, and live provider evidence, and
records blocked/not-run cases explicitly. Raw evidence and per-attempt artifacts
stay private and ignored. A successful R25 check proves only that this activated
candidate resolved and read the runtime-selected canonical workbook during that
run; it does not prove write capability or authorize workbook changes.
