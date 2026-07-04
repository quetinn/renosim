"""Loader for the tabulated data shipped inside the package (engine/renosim/tables)."""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any


@cache
def load_table(name: str) -> dict[str, Any]:
    """Load a JSON table bundled with the package, cached after first read.

    Parameters
    ----------
    name
        Base file name without extension, e.g. ``"climate_zones"``.

    Returns
    -------
    dict[str, Any]
        Parsed JSON content, including its ``_meta`` provenance block.
    """
    resource = files("renosim.tables").joinpath(f"{name}.json")
    with resource.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data
