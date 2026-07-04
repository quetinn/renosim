"""Tests for renosim.envelope — heat-loss coefficient GV and its breakdown.

Hand-computed reference (see test_gv_hand_computed):
House: 100 m2 living area, Hsp default 2.5 m, walls 120 m2 U=2.5, roof (combles)
100 m2 U=2.5, floor 100 m2 U=2.0, windows 15 m2 Uw=4.8, all b=1, natural
ventilation ("ouverture des fenêtres"), built 1948-1974, several exposed facades.

Surface losses = 120*2.5 + 100*2.5 + 100*2.0 + 15*4.8 = 300 + 250 + 200 + 72
               = 822 W/K
Thermal bridges (V1 flat 8 % of surface losses) = 0.08 * 822 = 65.76 W/K
Hvent = 0.34 * Qvarep * Sh = 0.34 * 1.2 * 100 = 40.8 W/K
Infiltration:
  Sdep (walls+roof+windows, floor excluded) = 120 + 100 + 15 = 235 m2
  Q4Pa_env = 2.2 * 235 = 517 m3/h
  Q4Pa = 517 + 0.45 * Smea(=0) * Sh = 517
  n50 = Q4Pa / ((4/50)^(2/3) * Hsp * Sh) = 517 / (0.185664 * 250) = 11.1382 h-1
  Qvasouf=Qvarep=1.2 -> delta=0, e=0.07, f=15
  Qvinf = 2.5*100*11.1382*0.07 / sqrt(1 + (15/0.07)*0^2) = 194.92 m3/h
  Hperm = 0.34 * 194.92 = 66.27 W/K
GV = 822 + 65.76 + 40.8 + 66.27 = 994.83 W/K
"""

import pytest

from renosim.envelope import default_u_values, envelope_heat_loss
from renosim.models import (
    ClimateZone,
    ConstructionPeriod,
    OpaqueEnvelopeElement,
    VentilationSystem,
    VentilationType,
    Window,
)
from tests.test_models import make_reference_building


def _bare_house_kwargs() -> dict[str, object]:
    return {
        "walls": (OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=2.5),),
        "roof": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=2.5),
        "floor": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=2.0),
        "windows": (Window(area_m2=15.0, u_value_w_per_m2k=4.8, solar_factor=0.56),),
        "construction_period": ConstructionPeriod.Y1948_1974,
    }


def test_gv_hand_computed() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    losses = envelope_heat_loss(building)

    assert losses.surface_w_per_k == pytest.approx(822.0)
    assert losses.thermal_bridges_w_per_k == pytest.approx(65.76)
    assert losses.ventilation_w_per_k == pytest.approx(40.8)
    assert losses.infiltration_w_per_k == pytest.approx(66.27, abs=0.05)
    assert losses.gv_w_per_k == pytest.approx(994.83, abs=0.1)


def test_b_coefficient_reduces_losses() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    kwargs = _bare_house_kwargs()
    kwargs["floor"] = OpaqueEnvelopeElement(
        area_m2=100.0, u_value_w_per_m2k=2.0, unheated_space_reduction_coefficient=0.8
    )
    reduced = make_reference_building(**kwargs)
    # floor loss drops from 200 to 160 W/K; bridges follow surface losses
    delta = envelope_heat_loss(building).gv_w_per_k - envelope_heat_loss(reduced).gv_w_per_k
    assert delta == pytest.approx(40.0 * 1.08)


def test_mechanical_ventilation_changes_flows() -> None:
    kwargs = _bare_house_kwargs()
    building_natural = make_reference_building(**kwargs)
    building_hygro_b = make_reference_building(
        **kwargs,
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.EXHAUST_ONLY_HYGRO_B),
    )
    natural = envelope_heat_loss(building_natural)
    hygro = envelope_heat_loss(building_hygro_b)
    # hygro B (before_2001 bracket for a 1948-74 house): Qvarep 1.36 vs 1.2
    assert hygro.ventilation_w_per_k == pytest.approx(0.34 * 1.36 * 100.0)
    assert hygro.ventilation_w_per_k > natural.ventilation_w_per_k
    # but balanced mechanical extract keeps infiltration lower than window airing
    assert hygro.infiltration_w_per_k != natural.infiltration_w_per_k


def test_default_u_values_lookup() -> None:
    # 1948-74 uninsulated house: wall U_nu = 2.5, floor U0 = 2.0, roof U0 = 2.5
    defaults = default_u_values(
        ConstructionPeriod.Y1948_1974, ClimateZone.H1A, insulated=False, electric_joule=False
    )
    assert defaults.wall == 2.5
    assert defaults.floor == 2.0
    assert defaults.roof == 2.5

    # Insulated at unknown date, pre-1975 construction -> 75-77 row (H1, autres): wall 1.0
    insulated = default_u_values(
        ConstructionPeriod.Y1948_1974, ClimateZone.H1A, insulated=True, electric_joule=False
    )
    assert insulated.wall == 1.0
    assert insulated.roof == 0.5
    assert insulated.floor == 0.9

    # RT2012-era house, H3, joule
    recent = default_u_values(
        ConstructionPeriod.AFTER_2013, ClimateZone.H3, insulated=True, electric_joule=True
    )
    assert recent.wall == 0.25
    assert recent.roof == 0.14
    assert recent.floor == 0.25


def test_insulation_never_increases_gv() -> None:
    """Invariant: adding insulation resistance must never increase GV."""
    kwargs = _bare_house_kwargs()
    building = make_reference_building(**kwargs)
    kwargs["walls"] = (
        OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=1.0 / (1.0 / 2.5 + 3.7)),
    )
    insulated = make_reference_building(**kwargs)
    assert envelope_heat_loss(insulated).gv_w_per_k < envelope_heat_loss(building).gv_w_per_k
