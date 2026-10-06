import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD = os.path.abspath(os.path.join(_HERE, "..", "..", "package", "agent-hold-em", "dashboard"))
if _DASHBOARD not in sys.path:
    sys.path.insert(0, _DASHBOARD)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: exhaustive/long-running tests (deselect with -m 'not slow')")
