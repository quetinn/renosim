# Journal de bord

## 2026-07-04 (fin d'après-midi) — Phase 2 : gestes de rénovation & économie

**Fait :** `renovation.py` (6 gestes en dataclasses gelées, transformation pure
Building→Building, bouquets appliqués dans l'ordre canonique enveloppe→ventilation→systèmes,
3 bouquets prédéfinis), `economics.py` (fourchettes de coûts, économies annuelles €/kWh/CO₂,
temps de retour simple borné à l'infini si économies nulles), `tables/renovation_costs.json`
(fourchettes ONRE pour l'enveloppe, guides professionnels pour les équipements — champ
`confidence` explicite, consolidation prévue Phase 5). `VentilationSystem` gagne
`installed_after_2012` pour que le geste VMC utilise les tranches récentes (résout la
limite notée en D-15).

**Résultat clé du notebook (`demo_phase2.ipynb`)** : maison G fioul → rénovation globale
G→C, −88 % de conso finale, 4 568 €/an économisés, retour 4-18 ans. Découverte
pédagogique : sur une passoire, le bouquet enveloppe est **super-additif** (l'effet
intermittence INT domine l'effet apports gratuits F) — le test de non-additivité teste
l'écart, pas la direction.

**Tests :** 68/68 verts, couverture 93,8 %, mypy strict OK (leçon : les membres d'un
`Protocol` doivent être des propriétés lecture seule pour matcher des dataclasses gelées).

**Prochaine étape :** Phase 3 — validation ADEME.

## 2026-07-04 (après-midi) — Phase 0 finalisée + Phase 1 : moteur cœur

**Phase 0 bouclée :** dépôt GitHub créé (`quetinn/renosim`), CI verte au premier push, GitHub
Pages activé (source Actions) et déployé après configuration manuelle de la source par Noé —
site en ligne : <https://quetinn.github.io/renosim/>. Tag `phase-0` poussé.

**Phase 1 — extraction des sources réglementaires :**

- Annexe 1 (méthode 3CL-DPE 2021) et annexes DPE habitation téléchargées depuis
  rt-re-batiment.developpement-durable.gouv.fr et extraites (pypdf/pdfplumber + rendu image
  pour la table Umur_tab qui n'existe qu'en image dans le PDF).
- Valeurs confirmées verbatim à la source : seuils étiquettes (annexe 5, y c. variante
  > 800 m H1b/H1c/H2d), facteurs CO₂ par énergie et par usage (arrêté modificatif
  JORFTEXT000043353421), tables U par défaut (murs/plancher/toiture × période × H1-H3 × joule),
  débits VMC conventionnels, Q4Pa-conv, SCOP PAC, COP CET, Re/Rd/Rr, I0/INT, formules
  Rpn/Rpint chaudières, Nadeq/Becs, apports internes, facteur d'utilisation par inertie,
  données climatiques mensuelles complètes (§18.2, parsées par script → `climate_zones.json`),
  tarifs conventionnels (annexe 7, 01/01/2021 — TODO mise à jour avant Phase 4).
- **Découverte réglementaire importante** : l'arrêté du 13 août 2025 abaisse le coefficient EP
  électricité de 2,3 à 1,9 au 01/01/2026 (déjà en vigueur aujourd'hui). Choix V1 : défaut 2,3
  (cohérent avec la base ADEME de validation), convention 2026 encodée et sélectionnable
  (`regulation_vintage`). Documenté en D-13.

**Phase 1 — implémentation :** `models.py` (dataclasses frozen), 7 tables JSON sourcées,
`occupancy.py` (scénario conventionnel figé + personnalisé, interpolation DH19/DH21),
`envelope.py` (GV complet avec infiltrations 3CL), `needs.py` (besoins mensuels, facteur
d'utilisation ISO 13790/3CL), `systems.py` (rendements officiels, INT), `outputs.py` (EP, CO₂,
étiquettes double seuil, coûts par tranches), `simulation.py` (API `simulate()`).
Écarts D-06 à D-15 documentés au fil de l'eau dans `deviations.md`.

**État des tests :** 53/53 verts, couverture 92 % (seuil monté à 85), mypy strict OK, ruff OK.
Tests unitaires avec valeurs calculées à la main (GV, Becs, Bch janvier, rendements chaudière,
ballon ECS) + 5 cas de référence de bout en bout + invariants. Notebook de démo exécuté :
`validation/notebooks/demo_phase1.ipynb` (maison fioul 1960s → G à 639 kWhep/m²/an ;
bouquet → C-D attendu en Phase 2).

**Pièges Windows (session) :** les shims `pip.exe`/`mypy.exe` du venv échouent silencieusement
(exit 1 sans sortie) — utiliser `python -m pip` / `python -m mypy`. Le `.pth` editable doit être
réécrit en chemin court 8.3 après chaque `pip install -e engine` (voir entrée Phase 0).

**Prochaines étapes :** Phase 2 — `renovation.py` (6 gestes, bouquets enveloppe→systèmes,
immutabilité), `economics.py`, `renovation_costs.json` sourcée (ONRE/ADEME, fourchettes déjà
repérées), tests d'invariants (bouquet ≥ meilleur geste, non-additivité).

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
