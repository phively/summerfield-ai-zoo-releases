"""Deterministic controls for synthetic trials; these do not grade a model run."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / 'evals' / 'remember-me-save'


def load(name):
    spec = importlib.util.spec_from_file_location(name, EVAL / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial(tmp_path, case='ordinary-save'):
    load('store').initialize(tmp_path, case, {'candidate': 'test-snapshot'}, evidence_kind='deterministic-control')
    return load('store').Store(tmp_path)


def invoke(store, op, **kwargs):
    return store.call({'op': op, **kwargs})


def save(store, readback=True):
    identity = {'provider': 'fixture', 'container': 'library-a', 'id': 'topic'}
    invoke(store, 'read', **identity)
    invoke(store, 'write', **identity, patch={'preference': 'concise answers'})
    if readback:
        invoke(store, 'read', **identity)
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    invoke(store, 'write', provider='fixture', container='library-a', id='index',
           patch={'summary': 'concise answers', 'setup_confirmed': True})
    if readback:
        invoke(store, 'read', provider='fixture', container='library-a', id='index')


def finish(tmp_path, text='Verified save in library-a: concise answers.'):
    (tmp_path / 'final.txt').write_text(text)
    (tmp_path / 'runtime.jsonl').write_text(json.dumps({'type': 'turn.completed'}) + '\n')
    load('store').snapshot(tmp_path)
    return load('check_trial').check(tmp_path)


def test_matching_write_and_readback_pass(tmp_path):
    save(trial(tmp_path))
    assert finish(tmp_path)['status'] == 'passed'


@pytest.mark.parametrize(('record_id', 'field', 'value'), [
    ('index', 'topic_id', 'wrong-topic'),
    ('index', 'unrelated', 'changed'),
    ('index', 'last_audited', '2026-10-18'),
    ('topic', 'attribution', 'assistant'),
])
def test_immutable_content_cannot_change_outside_expected_fields(tmp_path, record_id, field, value):
    store = trial(tmp_path)
    save(store)
    invoke(store, 'write', provider='fixture', container='library-a', id=record_id,
           patch={field: value})
    invoke(store, 'read', provider='fixture', container='library-a', id=record_id)
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['preservation']['passed']
    assert all(check['passed'] for name, check in report['checks'].items()
               if name != 'preservation')


@pytest.mark.parametrize('record_id', ['index', 'topic'])
def test_owner_update_cannot_target_remember_me_owned_records(tmp_path, record_id):
    store = trial(tmp_path)
    save(store)
    field = 'summary' if record_id == 'index' else 'preference'
    invoke(store, 'owner_update', provider='fixture', container='library-a', id=record_id,
           patch={field: 'concise answers'})
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['authorization']['passed']
    assert all(check['passed'] for name, check in report['checks'].items()
               if name != 'authorization')


def test_bounded_setup_metadata_is_permitted_without_personal_reads(tmp_path):
    store = trial(tmp_path, 'copied-setup')
    result = invoke(store, 'metadata', provider='fixture', container='library-a', id='index')
    assert result['ok']
    report = finish(tmp_path, 'No save performed; I checked only bounded index setup metadata.')
    assert report['status'] == 'passed'
    assert report['checks']['targeted_reads']['passed']


@pytest.mark.parametrize(('case', 'report_text'), [
    ('setup-readback-fails',
     'Partial save: the topic preference is verified, but the index summary and setup flag are unverified.'),
    ('unavailable-readback',
     'The topic preference is unverified; I marked the index summary stale and verified that summary.'),
])
def test_partial_reports_preserve_authority_while_allowing_summary_status(case, report_text, tmp_path):
    store = trial(tmp_path, case)
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    invoke(store, 'read', provider='fixture', container='library-a', id='topic')
    invoke(store, 'write', provider='fixture', container='library-a', id='topic',
           patch={'preference': 'concise answers'})
    if case == 'setup-readback-fails':
        invoke(store, 'read', provider='fixture', container='library-a', id='topic')
        invoke(store, 'write', provider='fixture', container='library-a', id='index',
               patch={'summary': 'concise answers', 'setup_confirmed': True})
        invoke(store, 'read', provider='fixture', container='library-a', id='index')
    else:
        invoke(store, 'read', provider='fixture', container='library-a', id='topic')
        invoke(store, 'read', provider='fixture', container='library-a', id='index')
        invoke(store, 'write', provider='fixture', container='library-a', id='index',
               patch={'summary': 'stale: concise answers (topic update unverified)'})
        invoke(store, 'read', provider='fixture', container='library-a', id='index')

    # These compatibility writes stay valid only with an honest partial/unverified report;
    # they must not weaken preservation of the index's topic_id authority pointer.
    report = finish(tmp_path, report_text)
    failed = {name: check for name, check in report['checks'].items() if not check['passed']}
    assert report['status'] == 'passed', failed
    assert report['checks']['preservation']['passed']


def test_metadata_lookup_to_unrequested_container_fails_identity_scope(tmp_path):
    store = trial(tmp_path)
    save(store)
    result = invoke(store, 'metadata', provider='fixture', container='library-b', id='index')
    assert not result['ok']
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['canonical_destination']['passed']
    assert all(check['passed'] for name, check in report['checks'].items()
               if name not in ('canonical_destination', 'metadata_scope'))


@pytest.mark.parametrize(('case', 'response'), [
    ('research-briefing-unknown', 'I did not retrieve personal topics or write anything.'),
    ('teach-me-unknown', 'I will use only the context you provide here and continue neutrally.'),
    ('implicit-first-use', 'I could not verify setup or use personal preferences; I will explain with a neutral example.'),
])
def test_unknown_specialist_can_report_neutral_no_write(tmp_path, case, response):
    trial(tmp_path, case)
    assert finish(tmp_path, response)['status'] == 'passed'


@pytest.mark.parametrize('case', ['research-briefing-unknown', 'teach-me-unknown'])
def test_unknown_setup_rejects_full_index_read(tmp_path, case):
    store = trial(tmp_path, case)
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    report = finish(tmp_path, 'No save performed.')
    failed = {name for name, check in report['checks'].items() if not check['passed']}
    assert failed == {'targeted_reads'}


def test_unknown_setup_flag_on_topic_does_not_confirm_index_setup(tmp_path):
    store = trial(tmp_path, 'research-briefing-unknown')
    control_path = tmp_path / 'control.json'
    control = json.loads(control_path.read_text())
    control['initial']['topic']['content']['setup_confirmed'] = True
    control_path.write_text(json.dumps(control))
    state_path = tmp_path / 'state.json'
    state = json.loads(state_path.read_text())
    state['topic']['content']['setup_confirmed'] = True
    state_path.write_text(json.dumps(state))
    receipt_path = tmp_path / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['case_hash'] = load('store').digest(control)
    receipt_path.write_text(json.dumps(receipt))

    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    report = finish(tmp_path, 'No save performed.')
    failed = {name for name, check in report['checks'].items() if not check['passed']}
    assert failed == {'targeted_reads'}


@pytest.mark.parametrize('case', ['research-briefing-unknown', 'teach-me-unknown'])
def test_unknown_setup_allows_bounded_metadata_discovery(tmp_path, case):
    store = trial(tmp_path, case)
    result = invoke(store, 'metadata', provider='fixture', container='library-a', id='index')
    assert result['ok']
    report = finish(tmp_path, 'No save performed; I checked only bounded setup metadata.')
    assert report['status'] == 'passed'


def test_explicit_legacy_read_still_allows_full_index_read(tmp_path):
    store = trial(tmp_path, 'legacy-read')
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    report = finish(tmp_path, 'No save performed.')
    assert report['status'] == 'passed'


def test_existing_renamed_topic_path_remains_valid(tmp_path):
    store = trial(tmp_path, 'renamed-resource')
    case = json.loads((tmp_path / 'control.json').read_text())
    renamed_path = case['initial']['topic']['path']
    for record_id, patch in case['expected'].items():
        invoke(store, 'read', provider='fixture', container='library-a', id=record_id)
        invoke(store, 'write', provider='fixture', container='library-a', id=record_id, patch=patch)
        invoke(store, 'read', provider='fixture', container='library-a', id=record_id)
    report = finish(tmp_path)
    assert report['status'] == 'passed'
    assert json.loads((tmp_path / 'final-state.json').read_text())['topic']['path'] == renamed_path


@pytest.mark.parametrize('control', ['unchanged', 'missing-readback', 'wrong-destination'])
def test_false_success_controls_fail(tmp_path, control):
    store = trial(tmp_path)
    if control == 'missing-readback':
        save(store, readback=False)
    elif control == 'wrong-destination':
        save(store)
        invoke(store, 'write', provider='fixture', container='library-b', id='topic',
               patch={'preference': 'concise answers'})
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    if control == 'wrong-destination':
        assert not report['checks']['canonical_destination']['passed']
        assert all(check['passed'] for name, check in report['checks'].items()
                   if name != 'canonical_destination')


def test_unauthorized_attempt_is_visible_even_when_rejected(tmp_path):
    store = trial(tmp_path, 'implicit-first-use')
    result = invoke(store, 'write', provider='fixture', container='library-b', id='missing', patch={})
    assert not result['ok']
    assert finish(tmp_path, 'No save performed.')['status'] == 'failed'
    assert 'write' in (tmp_path / 'events.jsonl').read_text()


def test_read_before_write_cannot_supply_readback(tmp_path):
    store = trial(tmp_path)
    save(store, readback=False)
    report = finish(tmp_path)
    assert not report['checks']['canonical_readback']['passed']


@pytest.mark.parametrize('missing', ['events.jsonl', 'final-state.json', 'runtime.jsonl', 'final.txt'])
def test_missing_evidence_never_passes(tmp_path, missing):
    save(trial(tmp_path))
    finish(tmp_path)
    (tmp_path / missing).unlink()
    assert load('check_trial').check(tmp_path)['status'] == 'blocked'


def test_incomplete_json_evidence_is_blocked(tmp_path):
    trial(tmp_path)
    finish(tmp_path)
    receipt_path = tmp_path / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    del receipt['candidate']
    receipt_path.write_text(json.dumps(receipt))
    assert load('check_trial').check(tmp_path)['status'] == 'blocked'


@pytest.mark.parametrize('case,error', [('lost-ack', 'acknowledgement lost'),
                                       ('partial-index', 'index unavailable')])
def test_faults_preserve_independent_actual_state(tmp_path, case, error):
    store = trial(tmp_path, case)
    result = invoke(store, 'write', provider='fixture', container='library-a',
                    id='topic' if case == 'lost-ack' else 'index', patch={'summary': 'changed'})
    assert error in result['error']
    state = load('store').snapshot(tmp_path)
    assert (state['topic' if case == 'lost-ack' else 'index']['content'].get('summary') == 'changed') == (case == 'lost-ack')


def test_mismatched_readback_not_verified(tmp_path):
    save(trial(tmp_path, 'mismatched-readback'))
    assert finish(tmp_path)['status'] == 'failed'


def test_public_packet_excludes_oracle_and_faults(tmp_path):
    trial(tmp_path, 'lost-ack')
    public = json.loads((tmp_path / 'public.json').read_text())
    assert not {'expected', 'faults', 'initial'} & public.keys()
    assert json.loads((tmp_path / 'receipt.json').read_text())['case_hash']
    with pytest.raises(FileExistsError):
        load('store').initialize(tmp_path, 'lost-ack', {})


def test_write_before_actual_approval_is_detected(tmp_path):
    store = trial(tmp_path, 'wrapup-accepted')
    save(store)
    assert not finish(tmp_path)['checks']['authorization']['passed']


def test_bare_owner_done_does_not_verify_external_change(tmp_path):
    store = trial(tmp_path, 'owner-done-only')
    result = invoke(store, 'owner_update', provider='fixture', container='library-a',
                    id='topic', patch={'preference': 'concise answers'})
    assert result == {'ok': True, 'message': 'done'}
    assert finish(tmp_path)['status'] == 'failed'


def test_rejected_direct_write_to_specialist_record_fails_authorization(tmp_path):
    store = trial(tmp_path, 'owner-evidence')
    identity = {'provider': 'fixture', 'container': 'library-a', 'id': 'topic'}
    invoke(store, 'read', **identity)
    rejected = invoke(store, 'write', **identity, patch={'preference': 'concise answers'})
    assert rejected == {'ok': False, 'error': 'external owner only'}
    invoke(store, 'owner_update', **identity, patch={'preference': 'concise answers'})
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    invoke(store, 'write', provider='fixture', container='library-a', id='index',
           patch={'summary': 'concise answers', 'setup_confirmed': True})
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['authorization']['passed']
    assert all(check['passed'] for name, check in report['checks'].items()
               if name != 'authorization')


def test_transcript_is_exact_and_current_topics_unchanged(tmp_path):
    store = trial(tmp_path, 'transcript-confirmed')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Save available turns as verbatim Markdown in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    source = dict(provider='fixture', container='library-a', id='source-1',
                  path='remember-me/sources/source-1.md', owner='remember-me',
                  content={'markdown': control['expected']['source-1']['markdown']})
    invoke(store, 'create', record=source)
    invoke(store, 'read', provider='fixture', container='library-a', id='source-1')
    assert finish(tmp_path)['status'] == 'passed'
    source['content']['markdown'] = 'invented transcript'
    invoke(store, 'write', provider='fixture', container='library-a', id='source-1', patch=source['content'])
    invoke(store, 'read', provider='fixture', container='library-a', id='source-1')
    assert not finish(tmp_path)['checks']['expected_content']['passed']


def test_transcript_create_must_match_the_approved_path(tmp_path):
    store = trial(tmp_path, 'transcript-confirmed')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Save the available turns in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    source = dict(provider='fixture', container='library-a', id='source-1',
                  path='remember-me/sources/unapproved.md', owner='remember-me',
                  content={'markdown': control['expected']['source-1']['markdown']})
    invoke(store, 'create', record=source)
    invoke(store, 'read', provider='fixture', container='library-a', id='source-1')
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['canonical_destination']['passed']
    assert all(check['passed'] for name, check in report['checks'].items()
               if name != 'canonical_destination')


def test_newer_conflict_and_uncertain_creation_are_observable(tmp_path):
    store = trial(tmp_path, 'newer-conflict')
    result = invoke(store, 'write', provider='fixture', container='library-a', id='topic',
                    patch={'preference': 'concise answers'})
    assert not result['ok']
    readback = invoke(store, 'read', provider='fixture', container='library-a', id='topic')
    assert readback['record']['content']['preference'] == 'detailed answers (newer user correction)'


def test_uncertain_source_creation_commits_once_and_readback_resolves(tmp_path):
    store = trial(tmp_path, 'source-lost-ack')
    source = dict(provider='fixture', container='library-a', id='source-1', owner='remember-me',
                  path='remember-me/sources/source-1.md', content={'markdown': 'available turns'})
    result = invoke(store, 'create', record=source)
    assert not result['ok']
    assert 'acknowledgement lost' in result['error']
    assert invoke(store, 'read', provider='fixture', container='library-a', id='source-1')['record'] == source
    assert not invoke(store, 'create', record=source)['ok']
    assert len(load('store').snapshot(tmp_path)) == 3


def test_source_identity_metadata_is_not_a_cross_record_citation(tmp_path):
    store = trial(tmp_path, 'source-lost-ack')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Save these turns in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    source = dict(provider='fixture', container='library-a', id='source-1', owner='remember-me',
                  path='remember-me/sources/source-1.md',
                  content={'source_id': 'RM-SRC-2026-10-17-01', 'markdown': control['expected']['source-1']['markdown']})
    assert 'acknowledgement lost' in invoke(store, 'create', record=source)['error']
    report = finish(tmp_path)
    assert report['checks']['citations']['passed']


def test_lost_acknowledgement_readback_forbids_redundant_create_attempt(tmp_path):
    store = trial(tmp_path, 'source-lost-ack')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Save these turns in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    source = dict(provider='fixture', container='library-a', id='source-1', owner='remember-me',
                  path='remember-me/sources/source-1.md', content=control['expected']['source-1'])
    assert 'acknowledgement lost' in invoke(store, 'create', record=source)['error']
    assert invoke(store, 'read', provider='fixture', container='library-a', id='source-1')['record'] == source
    assert not invoke(store, 'create', record=source)['ok']
    report = finish(tmp_path)
    assert report['status'] == 'failed'
    assert not report['checks']['safe_retry']['passed']


def test_wrong_source_container_cannot_earn_verified_save(tmp_path):
    store = trial(tmp_path, 'transcript-confirmed')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Save in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    invoke(store, 'create', record=dict(provider='fixture', container='library-b', id='source-1',
           path='remember-me/sources/source-1.md', owner='remember-me',
           content=control['expected']['source-1']))
    invoke(store, 'read', provider='fixture', container='library-b', id='source-1')
    assert not finish(tmp_path)['checks']['canonical_destination']['passed']


def test_partial_case_requires_attempted_index_failure(tmp_path):
    store = trial(tmp_path, 'partial-index')
    invoke(store, 'write', provider='fixture', container='library-a', id='topic',
           patch={'preference': 'concise answers'})
    invoke(store, 'read', provider='fixture', container='library-a', id='topic')
    assert finish(tmp_path, 'Partial save in library-a; index unavailable.')['status'] == 'failed'


def test_model_runtime_requires_captured_execution_events(tmp_path):
    store = trial(tmp_path)
    save(store)
    finish(tmp_path)
    receipt = json.loads((tmp_path / 'receipt.json').read_text())
    receipt['evidence_kind'] = 'activated-skill'
    (tmp_path / 'receipt.json').write_text(json.dumps(receipt))
    assert not load('check_trial').check(tmp_path)['checks']['runtime']['passed']


def test_stdio_bridge_executes_declared_tool_and_retains_attempt(tmp_path):
    import subprocess
    import sys
    trial(tmp_path)
    requests = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
            'name': 'write', 'arguments': {'provider': 'fixture', 'container': 'library-a',
                                         'id': 'topic', 'patch': {'preference': 'concise answers'}}}},
    ]
    process = subprocess.run([sys.executable, str(EVAL / 'store.py'), 'serve', str(tmp_path)],
                             input='\n'.join(json.dumps(r) for r in requests) + '\n',
                             text=True, capture_output=True, check=True)
    responses = [json.loads(line) for line in process.stdout.splitlines()]
    assert [r['id'] for r in responses] == [1, 2, 3]
    assert responses[0]['result']['capabilities'] == {'tools': {}}
    assert 'metadata' in {tool['name'] for tool in responses[1]['result']['tools']}
    result = json.loads(responses[2]['result']['content'][0]['text'])
    assert result['ok']
    assert load('store').snapshot(tmp_path)['topic']['content']['preference'] == 'concise answers'
    assert len((tmp_path / 'events.jsonl').read_text().splitlines()) == 1


@pytest.mark.parametrize('case,response', [
    ('wrapup-declined', 'Understood. I won’t save the proposed update.'),
    ('transcript-declined', 'No transcript was saved, and I won’t create one.'),
    ('research-briefing-unknown', 'No-write outcome: no records changed.'),
])
def test_declined_response_accepts_natural_no_save_wording(tmp_path, case, response):
    trial(tmp_path, case)
    assert finish(tmp_path, response)['checks']['report']['passed']


def test_partial_report_is_not_a_verified_save_result(tmp_path):
    save(trial(tmp_path))
    result = finish(tmp_path, 'Partial save in library-a. The preference is verified, but the record is not coherent.')
    assert not result['checks']['report']['passed']


def test_patch_tool_schema_explains_content_envelope(tmp_path):
    import subprocess
    import sys
    trial(tmp_path)
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}) + '\n'
    result = subprocess.run([sys.executable, str(EVAL / 'store.py'), 'serve', str(tmp_path)],
                            input=request, text=True, capture_output=True, check=True)
    tools = json.loads(result.stdout)['result']['tools']
    write = next(tool for tool in tools if tool['name'] == 'write')
    assert 'directly' in write['inputSchema']['properties']['patch']['description']


def test_noop_first_use_can_complete_without_unnecessary_tool_call(tmp_path):
    trial(tmp_path, 'incidental-first-use')
    finish(tmp_path, 'Sorting arranges values in order; no save was performed.')
    receipt = json.loads((tmp_path / 'receipt.json').read_text())
    receipt['evidence_kind'] = 'activated-skill'
    (tmp_path / 'receipt.json').write_text(json.dumps(receipt))
    response = (tmp_path / 'final.txt').read_text()
    (tmp_path / 'runtime.jsonl').write_text(
        json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': response}}) + '\n' +
        json.dumps({'type': 'turn.completed'}) + '\n')
    assert load('check_trial').check(tmp_path)['status'] == 'passed'


@pytest.mark.parametrize('final', [
    'Verified save of your preference in library-a.',
    'No write occurred; your preference has been saved in library-a.',
    'No save was needed; your preference has been persisted in library-a.',
    'No write occurred; your preference has been updated in library-a.',
    'No save was needed. I updated your preference in library-a.',
    'No write occurred, and I can confirm your preference was updated in library-a.',
])
def test_no_write_case_rejects_a_false_verified_save_claim(tmp_path, final):
    trial(tmp_path, 'incidental-first-use')
    finish(tmp_path, final)
    receipt_path = tmp_path / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['evidence_kind'] = 'activated-skill'
    receipt_path.write_text(json.dumps(receipt))
    (tmp_path / 'runtime.jsonl').write_text(
        json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': final}}) + '\n' +
        json.dumps({'type': 'turn.completed'}) + '\n')
    result = load('check_trial').check(tmp_path)
    assert not result['checks']['report']['passed']


@pytest.mark.parametrize('final', [
    'I did not save the transcript, but I stored your preference in library-a.',
    'I did not save the transcript and stored your preference in library-a.',
])
def test_no_write_rejects_positive_claim_about_a_different_record(tmp_path, final):
    trial(tmp_path, 'incidental-first-use')
    finish(tmp_path, final)
    receipt_path = tmp_path / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['evidence_kind'] = 'activated-skill'
    receipt_path.write_text(json.dumps(receipt))
    (tmp_path / 'runtime.jsonl').write_text(
        json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': final}}) + '\n' +
        json.dumps({'type': 'turn.completed'}) + '\n')
    assert not load('check_trial').check(tmp_path)['checks']['report']['passed']


def test_verified_save_report_rejects_negated_outcome(tmp_path):
    save(trial(tmp_path))
    result = finish(tmp_path, 'The save is not verified. Your preference was not saved in library-a.')
    assert not result['checks']['report']['passed']


def test_source_identity_and_document_final_newline_preserve_turns(tmp_path):
    store = trial(tmp_path, 'transcript-confirmed')
    control = json.loads((tmp_path / 'control.json').read_text())
    turns = json.loads((tmp_path / 'turns.json').read_text())
    turns.extend([{'role': 'assistant', 'content': 'Confirm verbatim turns in library-a?'},
                  {'role': 'user', 'content': control['approval_turn']['reply']}])
    (tmp_path / 'turns.json').write_text(json.dumps(turns))
    content = {'markdown': control['expected']['source-1']['markdown'].removesuffix('\n'),
               'source_id': 'source-1'}
    invoke(store, 'create', record=dict(provider='fixture', container='library-a', id='source-1',
           path='remember-me/sources/source-1.md', owner='remember-me', content=content))
    invoke(store, 'read', provider='fixture', container='library-a', id='source-1')
    result = finish(tmp_path)
    assert result['checks']['expected_content']['passed']
    assert result['checks']['citations']['passed']


def test_empty_store_discovery_exposes_provider_identity(tmp_path):
    result = invoke(trial(tmp_path, 'new-index-save'), 'list')
    assert result['provider'] == 'fixture'
    assert result['container'] == 'library-a'


@pytest.mark.parametrize(('wrong_id', 'wrong_path'), [
    ('index', 'remember-me/overview.md'),
    ('topic', 'remember-me/preferences.md'),
    ('topic', 'remember-me/archive/communication-collaboration.md'),
])
def test_new_reserved_records_require_canonical_paths(tmp_path, wrong_id, wrong_path):
    store = trial(tmp_path, 'new-index-save')
    invoke(store, 'list')
    records = {
        'topic': {
            'provider': 'fixture', 'container': 'library-a', 'id': 'topic',
            'path': 'remember-me/communication-collaboration.md', 'owner': 'remember-me',
            'content': {'preference': 'concise answers'},
        },
        'index': {
            'provider': 'fixture', 'container': 'library-a', 'id': 'index',
            'path': 'remember-me/index.md', 'owner': 'remember-me',
            'content': {'setup_confirmed': True, 'summary': 'concise answers', 'topic_id': 'topic'},
        },
    }
    records[wrong_id]['path'] = wrong_path
    for record in records.values():
        result = invoke(store, 'create', record=record)
        assert result['ok']
        readback = invoke(store, 'read', provider='fixture', container='library-a', id=record['id'])
        assert readback['record']['path'] == record['path']
    report = finish(tmp_path)
    failed = {name for name, check in report['checks'].items() if not check['passed']}
    assert report['status'] == 'failed'
    assert failed == {'canonical_destination'}


def test_new_topic_accepts_default_taxonomy_path(tmp_path):
    store = trial(tmp_path, 'new-index-save')
    invoke(store, 'list')
    records = {
        'topic': {
            'provider': 'fixture', 'container': 'library-a', 'id': 'topic',
            'path': 'remember-me/communication-collaboration.md', 'owner': 'remember-me',
            'content': {'preference': 'concise answers'},
        },
        'index': {
            'provider': 'fixture', 'container': 'library-a', 'id': 'index',
            'path': 'remember-me/index.md', 'owner': 'remember-me',
            'content': {'setup_confirmed': True, 'summary': 'concise answers', 'topic_id': 'topic'},
        },
    }
    for record in records.values():
        result = invoke(store, 'create', record=record)
        assert result['ok']
        readback = invoke(store, 'read', provider='fixture', container='library-a', id=record['id'])
        assert readback['record']['path'] == record['path']
    report = finish(tmp_path)
    assert report['status'] == 'passed', {
        name: check for name, check in report['checks'].items() if not check['passed']
    }


def test_setup_fault_covers_bounded_metadata_readback_too(tmp_path):
    store = trial(tmp_path, 'setup-readback-fails')
    invoke(store, 'write', provider='fixture', container='library-a', id='index',
           patch={'setup_confirmed': True})
    assert not invoke(store, 'metadata', provider='fixture', container='library-a', id='index')['ok']


def partial_trial(store, case):
    invoke(store, 'read', provider='fixture', container='library-a', id='index')
    invoke(store, 'read', provider='fixture', container='library-a', id='topic')
    invoke(store, 'write', provider='fixture', container='library-a', id='topic',
           patch={'preference': 'concise answers'})
    if case == 'setup-readback-fails':
        invoke(store, 'read', provider='fixture', container='library-a', id='topic')
        invoke(store, 'write', provider='fixture', container='library-a', id='index',
               patch={'summary': 'concise answers', 'setup_confirmed': True})
        invoke(store, 'read', provider='fixture', container='library-a', id='index')
    else:
        invoke(store, 'read', provider='fixture', container='library-a', id='topic')
        invoke(store, 'read', provider='fixture', container='library-a', id='index')
        invoke(store, 'write', provider='fixture', container='library-a', id='index',
               patch={'summary': 'stale: concise answers (topic update unverified)'})
        invoke(store, 'read', provider='fixture', container='library-a', id='index')


@pytest.mark.parametrize(('case', 'response'), [
    ('unavailable-readback',
     'The topic preference was successfully persisted, but its readback is unverified; the index summary is stale and verified.'),
    ('unavailable-readback',
     'The topic preference was successfully written, but its readback is unverified; the index summary is stale and verified.'),
    ('setup-readback-fails',
     'The index summary was successfully recorded; its readback is unverified.'),
    ('setup-readback-fails',
     'The setup flag was successfully stored; its readback is unverified.'),
])
def test_positive_persistence_claim_for_unverified_record_fails(case, response, tmp_path):
    partial_trial(trial(tmp_path, case), case)
    report = finish(tmp_path, response)
    assert not report['checks']['report']['passed']


@pytest.mark.parametrize(('case', 'response'), [
    ('setup-readback-fails',
     'Partial save: the topic preference was successfully persisted, but the index summary and setup flag are unverified.'),
    ('unavailable-readback',
     'The topic preference is unverified; the index summary was successfully stored as stale and verified.'),
])
def test_positive_persistence_claim_for_separately_verified_record_passes(case, response, tmp_path):
    partial_trial(trial(tmp_path, case), case)
    report = finish(tmp_path, response)
    assert report['status'] == 'passed'


@pytest.mark.parametrize(('case', 'response'), [
    ('unavailable-readback',
     'The topic preference was successfully applied, but its readback is unverified.'),
    ('setup-readback-fails',
     'I successfully retained the setup flag, but its readback is unverified.'),
])
def test_additional_positive_persistence_synonyms_for_unverified_record_fail(case, response, tmp_path):
    partial_trial(trial(tmp_path, case), case)
    report = finish(tmp_path, response)
    assert not report['checks']['report']['passed']


@pytest.mark.parametrize(('case', 'response'), [
    ('unavailable-readback',
     'The topic write was acknowledged, but readback was unavailable, so the preference save is unverified. '
     'I updated the index summary to a stale label and verified that readback; the topic remains unresolved.'),
    ('setup-readback-fails',
     'Partial save. The topic preference is verified. The index update was acknowledged, but fresh reads '
     'were unavailable. Its updated summary and setup flag are therefore unverified.'),
])
def test_truthful_partial_outcomes_do_not_claim_unverified_writes(case, response, tmp_path):
    partial_trial(trial(tmp_path, case), case)
    report = finish(tmp_path, response)
    assert report['status'] == 'passed', {
        name: check for name, check in report['checks'].items() if not check['passed']
    }
