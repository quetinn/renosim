# RénoSim — Simulateur de rénovation énergétique résidentielle

> ⚠️ **Projet en construction (Phase 1 terminée — moteur cœur).** Les gestes de rénovation, la
> validation ADEME et l'application arrivent dans les phases suivantes (feuille de route ci-dessous).
> Démo en ligne (placeholder) : <https://quetinn.github.io/renosim/>

**RénoSim** est un simulateur open-source de rénovation énergétique pour maisons individuelles
françaises. Décrivez votre logement, obtenez une estimation de sa performance (consommation,
émissions CO₂, étiquette DPE), puis comparez des gestes de rénovation — seuls ou en bouquets —
avec coûts, économies annuelles et temps de retour.

**Ce qui distingue ce projet :**

1. **Un moteur physique** inspiré de la méthode réglementaire 3CL-DPE 2021 (simplifiée, écarts
   documentés dans [`docs/deviations.md`](docs/deviations.md)), implémenté en Python pur, testé.
2. **Une validation quantitative** contre la base des DPE de l'ADEME (plusieurs milliers de
   logements), avec note technique publiée.
3. **Aucun backend** : le moteur Python s'exécute dans le navigateur via
   [Pyodide](https://pyodide.org). Une seule implémentation du calcul, une app 100 % statique.
   Vos données ne quittent jamais votre navigateur.

> 🛈 **Outil pédagogique** — RénoSim ne remplace ni un DPE officiel ni un audit énergétique.
> Pour un accompagnement réel : [France Rénov'](https://france-renov.gouv.fr).

## Architecture

```
Navigateur : App React (Vite, TS)  ◄──JSON──►  Pyodide (package Python `renosim`)
Développement : même package `renosim` + scripts de validation contre la base DPE ADEME
```

- `engine/` — le moteur de calcul (`renosim`), Python ≥ 3.11, stdlib uniquement, wheel pure-Python.
- `tests/` — tests unitaires, cas de référence, propriétés invariantes (pytest).
- `validation/` — campagne de validation contre la base DPE ADEME + note technique.
- `app/` — application web (Vite + React + TypeScript), déployée sur GitHub Pages.
- `docs/` — écarts à la méthode 3CL ([`deviations.md`](docs/deviations.md)), journal de bord.

## Développement

```bash
# Moteur
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -e "engine[dev]"
pytest
ruff check . && mypy engine/renosim

# App
cd app
npm install
npm run dev
```

## Feuille de route

- [x] **Phase 0** — Scaffolding : structure, CI, app vide déployée
- [x] **Phase 1** — Moteur cœur : enveloppe, besoins, systèmes, étiquettes, 2 modes
- [x] **Phase 2** — Gestes de rénovation & économie
- [ ] **Phase 3** — Validation contre la base DPE ADEME + note technique
- [ ] **Phase 4** — App React + Pyodide (3 écrans)
- [ ] **Phase 5** — Consolidation, docs, v1.0

**Hors périmètre V1** (extensions futures) : appartements et collectif, calcul des aides
financières (lien France Rénov' uniquement), confort d'été/climatisation, photovoltaïque,
distinction ITE/ITI, actualisation financière (VAN/TRI), export PDF.

## Licence

[MIT](LICENSE) — © 2026 Noé Quetin. Projet personnel réalisé dans le cadre d'une spécialisation
en énergies renouvelables et efficacité énergétique.
