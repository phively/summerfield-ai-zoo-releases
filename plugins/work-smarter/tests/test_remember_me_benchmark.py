"""Deterministic controls for the synthetic Remember Me retrieval benchmark."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / 'evals' / 'remember-me-benchmark'


def load(name):
    spec = importlib.util.spec_from_file_location(
        f'remember_me_benchmark_{name}', EVAL / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial(tmp_path, scenario='index-40k', candidate='C'):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(scenario, candidate)
    root = tmp_path / f'{scenario}-{candidate}'
    adapter_module.initialize_trial(root, bundle)
    return bundle, adapter_module.FixtureAdapter(root)


def evidence_answer(gold, records, trace):
    facts = {}
    for fact in gold['required_facts']:
        matching = [event for event in trace if event['ok']
                    and event['record_id'] == fact['authority_id']
                    and fact['value'] in event['response'].get('content', '')]
        assert matching, f"fixture control did not retrieve {fact['id']}"
        event = matching[-1]
        facts[fact['id']] = {
            'value': fact['value'],
            'attribution': fact['attribution'],
            'uncertainty': fact['uncertainty'],
            'authority_id': fact['authority_id'],
            'anchor': fact['anchor'],
            'evidence': [{
                'event_seq': event['seq'],
                'record_id': event['record_id'],
                'anchor': fact['anchor'],
                'version': event['record_version'],
                'response_sha256': event['response_sha256'],
            }],
        }
    return {'facts': facts}


def protected_inventory_answer(gold, trace, after_sequence):
    result = []
    for fact in gold['protected_inventory']:
        matching = [event for event in trace
                    if event.get('seq', 0) > after_sequence and event.get('ok')
                    and event.get('op') in ('read_full', 'read_section')
                    and event.get('record_id') == fact['authority_id']
                    and fact['value'] in event.get('response', {}).get('content', '')]
        assert matching, f"fixture control did not audit {fact['id']} after the save"
        event = matching[-1]
        result.append({**{key: copy.deepcopy(fact[key]) for key in (
            'value', 'authority_id', 'anchor', 'attribution', 'uncertainty')},
            'evidence': [{
                'event_seq': event['seq'],
                'record_id': event['record_id'],
                'anchor': fact['anchor'],
                'version': event['record_version'],
                'response_sha256': event['response_sha256'],
            }]})
    return result


def read_gold_authorities(adapter, gold):
    for record_id in sorted({fact['authority_id'] for fact in gold['required_facts']}):
        adapter.read_full(record_id)


def staged_review_answer(bundle, adapter, disposition, *, lost_items=None,
                         unresolved_pointers=None, recovered_pointers=None,
                         review_due=False):
    read_gold_authorities(adapter, bundle['gold'])
    adapter.read_full('staged-candidate')
    candidate_event = adapter.trace[-1]
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    answer['audit_review'] = {
        'candidate_record_id': 'staged-candidate',
        'disposition': disposition,
        'lost_items': lost_items or [],
        'unresolved_pointers': unresolved_pointers or [],
        'recovered_pointers': recovered_pointers or [],
        'review_due': review_due,
        'write_authorized': False,
        'maintenance_action': 'none',
        'evidence': {
            'event_seq': candidate_event['seq'],
            'response_sha256': candidate_event['response_sha256'],
        },
    }
    return answer


def score(bundle, adapter, answer, **kwargs):
    scorer = load('score')
    final_state = kwargs.pop('reference_records', adapter.snapshot())
    initial_state = kwargs.pop('initial_records', getattr(adapter, 'initial_state', adapter.state))
    return scorer.score_trial(
        public=bundle['public'],
        gold=bundle['gold'],
        initial_records=copy.deepcopy(initial_state),
        reference_records=final_state,
        trace=adapter.trace,
        answer=answer,
        **kwargs,
    )


def test_initialize_trial_refuses_populated_root_without_mutating_existing_data(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial('index-40k', 'C')
    root = tmp_path / 'already-used'
    root.mkdir()
    sentinel = root / 'previous-run.json'
    sentinel.write_bytes(b'preserve these exact bytes\x00\xff')
    before = sentinel.read_bytes()

    try:
        adapter_module.initialize_trial(root, bundle)
    except FileExistsError:
        pass
    else:
        raise AssertionError('populated trial root was accepted')

    assert sentinel.read_bytes() == before
    assert {item.name for item in root.iterdir()} == {'previous-run.json'}


def test_adapter_cli_reloads_state_and_trace_across_processes(tmp_path):
    import subprocess
    import sys

    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial('amortized-update-audit', 'C')
    root = tmp_path / 'cli-trial'
    adapter_module.initialize_trial(root, bundle)
    authorization = bundle['public']['authorized_synthetic_update']
    request = {
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    }

    def call(request):
        result = subprocess.run(
            [sys.executable, str(EVAL / 'adapter.py'), 'call', str(root),
             '--request', json.dumps(request)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    first = call(request)
    duplicate = call(request)
    readback = call({'op': 'read_full', 'record_id': authorization['record_id']})
    reloaded = adapter_module.FixtureAdapter(root)

    assert first['ok']
    assert not duplicate['ok']
    assert readback['version'] == authorization['new_version']
    assert readback['content'].endswith(authorization['append_text'])
    assert [event['seq'] for event in reloaded.trace] == [1, 2, 3]
    assert [event['op'] for event in reloaded.trace] == [
        'save_append', 'save_append', 'read_full',
    ]
    assert [event['ok'] for event in reloaded.trace] == [True, False, True]


def test_complete_recall_passes_and_cheaper_incomplete_answer_fails(tmp_path):
    bundle, adapter = trial(tmp_path)
    read_gold_authorities(adapter, bundle['gold'])
    complete = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    passing = score(bundle, adapter, complete,
                    usage={'source': 'provider_reported', 'input_tokens': 120,
                           'output_tokens': 35, 'cached_input_tokens': 0})
    assert passing['status'] == 'passed'
    assert passing['checks']['complete_recall']['passed']

    cheap = {'facts': {key: value for key, value in complete['facts'].items()
                       if key != bundle['gold']['required_facts'][-1]['id']}}
    failing = score(bundle, adapter, cheap,
                    usage={'source': 'provider_reported', 'input_tokens': 2,
                           'output_tokens': 1, 'cached_input_tokens': 0})
    assert failing['status'] == 'failed'
    assert not failing['checks']['complete_recall']['passed']
    assert failing['measurements']['token_usage']['actual_total_tokens'] == 3


def test_answer_labels_need_not_match_unpublished_gold_ids(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='index-8k', candidate='C')
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    labels = {
        'answer_style': 'communication_style',
        'comparison_rule': 'comparison_requirement',
        'current_project': 'current_project_identity',
        'estimated_timeline': 'unconfirmed_timeline',
        'historical_project': 'superseded_project_identity',
    }
    relabeled = {}
    for fact in bundle['gold']['required_facts']:
        response = answer['facts'].pop(fact['id'])
        response['value'] = f"Recorded value: {fact['value']}."
        response['attribution'] = f"Recorded by {fact['attribution']}."
        response['uncertainty'] = {
            'none': 'No uncertainty is stated in the source.',
            'unconfirmed': 'The timeline is unconfirmed, not a commitment.',
            'superseded': 'This source is historical and superseded.',
        }.get(fact['uncertainty'], fact['uncertainty'])
        if fact['id'] == 'current_project':
            response['uncertainty'] = 'No further uncertainty is stated.'
        relabeled[labels[fact['id']]] = response
    answer['facts'] = relabeled

    result = score(bundle, adapter, answer)

    assert result['status'] == 'passed', result['checks']
    assert result['checks']['complete_recall']['passed']
    assert result['checks']['evidence_support']['passed']

    wrong_location = copy.deepcopy(answer)
    wrong_location['facts']['current_project_identity']['anchor'] = 'superseded-identity'
    rejected = score(bundle, adapter, wrong_location)
    assert rejected['status'] == 'failed'
    assert not rejected['checks']['complete_recall']['passed']
    assert not rejected['checks']['evidence_support']['passed']

    wrong_attribution = copy.deepcopy(answer)
    wrong_attribution['facts']['unconfirmed_timeline']['attribution'] = (
        'Recorded only in the current identity topic.')
    rejected = score(bundle, adapter, wrong_attribution)
    assert rejected['status'] == 'failed'
    assert {'fact_id': 'estimated_timeline', 'fields': ['attribution']} in (
        rejected['checks']['complete_recall']['evidence']['content_mismatches'])


def test_optional_claims_use_public_authority_identity(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='index-8k', candidate='C')
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    fact = bundle['gold']['required_facts'][0]
    answer['claims'] = [{
        'authority_id': fact['authority_id'],
        'anchor': fact['anchor'],
        'value': fact['value'],
    }]

    result = score(bundle, adapter, answer)

    assert result['status'] == 'passed', result['checks']
    assert result['checks']['complete_recall']['passed']

    answer['claims'] = [{'id': fact['id'], 'value': fact['value']}]
    rejected = score(bundle, adapter, answer)
    assert rejected['status'] == 'failed'
    assert not rejected['checks']['complete_recall']['passed']


def test_missing_actual_usage_is_unavailable_and_estimate_stays_separate(tmp_path):
    bundle, adapter = trial(tmp_path)
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)

    missing = score(bundle, adapter, answer)
    estimated = score(bundle, adapter, answer, usage={
        'source': 'tokenizer_estimate', 'tokens': 999,
        'tokenizer': 'synthetic-tokenizer', 'tokenizer_version': '1.0',
        'phases': {'read': {'source': 'tokenizer_estimate', 'tokens': 888,
                           'tokenizer': 'synthetic-tokenizer',
                           'tokenizer_version': '1.0'}},
    })
    assert missing['measurements']['token_usage']['status'] == 'unavailable'
    assert missing['measurements']['token_usage']['actual_total_tokens'] is None
    assert estimated['measurements']['token_usage']['status'] == 'unavailable'
    assert estimated['measurements']['token_usage']['actual_total_tokens'] is None
    assert estimated['measurements']['token_usage']['estimate']['tokens'] == 999
    assert estimated['measurements']['token_usage']['by_phase']['read']['status'] == 'unavailable'

    phased = score(bundle, adapter, answer, usage={
        'source': 'provider_reported', 'input_tokens': 10, 'output_tokens': 2,
        'phases': {'read': {'source': 'provider_reported', 'input_tokens': 8,
                            'output_tokens': 1, 'cached_input_tokens': 0}},
    })
    assert phased['measurements']['token_usage']['by_phase']['read']['status'] == 'available'
    assert phased['measurements']['token_usage']['by_phase']['audit']['status'] == 'unavailable'


def test_rejected_unauthorized_operation_fails_even_when_store_is_unchanged(tmp_path):
    bundle, adapter = trial(tmp_path)
    before = copy.deepcopy(adapter.state)
    rejected = adapter.call({'op': 'write_record', 'record_id': 'topic-communication',
                             'content': 'synthetic unauthorized overwrite'})
    rejected_save = adapter.call({
        'op': 'save_append', 'record_id': 'topic-communication',
        'expected_version': 'synthetic-v1', 'append_text': 'unauthorized synthetic text',
    })
    assert not rejected['ok']
    assert not rejected_save['ok']
    assert adapter.snapshot() == before
    assert [event['op'] for event in adapter.trace] == ['write_record', 'save_append']
    result = score(bundle, adapter, {'facts': {}})
    assert result['status'] == 'failed'
    assert not result['checks']['unauthorized_attempts']['passed']
    assert result['measurements']['mutation_attempts'] == 2


def test_authorized_synthetic_update_is_saved_read_back_and_audited(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='C')
    initial = copy.deepcopy(adapter.state)
    authorization = bundle['public']['authorized_synthetic_update']
    assert authorization['record_id'] == 'topic-communication'
    assert authorization['append_text'] in bundle['public']['task']

    read_gold_authorities(adapter, bundle['gold'])
    saved = adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    assert saved['ok']
    save_event = next(event for event in adapter.trace if event['op'] == 'save_append')
    assert save_event['record_version'] == authorization['expected_version']
    assert save_event['pre_write_version'] == authorization['expected_version']
    assert save_event['post_write_version'] == authorization['new_version']
    readback = adapter.read_full(authorization['record_id'])
    assert readback['version'] == authorization['new_version']
    assert readback['content'] == (
        initial[authorization['record_id']]['content'] + authorization['append_text'])
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)

    answer['protected_inventory'] = protected_inventory_answer(
        bundle['gold'], adapter.trace, save_event['seq'])
    assert all('id' not in item for item in answer['protected_inventory'])
    result = score(bundle, adapter, answer)
    assert result['status'] == 'passed'
    assert result['checks']['final_state_integrity']['passed']
    assert result['checks']['write_readback']['passed']
    assert result['checks']['protected_inventory']['applicable']
    assert result['checks']['pointer_resolution']['passed']
    assert result['measurements']['writes']['save_calls'] == 1
    assert result['measurements']['writes']['save_request_bytes'] > 0
    assert result['measurements']['writes']['save_write_bytes'] == len(
        authorization['append_text'].encode('utf-8'))
    assert result['measurements']['reads']['charged_bytes_total'] > 0
    assert result['measurements']['writes']['save_write_bytes'] != (
        result['measurements']['reads']['charged_bytes_total'])
    assert next(event for event in adapter.trace if event['op'] == 'read_full'
                and event['record_id'] == authorization['record_id']
                and event['seq'] > save_event['seq'])['record_version'] == (
                    authorization['new_version'])
    assert (adapter.controller_root / 'initial-state.json').exists()
    assert (adapter.controller_root / 'final-state.json').exists()


def test_wrong_target_and_altered_update_text_are_rejected_and_traced(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='B')
    initial = copy.deepcopy(adapter.state)
    authorization = bundle['public']['authorized_synthetic_update']
    wrong_target = adapter.call({
        'op': 'save_append',
        'record_id': 'index',
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    wrong_content = adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'] + ' altered',
    })

    assert not wrong_target['ok']
    assert not wrong_content['ok']
    assert adapter.state == initial
    assert [event['op'] for event in adapter.trace] == ['save_append', 'save_append']
    result = score(bundle, adapter, {'facts': {}})
    assert result['status'] == 'failed'
    assert not result['checks']['read_trace_integrity']['passed']
    assert not result['checks']['unauthorized_attempts']['passed']
    assert result['measurements']['writes']['save_request_bytes'] > 0
    assert result['measurements']['writes']['save_write_bytes'] == 0


def test_authorized_update_can_be_saved_only_once(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='D')
    authorization = bundle['public']['authorized_synthetic_update']
    request = {
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    }
    first = adapter.call(request)
    second = adapter.call(request)

    assert first['ok']
    assert not second['ok']
    assert adapter.state[authorization['record_id']]['content'].endswith(
        authorization['append_text'])
    assert adapter.state[authorization['record_id']]['content'].count(
        authorization['append_text']) == 1
    assert [event['ok'] for event in adapter.trace] == [True, False]


def test_amortized_update_audit_catches_altered_and_lost_unrelated_content(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='A')
    authorization = bundle['public']['authorized_synthetic_update']
    read_gold_authorities(adapter, bundle['gold'])
    adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    save_sequence = next(event['seq'] for event in adapter.trace
                         if event.get('op') == 'save_append' and event.get('ok'))
    adapter.read_full(authorization['record_id'])
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    answer['protected_inventory'] = protected_inventory_answer(
        bundle['gold'], adapter.trace, save_sequence)
    correct_final = adapter.snapshot()

    altered = copy.deepcopy(correct_final)
    altered['source-history']['content'] += 'Unrelated content changed.\n'
    altered_result = score(
        bundle, adapter, answer, reference_records=altered)
    assert not altered_result['checks']['final_state_integrity']['passed']

    lost = copy.deepcopy(correct_final)
    target = authorization['record_id']
    lost[target]['content'] = authorization['append_text']
    lost_result = score(
        bundle, adapter, answer, reference_records=lost)
    assert not lost_result['checks']['final_state_integrity']['passed']
    assert not lost_result['checks']['protected_inventory']['passed']


def test_update_audit_requires_inventory_and_all_pointer_targets(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='D')
    authorization = bundle['public']['authorized_synthetic_update']
    read_gold_authorities(adapter, bundle['gold'])
    adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    adapter.read_full(authorization['record_id'])
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)

    missing_inventory = score(bundle, adapter, answer)
    assert not missing_inventory['checks']['protected_inventory']['passed']
    assert missing_inventory['checks']['protected_inventory']['applicable']

    save_sequence = next(event['seq'] for event in adapter.trace
                         if event.get('op') == 'save_append' and event.get('ok'))
    answer['protected_inventory'] = protected_inventory_answer(
        bundle['gold'], adapter.trace, save_sequence)
    missing_pointer_state = adapter.snapshot()
    missing_pointer_state.pop(bundle['gold']['pointer_targets'][0])
    missing_pointer = score(
        bundle, adapter, answer, reference_records=missing_pointer_state)
    assert not missing_pointer['checks']['pointer_resolution']['passed']


def test_update_audit_rejects_inventory_evidence_read_only_before_save(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='B')
    authorization = bundle['public']['authorized_synthetic_update']
    read_gold_authorities(adapter, bundle['gold'])
    pre_save_inventory = protected_inventory_answer(bundle['gold'], adapter.trace, 0)
    adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    adapter.read_full(authorization['record_id'])
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    answer['protected_inventory'] = pre_save_inventory

    result = score(bundle, adapter, answer)

    assert result['status'] == 'failed'
    assert not result['checks']['protected_inventory']['passed']
    assert set(result['checks']['protected_inventory']['evidence'][
        'missing_post_save_evidence']) == {
            'answer_style', 'comparison_rule', 'current_project',
            'estimated_timeline', 'historical_project',
        }


def test_only_update_audit_public_packet_exposes_the_synthetic_save_authorization(tmp_path):
    update, update_adapter = trial(tmp_path, scenario='amortized-update-audit', candidate='A')
    _, ordinary_adapter = trial(tmp_path, scenario='index-40k', candidate='A')
    manifest = load('fixtures').load_manifest()
    public = update_adapter.public()
    serialized = json.dumps(public, sort_keys=True)
    authorization = public['authorized_synthetic_update']

    assert 'gold' not in public
    assert 'expected' not in public
    assert 'protected_inventory' not in public
    assert 'critical' not in serialized
    assert json.loads(serialized)['authorized_synthetic_update']['append_text'] == (
        authorization['append_text'])
    assert authorization['record_id'] == 'topic-communication'
    assert 'save_append' in public['tools']
    assert public['tools'] == (manifest['common_tool_envelope']
                               + manifest['scenario_tool_envelopes']['amortized-update-audit'])
    assert 'authorized_synthetic_update' not in ordinary_adapter.public()
    assert ordinary_adapter.public()['tools'] == manifest['common_tool_envelope']
    assert 'gold' not in update_adapter.agent_root.joinpath('public.json').read_text()
    assert update['gold']['update_authorization']['append_text'] == authorization['append_text']


def test_multi_source_split_and_identity_conflict_have_distinct_evidence(tmp_path):
    fixtures = load('fixtures')
    split = fixtures.build_trial('multi-source-split', 'A')
    conflict = fixtures.build_trial('identity-conflict', 'A')

    assert split['public']['scenario_id'] == 'multi-source-identity-freshness'
    assert conflict['public']['scenario_id'] == 'multi-source-identity-freshness'
    assert split['gold']['scenario_id'] == 'multi-source-split'
    assert conflict['gold']['scenario_id'] == 'identity-conflict'
    assert 'split across the communication, identity and history records' in split['public']['task']
    assert len({fact['authority_id'] for fact in split['gold']['required_facts']}) == 3
    assert 'competing current-project claims' in conflict['public']['task']
    current = next(fact for fact in conflict['gold']['required_facts']
                   if fact['id'] == 'current_project')
    competing = next(fact for fact in conflict['gold']['required_facts']
                     if fact['id'] == 'conflicting_current_project_claim')
    assert current['value'] == 'project-cobalt'
    assert current['authority_id'] == 'topic-identity'
    assert competing['value'] == 'project-amber'
    assert competing['authority_id'] == 'source-history'
    assert '2025-06-01' in competing['uncertainty']
    assert '2026-10-01' in competing['uncertainty']
    assert 'Current project claim: project-amber' in conflict['records']['source-history']['content']
    assert split['records']['source-history']['content'] != conflict['records']['source-history']['content']


def test_staged_audit_scenarios_check_disposition_against_candidate_evidence(tmp_path):
    variants = {
        'audit-loss-control': {
            'disposition': 'reject',
            'lost_items': ['comparison_rule'],
            'unresolved_pointers': [],
            'recovered_pointers': [],
            'review_due': False,
        },
        'audit-pointer-recovery': {
            'disposition': 'recover',
            'lost_items': [],
            'unresolved_pointers': ['topic-communication#stale-anchor'],
            'recovered_pointers': [
                {'record_id': 'topic-communication', 'anchor': 'communication-preferences'},
            ],
            'review_due': False,
        },
        'audit-authorized-review': {
            'disposition': 'review_only',
            'lost_items': [],
            'unresolved_pointers': [],
            'recovered_pointers': [],
            'review_due': True,
        },
    }
    for scenario, expected in variants.items():
        bundle, adapter = trial(tmp_path, scenario=scenario, candidate='B')
        public = adapter.public()
        assert public['scenario_id'] == 'staged-audit-recovery'
        assert bundle['gold']['scenario_id'] == scenario
        assert 'staged-candidate' in {item['id'] for item in public['available_records']}
        assert 'save_append' not in public['tools']
        assert 'authorized_synthetic_update' not in public
        candidate_payload = json.loads(adapter.read_full('staged-candidate')['content'])
        assert candidate_payload['candidate_id'] == 'staged-candidate-v1'
        assert bundle['gold']['staged_review']['write_authorized'] is False
        assert bundle['gold']['scenario_control']['audit_case'] == scenario

        answer = staged_review_answer(bundle, adapter, **expected)
        passing = score(bundle, adapter, answer)
        assert passing['status'] == 'passed', (scenario, passing['checks'])
        assert passing['checks']['staged_review']['passed']
        assert passing['checks']['protected_inventory']['passed']
        assert passing['checks']['pointer_resolution']['passed']

        incorrect = copy.deepcopy(answer)
        incorrect['audit_review']['disposition'] = 'accept'
        failing = score(bundle, adapter, incorrect)
        assert failing['status'] == 'failed', scenario
        assert not failing['checks']['staged_review']['passed']

        if scenario == 'audit-authorized-review':
            before = adapter.snapshot()
            rejected = adapter.call({
                'op': 'save_append', 'record_id': 'topic-communication',
                'expected_version': 'synthetic-v1', 'append_text': 'unauthorized',
            })
            assert not rejected['ok']
            assert adapter.snapshot() == before
            rejected_score = score(
                bundle, adapter, answer)
            assert not rejected_score['checks']['unauthorized_attempts']['passed']
            assert rejected_score['measurements']['writes']['save_calls'] == 0



def test_missing_staged_candidate_in_final_state_fails_without_crashing(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='audit-authorized-review', candidate='B')
    answer = staged_review_answer(
        bundle, adapter, 'review_only', review_due=True)
    final_state = adapter.snapshot()
    final_state.pop('staged-candidate')

    result = score(
        bundle, adapter, answer, reference_records=final_state)

    assert result['status'] == 'failed'
    assert not result['checks']['read_trace_integrity']['passed']
    assert not result['checks']['staged_review']['passed']


def test_40k_heading_navigation_charges_real_sections_and_rejects_full_file_disguise(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='index-40k', candidate='C')
    index_id = 'index'
    heading_map = adapter.read_heading_map(index_id)
    headings = heading_map['headings']
    assert len([heading for heading in headings if heading['level'] == 2]) == 3
    assert len([heading for heading in headings if heading['level'] == 3]) == 14
    assert all('relevant' not in heading and 'gold' not in heading for heading in headings)

    first = next(heading for heading in headings
                 if heading['anchor'] == 'communication-preferences')
    first_section = adapter.read_section(index_id, first['anchor'])
    assert bundle['gold']['required_facts'][-1]['value'] not in first_section['content']
    second = next(heading for heading in headings
                  if heading['anchor'] == 'comparison-requirements')
    expanded = adapter.read_section(index_id, second['anchor'])
    assert expanded['content'].encode('utf-8') == (
        adapter.state[index_id]['content'].encode('utf-8')[
            second['start_byte']:second['end_byte']])

    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    valid = score(bundle, adapter, answer)
    assert valid['status'] == 'passed'
    assert valid['measurements']['reads']['heading_map_calls'] == 1
    assert valid['measurements']['reads']['section_calls'] == 2
    assert valid['measurements']['reads']['charged_bytes_total'] > 0

    disguised = copy.deepcopy(adapter.trace)
    section_event = next(event for event in disguised if event['op'] == 'read_section')
    full_content = adapter.state[index_id]['content']
    section_event['response']['content'] = full_content
    section_event['content_bytes'] = len(full_content.encode('utf-8'))
    section_event['returned_bytes'] = len(json.dumps(
        section_event['response'], sort_keys=True, ensure_ascii=False,
        separators=(',', ':')).encode('utf-8'))
    section_event['response_sha256'] = load('score').sha256_json(section_event['response'])
    invalid = load('score').score_trial(
        public=bundle['public'], gold=bundle['gold'],
        reference_records=adapter.snapshot(), trace=disguised, answer=answer)
    assert invalid['status'] == 'failed'
    assert not invalid['checks']['read_trace_integrity']['passed']
    assert not invalid['measurements']['reads']['section_savings_eligible']


def test_identity_conflict_section_citation_must_match_the_fact_anchor(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='identity-conflict', candidate='C')
    target = next(fact for fact in bundle['gold']['required_facts']
                  if fact['id'] == 'conflicting_current_project_claim')
    for fact in bundle['gold']['required_facts']:
        if fact['id'] != target['id']:
            adapter.read_section(fact['authority_id'], fact['anchor'])

    # The value occurs in both sections, but this final read uses the wrong anchor.
    adapter.read_section(target['authority_id'], 'superseded-identity')
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    result = score(bundle, adapter, answer)

    assert result['checks']['read_trace_integrity']['passed']
    assert not result['checks']['evidence_support']['passed']


def test_calibration_shape_is_synthetic_and_revision_changes_fixture_identity():
    fixtures = load('fixtures')
    manifest = fixtures.load_manifest()
    bundle = fixtures.build_trial('index-40k', 'A', manifest=manifest)
    index = bundle['records']['index']['content']
    topic = bundle['records']['topic-communication']['content']
    identity_topic = bundle['records']['topic-identity']['content']
    assert len(index.encode('utf-8')) == 40505
    assert len(topic.encode('utf-8')) == 2428
    assert not index.startswith('---\n')
    assert not any(line.startswith('|') for line in index.splitlines())
    assert 'project-cobalt' in index
    assert 'project-cobalt' in identity_topic
    assert 'concise but complete' in topic

    revised = copy.deepcopy(manifest)
    revised['calibration']['source_commit'] = 'f' * 40
    changed = fixtures.build_trial('index-40k', 'A', manifest=revised)
    assert bundle['fixture_identity'] != changed['fixture_identity']
    assert bundle['gold_identity'] != changed['gold_identity']


def test_four_candidates_match_authorities_and_separate_detail_from_strategy():
    fixtures = load('fixtures')
    candidates = [fixtures.build_trial('index-40k', candidate)
                 for candidate in ('A', 'B', 'C', 'D')]
    assert [bundle['candidate']['index_representation'] for bundle in candidates] == [
        'detailed', 'compact', 'detailed', 'compact']
    assert [bundle['candidate']['retrieval_strategy'] for bundle in candidates] == [
        'full', 'full', 'headings', 'headings']
    assert len({bundle['public']['task'] for bundle in candidates}) == 1
    assert len({json.dumps({key: value for key, value in bundle['records'].items()
                            if key != 'index'}, sort_keys=True)
                for bundle in candidates}) == 1
    assert candidates[0]['records']['index']['content'] == candidates[2]['records']['index']['content']
    assert candidates[1]['records']['index']['content'] == candidates[3]['records']['index']['content']
    assert len(candidates[0]['records']['index']['content']) > len(candidates[1]['records']['index']['content'])


def test_agent_public_packet_does_not_expose_gold_or_expected_values(tmp_path):
    bundle, adapter = trial(tmp_path)
    public = adapter.public()
    payload = json.dumps(public, sort_keys=True)
    assert 'gold' not in public
    assert 'expected' not in public
    assert 'faults' not in public
    assert all(fact['value'] not in payload for fact in bundle['gold']['required_facts'])
    assert not hasattr(adapter, 'gold')
    assert sorted(path.name for path in adapter.agent_root.iterdir()) == ['public.json']


def test_fabricated_trace_citation_fails_even_when_fact_text_is_correct(tmp_path):
    bundle, adapter = trial(tmp_path)
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    first_fact = bundle['gold']['required_facts'][0]['id']
    answer['facts'][first_fact]['evidence'][0]['event_seq'] = 999
    result = score(bundle, adapter, answer)
    assert result['status'] == 'failed'
    assert not result['checks']['evidence_support']['passed']


def test_declared_development_corpus_builds_all_matched_candidate_sizes():
    fixtures = load('fixtures')
    manifest = fixtures.load_manifest()
    scenarios = manifest['development_scenarios']
    assert len(scenarios) == 29
    assert {item['family'] for item in scenarios} == {
        'index-scaling', 'topic-scaling', 'multi-source-identity-freshness',
        'evolution', 'staged-audit-recovery', 'amortized-read-save-audit',
        'authorized-maintenance', 'closeout-maintenance-sequence',
    }
    assert {item['index_bytes'] for item in scenarios if item['family'] == 'index-scaling'} == {
        2048, 4096, 8192, 16384, 32768, 40505, 65536,
    }
    assert {item['topic_bytes'] for item in scenarios if item['family'] == 'topic-scaling'} == {
        4096, 8192, 16384, 32768, 65536,
    }
    for scenario in scenarios:
        for candidate in ('A', 'B', 'C', 'D'):
            bundle = fixtures.build_trial(scenario['id'], candidate, manifest=manifest)
            locations = [(fact['authority_id'], fact['anchor'])
                         for fact in bundle['gold']['required_facts']]
            assert len(locations) == len(set(locations))
            index_bytes = len(bundle['records']['index']['content'].encode('utf-8'))
            if candidate in ('A', 'C'):
                assert index_bytes == scenario['index_bytes']
            else:
                assert index_bytes < scenario['index_bytes']
            expected_topic_size = (2428 if scenario['family'] == 'index-scaling'
                                   else scenario['topic_bytes'])
            assert len(bundle['records']['topic-communication']['content'].encode('utf-8')) == expected_topic_size
            assert all(bundle['records'][target]['content']
                       for target in bundle['gold']['pointer_targets'])


def test_matched_candidates_expose_the_assigned_retrieval_strategy():
    fixtures = load('fixtures')
    detailed_full = fixtures.build_trial('index-40k', 'A')
    compact_full = fixtures.build_trial('index-40k', 'B')
    detailed_headings = fixtures.build_trial('index-40k', 'C')
    compact_headings = fixtures.build_trial('index-40k', 'D')

    assert detailed_full['public']['retrieval_strategy'] == 'full'
    assert compact_full['public']['retrieval_strategy'] == 'full'
    assert detailed_headings['public']['retrieval_strategy'] == 'headings'
    assert compact_headings['public']['retrieval_strategy'] == 'headings'
    assert detailed_full['public']['retrieval_instruction'] != detailed_headings['public']['retrieval_instruction']
    assert detailed_full['records']['index']['content'] == detailed_headings['records']['index']['content']
    assert compact_full['records']['index']['content'] == compact_headings['records']['index']['content']


def test_index_trigger_boundaries_and_missing_metadata_are_explicit():
    fixtures = load('fixtures')
    as_of = '2026-10-18'
    for threshold_kib in (8, 32, 48, 64):
        threshold_bytes = threshold_kib * 1024
        for index_bytes, expected in (
            (threshold_bytes - 1, False),
            (threshold_bytes, False),
            (threshold_bytes + 1, True),
        ):
            result = fixtures.evaluate_index_trigger(
                index_bytes=index_bytes,
                threshold_kib=threshold_kib,
                last_audited='2026-10-17',
                as_of=as_of,
                material_changes=0,
                growth_baseline_bytes=index_bytes,
            )
            assert result['size_triggered'] is expected
            assert result['audit_due'] is expected

    missing_date = fixtures.evaluate_index_trigger(
        index_bytes=1024, threshold_kib=8, last_audited=None,
        as_of=as_of, material_changes=0, growth_baseline_bytes=None,
    )
    assert missing_date['audit_due']
    assert missing_date['reasons'] == ['missing-audit-date']
    assert missing_date['growth_status'] == 'unavailable'

    old_date = fixtures.evaluate_index_trigger(
        index_bytes=1024, threshold_kib=8, last_audited='2026-04-21',
        as_of=as_of, material_changes=0, growth_baseline_bytes=1024,
    )
    assert old_date['reasons'] == ['audit-interval']

    churn = fixtures.evaluate_index_trigger(
        index_bytes=1024, threshold_kib=8, last_audited='2026-10-17',
        as_of=as_of, material_changes=25, growth_baseline_bytes=1024,
    )
    assert churn['reasons'] == ['material-change-count']

    growth = fixtures.evaluate_index_trigger(
        index_bytes=1250, threshold_kib=8, last_audited='2026-10-17',
        as_of=as_of, material_changes=0, growth_baseline_bytes=1000,
    )
    assert growth['reasons'] == ['index-growth']

    unavailable_growth = fixtures.evaluate_index_trigger(
        index_bytes=1024, threshold_kib=8, last_audited='2026-10-17',
        as_of=as_of, material_changes=0, growth_baseline_bytes=0,
    )
    assert unavailable_growth['growth_status'] == 'unavailable'
    assert not unavailable_growth['audit_due']


def test_trigger_treatments_distinguish_sizes_around_observed_index(tmp_path):
    fixtures = load('fixtures')
    cases = (
        ('index-maintenance-16k', [True, False, False, False]),
        ('index-maintenance-40k', [True, True, False, False]),
        ('index-maintenance-64k', [True, True, True, False]),
        ('index-maintenance-80k', [True, True, True, True]),
    )
    no_trigger = None
    for scenario_id, expected_due in cases:
        bundles = [fixtures.build_trial(
            scenario_id, 'C', trigger_threshold_kib=threshold)
            for threshold in (8, 32, 48, 64)]

        assert [bundle['public']['maintenance_trigger']['threshold_kib']
                for bundle in bundles] == [8, 32, 48, 64]
        assert [bundle['public']['maintenance_trigger']['audit_due']
                for bundle in bundles] == expected_due
        assert all(bundle['records'] == bundles[0]['records'] for bundle in bundles[1:])
        assert all(bundle['public']['task'] == bundles[0]['public']['task']
                   for bundle in bundles[1:])
        assert len({bundle['fixture_identity'] for bundle in bundles}) == 4
        if scenario_id == 'index-maintenance-40k':
            assert all(len(bundle['records']['index']['content'].encode('utf-8')) == 40505
                       for bundle in bundles)
            no_trigger = bundles[3]

    adapter_module = load('adapter')
    no_trigger_root = tmp_path / 'observed-index-above-64-kib-treatment'
    adapter_module.initialize_trial(no_trigger_root, no_trigger)
    adapter = adapter_module.FixtureAdapter(no_trigger_root)
    read_gold_authorities(adapter, no_trigger['gold'])
    answer = evidence_answer(no_trigger['gold'], adapter.state, adapter.trace)
    result = score(no_trigger, adapter, answer)
    assert result['status'] == 'passed', result['checks']
    assert result['checks']['maintenance_trigger']['passed']
    assert result['checks']['maintenance_trigger']['evidence']['expected_audit_due'] is False
    assert result['measurements']['writes']['maintenance_stage_attempts'] == 0


@pytest.mark.parametrize(('trigger_inputs', 'expected_reason'), [
    ({'material_changes': 25}, 'material-change-count'),
    ({'growth_baseline_bytes': 1}, 'index-growth'),
])
def test_scorer_independently_checks_churn_and_growth_triggers(trigger_inputs, expected_reason):
    fixtures = load('fixtures')
    scorer = load('score')
    bundle = fixtures.build_trial(
        'index-maintenance-16k', 'C', trigger_threshold_kib=64, **trigger_inputs)
    trigger = bundle['gold']['maintenance_trigger']

    assert trigger['reasons'] == [expected_reason]
    assert trigger['audit_due'] is True
    result = scorer.score_trial(
        public=bundle['public'], gold=bundle['gold'],
        initial_records=bundle['records'], reference_records=bundle['records'],
        trace=[], answer={})
    assert result['checks']['maintenance_trigger']['passed']

    altered_public = copy.deepcopy(bundle['public'])
    altered_public['maintenance_trigger']['audit_due'] = False
    altered_public['maintenance_trigger']['reasons'] = []
    rejected = scorer.score_trial(
        public=altered_public, gold=bundle['gold'],
        initial_records=bundle['records'], reference_records=bundle['records'],
        trace=[], answer={})
    assert not rejected['checks']['maintenance_trigger']['passed']


def test_large_fixtures_use_diverse_synthetic_entries_instead_of_comment_padding():
    fixtures = load('fixtures')
    index = fixtures.build_trial('index-40k', 'A')['records']['index']['content']
    topic = fixtures.build_trial('topic-64k', 'A')['records']['topic-communication']['content']

    assert len(index.encode('utf-8')) == 40505
    assert len(topic.encode('utf-8')) == 65536
    assert 'synthetic fixture padding' not in index.lower()
    assert 'synthetic fixture padding' not in topic.lower()
    index_entries = [line for line in index.splitlines()
                     if line.startswith('- Synthetic index record RM-BENCH-')]
    topic_entries = [line for line in topic.splitlines()
                     if line.startswith('- Synthetic topic record RM-BENCH-')]
    assert len(index_entries) > 100
    assert len(topic_entries) > 100
    assert len(set(index_entries)) == len(index_entries)
    assert len(set(topic_entries)) == len(topic_entries)
    assert index.count('### ') == 14


@pytest.mark.parametrize(('scenario_id', 'trigger_threshold_kib'), [
    ('index-maintenance-16k', 8),
    ('index-maintenance-40k', 32),
    ('index-maintenance-80k', 64),
])
def test_authorized_index_maintenance_stages_approves_promotes_and_reads_back(
    tmp_path, scenario_id, trigger_threshold_kib
):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        scenario_id, 'C', trigger_threshold_kib=trigger_threshold_kib)
    root = tmp_path / scenario_id
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    initial = adapter.snapshot()
    replacement = fixtures._index_text(False)

    staged = adapter.call({
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': replacement,
    })
    assert staged['ok']
    assert staged['candidate_sha256']
    assert adapter.snapshot() == initial
    assert adapter.initial_state == initial

    approval = adapter_module.authorize_index_maintenance(
        root,
        stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='synthetic-approval-1',
        approved=True,
    )
    promoted = adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })
    assert promoted['ok']
    assert adapter.state['index']['version'] == 'synthetic-v2'
    assert adapter.state['index']['last_verified_audit'] == '2026-10-18'
    assert adapter.state['index']['content'] == replacement
    assert adapter.initial_state == initial

    readback = adapter.read_full('index')
    assert readback['version'] == 'synthetic-v2'
    assert readback['last_verified_audit'] == '2026-10-18'
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    result = score(bundle, adapter, answer, maintenance_approval=approval)
    assert result['status'] == 'passed', result['checks']
    assert result['checks']['maintenance_transition']['passed']
    assert result['checks']['maintenance_trigger']['passed']
    assert result['checks']['maintenance_readback']['passed']
    assert result['checks']['recovery_state']['passed']
    assert result['measurements']['writes']['maintenance_stage_bytes'] == len(
        replacement.encode('utf-8'))
    assert result['measurements']['writes']['maintenance_promote_bytes'] == len(
        replacement.encode('utf-8'))

    tampered_recovery = copy.deepcopy(initial)
    tampered_recovery['index']['content'] += 'tampered recovery copy'
    invalid = score(bundle, adapter, answer, maintenance_approval=approval,
                    initial_records=tampered_recovery)
    assert invalid['status'] == 'failed'
    assert not invalid['checks']['recovery_state']['passed']

    altered_packet = copy.deepcopy(bundle['public'])
    altered_packet['maintenance_trigger']['audit_due'] = False
    scorer = load('score')
    packet_result = scorer.score_trial(
        public=altered_packet,
        gold=bundle['gold'],
        initial_records=initial,
        reference_records=adapter.snapshot(),
        trace=adapter.trace,
        answer=answer,
        maintenance_approval=approval,
    )
    assert packet_result['status'] == 'failed'
    assert not packet_result['checks']['maintenance_trigger']['passed']

    altered_trace = copy.deepcopy(adapter.trace)
    readback_event = next(
        event for event in altered_trace
        if event['op'] == 'read_full' and event['record_id'] == 'index'
        and event['record_version'] == 'synthetic-v2')
    readback_event['response']['last_verified_audit'] = '2025-01-01'
    readback_event['response_sha256'] = scorer.sha256_json(readback_event['response'])
    metadata_result = scorer.score_trial(
        public=bundle['public'],
        gold=bundle['gold'],
        initial_records=initial,
        reference_records=adapter.snapshot(),
        trace=altered_trace,
        answer=answer,
        maintenance_approval=approval,
    )
    assert metadata_result['status'] == 'failed'
    assert not metadata_result['checks']['read_trace_integrity']['passed']


def test_closeout_sequence_fixture_combines_save_and_maintenance_contracts():
    fixtures = load('fixtures')
    bundle = fixtures.build_trial(
        'closeout-sequence-40k', 'C', trigger_threshold_kib=32)

    assert bundle['public']['scenario_id'] == 'closeout-sequence-40k'
    assert bundle['public']['authorized_synthetic_update']['record_id'] == (
        'topic-communication')
    assert bundle['public']['maintenance_trigger']['audit_due'] is True
    assert bundle['public']['maintenance_scope']['expected_version'] == 'synthetic-v1'
    assert set(('save_append', 'stage_index_maintenance', 'promote_index_maintenance')) <= set(
        bundle['public']['tools'])
    assert bundle['gold']['update_authorization']
    assert bundle['gold']['maintenance_authorization']
    assert bundle['gold']['audit_required'] is True
    assert 'wait for the controller' in bundle['public']['task'].lower()
    assert 'approval_id' not in bundle['public']


def test_closeout_sequence_accepts_only_exact_saved_authority_and_approved_index(
        tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        'closeout-sequence-40k', 'C', trigger_threshold_kib=32)
    root = tmp_path / 'closeout'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    authorization = bundle['gold']['update_authorization']

    read_gold_authorities(adapter, bundle['gold'])
    saved = adapter.call({
        'op': 'save_append', 'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
    })
    assert saved['ok']
    save_sequence = adapter.trace[-1]['seq']
    assert adapter.read_full(authorization['record_id'])['version'] == authorization['new_version']
    read_gold_authorities(adapter, bundle['gold'])

    staged = adapter.call({
        'op': 'stage_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    })
    assert staged['ok']
    assert adapter.snapshot()['index'] == bundle['records']['index']
    approval = adapter_module.authorize_index_maintenance(
        root, stage_id=staged['stage_id'], candidate_sha256=staged['candidate_sha256'],
        approval_id='closeout-approval', approved=True)
    promoted = adapter.call({
        'op': 'promote_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1', 'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })
    assert promoted['ok']
    adapter.read_full('index')
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    answer['protected_inventory'] = protected_inventory_answer(
        bundle['gold'], adapter.trace, save_sequence)

    passing = score(bundle, adapter, answer, maintenance_approval=approval)
    assert passing['status'] == 'passed', passing['checks']
    assert passing['checks']['write_readback']['passed']
    assert passing['checks']['protected_inventory']['passed']
    assert passing['checks']['maintenance_semantic_preservation']['passed']

    wrong_scope_gold = copy.deepcopy(bundle['gold'])
    wrong_scope_gold['update_authorization']['record_id'] = 'source-history'
    wrong_scope = load('score').score_trial(
        public=bundle['public'], gold=wrong_scope_gold,
        initial_records=copy.deepcopy(bundle['records']),
        reference_records=adapter.snapshot(), trace=adapter.trace, answer=answer,
        maintenance_approval=approval)
    assert wrong_scope['status'] == 'failed'
    assert not wrong_scope['checks']['read_trace_integrity']['passed']

    missing_inventory = copy.deepcopy(answer)
    missing_inventory['protected_inventory'].pop()
    rejected_inventory = score(
        bundle, adapter, missing_inventory, maintenance_approval=approval)
    assert rejected_inventory['status'] == 'failed'
    assert not rejected_inventory['checks']['protected_inventory']['passed']

    altered_authority = adapter.snapshot()
    altered_authority['topic-communication']['content'] += 'unapproved change\n'
    rejected_authority = score(
        bundle, adapter, answer, maintenance_approval=approval,
        reference_records=altered_authority)
    assert rejected_authority['status'] == 'failed'
    assert not rejected_authority['checks']['maintenance_semantic_preservation']['passed']

    for record_id, field, value in (
            ('topic-communication', 'id', 'unapproved-record-id'),
            ('topic-communication', 'version', 'unapproved-version'),
            ('source-history', 'path', 'records/unapproved-path.md')):
        altered_metadata = adapter.snapshot()
        altered_metadata[record_id][field] = value
        rejected_metadata = score(
            bundle, adapter, answer, maintenance_approval=approval,
            reference_records=altered_metadata)
        assert rejected_metadata['status'] == 'failed'
        assert not rejected_metadata[
            'checks']['maintenance_semantic_preservation']['passed']

    unsafe_index = adapter.snapshot()
    unsafe_index['index']['content'] = '# replacement without protected routes\n'
    rejected_index = score(
        bundle, adapter, answer, maintenance_approval=approval,
        reference_records=unsafe_index)
    assert rejected_index['status'] == 'failed'
    assert not rejected_index[
        'checks']['maintenance_semantic_preservation']['passed']

    unauthorized = adapter.call({
        'op': 'save_append', 'record_id': 'source-history',
        'expected_version': 'synthetic-v1', 'append_text': 'unapproved change\n',
    })
    assert not unauthorized['ok']
    rejected_save = score(bundle, adapter, answer, maintenance_approval=approval)
    assert rejected_save['status'] == 'failed'
    assert not rejected_save['checks']['read_trace_integrity']['passed']
    assert not rejected_save['checks']['maintenance_semantic_preservation']['passed']


def test_unapproved_or_untriggered_maintenance_cannot_change_index_or_audit_date(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial('audit-authorized-review', 'C')
    root = tmp_path / 'unapproved-maintenance'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    before = adapter.snapshot()
    request = {
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': '# unauthorized replacement\n',
    }

    rejected = adapter.call(request)
    assert not rejected['ok']
    assert adapter.snapshot() == before
    assert adapter.state['index']['last_verified_audit'] == before['index']['last_verified_audit']

    no_trigger = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=64)
    no_trigger_root = tmp_path / 'untriggered-maintenance'
    adapter_module.initialize_trial(no_trigger_root, no_trigger)
    no_trigger_adapter = adapter_module.FixtureAdapter(no_trigger_root)
    no_trigger_before = no_trigger_adapter.snapshot()
    no_trigger_result = no_trigger_adapter.call(request)
    assert not no_trigger_result['ok']
    assert no_trigger_adapter.snapshot() == no_trigger_before

    approved_bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    approval_root = tmp_path / 'rejected-approval'
    adapter_module.initialize_trial(approval_root, approved_bundle)
    approval_adapter = adapter_module.FixtureAdapter(approval_root)
    candidate = fixtures._index_text(False)
    staged = approval_adapter.call({
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': candidate,
    })
    assert staged['ok']
    approval = adapter_module.authorize_index_maintenance(
        approval_root,
        stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='synthetic-denial-1',
        approved=False,
    )
    before_promotion = approval_adapter.snapshot()
    denied = approval_adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })
    assert not denied['ok']
    assert approval_adapter.snapshot() == before_promotion
    assert approval_adapter.state['index']['last_verified_audit'] == (
        before_promotion['index']['last_verified_audit'])

    tamper_root = tmp_path / 'tampered-staged-candidate'
    adapter_module.initialize_trial(tamper_root, approved_bundle)
    tamper_adapter = adapter_module.FixtureAdapter(tamper_root)
    staged = tamper_adapter.call({
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': candidate,
    })
    assert staged['ok']
    approval = adapter_module.authorize_index_maintenance(
        tamper_root,
        stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='synthetic-approval-2',
        approved=True,
    )
    staged_path = tamper_root / 'controller' / 'staged-index.json'
    stored = json.loads(staged_path.read_text(encoding='utf-8'))
    stored['candidate_content'] += '# tampered after approval\n'
    staged_path.write_text(json.dumps(stored), encoding='utf-8')
    before_tampered_promotion = tamper_adapter.snapshot()
    rejected_tampering = tamper_adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })
    assert not rejected_tampering['ok']
    assert tamper_adapter.snapshot() == before_tampered_promotion


def test_maintenance_promotion_requires_exact_approval_id(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    root = tmp_path / 'mismatched-approval-id'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    staged = adapter.call({
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    })
    assert staged['ok']
    adapter_module.authorize_index_maintenance(
        root,
        stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='synthetic-approval-current',
        approved=True,
    )
    before = adapter.snapshot()

    rejected = adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': 'synthetic-approval-stale',
    })

    assert not rejected['ok']
    assert adapter.snapshot() == before
    assert adapter.state['index']['version'] == 'synthetic-v1'
    assert adapter.state['index']['content'] == before['index']['content']
    assert adapter.state['index']['last_verified_audit'] == (
        before['index']['last_verified_audit'])
    assert not any(event['op'] == 'promote_index_maintenance' and event['ok']
                   for event in adapter.trace)


def test_maintenance_stage_retry_recovers_lost_ack_without_rewriting(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    root = tmp_path / 'lost-stage-ack'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    request = {
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    }

    adapter.call(request)  # The controller persists the stage; the caller loses this reply.
    retry = adapter.call(request)

    assert retry['ok']
    assert retry['stage_id']
    assert retry['candidate_sha256']
    stage_events = [event for event in adapter.trace
                    if event['op'] == 'stage_index_maintenance']
    assert len(stage_events) == 2
    assert all(event['ok'] for event in stage_events)
    assert stage_events[0]['write_bytes'] == len(
        request['candidate_content'].encode('utf-8'))
    assert stage_events[1]['write_bytes'] == 0
    assert adapter.snapshot() == adapter.initial_state

    conflicting = {**request, 'candidate_content': request['candidate_content'] + '# changed\n'}
    rejected = adapter.call(conflicting)
    assert not rejected['ok']
    assert adapter.snapshot() == adapter.initial_state
    assert json.loads((root / 'controller' / 'staged-index.json').read_text(
        encoding='utf-8'))['candidate_sha256'] == retry['candidate_sha256']


def test_exact_maintenance_stage_retry_scores_and_promotes_on_same_adapter(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    root = tmp_path / 'scored-lost-stage-ack'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    initial = adapter.snapshot()
    request = {
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    }

    first = adapter.call(request)
    retry = adapter.call(request)
    assert first['ok'] and retry == first
    assert adapter.snapshot() == initial

    approval = adapter_module.authorize_index_maintenance(
        root, stage_id=first['stage_id'],
        candidate_sha256=first['candidate_sha256'],
        approval_id='synthetic-retry-approval', approved=True)
    promoted = adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': first['stage_id'],
        'candidate_sha256': first['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })
    assert promoted['ok']
    adapter.read_full('index')
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)

    result = score(bundle, adapter, answer, maintenance_approval=approval)

    assert result['status'] == 'passed', result['checks']
    assert result['checks']['read_trace_integrity']['passed']
    assert result['checks']['final_state_integrity']['passed']
    assert result['checks']['maintenance_transition']['passed']
    assert result['measurements']['writes']['maintenance_stage_attempts'] == 2
    assert result['measurements']['writes']['maintenance_stage_persisted_stages'] == 1
    assert result['measurements']['writes']['maintenance_stage_retries'] == 1
    assert result['measurements']['writes']['maintenance_stage_bytes'] == len(
        request['candidate_content'].encode('utf-8'))


def test_mutation_tool_schemas_are_closed_and_runtime_rejects_extra_fields(tmp_path):
    import contextlib
    import io
    import sys

    fixtures = load('fixtures')
    adapter_module = load('adapter')

    def listed_tools(root):
        incoming = json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list',
        }) + '\n'
        saved_stdin = sys.stdin
        output = io.StringIO()
        try:
            sys.stdin = io.StringIO(incoming)
            with contextlib.redirect_stdout(output):
                adapter_module.serve(root)
        finally:
            sys.stdin = saved_stdin
        return {tool['name']: tool['inputSchema'] for tool in
                json.loads(output.getvalue())['result']['tools']}

    save_bundle = fixtures.build_trial('amortized-update-audit', 'C')
    save_root = tmp_path / 'save-schema'
    adapter_module.initialize_trial(save_root, save_bundle)
    save_tools = listed_tools(save_root)
    assert save_tools['save_append']['additionalProperties'] is False
    save_adapter = adapter_module.FixtureAdapter(save_root)
    save_before = save_adapter.snapshot()
    authorization = save_bundle['gold']['update_authorization']
    save_rejected = save_adapter.call({
        'op': 'save_append',
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'append_text': authorization['append_text'],
        'unexpected': True,
    })
    assert not save_rejected['ok']
    assert save_adapter.snapshot() == save_before

    maintenance_bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    maintenance_root = tmp_path / 'maintenance-schema'
    adapter_module.initialize_trial(maintenance_root, maintenance_bundle)
    maintenance_tools = listed_tools(maintenance_root)
    for name in ('stage_index_maintenance', 'promote_index_maintenance'):
        assert maintenance_tools[name]['additionalProperties'] is False
    maintenance_adapter = adapter_module.FixtureAdapter(maintenance_root)
    maintenance_before = maintenance_adapter.snapshot()
    candidate = fixtures._index_text(False)
    stage_rejected = maintenance_adapter.call({
        'op': 'stage_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1', 'candidate_content': candidate,
        'unexpected': True,
    })
    assert not stage_rejected['ok']
    assert maintenance_adapter.snapshot() == maintenance_before

    staged = maintenance_adapter.call({
        'op': 'stage_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1', 'candidate_content': candidate,
    })
    approval = adapter_module.authorize_index_maintenance(
        maintenance_root, stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='synthetic-approval-schema', approved=True)
    before_promotion = maintenance_adapter.snapshot()
    promotion_rejected = maintenance_adapter.call({
        'op': 'promote_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1', 'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'], 'unexpected': True,
    })
    assert not promotion_rejected['ok']
    assert maintenance_adapter.snapshot() == before_promotion


def test_stdio_bridge_exposes_only_reads_and_returns_actual_heading_map(tmp_path):
    import contextlib
    import io
    import sys

    bundle, _ = trial(tmp_path)
    adapter_module = load('adapter')
    root = tmp_path / 'index-40k-C'
    incoming = '\n'.join([
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                    'params': {'protocolVersion': '2025-11-25'}}),
        json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}),
        json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                    'params': {'name': 'read_heading_map',
                               'arguments': {'record_id': 'index'}}}),
    ]) + '\n'
    saved_stdin = sys.stdin
    output = io.StringIO()
    try:
        sys.stdin = io.StringIO(incoming)
        with contextlib.redirect_stdout(output):
            adapter_module.serve(root)
    finally:
        sys.stdin = saved_stdin
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    tools = responses[1]['result']['tools']
    assert [tool['name'] for tool in tools] == [
        'read_full', 'read_heading_map', 'read_section',
    ]
    result = json.loads(responses[2]['result']['content'][0]['text'])
    assert result['record_id'] == 'index'
    assert result['version'] == 'synthetic-v1'
    assert len(result['headings']) == 18
    assert {level: sum(item['level'] == level for item in result['headings'])
            for level in (1, 2, 3)} == {1: 1, 2: 3, 3: 14}
    assert (root / 'agent' / 'public.json').exists()
    assert not (root / 'agent' / 'control.json').exists()



def test_stdio_bridge_rejects_malformed_tool_call_parameters(tmp_path):
    import contextlib
    import io
    import sys

    trial(tmp_path)
    root = tmp_path / 'index-40k-C'
    incoming = '\n'.join([
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {}}),
        json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': None}),
        json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                    'params': {'name': 'read_full', 'arguments': None}}),
    ]) + '\n'
    adapter_module = load('adapter')
    saved_stdin = sys.stdin
    output = io.StringIO()
    try:
        sys.stdin = io.StringIO(incoming)
        with contextlib.redirect_stdout(output):
            adapter_module.serve(root)
    finally:
        sys.stdin = saved_stdin

    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [response['id'] for response in responses] == [1, 2, 3]
    assert all(response['error']['code'] == -32602 for response in responses)
    events = root / 'controller' / 'events.jsonl'
    assert not events.exists() or not events.read_text(encoding='utf-8').strip()


def test_stdio_bridge_exposes_and_executes_only_the_authorized_synthetic_save(tmp_path):
    import contextlib
    import io
    import sys

    bundle, _ = trial(tmp_path, scenario='amortized-update-audit', candidate='A')
    root = tmp_path / 'amortized-update-audit-A'
    authorization = bundle['public']['authorized_synthetic_update']
    incoming = '\n'.join([
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}),
        json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                    'params': {'name': 'save_append', 'arguments': {
                        'record_id': authorization['record_id'],
                        'expected_version': authorization['expected_version'],
                        'append_text': authorization['append_text'],
                    }}}),
        json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                    'params': {'name': 'read_full', 'arguments': {
                        'record_id': authorization['record_id'],
                    }}}),
    ]) + '\n'
    adapter_module = load('adapter')
    saved_stdin = sys.stdin
    output = io.StringIO()
    try:
        sys.stdin = io.StringIO(incoming)
        with contextlib.redirect_stdout(output):
            adapter_module.serve(root)
    finally:
        sys.stdin = saved_stdin

    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert 'save_append' in [tool['name'] for tool in responses[0]['result']['tools']]
    saved = json.loads(responses[1]['result']['content'][0]['text'])
    readback = json.loads(responses[2]['result']['content'][0]['text'])
    assert saved['ok']
    assert readback['version'] == authorization['new_version']
    assert authorization['append_text'] in readback['content']


def test_heading_navigation_expands_to_full_authority_after_stale_anchor(tmp_path):
    bundle, adapter = trial(tmp_path, scenario='stale-pointer', candidate='D')
    headings = adapter.read_heading_map('index')['headings']
    topic_heading = next(item for item in headings if item['anchor'] == 'communication-topic')
    adapter.read_section('index', topic_heading['anchor'])
    stale = adapter.read_section('index', 'stale-anchor')
    assert stale is None
    adapter.read_full('topic-communication', reason='fallback')
    read_gold_authorities(adapter, bundle['gold'])
    answer = evidence_answer(bundle['gold'], adapter.state, adapter.trace)
    recovered = score(bundle, adapter, answer)
    assert recovered['status'] == 'passed'
    assert recovered['checks']['pointer_resolution']['passed']
    assert recovered['measurements']['reads']['fallback_full_reads'] == 1

    fixtures = load('fixtures')
    adapter_module = load('adapter')
    no_fallback_bundle = fixtures.build_trial('stale-pointer', 'D')
    root = tmp_path / 'no-fallback'
    adapter_module.initialize_trial(root, no_fallback_bundle)
    no_fallback = adapter_module.FixtureAdapter(root)
    no_fallback.read_heading_map('index')
    read_gold_authorities(no_fallback, no_fallback_bundle['gold'])
    complete_answer = evidence_answer(no_fallback_bundle['gold'],
                                     no_fallback.state, no_fallback.trace)
    rejected = score(no_fallback_bundle, no_fallback, complete_answer)
    assert rejected['status'] == 'failed'
    assert not rejected['checks']['pointer_resolution']['passed']
