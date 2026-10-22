import copy
import importlib.util
import json
from pathlib import Path

import pytest


EVAL = Path(__file__).resolve().parents[1] / 'evals' / 'remember-me-benchmark'


def load(name):
    spec = importlib.util.spec_from_file_location(
        f'remember_me_adapter_fail_closed_{name}', EVAL / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staged_trial(tmp_path):
    fixtures = load('fixtures')
    adapter_module = load('adapter')
    bundle = fixtures.build_trial(
        'index-maintenance-40k', 'C', trigger_threshold_kib=8)
    root = tmp_path / 'trial'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    request = {
        'op': 'stage_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    }
    staged = adapter.call(request)
    assert staged['ok']
    return adapter_module, root, adapter, request, staged


def corrupt_staged_candidate(root):
    staged_path = root / 'controller' / 'staged-index.json'
    malformed_bytes = b'\xff\xfe'
    staged_path.write_bytes(malformed_bytes)
    return staged_path, malformed_bytes


def test_malformed_utf8_stage_file_is_rejected_without_overwrite(tmp_path):
    _, root, adapter, request, _ = staged_trial(tmp_path)
    before = copy.deepcopy(adapter.state)
    staged_path, malformed_bytes = corrupt_staged_candidate(root)

    result = adapter.call(request)

    assert not result['ok']
    assert adapter.state == before
    assert staged_path.read_bytes() == malformed_bytes
    assert adapter.trace[-1]['ok'] is False


def test_malformed_utf8_stage_file_blocks_promotion_without_mutation(tmp_path):
    adapter_module, root, adapter, _, staged = staged_trial(tmp_path)
    approval = adapter_module.authorize_index_maintenance(
        root,
        stage_id=staged['stage_id'],
        candidate_sha256=staged['candidate_sha256'],
        approval_id='malformed-stage-approval',
        approved=True,
    )
    before = copy.deepcopy(adapter.state)
    staged_path, malformed_bytes = corrupt_staged_candidate(root)

    result = adapter.call({
        'op': 'promote_index_maintenance',
        'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'stage_id': staged['stage_id'],
        'candidate_sha256': staged['candidate_sha256'],
        'approval_id': approval['approval_id'],
    })

    assert not result['ok']
    assert adapter.state == before
    assert staged_path.read_bytes() == malformed_bytes
    assert adapter.trace[-1]['ok'] is False
    assert adapter.read_full('index')['version'] == 'synthetic-v1'


def test_malformed_utf8_stage_file_rejects_controller_approval(tmp_path):
    adapter_module, root, _, _, staged = staged_trial(tmp_path)
    staged_path, malformed_bytes = corrupt_staged_candidate(root)
    control_path = root / 'controller' / 'control.json'
    receipt_path = root / 'controller' / 'receipt.json'
    before_control = control_path.read_bytes()
    before_receipt = receipt_path.read_bytes()

    with pytest.raises(ValueError, match='staged candidate is not readable JSON'):
        adapter_module.authorize_index_maintenance(
            root,
            stage_id=staged['stage_id'],
            candidate_sha256=staged['candidate_sha256'],
            approval_id='malformed-stage-approval',
            approved=True,
        )

    assert staged_path.read_bytes() == malformed_bytes
    assert control_path.read_bytes() == before_control
    assert receipt_path.read_bytes() == before_receipt
