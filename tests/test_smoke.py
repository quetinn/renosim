"""Phase 0 smoke tests: the package installs, imports and identifies itself.

Real engine tests (envelope, needs, systems, reference cases) arrive in Phase 1.
"""

import renosim


def test_package_imports_and_has_version() -> None:
    assert renosim.__version__ == "0.1.0"


def test_engine_info_contract() -> None:
    info = renosim.engine_info()
    assert info["name"] == "renosim"
    assert info["version"] == renosim.__version__
    assert info["schema_version"] == renosim.SCHEMA_VERSION
