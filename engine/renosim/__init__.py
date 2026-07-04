"""renosim — simplified 3CL-DPE 2021 energy engine for French single-family homes.

Single source of truth for all energy, CO2 and cost calculations. Consumed by
the validation scripts (CPython) and by the web app through Pyodide. The engine
is stdlib-only so it ships as a pure-Python wheel loadable by micropip.
"""

from renosim.economics import ScenarioAssessment, assess_scenario, measure_cost_range
from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    OpaqueEnvelopeElement,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.renovation import (
    ALL_MEASURE_FACTORIES,
    DHWUpgrade,
    HeatingReplacement,
    RenovationMeasure,
    RoofInsulation,
    VentilationUpgrade,
    WallInsulation,
    WindowReplacement,
    apply_measures,
    predefined_bundles,
)
from renosim.simulation import SimulationResult, simulate

__version__ = "0.3.0"

#: Version of the JSON input/output schema exchanged with the front end.
#: Bumped on any breaking change to the interface (CLAUDE.md §3.2).
SCHEMA_VERSION = "0.1"

__all__ = [
    "ALL_MEASURE_FACTORIES",
    "CONVENTIONAL",
    "SCHEMA_VERSION",
    "AltitudeClass",
    "Building",
    "ClimateZone",
    "ConstructionPeriod",
    "DHWGeneratorType",
    "DHWSystem",
    "DHWUpgrade",
    "EnergyCarrier",
    "HeatingGeneratorType",
    "HeatingReplacement",
    "HeatingSystem",
    "OccupancyScenario",
    "OpaqueEnvelopeElement",
    "RenovationMeasure",
    "RoofInsulation",
    "ScenarioAssessment",
    "SimulationResult",
    "VentilationSystem",
    "VentilationType",
    "VentilationUpgrade",
    "WallInsulation",
    "Window",
    "WindowReplacement",
    "__version__",
    "apply_measures",
    "assess_scenario",
    "engine_info",
    "measure_cost_range",
    "predefined_bundles",
    "simulate",
]


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
