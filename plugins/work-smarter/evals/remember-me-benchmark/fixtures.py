import copy
import hashlib
import json
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / 'manifest.json'
FACT_VALUES = {
    'answer_style': 'concise but complete',
    'comparison_rule': 'include trade-offs and a confidence note',
    'current_project': 'project-cobalt',
    'estimated_timeline': 'possibly by Q4 2027',
    'historical_project': 'project-amber',
}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_json(value):
    return sha256_bytes(canonical_json(value).encode('utf-8'))


def load_manifest(path=None):
    return json.loads(Path(path or MANIFEST_PATH).read_text(encoding='utf-8'))


def _synthetic_entry_prefix(index, kind):
    domains = ('routing', 'project-state', 'communication', 'source-history',
               'reference-catalog', 'workflow', 'archive')
    statuses = ('current', 'verified', 'historical', 'uncertain', 'reviewable')
    owners = ('remember-me', 'synthetic-source', 'external-record', 'system-index')
    signals = ('exact-value', 'stable-route', 'superseded-claim', 'bounded-retrieval',
               'freshness-check', 'ownership-boundary')
    return (
        f'- Synthetic {kind} record RM-BENCH-{index:06d}: '
        f'domain={domains[index % len(domains)]}; '
        f'status={statuses[index % len(statuses)]}; '
        f'owner={owners[index % len(owners)]}; '
        f'signal={signals[index % len(signals)]}; context='
    )


def _synthetic_entry(index, kind, length):
    prefix = _synthetic_entry_prefix(index, kind)
    if length < len(prefix):
        raise ValueError('synthetic entry is too short for its structured fields')
    note = ('synthetic benchmark reference context ' * (length // 38 + 2))[:length - len(prefix)]
    entry = prefix + note
    if len(entry) != length:
        raise AssertionError('synthetic entry did not reach its assigned byte size')
    return entry


def _expand_with_synthetic_entries(text, target, kind):
    """Scale a fixture with unique structured facts while preserving its headings."""
    base = text.rstrip('\n')
    current = len(base.encode('utf-8'))
    if current > target:
        raise ValueError(f'fixture base is {current} bytes, above requested size {target}')
    remaining = target - current
    if not remaining:
        return base

    entries = []
    index = 1
    while remaining:
        newline_bytes = 1
        prefix_length = len(_synthetic_entry_prefix(index, kind).encode('ascii'))
        if remaining <= newline_bytes + prefix_length:
            base = _pad_short_remainder(base, entries, remaining)
            remaining = 0
            break

        line_length = min(190, remaining - newline_bytes)
        if 0 < remaining - newline_bytes - line_length <= newline_bytes + prefix_length:
            line_length = remaining - newline_bytes
        entries.append(_synthetic_entry(index, kind, line_length))
        remaining -= newline_bytes + line_length
        index += 1

    lines = base.split('\n')
    heading_ranges = []
    headings = []
    for position, line in enumerate(lines):
        if line.startswith('##'):
            headings.append((position, len(line) - len(line.lstrip('#'))))
    for heading_index, (position, level) in enumerate(headings):
        end = len(lines)
        for next_position, next_level in headings[heading_index + 1:]:
            if next_level <= level:
                end = next_position
                break
        heading_ranges.append(end)

    insertions = {}
    if heading_ranges:
        for entry_index, entry in enumerate(entries):
            boundary = heading_ranges[entry_index % len(heading_ranges)]
            insertions.setdefault(boundary, []).append(entry)
    elif entries:
        insertions[len(lines)] = entries

    expanded = []
    for position in range(len(lines) + 1):
        expanded.extend(insertions.get(position, []))
        if position < len(lines):
            expanded.append(lines[position])
    result = '\n'.join(expanded)
    if len(result.encode('utf-8')) != target:
        raise AssertionError('structured synthetic fixture did not reach the requested UTF-8 size')
    return result


def _pad_short_remainder(base, entries, remaining):
    if entries:
        entries[-1] += (' synthetic' * (remaining // 9 + 1))[:remaining]
        return base
    return base + '.' * remaining


def evaluate_index_trigger(*, index_bytes, threshold_kib, last_audited, as_of,
                           material_changes=None, growth_baseline_bytes=None,
                           current_bytes=None):
    """Evaluate existing audit triggers with a parameterized index-size threshold."""
    if (not isinstance(threshold_kib, int) or isinstance(threshold_kib, bool)
            or threshold_kib <= 0):
        raise ValueError('threshold_kib must be a positive integer')
    try:
        review_date = date.fromisoformat(as_of)
    except (TypeError, ValueError) as error:
        raise ValueError('as_of must be an ISO date') from error

    reasons = []
    size_triggered = False
    size_status = 'unavailable'
    if isinstance(index_bytes, int) and not isinstance(index_bytes, bool) and index_bytes >= 0:
        size_status = 'measured'
        size_triggered = index_bytes > threshold_kib * 1024
        if size_triggered:
            reasons.append('index-size')

    if not isinstance(last_audited, str) or not last_audited:
        reasons.append('missing-audit-date')
    else:
        try:
            audit_date = date.fromisoformat(last_audited)
        except ValueError:
            reasons.append('invalid-audit-date')
        else:
            if (review_date - audit_date).days >= 180:
                reasons.append('audit-interval')

    if (isinstance(material_changes, int) and not isinstance(material_changes, bool)
            and material_changes >= 25):
        reasons.append('material-change-count')

    observed_bytes = index_bytes if current_bytes is None else current_bytes
    growth_status = 'unavailable'
    if (isinstance(growth_baseline_bytes, int) and not isinstance(growth_baseline_bytes, bool)
            and growth_baseline_bytes > 0 and isinstance(observed_bytes, int)
            and not isinstance(observed_bytes, bool) and observed_bytes >= 0):
        growth_status = 'measured'
        if (observed_bytes - growth_baseline_bytes) * 4 >= growth_baseline_bytes:
            reasons.append('index-growth')

    return {
        'audit_due': bool(reasons),
        'size_status': size_status,
        'size_triggered': size_triggered,
        'growth_status': growth_status,
        'reasons': reasons,
    }


def _index_text(detailed, values=None):
    values = values or FACT_VALUES
    if detailed:
        lines = [
            '# Remember Me Index',
            '',
            '## Routing and ownership',
            '### Overview',
            'Synthetic library owner: benchmark-user. Current topics are authoritative.',
            '### Identity and freshness',
            'Current project: ' + values['current_project'] + '; route: topic-identity#current-identity-and-freshness; checked 2026-10-01.',
            '### Communication preferences',
            f'Answer style: {values["answer_style"]}; source: synthetic user.',
            '### Comparison requirements',
            f'Comparison rule: {values["comparison_rule"]}; source: synthetic user.',
            'Authoritative route: topic-communication#comparison-requirements.',
            '### Confidence and uncertainty',
            f'Timeline: {values["estimated_timeline"]}; status: unconfirmed.',
            'Authoritative route: topic-identity#unconfirmed-timeline.',
            '## Authoritative topics',
            '### Communication topic',
            'Current exact wording is in topic-communication#communication-preferences; retain attribution and uncertainty.',
            '### Identity topic',
            'Current identity is in topic-identity; an older source is historical only.',
            '### Historical source',
            f'Superseded identity: {values["historical_project"]}; source-history#superseded-identity is not current.',
            '### Current pointer',
            'topic-communication, topic-identity and source-history are stable record IDs.',
            '### Audit inventory',
            'Preserve exact values, attribution, uncertainty and all three topic pointers.',
            '## Maintenance',
            '### Staged review',
            'Stage proposed changes separately and compare the protected inventory.',
            '### Recovery',
            'Retain the original index when a staged candidate loses a protected item.',
            '### Lifecycle',
            'An authorized semantic change is material; formatting alone is not.',
            '### Citation format',
            'Cite the authoritative record ID and actual Markdown heading anchor.',
        ]
    else:
        lines = [
            '## Routing and ownership',
            '### Overview',
            'Synthetic library owner: benchmark-user. Current topics are authoritative.',
            '### Identity and freshness',
            'Current identity and freshness: topic-identity#current-identity-and-freshness.',
            '### Communication preferences',
            'Communication detail: topic-communication#communication-preferences.',
            '### Comparison requirements',
            'Comparison detail: topic-communication#comparison-requirements.',
            '### Confidence and uncertainty',
            'Uncertainty detail: topic-identity#unconfirmed-timeline.',
            '## Authoritative topics',
            '### Communication topic',
            'Read topic-communication for current preference details.',
            '### Identity topic',
            'Read topic-identity for current identity and freshness.',
            '### Historical source',
            'Read source-history#superseded-identity for superseded source context only.',
            '### Current pointer',
            'topic-communication, topic-identity and source-history are stable record IDs.',
            '### Audit inventory',
            'Preserve exact values, attribution, uncertainty and all three topic pointers.',
            '## Maintenance',
            '### Staged review',
            'Stage proposed changes separately and compare the protected inventory.',
            '### Recovery',
            'Retain the original index when a staged candidate loses a protected item.',
            '### Lifecycle',
            'An authorized semantic change is material; formatting alone is not.',
            '### Citation format',
            'Cite the authoritative record ID and actual Markdown heading anchor.',
        ]
    return '\n'.join(lines) + '\n'


def _topic_text(record_id, values=None, attributions=None, identity_conflict=False):
    values = values or FACT_VALUES
    attributions = attributions or {}
    if record_id == 'topic-communication':
        return (
            '# Synthetic communication topic\n\n'
            '## Communication Preferences\n'
            f'- Answer style: {values["answer_style"]}.\n'
            f"- Attribution: {attributions.get('answer_style', 'synthetic user')}.\n\n"
            '## Comparison Requirements\n'
            f'- Exact constraint: {values["comparison_rule"]}.\n'
            f"- Attribution: {attributions.get('comparison_rule', 'synthetic user')}.\n"
        )
    if record_id == 'topic-identity':
        return (
            '# Synthetic identity topic\n\n'
            '## Current Identity and Freshness\n'
            f'- Current project: {values["current_project"]}.\n'
            f"- Attribution: {attributions.get('comparison_rule', 'synthetic user')}.\n"
            '- Last verified: 2026-10-01.\n\n'
            '## Unconfirmed Timeline\n'
            f'- Estimate: {values["estimated_timeline"]}.\n'
            '- Uncertainty: unconfirmed; do not state as a commitment.\n'
        )
    history = (
        '# Synthetic source history\n\n'
        '## Superseded Identity\n'
        f'- Historical project: {values["historical_project"]}.\n'
        '- Status: superseded by topic-identity; do not report as current.\n'
    )
    if identity_conflict:
        history += (
            '\n## Competing Current Identity Claim\n'
            f'- Current project claim: {values["historical_project"]}.\n'
            '- Source: synthetic source-history record.\n'
            '- Recorded: 2025-06-01; not re-verified after the identity topic update.\n'
            '- This older claim conflicts with the current-identity topic.\n'
        )
    return history


def _fact_inventory(values=None, attributions=None, identity_conflict=False):
    values = values or FACT_VALUES
    attributions = attributions or {}
    rows = [
        ('answer_style', values['answer_style'], 'topic-communication',
         'communication-preferences', attributions.get('answer_style', 'synthetic user'), 'none'),
        ('comparison_rule', values['comparison_rule'], 'topic-communication',
         'comparison-requirements', attributions.get('comparison_rule', 'synthetic user'), 'none'),
        ('current_project', values['current_project'], 'topic-identity',
         'current-identity-and-freshness', 'synthetic user', 'none'),
        ('estimated_timeline', values['estimated_timeline'], 'topic-identity',
         'unconfirmed-timeline', attributions.get('estimated_timeline', 'synthetic user'), 'unconfirmed'),
        ('historical_project', values['historical_project'], 'source-history',
         'superseded-identity', 'synthetic source', 'superseded'),
    ]
    if identity_conflict:
        rows.append((
            'conflicting_current_project_claim', values['historical_project'],
            'source-history', 'competing-current-identity-claim', 'synthetic source',
            'conflicting; recorded 2025-06-01, older than topic-identity verification dated 2026-10-01',
        ))
    return [dict(id=fact_id, value=value, authority_id=authority_id,
                 anchor=anchor, attribution=attribution, uncertainty=uncertainty,
                 critical=True)
            for fact_id, value, authority_id, anchor, attribution, uncertainty in rows]




STAGED_REVIEW_POLICY = {'review_date': '2026-10-18', 'review_after_days': 180}


def _staged_candidate(scenario_id, facts):
    if scenario_id not in {
        'audit-loss-control', 'audit-pointer-recovery', 'audit-authorized-review',
    }:
        return None
    inventory = [
        {key: value for key, value in fact.items() if key != 'critical'}
        for fact in facts
    ]
    pointers = [
        {'record_id': 'topic-communication', 'anchor': 'communication-preferences'},
        {'record_id': 'topic-identity', 'anchor': 'current-identity-and-freshness'},
        {'record_id': 'source-history', 'anchor': 'superseded-identity'},
    ]
    last_audit = '2026-10-01'
    if scenario_id == 'audit-loss-control':
        inventory = [item for item in inventory if item['id'] != 'comparison_rule']
    elif scenario_id == 'audit-pointer-recovery':
        pointers[0]['anchor'] = 'stale-anchor'
    else:
        last_audit = '2025-01-01'
    return json.dumps({
        'candidate_id': 'staged-candidate-v1',
        'fact_inventory': inventory,
        'pointer_references': pointers,
        'last_verified_audit': last_audit,
    }, sort_keys=True, ensure_ascii=False, indent=2) + '\n'


def _task_for_family(family):
    return {
        'index-scaling': (
            'Use the synthetic records to report the current communication and identity facts, '
            'their source and uncertainty, and distinguish any superseded history.'),
        'topic-scaling': (
            'Retrieve the same exact synthetic facts from their authoritative topics and report '
            'attribution, freshness and uncertainty.'),
        'multi-source-identity-freshness': (
            'Resolve synthetic facts across current topics and history. State which identity is '
            'current, cite its source and freshness, and distinguish superseded content.'),
        'evolution': (
            'Report the latest synthetic correction with its exact value, attribution and '
            'uncertainty; identify any superseded value without treating it as current.'),
        'staged-audit-recovery': (
            'Review a staged synthetic memory candidate against the exact protected facts and '
            'stable topic pointers. Report any lost item or unresolved route.'),
        'authorized-maintenance': (
            'Audit the source-shaped synthetic index and authoritative records. If the declared '
            'size trigger is due, prepare a shorter routing index, stage it beside the original, '
            'compare its exact pointers and protected facts, and wait for case-specific approval '
            'before promotion. Read back the promoted version and report any rejected or partial '
            'outcome.'),
        'closeout-maintenance-sequence': (
            'Complete the synthetic read, save, readback and audit sequence before maintenance. '
            'Preserve all protected facts, unrelated content and authoritative pointers. If the '
            'declared index-size trigger is due, prepare and stage a shorter routing index beside '
            'the recoverable original, then stop and wait for a separate controller decision. '
            'Continue only in the same session after the controller sends an exact approval or '
            'decline; promote only the approved staged digest, then read back the promoted index '
            'and report the final facts and maintenance outcome.'),
        'amortized-read-save-audit': (
            'Complete the synthetic read, update and audit sequence while preserving current '
            'facts, unrelated content and all authoritative pointers.'),
    }[family]


def _retrieval_instruction(strategy):
    if strategy == 'full':
        return ('Use full-record reads for source records. Do not use heading maps or section '
                'reads; if a full read is incomplete or unavailable, report the limitation.')
    if strategy == 'headings':
        return ('Use a heading map and read the sections that contain relevant evidence. Expand '
                'to additional sections or a full-record read whenever evidence is incomplete.')
    raise ValueError(f'unsupported retrieval strategy: {strategy}')


def _update_authorization(scenario_id):
    if scenario_id not in ('amortized-update-audit', 'closeout-sequence-40k'):
        return None
    return {
        'op': 'save_append',
        'record_id': 'topic-communication',
        'expected_version': 'synthetic-v1',
        'new_version': 'synthetic-v2',
        'append_text': (
            '\n## Synthetic Update Log\n'
            '- Meeting format: plain-text weekly digest (synthetic user).\n'
        ),
    }

def build_trial(scenario_id, candidate_id, manifest=None, trigger_threshold_kib=None,
                material_changes=0, growth_baseline_bytes=None):
    manifest = manifest or load_manifest()
    scenarios = {entry['id']: entry for entry in manifest['development_scenarios']}
    scenario = scenarios[scenario_id]
    candidates = {entry['id']: entry for entry in manifest['candidate_matrix']}
    candidate = candidates[candidate_id]
    family = scenario['family']
    if trigger_threshold_kib is None:
        trigger_threshold_kib = manifest['index_trigger_treatments_kib'][0]
    if (not isinstance(trigger_threshold_kib, int)
            or isinstance(trigger_threshold_kib, bool)
            or trigger_threshold_kib not in manifest['index_trigger_treatments_kib']):
        raise ValueError('trigger threshold is outside the declared treatment set')
    values = dict(FACT_VALUES)
    attributions = {}
    if scenario_id == 'evolution-correction':
        values['answer_style'] = 'short first, expand on request'
    elif scenario_id == 'evolution-uncertainty':
        values['estimated_timeline'] = 'possibly by Q1 2028'
    elif scenario_id == 'evolution-attribution':
        attributions['answer_style'] = 'synthetic owner confirmation'
    detailed = candidate['index_representation'] == 'detailed'
    compact_base_bytes = len(_index_text(False, values).encode('utf-8'))
    index_size = (scenario['index_bytes'] if detailed else
                  max(compact_base_bytes, scenario['index_bytes'] // 3))
    index = _expand_with_synthetic_entries(_index_text(detailed, values), index_size, 'index')
    if scenario_id == 'stale-pointer':
        index = index.replace('topic-communication#communication-preferences',
                              'topic-communication#stale-anchor')
        index = _expand_with_synthetic_entries(index, index_size, 'index')
    topic_target = scenario['topic_bytes']
    communication_target = (2428 if family == 'index-scaling' else topic_target)
    identity_target = max(1024, min(4096, topic_target // 3))
    history_target = 1024

    records = {
        'index': {
            'id': 'index', 'path': 'remember-me-index.md', 'version': 'synthetic-v1',
            'kind': 'index', 'content': index,
            'last_verified_audit': ('2025-01-01' if scenario_id == 'audit-authorized-review'
                                    else '2026-10-01'),
        },
        'topic-communication': {
            'id': 'topic-communication', 'path': 'topics/communication.md',
            'version': 'synthetic-v1', 'kind': 'topic',
            'content': _expand_with_synthetic_entries(
                _topic_text('topic-communication', values, attributions), communication_target, 'topic'),
        },
        'topic-identity': {
            'id': 'topic-identity', 'path': 'topics/identity.md',
            'version': 'synthetic-v1', 'kind': 'topic',
            'content': _expand_with_synthetic_entries(
                _topic_text('topic-identity', values, attributions), identity_target, 'topic'),
        },
        'source-history': {
            'id': 'source-history', 'path': 'sources/history.md',
            'version': 'synthetic-v1', 'kind': 'source',
            'content': _expand_with_synthetic_entries(
                _topic_text('source-history', values, attributions), history_target, 'topic'),
        },
    }
    update_authorization = _update_authorization(scenario_id)
    identity_conflict = scenario_id == 'identity-conflict'
    if identity_conflict:
        records['source-history']['content'] = _expand_with_synthetic_entries(
            _topic_text('source-history', values, attributions, identity_conflict=True),
            history_target, 'topic')
    facts = _fact_inventory(values, attributions, identity_conflict=identity_conflict)
    staged_candidate = _staged_candidate(scenario_id, facts)
    if staged_candidate is not None:
        records['staged-candidate'] = {
            'id': 'staged-candidate',
            'path': 'staging/staged-candidate.json',
            'version': 'candidate-v1',
            'kind': 'candidate',
            'content': staged_candidate,
        }
    audit_required = (family in (
        'staged-audit-recovery', 'authorized-maintenance',
        'closeout-maintenance-sequence')
        or scenario_id == 'amortized-update-audit')
    tools = list(manifest['common_tool_envelope'])
    tools.extend(manifest.get('scenario_tool_envelopes', {}).get(scenario_id, []))
    if (update_authorization
            and update_authorization['op'] not in tools):
        raise ValueError('update scenario is missing its declared save tool envelope')
    maintenance_trigger = None
    maintenance_authorization = None
    if family in ('authorized-maintenance', 'closeout-maintenance-sequence'):
        index_bytes = len(records['index']['content'].encode('utf-8'))
        if growth_baseline_bytes is None:
            growth_baseline_bytes = index_bytes
        maintenance_trigger = evaluate_index_trigger(
            index_bytes=index_bytes,
            threshold_kib=trigger_threshold_kib,
            last_audited=records['index']['last_verified_audit'],
            as_of='2026-10-18',
            material_changes=material_changes,
            growth_baseline_bytes=growth_baseline_bytes,
            current_bytes=index_bytes,
        )
        maintenance_trigger['threshold_kib'] = trigger_threshold_kib
        maintenance_trigger['index_bytes'] = index_bytes
        maintenance_trigger['last_audited'] = records['index']['last_verified_audit']
        maintenance_trigger['as_of'] = '2026-10-18'
        maintenance_trigger['material_changes'] = material_changes
        maintenance_trigger['growth_baseline_bytes'] = growth_baseline_bytes
        maintenance_trigger['current_bytes'] = index_bytes
        if maintenance_trigger['audit_due']:
            maintenance_authorization = {
                'record_id': 'index',
                'expected_version': 'synthetic-v1',
                'new_version': 'synthetic-v2',
                'completed_date': '2026-10-18',
            }
            tools.extend(manifest['conditional_tool_envelopes'][scenario_id])
    task = _task_for_family(family)
    if scenario_id == 'multi-source-split':
        task = (
            'Retrieve the synthetic facts split across the communication, identity and history '
            'records. Cite each fact’s authority and freshness, and distinguish current facts '
            'from superseded history.')
    elif identity_conflict:
        task = (
            'Resolve the competing current-project claims in the identity and source-history '
            'records. Compare their authorities and verification dates, report the current claim, '
            'and identify the older conflicting claim as not current.')
    elif scenario_id == 'audit-loss-control':
        task = (
            'Review the staged candidate record against the authoritative records. Identify any '
            'protected fact it omits, and recommend whether to accept or reject the candidate.')
    elif scenario_id == 'audit-pointer-recovery':
        task = (
            'Review the staged candidate record against the authoritative records. Identify any '
            'unresolved pointer and give the verified route that would recover it.')
    elif scenario_id == 'audit-authorized-review':
        task = (
            'Review the staged candidate using the supplied review date and interval. State '
            'whether review is due. No write approval has been given; make no maintenance write.')
    hidden_variant_ids = {
        'multi-source-split', 'identity-conflict', 'audit-loss-control',
        'audit-pointer-recovery', 'audit-authorized-review',
    }
    public = {
        'schema_version': 1,
        'scenario_id': family if scenario_id in hidden_variant_ids else scenario_id,
        'task': task,
        'retrieval_strategy': candidate['retrieval_strategy'],
        'retrieval_instruction': _retrieval_instruction(candidate['retrieval_strategy']),
        'available_records': [
            {key: record[key] for key in ('id', 'path', 'version', 'kind')}
            for record in records.values()
        ],
        'tools': tools,
        'tool_contract': (
            'Full reads return an entire record. Heading maps return actual Markdown '
            'headings, anchors, byte ranges, record ID and version. Section reads return exactly '
            'the requested byte slice. Reads are charged by returned bytes; save request and '
            'append bytes are measured separately. Every operation is traced; '
            'expand or use a full read when evidence is incomplete.'
        ),
    }
    if staged_candidate is not None:
        public['staged_review_policy'] = dict(STAGED_REVIEW_POLICY)
        public['task'] += (
            ' Read staged-candidate and report audit_review with its candidate_record_id, '
            'disposition, lost_items, unresolved_pointers, recovered_pointers, review_due, '
            'write_authorized, maintenance_action, and trace evidence for the candidate read. '
            'No staged-review scenario authorizes a maintenance write.')
    if family in ('amortized-read-save-audit', 'closeout-maintenance-sequence'):
        public['task_sequence'] = [
            {'phase': 'read', 'task': 'Retrieve the current communication and identity facts.'},
            {'phase': 'update', 'task': 'Apply only the explicitly authorized synthetic update and read it back.'},
            {'phase': 'audit', 'task': 'Compare the current protected inventory and pointers after the update.'},
        ]
        if family == 'closeout-maintenance-sequence':
            public['task_sequence'].append({
                'phase': 'maintenance',
                'task': 'Stage a shorter index only when the trigger is due, then wait for the controller decision in the same session.',
            })
    if update_authorization:
        public['authorized_synthetic_update'] = {
            key: update_authorization[key]
            for key in ('op', 'record_id', 'expected_version', 'new_version', 'append_text')
        }
        public['task'] += (
            ' The controller authorizes one save_append to record '
            f"{update_authorization['record_id']} at version "
            f"{update_authorization['expected_version']}; append exactly this text:\n"
            f"{update_authorization['append_text']} Read the saved record back, preserve every "
            'other record and protected fact, and resolve every stable topic pointer in the index. '
            'Return `protected_inventory` in your answer with each item’s exact value, '
            '`authority_id`, heading anchor, attribution and uncertainty, plus trace evidence '
            'from a successful post-save read of every authority record. Do not include '
            'controller-only item IDs; items are matched by authority and heading anchor.'
        )
        public['tool_contract'] += (
            ' For this scenario only, save_append may append the exact authorized text to the '
            'specified record and expected version once; read that record after saving to verify it.'
        )
    if maintenance_trigger is not None:
        public['maintenance_trigger'] = copy.deepcopy(maintenance_trigger)
        if family == 'closeout-maintenance-sequence':
            public['task'] += (
                ' Follow the supplied trigger evidence. Stage a candidate only when audit_due is '
                'true. After staging, stop and wait for the controller to continue this exact '
                'session with a separate decision; there is no approval payload in this packet. '
                'If approved, promote only the exact staged candidate and read back the resulting '
                'index version and audit date.'
            )
        else:
            public['task'] += (
                ' Follow the supplied maintenance trigger evidence. Stage a candidate only when '
                'audit_due is true, request its separate case-specific approval, and promote only the '
                'exact approved candidate. Verify any resulting index version and audit metadata by '
                'reading it back.'
            )
        if maintenance_authorization:
            public['maintenance_scope'] = copy.deepcopy(maintenance_authorization)
        public['tool_contract'] += (
            ' Staging records a recoverable candidate but leaves canonical state unchanged. '
            'Promotion requires an out-of-band, case-specific approval matching the exact '
            'staged digest and the current record version.'
        )
    gold = {
        'scenario_id': scenario_id,
        'required_facts': facts,
        'protected_inventory': copy.deepcopy(facts),
        'pointer_targets': ['topic-communication', 'topic-identity', 'source-history'],
        'audit_required': audit_required,
        'update_authorization': copy.deepcopy(update_authorization),
        'maintenance_authorization': copy.deepcopy(maintenance_authorization),
        'maintenance_trigger': copy.deepcopy(maintenance_trigger),
        'recovery_state_sha256': digest_json(records),
        'staged_review': ({
            'record_id': 'staged-candidate',
            'review_policy': dict(STAGED_REVIEW_POLICY),
            'write_authorized': False,
        } if staged_candidate is not None else None),
        'scenario_control': {
            'stale_anchor': 'topic-communication#stale-anchor'
            if scenario_id == 'stale-pointer' else None,
            'evolution_case': scenario_id if family == 'evolution' else None,
            'stale_anchor_target': 'topic-communication'
            if scenario_id == 'stale-pointer' else None,
            'audit_case': scenario_id if audit_required else None,
        },
    }
    calibration_digest = digest_json(manifest['calibration'])
    fixture_identity = digest_json({
        'suite_id': manifest['suite_id'],
        'suite_version': manifest['suite_version'],
        'scenario': scenario,
        'candidate': candidate,
        'tool_envelope': tools,
        'update_authorization': update_authorization,
        'maintenance_authorization': maintenance_authorization,
        'maintenance_trigger': maintenance_trigger,
        'trigger_threshold_kib': trigger_threshold_kib if maintenance_trigger else None,
        'calibration_digest': calibration_digest,
        'records': {key: sha256_bytes(value['content'].encode('utf-8'))
                    for key, value in records.items()},
    })
    gold_identity = digest_json({'fixture_identity': fixture_identity, 'gold': gold})
    return {
        'public': public,
        'gold': gold,
        'records': records,
        'candidate': dict(candidate),
        'fixture_identity': fixture_identity,
        'gold_identity': gold_identity,
        'calibration_digest': calibration_digest,
    }
