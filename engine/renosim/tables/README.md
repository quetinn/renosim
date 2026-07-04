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
