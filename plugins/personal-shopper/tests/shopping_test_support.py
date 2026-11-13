"""Shared loaders for the Personal Shopper acceptance test modules."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "shopping"


def load_store():
    spec = importlib.util.spec_from_file_location("personal_shopper_synthetic_store", EVAL / "store.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_runner():
    sys.path.insert(0, str(EVAL))
    try:
        spec = importlib.util.spec_from_file_location("personal_shopper_synthetic_runner", EVAL / "run_trial.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def load_scorer():
    sys.path.insert(0, str(EVAL))
    try:
        spec = importlib.util.spec_from_file_location("personal_shopper_trial_scorer", EVAL / "score_trial.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)
