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


class TestCeilingHeight:
    """Declared ceiling height vs the 3CL §4 infiltration (audit 2026-11-25 §4.10).

    In the 3CL formula Hsp cancels out: n50 = Q4Pa/((4/50)^(2/3)*Hsp*Sh), so
    Hsp*n50 and therefore both the unbalance term and Qvinf = Hsp*Sh*n50*e/...
    do not depend on Hsp. The declared height only acts on intermittence
    (test_systems.py).
    """

    def test_unset_equals_conventional_2_5_m(self) -> None:
        unset = envelope_heat_loss(make_reference_building(**_bare_house_kwargs()))
        explicit = envelope_heat_loss(
            make_reference_building(**_bare_house_kwargs(), ceiling_height_m=2.5)
        )
        assert unset == explicit

    @pytest.mark.parametrize(
        "ventilation",
        [VentilationType.NATURAL, VentilationType.EXHAUST_ONLY_MANUAL],
    )
    def test_infiltration_is_height_independent(self, ventilation: VentilationType) -> None:
        vmc = VentilationSystem(ventilation_type=ventilation)
        low = envelope_heat_loss(
            make_reference_building(**_bare_house_kwargs(), ventilation_system=vmc)
        )
        high = envelope_heat_loss(
            make_reference_building(
                **_bare_house_kwargs(), ventilation_system=vmc, ceiling_height_m=3.0
            )
        )
        assert high.infiltration_w_per_k == pytest.approx(low.infiltration_w_per_k)

    def test_nonpositive_height_rejected(self) -> None:
        with pytest.raises(ValueError, match="ceiling_height_m"):
            make_reference_building(**_bare_house_kwargs(), ceiling_height_m=0.0)


def test_uninsulated_wall_u_from_material_hand_computed() -> None:
    """Umur0 by material and thickness (3CL §3.2.1.2, p.14-15), Umur_nu = min(Umur0; 2.5).

    The thickness takes the largest tabulated column not above it:
      stone 50 cm -> 2.05 ; stone 52 cm -> 2.05 ; stone 15 cm -> 3.2 capped at 2.5
      hollow brick 30 cm -> 28 cm column 1.68 ; hollow concrete block 20 cm -> 2.8 -> 2.5
      rammed earth 60 cm -> 1.35 ; log wall 30 cm -> 0.8 ; solid brick 34 cm -> 2.0
    """
    from renosim.envelope import WALL_MATERIALS, uninsulated_wall_u

    cases = (
        ("stone", 50.0, 2.05),
        ("stone", 52.0, 2.05),
        ("stone", 15.0, 2.5),
        ("hollow_brick", 30.0, 1.68),
        ("hollow_concrete_block", 20.0, 2.5),
        ("rammed_earth", 60.0, 1.35),
        ("log_wall", 30.0, 0.8),
        ("solid_brick", 34.0, 2.0),
    )
    for material, thickness, expected in cases:
        assert uninsulated_wall_u(material, thickness) == pytest.approx(expected)
    assert "stone" in WALL_MATERIALS
    with pytest.raises(ValueError, match="wall material"):
        uninsulated_wall_u("cardboard", 20.0)


def test_linear_thermal_bridges_hand_computed() -> None:
    """Linear thermal bridges (3CL §3.4, p.35-37), default joinery: in tunnel,
    5 cm frame, no insulation return. Window perimeter convention: square
    1.5 m2 windows -> 4/sqrt(1.5) = 3.26599 m per m2 of window.

    Case 1 — single level, uninsulated walls and floor, light ceiling,
    perimeter 40 m, windows 15 m2 (perimeter 48.990 m):
      k_pb(NI, NI) 0.39 * 40 = 15.600 ; no intermediate floor ; light ceiling -> 0
      k_men(NI, tunnel, Lp 5) 0.31 * 48.990 = 15.187  ->  PT = 30.787 W/K
    Case 2 — two levels, ITI walls, ITE floor, heavy ITE ceiling, perimeter 30 m,
    windows 10 m2 (32.660 m):
      k_pb(ITI, ITE) 0.71 * 30 = 21.300 ; k_pi(ITI) 0.92 * 30 = 27.600
      k_ph(ITI, ITE) 0.75 * 30 = 22.500 ; k_men(ITI w/o return) 0.31 * 32.660 = 10.125
      -> PT = 81.525 W/K
    Case 3 — timber-frame walls: no wall junction counts (§3.4.1-3.4.5) -> 0.
    """
    from renosim.envelope import linear_thermal_bridges_w_per_k
    from renosim.models import InsulationLayout, ThermalBridgeInputs

    case1 = ThermalBridgeInputs(
        exposed_perimeter_m=40.0,
        levels=1,
        window_area_m2=15.0,
        wall_insulation=InsulationLayout.NONE,
        floor_insulation=InsulationLayout.NONE,
        roof_insulation=InsulationLayout.ITE,
    )
    assert linear_thermal_bridges_w_per_k(case1) == pytest.approx(30.787, abs=0.001)
    case2 = ThermalBridgeInputs(
        exposed_perimeter_m=30.0,
        levels=2,
        window_area_m2=10.0,
        wall_insulation=InsulationLayout.ITI,
        floor_insulation=InsulationLayout.ITE,
        roof_insulation=InsulationLayout.ITE,
        heavy_ceiling=True,
    )
    assert linear_thermal_bridges_w_per_k(case2) == pytest.approx(81.525, abs=0.001)
    case3 = ThermalBridgeInputs(
        exposed_perimeter_m=40.0,
        levels=2,
        window_area_m2=15.0,
        wall_insulation=InsulationLayout.ITR,
        floor_insulation=InsulationLayout.NONE,
        roof_insulation=InsulationLayout.NONE,
        heavy_walls=False,
    )
    assert linear_thermal_bridges_w_per_k(case3) == 0.0


def test_default_insulation_layout_3cl_3_4() -> None:
    """Unknown insulation (§3.4): before 1975 uninsulated; from 1975 walls ITI,
    ceilings ITE, floors ITE. Declared states win."""
    from renosim.envelope import default_insulation_layout
    from renosim.models import InsulationLayout

    old, recent = ConstructionPeriod.Y1948_1974, ConstructionPeriod.Y1989_2000
    assert default_insulation_layout("wall", None, old) is InsulationLayout.NONE
    assert default_insulation_layout("wall", None, recent) is InsulationLayout.ITI
    assert default_insulation_layout("roof", None, recent) is InsulationLayout.ITE
    assert default_insulation_layout("floor", None, recent) is InsulationLayout.ITE
    assert default_insulation_layout("wall", True, old) is InsulationLayout.ITI
    assert default_insulation_layout("roof", False, recent) is InsulationLayout.NONE
