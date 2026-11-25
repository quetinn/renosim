# Tabulated data (engine)

All business constants live here as JSON/CSV files shipped inside the wheel — never hard-coded
in Python (CLAUDE.md §5). Every file MUST carry `source` and `date` fields; an unsourced value
is a blocking TODO, not a guess.

Planned files (Phase 1+):

| File | Content | Source |
|---|---|---|
| `u_values_default.json` | Default U-values per wall type × construction period | 3CL-DPE 2021 method (arrêté annex) |
| `climate_zones.json` | Monthly degree-hours, temperatures, solar data per zone H1a…H3 + altitude | 3CL conventional data |
| `system_efficiencies.json` | Generator efficiencies × age; heat-pump SCOP per zone | 3CL tables |
| `ventilation.json` | Conventional airflow rates per ventilation type | 3CL tables |
| `emission_factors.json` | gCO₂e/kWh per energy carrier | DPE 2021 convention / Base Carbone ADEME |
| `energy_prices.json` | €/kWh per energy carrier, dated | Regulated tariffs / public databases |
| `renovation_costs.json` | Cost ranges per renovation measure | ADEME / renovation cost observatories |
| `dpe_thresholds.json` | DPE label thresholds (primary energy and CO₂) | Arrêté DPE 2021 |
| `insulation_materials.json` | Design thermal conductivity λ per insulation material (R = e/λ) | Règles Th-Bât fascicule « Matériaux » ; convention 3CL λ=0,04 pour isolant inconnu |
| `solar_orientation.json` | Heating-season C1 averages per zone × orientation + Fe2 shading factors | Annexe 1 3CL-DPE 2021 §18.5 (C1) et §6.2.2.2.1 (Fe2) |
| `summer_comfort.json` | Passive summer-comfort indicator decision grid (3 levels) | Annexe 9 de l'arrêté DPE habitation du 31/03/2021 consolidé, §1.2 |
| `cooling.json` | Cooling chain parameters (SEER/EER, intermittence, Cin per inertia, 28 °C setpoint) | Annexe 1 3CL-DPE 2021 §10 |
| `conventions.json` | Engine conventions and calibrated parameters: default ceiling height, thermal-bridge surcharge (D-03), solar coefficient (D-06), boiler seasonal blend (D-08), default measure R, generator age → installation-period rules | Per entry; moved out of Python on 2026-11-25 (audit §4.11), values unchanged |
