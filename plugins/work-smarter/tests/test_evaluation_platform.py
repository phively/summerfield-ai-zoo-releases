"""Real process and lock checks for evaluation portability boundaries."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


EVALS = Path(__file__).resolve().parents[1] / 'evals'


def load_support():
    spec = importlib.util.spec_from_file_location('test_platform_support', EVALS / 'platform_support.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object integration')
@pytest.mark.parametrize('parent_exits', [False, True])
def test_windows_job_reaps_descendant_even_after_parent_exit(parent_exits):
    support = load_support()
    script = (
        'import subprocess,sys,time\n'
        'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],'
        'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
        'print(child.pid,flush=True)\n'
        + ('sys.exit(0)\n' if parent_exits else 'time.sleep(30)\n')
    )
    process = support.start_process([sys.executable, '-c', script], stdout=subprocess.PIPE, text=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    child_handle = None
    try:
        child_pid = int(process.stdout.readline())
        child_handle = kernel.OpenProcess(0x100000, False, child_pid)  # SYNCHRONIZE
        assert child_handle, ctypes.get_last_error()
        if parent_exits:
            assert process.wait(timeout=5) == 0
            support.close_process(process)
        else:
            support.terminate_process_group(process)
        assert kernel.WaitForSingleObject(child_handle, 5000) == 0
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            support.terminate_process_group(process)
        support.close_process(process)
        process.stdout.close()
        if child_handle:
            kernel.CloseHandle(child_handle)


@pytest.mark.skipif(os.name != 'nt', reason='Windows suspended-process setup failure')
@pytest.mark.parametrize('phase', ['assignment', 'resume'])
def test_windows_startup_failure_kills_suspended_child_and_closes_job(tmp_path, monkeypatch, phase):
    support = load_support()
    captured = {}
    original_bind = support._WindowsJob.assign_and_resume
    failure = OSError('injected job assignment failure')

    def bind(job, process):
        captured.update(job=job, process=process)
        if phase == 'assignment':
            raise failure
        return original_bind(job, process)

    def failed_resume(thread):
        ctypes.set_last_error(5)
        return 0xFFFFFFFF

    monkeypatch.setattr(support._WindowsJob, 'assign_and_resume', bind)
    if phase == 'resume':
        monkeypatch.setattr(support._kernel, 'ResumeThread', failed_resume)
    marker = tmp_path / 'must-not-run'
    command = [sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).write_text("ran")']
    with pytest.raises(OSError) as raised:
        support.start_process(command)
    if phase == 'assignment':
        assert raised.value is failure
    else:
        assert raised.value.winerror == 5
    assert captured['process'].poll() is not None
    assert captured['job'].handle is None
    assert not marker.exists()


def test_concurrent_ledger_reservations_are_not_lost(tmp_path):
    runner = EVALS / 'remember-me-benchmark' / 'run_study.py'
    script = (
        'import importlib.util,sys\n'
        f'spec=importlib.util.spec_from_file_location("study",{str(runner)!r})\n'
        'study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)\n'
        'study.reserve_launch(sys.argv[1],sys.argv[2],"prepare")\n'
    )
    processes = [subprocess.Popen(
        [sys.executable, '-c', script, str(tmp_path), f'trial-{number}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) for number in range(8)]
    try:
        for process in processes:
            _, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait()
    ledger = json.loads((tmp_path / 'launch-ledger.json').read_text(encoding='utf-8'))
    assert sorted(row['sequence'] for row in ledger['launches']) == list(range(1, 9))
    assert {row['trial_id'] for row in ledger['launches']} == {f'trial-{n}' for n in range(8)}


def test_atomic_replace_retries_only_windows_sharing_errors(tmp_path, monkeypatch):
    support = load_support()
    monkeypatch.setattr(support, 'IS_WINDOWS', True)
    source, target = tmp_path / 'new', tmp_path / 'old'
    source.write_bytes(b'new')
    target.write_bytes(b'old')
    real_replace = Path.replace
    attempts = []

    def sharing_violation(path, destination):
        attempts.append(1)
        if len(attempts) < 3:
            error = PermissionError('temporarily held by another Windows reader')
            error.winerror = 32
            raise error
        return real_replace(path, destination)

    monkeypatch.setattr(Path, 'replace', sharing_violation)
    monkeypatch.setattr(support.time, 'sleep', lambda delay: None)
    support.atomic_replace(source, target)
    assert len(attempts) == 3
    assert target.read_bytes() == b'new'


def test_atomic_replace_does_not_hide_persistent_failure(tmp_path, monkeypatch):
    support = load_support()
    monkeypatch.setattr(support, 'IS_WINDOWS', True)
    source, target = tmp_path / 'new', tmp_path / 'old'
    source.write_bytes(b'new')
    target.write_bytes(b'old')
    attempts = []

    def denied(path, destination):
        attempts.append(1)
        error = PermissionError('persistent access denial')
        error.winerror = 5
        raise error

    monkeypatch.setattr(Path, 'replace', denied)
    monkeypatch.setattr(support.time, 'sleep', lambda delay: None)
    with pytest.raises(PermissionError):
        support.atomic_replace(source, target)
    assert len(attempts) == 20
    assert target.read_bytes() == b'old'
    assert source.read_bytes() == b'new'
