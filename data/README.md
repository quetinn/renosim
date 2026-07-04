# Data directory

**No raw data is ever committed to this repository** (CLAUDE.md §5, rule 6). This directory only
documents provenance; `.gitignore` excludes everything else in it.

## ADEME DPE database (validation only)

- **Dataset:** « DPE logements existants (depuis juillet 2021) », data.ademe.fr.
- **Access:** ADEME open-data API (exact endpoint verified at implementation time — Phase 3).
- **Usage:** validation campaign only (`validation/`). Never embedded in the web app.
- **Sampling:** single-family homes, DPE 2021+, sufficiently complete technical fields;
  target 5,000–20,000 rows after cleaning, stratified by construction period × climate zone ×
  heating energy.

To reproduce the validation sample, run `validation/download_dpe.py` (Phase 3).
