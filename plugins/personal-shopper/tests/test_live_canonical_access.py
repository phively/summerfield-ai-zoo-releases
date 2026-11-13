from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "evals" / "shopping" / "check_trial.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("personal_shopper_live_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.shopping_live
def test_live_canonical_grocery_access(request):
    receipt_path = request.config.getoption("--shopping-live-receipt")
    host_capture_path = request.config.getoption("--shopping-host-capture")
    config_path = os.environ.get("SHOPPING_LIVE_CONFIG")
    locator = os.environ.get("SHOPPING_CANONICAL_GROCERY_LOCATOR", "")
    run_id = os.environ.get("SHOPPING_LIVE_RUN_ID", "")
    key = os.environ.get("SHOPPING_LIVE_RECEIPT_KEY", "")
    required = request.config.getoption("--require-shopping-live")

    any_live_input = bool(receipt_path or host_capture_path or config_path or locator or run_id or key)
    if not any_live_input and not required:
        pytest.skip("R25 NOT RUN: private runtime identity, credentials, and activated-skill receipt were not supplied")
    if not any_live_input and required:
        pytest.fail("R25 BLOCKED: --require-shopping-live needs private configuration and a fresh host receipt")

    checker = load_checker()
    config, receipt, load_issues = checker.load_private_inputs(config_path, receipt_path)
    if load_issues:
        pytest.fail("R25 BLOCKED: " + ", ".join(load_issues))

    result = checker.validate_receipt(
        receipt,
        config,
        locator=locator,
        run_id=run_id,
        key=key,
        host_capture_path=host_capture_path,
    )
    if not result["accepted"]:
        pytest.fail("R25 NOT ACCEPTED (" + result["status"] + "): " + ", ".join(result["issues"]))

    assert result["status"] == "accepted"
