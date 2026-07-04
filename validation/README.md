# Validation campaign (Phase 3)

Quantitative validation of the `renosim` engine against official DPE diagnoses from the ADEME
open database. Planned contents:

- `download_dpe.py` — download and sample the ADEME DPE dataset (API).
- `mapping.py` — ADEME fields → `renosim` models, with documented mapping choices and
  rejection-rate logging.
- `run_validation.py` — run the engine (conventional mode) on each dwelling, compute metrics:
  mean bias, MAE/MAPE on kWhep/m²/yr, label confusion matrix, exact and ±1-class agreement.
- `notebooks/` — exploration and figures.
- `report/` — technical validation note (Quarto).

**V1 success criterion:** ≥ 60 % exact label agreement and ≥ 90 % within ±1 class on the cleaned
sample (CLAUDE.md §7.2). Calibration iterations, if needed, are documented — they feed the report.

Validation-side code may use pandas/numpy freely: the stdlib-only constraint applies to
`engine/` only.
