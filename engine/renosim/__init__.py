"""renosim — simplified 3CL-DPE 2021 energy engine for French single-family homes.

Single source of truth for all energy, CO2 and cost calculations. Consumed by
the validation scripts (CPython) and by the web app through Pyodide. The engine
is stdlib-only so it ships as a pure-Python wheel loadable by micropip.

Public API is re-exported here; internal module layout may change.
"""

__version__ = "0.1.0"

#: Version of the JSON input/output schema exchanged with the front end.
#: Bumped on any breaking change to the interface (CLAUDE.md §3.2).
SCHEMA_VERSION = "0.1"


def engine_info() -> dict[str, str]:
    """Return engine identification, used as a smoke test across the JS bridge.

    Returns
    -------
    dict[str, str]
        Mapping with ``name``, ``version`` and ``schema_version`` keys.
    """
    return {
        "name": "renosim",
        "version": __version__,
        "schema_version": SCHEMA_VERSION,
    }
