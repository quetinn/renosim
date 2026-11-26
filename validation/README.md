# Validation campaign

Quantitative validation of the `renosim` engine against official DPE diagnoses from the ADEME
open database (dataset `dpe03existant`, Licence Ouverte v2.0). The results and their reading are
in the validation note: [`report/note_validation.md`](report/note_validation.md), also published
as an HTML page with the app (`<site>/validation/`).

| Script | Role |
|---|---|
| `download_dpe.py` | Stratified sample through the ADEME API (`--random` for an independent test sample, `--exclude` to keep it disjoint) |
| `mapping.py` | ADEME fields → `renosim` building, with the documented mapping choices M-1 to M-11 and rejection logging |
| `run_validation.py` | Runs the engine (conventional mode) and computes bias, MAE/MAPE, confusion matrix, exact and ±1-class agreement; optional bootstrap, post-stratification and per-year breakdown |
| `stratum_counts.py` | Number of DPE per stratum in the ADEME dataset (post-stratification weights) |
| `enrich_sample.py` | Extra fields per DPE (method version, per-use consumptions) in a sidecar file |
| `analyze_bias.py` | Bias by DPE method version and by end use |
| `run_summer_comfort.py`, `run_cooling_validation.py` | Summer-comfort and cooling campaigns |
| `make_figures.py` | Figures of the note, from the committed result files only |

Raw ADEME data is never committed (`data/` is gitignored): the scripts download it again. The
committed files in `report/` are aggregates. Exact commands: §8 of the note.

**V1 success criterion:** ≥ 60 % exact label agreement and ≥ 90 % within ±1 class (CLAUDE.md
§7.2). Status at v1.0: met on the DPE of the current method version (93.6 % within ±1 class), not
on the whole independent test sample (87.0 %). The protocol of the next calibration is announced
in §7 of the note.

Validation-side code may use pandas, numpy or matplotlib (`requirements.txt`): the stdlib-only
constraint applies to `engine/` only.
