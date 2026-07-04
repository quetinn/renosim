# Journal de bord

## 2026-07-04 — Phase 0 : scaffolding

**Fait :**

- Dépôt git initialisé (branche `main`), structure complète conforme au brief (§3.1) :
  `engine/renosim` (+ `tables/`), `tests/`, `validation/`, `app/`, `data/`, `docs/`, workflows.
- **Packaging** : le `pyproject.toml` du package vit dans `engine/` (build hatchling, wheel
  pure-Python vérifié : `renosim-0.1.0-py3-none-any.whl`) pour que `pip install -e engine`
  fonctionne comme prévu en §10. Le `pyproject.toml` racine ne contient que la config outils
  (ruff, mypy strict, pytest, coverage). Écart mineur vs §3.1 (qui plaçait tout à la racine) —
  les deux exigences étaient incompatibles, celle de §10 a été retenue.
- `renosim.__init__` expose `__version__`, `SCHEMA_VERSION` et `engine_info()` (smoke test du
  futur pont JS↔Python).
- Tests : `tests/test_smoke.py` (import + contrat `engine_info`) — 2 verts, couverture 100 %.
  Le seuil `fail_under` de coverage est à 0 pour la Phase 0 ; à monter à 85 en Phase 1.
- Lint/typage : ruff (check + format) et mypy strict passent en local.
- CI (`.github/workflows/ci.yml`) : job engine (ruff, mypy, pytest, build wheel + assertion
  pure-Python) + job app (npm ci, tsc, vite build).
- Déploiement (`.github/workflows/deploy.yml`) : build du wheel → `app/public/wheels/` (préparé
  pour micropip en Phase 4), build Vite avec `VITE_BASE=/<repo>/`, déploiement GitHub Pages.
- App Vite + React 19 + TS strict : placeholder FR avec avertissement « outil pédagogique » et
  mention vie privée. Build local OK.
- Docs : `docs/deviations.md` créé et pré-alimenté (D-01 à D-05, écarts déjà actés par le brief),
  `data/README.md` (provenance ADEME, aucune donnée committée), `validation/README.md`,
  `README.md` racine avec feuille de route, LICENSE MIT, `.editorconfig`, `.pre-commit-config.yaml`.

**Pièges rencontrés (Windows) :**

- Le chemin du projet contient des accents (« Noé ») : Python 3.11 lit les fichiers `.pth` en
  encodage locale (cp1252), ce qui casse l'install editable (`ModuleNotFoundError: renosim`).
  Correctif appliqué : réécriture du `.pth` du venv avec le chemin court 8.3 (ASCII). **À refaire
  après tout `pip install -e engine`** tant que le projet reste dans ce dossier ; corrigé
  nativement à partir de Python 3.13, ou en déplaçant le projet vers un chemin sans accents
  (recommandé).
- Node.js n'était pas installé ; l'installation winget (MSI) attend une élévation admin.
  Un Node portable v24 a servi pour cette session. **Installer Node LTS de façon permanente**
  avant la Phase 4 (ou valider l'invite UAC de winget).

**État des tests :** 2/2 verts (smoke), ruff OK, mypy strict OK, wheel pure-Python OK,
`npm run build` OK. CI non encore exécutée (pas de remote GitHub configuré).

**Prochaines étapes :**

1. Créer le dépôt GitHub, pousser `main`, vérifier CI verte et activer Pages (source :
   GitHub Actions) — dernier critère de sortie de la Phase 0.
2. Phase 1 : encoder les tables §5 (sources arrêté DPE 2021 à vérifier au moment du codage),
   puis `models.py` → `envelope.py` → `needs.py` → `systems.py` → `outputs.py` → `occupancy.py`,
   tests d'abord (valeurs calculées à la main).
