"""Smoke tests: the package installs, imports and identifies itself."""

import renosim


def test_package_imports_and_has_version() -> None:
    assert renosim.__version__ == "0.2.0"


def test_engine_info_contract() -> None:
    info = renosim.engine_info()
    assert info["name"] == "renosim"
    assert info["version"] == renosim.__version__
    assert info["schema_version"] == renosim.SCHEMA_VERSION
