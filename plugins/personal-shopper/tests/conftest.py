from pathlib import Path
import sys


test_directory = str(Path(__file__).resolve().parent)
if test_directory not in sys.path:
    sys.path.insert(0, test_directory)


def pytest_addoption(parser):
    group = parser.getgroup("personal-shopper-live")
    group.addoption(
        "--require-shopping-live",
        action="store_true",
        default=False,
        help="require fresh same-run host evidence for R25; missing evidence fails",
    )
    group.addoption(
        "--shopping-live-receipt",
        metavar="PATH",
        default=None,
        help="private, untracked receipt from the actual activated-skill host run",
    )
    group.addoption(
        "--shopping-host-capture",
        metavar="PATH",
        default=None,
        help="private complete JSONL host capture from the same activated-skill run",
    )
    native = parser.getgroup("personal-shopper-native")
    native.addoption(
        "--require-shopping-native",
        action="store_true",
        default=False,
        help="require provider-backed B12 preservation evidence; missing evidence fails",
    )
    native.addoption(
        "--shopping-native-config",
        metavar="PATH",
        default=None,
        help="private expected-resource and preservation configuration for B12",
    )
    native.addoption(
        "--shopping-native-capture",
        metavar="PATH",
        default=None,
        help="private host capture from the actual native-preservation skill run",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "shopping_live: requires private host activation evidence")
    config.addinivalue_line("markers", "shopping_native: requires private native-provider evidence")
