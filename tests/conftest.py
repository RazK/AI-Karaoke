import pytest


def pytest_addoption(parser):
    parser.addoption("--smoke", action="store_true", default=False)
    parser.addoption("--full", action="store_true", default=False)
    parser.addoption("--yes", action="store_true", default=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: real API call — pass --smoke to run")
    config.addinivalue_line("markers", "full: full acceptance matrix — pass --full --yes to run")


def pytest_collection_modifyitems(config, items):
    smoke_ok = config.getoption("--smoke") or config.getoption("--full")
    full_ok = config.getoption("--full") and config.getoption("--yes")

    skip_smoke = pytest.mark.skip(reason="pass --smoke (or --full --yes) to run real API tests")
    skip_full = pytest.mark.skip(reason="pass --full --yes to run the full acceptance matrix")

    for item in items:
        if "smoke" in item.keywords and not smoke_ok:
            item.add_marker(skip_smoke)
        if "full" in item.keywords and not full_ok:
            item.add_marker(skip_full)
