# Journal de bord

## 2026-07-07 — Quatre améliorations du backlog (#3, #7, #8, #10)

**Fait :** implémentation de quatre pistes du backlog (`docs/improvements_backlog.md`), toutes
calibration-neutres par défaut ; les items ⚠️ (#5 auxiliaires, #9 intermittence) sont laissés
pour l'itération de calibration couplée à la re-validation #14.

1. **#10 Inertie paramétrée** — enum `InertiaClass` (`models.py`), exposant du facteur
   d'utilisation par classe (§6.1 : légère 2,5 / moyenne 2,9 / lourde 3,6, valeurs déjà
   tabulées dans `occupancy_conventional.json`), champ additif `inertia` du schéma 0.1,
   question « Type de construction (inertie) » à l'étape Enveloppe. « Je ne sais pas »
   (défaut) = moyenne, identique au comportement calibré Phase 3. D-14 marqué partiellement
   levé. Vérifié : lourde < moyenne < légère sur les besoins, unknown ≡ medium.
2. **#8 Objectif d'étiquette** — entrée optionnelle `label_targets` du schéma : le bridge
   évalue les 63 combinaisons des six gestes (paramètres des cartes inclus) et renvoie, par
   classe meilleure que l'étiquette actuelle, la combinaison la moins chère qui l'atteint
   (départage à l'investissement médian). Section « Viser une étiquette »
   (`LabelTargets.tsx`) : puces de classes (désactivées si hors de portée), bouquet gagnant,
   bouton « Activer ce bouquet ». Demandé seulement sur l'écran Scénarios (l'écran Situation
   reste instantané). Vérifié navigateur : maison F → cibles E/D/C/B accessibles, A grisée ;
   « atteindre C » = combles + PAC, 10 700–27 300 €, 1 681 €/an, cohérent avec le tableau.
3. **#7 Partage par URL** — bouton « Partager » (copie presse-papier) encodant l'instantané
   en base64 URL-safe dans `#s=…` ; import prioritaire sur localStorage à l'ouverture,
   arrivée directe sur Situation, hash nettoyé. Vérifié : aller-retour complet (session
   vierge → restauration postal/inertie/gestes).
4. **#3 Rapport imprimable** — `print:hidden` sur tout le chrome interactif, bloc
   `@media print` (couleurs DPE préservées via `print-color-adjust: exact`, fond blanc,
   `break-inside: avoid`), ligne print-only date/mode/avertissement, bouton « Imprimer »
   (`PageActions.tsx`) sur Situation et Scénarios.

**État des tests :** moteur 133/133 verts (couverture ~94 %), ruff + format + mypy strict OK,
`npm run build` OK, wheel régénéré (`renosim-0.4.0`). Vérification navigateur de bout en
bout : parcours, résultats (F, 414 kWhep/m²), scénarios, objectif d'étiquette, partage.

**Prochaines étapes :** Phase 5 (README, note finale, billet de blog, tag v1.0) ; puis #14
(re-validation ADEME v2) en y intégrant #5 et #9 ; côté design : #6 mode sombre, #11 export
PDF (s'appuie sur #3).

## 2026-07-07 — Trois premières améliorations du backlog (#1, #2, #4)

**Fait :** implémentation des trois pistes recommandées avant Phase 5, dans l'ordre
faisabilité croissante.

- **#2 Seuils DPE petites surfaces (≤ 40 m²) — écart D-12 LEVÉ.** Les tableaux officiels de
  l'arrêté du 25 mars 2024 (annexe 5 §1.2.2.1 standard et §1.2.2.2 zones froides d'altitude,
  E/F relâchés) sont en images dans le PDF : rendus en PNG via PyMuPDF puis **lus
  visuellement** cellule par cellule (une transcription automatisée avait lissé à tort la
  colonne EGES_d, non monotone : 51→52→53→54→55 en fin de tableau). Encodés verbatim dans
  `dpe_thresholds.json` (33 lignes × 12 bornes + variante altitude). `outputs.py` interpole
  linéairement en surface (≤ 8 m² → ligne « ≤ 8 » ; > 40 m² → tables standards inchangées) ;
  `simulate()` passe la surface. 6 tests calculés à la main (dont la discontinuité officielle
  à 40 m² : EGES_d = 55 côté ≤ 40 vs 50 au-delà). D-12 marqué RÉSOLU dans `deviations.md`.
- **#1 Alerte passoire thermique.** Composant `PassoireAlert` (écran Situation) : encart sourcé
  loi Climat & Résilience quand l'étiquette conventionnelle est E/F/G — message différencié
  (passoire F/G vs. E « bientôt concerné »), dates d'interdiction de location (G 2025, F 2028,
  E 2034), précision « location, pas propriétaire occupant », lien France Rénov'. UI seule,
  aucun calcul d'aides (hors périmètre).
- **#4 Badges « par où commencer ».** Le bridge renvoie `measure_previews` : évaluation
  conventionnelle autonome des 6 gestes sur le logement courant (économies €, retour, ΔCO₂,
  étiquette après), réutilisant `assess_scenario`. Le front (`pickMeasureBadges`) badge la carte
  la plus rentable (retour simple mini positif) et le plus gros gain CO₂, **avant** activation.
  Ajout additif au schéma 0.1 (rétro-compatible). 2 tests bridge.

**État des tests :** moteur 123/123 verts (couverture 94,3 %), ruff + format + mypy strict OK,
`npm run build` OK (bundle initial 427 kB, recharts en chunk séparé), wheel régénéré et vérifié
(table petites surfaces présente, 33 lignes). Vérification navigateur : maison 1948-74 fioul
69003 → étiquette F, alerte « interdiction location 2028 » affichée ; écran scénarios → badge
« Le plus rentable » sur Combles, « Plus gros gain CO₂ » sur Chauffage ; aucune erreur
console/réseau. NB : rendu d'animation gelé dans l'environnement de preview (artefact connu,
non reproductible en usage réel) — vérifications faites via DOM/accessibilité.

**Prochaines étapes :** reste du backlog (`docs/improvements_backlog.md`) ; #14 (re-validation
ADEME v2) reste le plus valorisant pour la note, #8 (objectif d'étiquette) la prochaine grosse
fonctionnalité conseil.

## 2026-07-04 (soir) — Phase 3 : validation contre la base DPE ADEME

**Fait :** `download_dpe.py` (API data-fair `dpe03existant` vérifiée en ligne, échantillon
stratifié époque×zone×énergie, 11 708 maisons, données jamais committées), `mapping.py`
(choix M-1 à M-7 documentés, 99,3 % de lignes mappées), `run_validation.py` (biais/MAE/MAPE,
matrice de confusion, accord exact/±1, déclinaisons par strate).

**Campagne : 6 itérations documentées** (voir `validation/report/note_validation.md`),
de biais +99 → **+7,8 kWhep/m²/an**, accord exact 27 % → **50,5 %**, ±1 classe 62 % →
**90,8 %**. Trois découvertes structurantes : (1) « isolation insuffisante » ADEME ≠ paroi
nue — les constructions ≥ 1975 ont l'isolation réglementaire d'époque ; (2) le coefficient
**Ue des planchers sur terre-plein** (annexe 1 p.18) est indispensable (~160 W/K d'écart sur
une maison ancienne) ; (3) la base ADEME **mélange les conventions EP 2,3 et 1,9** depuis le
01/01/2026 — le millésime est maintenant choisi par DPE selon sa date d'établissement.

**Critères §7.2 : ±1 classe ✅ (90,8 % ≥ 90 %) ; exact ❌ (50,5 % < 60 %).** Analyse dans la
note : plafond d'information du mapping (4 classes de qualité par paroi), pas de la physique —
le gaz, population homogène, atteint 65,9 % ; le parcours app collectera une information plus
riche. Pistes listées (rendements bûches officiels, ligne U RE2020, ECS électrique affinée).

**Tests :** 68/68 verts (2 ancres manuelles recalculées après itération 6), couverture 93,8 %,
mypy strict, ruff.

**Prochaine étape :** Phase 4 — app React + Pyodide (bridge JSON versionné, 3 écrans).

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

---

## 2026-07-05 — Phase 4 : application React + Pyodide

**Fait :**

- `engine/renosim/bridge.py` : pont JSON versionné (`SCHEMA_VERSION` 0.1) — unique point
  d'entrée `run_simulation(payload_json)` appelé depuis JS. Le bridge possède le mapping
  formulaire → `Building` (géométrie M-1, U par états d'isolation M-2/M-6, plancher bas Ue
  M-7 — conventions identiques à la validation, ajoutées aux tables avec sources). Écart
  documenté D-17. 22 tests (`tests/test_bridge.py`), moteur v0.4.0, couverture 93,8 %.
- Pipeline wheel : `npm run wheel` (build + `make-wheel-manifest.mjs`), manifest généré aussi
  dans `deploy.yml` ; les .whl restent ignorés par git.
- App complète (Vite + React + TS + Tailwind 4 + Recharts + motion + lucide) :
  - Direction design « éco-tech premium » (fond papier chaud, vert pin, accent ambre,
    Fraunces + Inter), tokens dans `index.css`, thème clair uniquement.
  - Landing : hero animé (maison SVG + échelle DPE F→B, particules de chaleur), stats de
    validation animées (11 624 DPE, 90,8 %), sections méthode/transparence, CTA.
  - Écran 1 : stepper 4 étapes (localisation → général → enveloppe → systèmes), code postal →
    zone climatique (table Légifrance R172-4 chap. IV sourcée dans `data/climateZones.ts`),
    défauts dérivés de l'époque, aides contextuelles partout.
  - Écran 2 : étiquette DPE animée (double seuil affiché), tuiles chiffres clés, répartition
    par usage, graphique « par où part la chaleur », toggle conventionnel/personnalisé
    (consigne, occupants, prix) — l'étiquette reste conventionnelle, expliqué dans l'UI ;
    toggle convention EP 2021/2026 (D-13).
  - Écran 3 : 6 cartes gestes paramétrables (coûts en fourchettes), 3 bouquets prédéfinis
    (définis par le moteur), tableau comparatif, message pédagogique de non-additivité chiffré,
    graphique coût vs gain.
  - Transverse : panneau « Comment est-ce calculé ? », avertissements DPE/France Rénov',
    « vos données restent chez vous », responsive 375→1440, `prefers-reduced-motion` respecté,
    focus visibles, alternative tabulaire sr-only pour le graphique.
- Pyodide : chargement CDN dès l'arrivée (masqué par la landing), micropip + wheel local via
  manifest, fallback d'erreur avec lien dépôt.

**État des tests :** moteur 90/90 verts (couverture 93,8 % ≥ 85 %), ruff + format + mypy strict
OK, `npm run build` OK. Test navigateur bout en bout : maison 1948-74 fioul non isolée (69003)
→ G (415 kWhep/m², 3 817 €/an) ; bouquet rénovation globale → B (85 kWhep/m², 3 135 €/an
d'économies, non-additivité visible vs 4 281 €/an en sommant les gestes) ; mode personnalisé
21 °C → 495 kWh/m² affichés, étiquette inchangée.

**Prochaines étapes (Phase 5) :**

1. Captures d'écran + badge CI dans le README, section « ce que cet outil n'est pas ».
2. Mise en forme finale de la note de validation, billet de blog (al-folio).
3. Envisager le code-splitting du bundle (795 kB minifié) : import dynamique de Recharts.
4. Tag `v1.0` après revue complète.

## 2026-07-06 — Saisie de l'isolation par matériau + épaisseur (pré-Phase 5)

**Fait :** remplacement de la saisie « résistance R » (que personne ne connaît) par une liste
déroulante d'isolants + champ épaisseur, aux deux endroits concernés : option « Je connais
l'isolant posé » du formulaire (étape Enveloppe) et cartes de gestes isolation combles/murs
(écran scénarios), avec aperçu en direct du R calculé.

- Nouvelle table `tables/insulation_materials.json` : λ utile par famille d'isolant, sourcée
  sur les **règles Th-Bât fascicule « Matériaux »** (valeurs par défaut §2.6, site
  rt-re-batiment) ; biosourcés (ouate, fibre de bois) et « isolant inconnu » sur la
  **convention 3CL λ = 0,04** (annexe 1 arrêté 31/03/2021 : U = 1/(1/U0 + e/0,04)).
- Moteur : `added_r_from_insulation(material, thickness_cm)` dans `renovation.py`
  (R = e/λ) ; le bridge accepte `material` + `thickness_cm` en plus de
  `r_value_m2k_per_w` / `added_r_m2k_per_w` (rétro-compatible, schéma 0.1 inchangé —
  ajouts optionnels uniquement).
- Front : la table du moteur est importée telle quelle par Vite (une seule source de vérité
  pour les λ) ; l'aperçu « soit R ≈ x » est purement affichage, le moteur recalcule.
  `MeasureParams` porte désormais matériau+épaisseur (défauts : laine de verre 28 cm combles
  ≈ R 7, 15 cm murs ≈ R 3,75, cohérents avec les défauts moteur).

**État des tests :** moteur 100/100 verts (couverture 93,9 %), ruff + mypy strict OK,
`npm run build` OK, wheel régénéré. Vérification navigateur : carte combles → passage
laine de verre → polyuréthane (28 cm) : R affiché 7 → 9,3 m²·K/W, conso après 272 → 270
kWhep/m²·an, économies 933 → 947 €/an (recalcul Pyodide OK). NB : la fenêtre de preview
sans rAF gèle les transitions AnimatePresence du Wizard (artefact d'environnement de test,
non reproductible en usage réel).

**Prochaines étapes :** Phase 5 (README, note finale, billet de blog, tag v1.0) ; voir la
liste d'améliorations proposées en discussion (orientation des vitrages, type de plancher
bas, saisie détaillée des métrés, Web Worker Pyodide, persistance locale).

## 2026-07-06 (soir) — Cinq améliorations pré-Phase 5

**Fait :** implémentation des cinq améliorations proposées, toutes calibration-neutres par
défaut (les défauts « je ne sais pas » reproduisent exactement le comportement validé en
Phase 3).

1. **Orientation des vitrages + masques** — nouveaux champs Enveloppe (orientation dominante,
   environnement dégagé/masqué). Moteur : `solar_orientation_modifier` (ratios des C1
   verticaux moyens oct→avr, table `solar_orientation.json` calculée depuis §18.5 de
   l'annexe 1) et `solar_shading_factor` (Fe2 §6.2.2.2.1 : 0,8 / 0,4). D-06 mis à jour.
   Vérifié : maison de référence 415 → 404 kWhep/m² en « plutôt sud ».
2. **Type de plancher bas** — terre-plein (tables Ue p.19 avant/après 2001), vide sanitaire /
   sous-sol (table p.18, inchangée = défaut M-7), garage/local non chauffé (b = 0,95, table b
   §3.1). Vérifié : 415 → 422 kWhep (F → G) en terre-plein pour la maison de référence.
3. **Saisie détaillée des métrés** — bloc optionnel `geometry` dans le schéma (murs, baies,
   toiture, plancher, hauteur sous plafond) remplaçant la reconstruction M-1 champ à champ ;
   panneau repliable « Je connais mes surfaces » à l'étape Général. D-17 mis à jour.
4. **Pyodide en Web Worker + code-splitting** — le runtime et chaque simulation tournent hors
   du thread UI (`engine.worker.ts`, protocole de messages typé, réponses obsolètes ignorées) ;
   Recharts lazy-loadé (`LossesChart`, `CostGainChart`). Bundle initial : 798 → 425 kB
   (chunk recharts 335 kB à la demande), plus d'avertissement de taille au build.
5. **Persistance locale** — form/occupancy/params/gestes/vintage dans `localStorage`
   (clé `renosim:v1`, fusion tolérante avec les défauts, best-effort en navigation privée),
   bouton « Effacer mes réponses et repartir de zéro » dans le parcours.

**État des tests :** moteur 116/116 verts (couverture 94,2 %), ruff + format + mypy strict OK,
`npm run build` OK, wheel régénéré. Vérification navigateur : moteur prêt via worker, baseline
identique (415 kWhep/m², F), effets orientation/plancher/géométrie confirmés ci-dessus,
restauration du formulaire après rechargement OK, aucune erreur console/réseau.

**Prochaines étapes :** Phase 5 — README exemplaire, note de validation finale, billet de
blog, tag v1.0. Penser à mentionner dans la note que les nouveaux champs (orientation,
plancher, métrés) sont neutres par défaut vis-à-vis de la calibration.

## 2026-07-10 — Passage en revue du backlog d'améliorations (13 items traités)

**Fait (calibration-neutres, front + schéma 0.1 additif) :**

1. **#10 Inertie paramétrée** — enum `InertiaClass`, exposants officiels §6.1 branchés dans
   `needs.py`, champ `inertia` du schéma, question « Type de construction (inertie) » à
   l'étape Enveloppe (défaut « je ne sais pas » = moyenne = comportement calibré). D-14 màj.
2. **#8 Objectif d'étiquette** — entrée optionnelle `label_targets` : le bridge évalue les
   63 combinaisons des 6 gestes (paramètres des cartes) et renvoie la moins chère par classe
   cible ; section « Viser une étiquette » (`LabelTargets.tsx`) avec activation en un clic.
   Demandé uniquement sur l'écran Scénarios (l'écran Situation reste instantané).
3. **#7 Partage par URL** — instantané complet en base64 URL-safe dans le fragment `#s=…`
   (rien ne quitte le navigateur), import prioritaire au chargement, arrivée directe sur les
   résultats, hash nettoyé. Bouton « Partager » (copie presse-papier).
4. **#3/#11 Rapport imprimable / export PDF** — `print:hidden` sur tout le chrome, bloc
   `@media print` (couleurs DPE forcées, fond blanc), en-tête print-only (date/mode/
   avertissement), bloc « Hypothèses de la simulation » (`PrintHypotheses.tsx`), bouton
   « Imprimer / PDF » (impression pilotée, option retenue du backlog).
5. **#6 Mode sombre** — palette re-déclarée sous `prefers-color-scheme: dark` (screen
   uniquement, l'impression reste claire), tokens `--color-on-pine`/`--color-on-amber`
   (pine/amber clairs + encre foncée dessus), gamme DPE et panneau `pine-ink` inchangés,
   graphiques sur variables, `theme-color` double.
6. **#12 Multi-projets** — magasin `renosim:projects:v1`, panneau « Mes logements »
   (enregistrer/charger/supprimer, tableau comparatif avec résumés conventionnels figés).
7. **#13 Maison interactive** — `HouseLossMap.tsx` : coupe SVG colorée vert→rouge selon la
   part de chaque zone dans GV, zones cliquables (accessibles clavier) qui activent le geste
   correspondant, à côté du graphique en barres.

**Fait (⚠️ moteur, itération de calibration documentée) :**

8. **#5 Auxiliaires §15** — annexe 1 consolidée re-téléchargée (rt-re-batiment, 10/07/2026),
   §15/§18.1 extraits : `Paux_g = G + H·Pn`, circulateur complet (Pcirc, Lem, Tbase),
   table `auxiliaries` sourcée, `heating_auxiliary_kwh`/`dhw_auxiliary_kwh`, 5 tests à la
   main. **Re-validation immédiate** (échantillon local, 11 624 maisons) :
   ±1 classe 90,8 % → 90,5 %, exact 50,5 % → 50,2 %, biais +7,8 → +10,8 kWhep/m² —
   dégradation marginale, auxiliaires conservés. D-11 RÉSOLU, `results_v2_aux.json`.
9. **#9 Intermittence** — item périmé : INT était déjà implémenté (calibré Phase 3).
   Complément : la classe d'inertie sélectionne désormais la colonne I0 « lourde » de la
   table §8 (les deux effets officiels opposés de l'inertie sont modélisés).

**Constat #14 :** l'échantillon local ne porte pas les colonnes plancher bas / orientation
des baies → le volet « nouveaux champs » exige un re-téléchargement ADEME (backlog màj).
**#15 appartements** : non traité (V2 après v1.0, brief §2.2).

**État des tests :** moteur 139/139 verts (couverture 94,6 %), ruff + format + mypy strict
OK, `npm run build` OK, wheel régénéré. Vérification navigateur : inertie visible à l'étape
Enveloppe, objectif d'étiquette E→B atteignables / A désactivée sur la maison de référence
(bouquet C = combles + PAC, 10 700-27 300 €, 1 681 €/an, retour 6-16 ans), activation en un
clic reflétée dans le tableau, partage par URL rebouclé (session vierge → résultats
restaurés), règles print présentes, mode sombre appliqué (fond #101612, contrastes on-pine).

**Prochaines étapes :** Phase 5 (README, note de validation finale — y intégrer l'itération
v2 auxiliaires —, billet de blog, tag v1.0) ; volet restant de #14 (échantillon ADEME enrichi
plancher/orientation).

## 2026-07-11 — #14 (v2), #15 appartements, proposition confort d'été

**#14 — échantillon enrichi + re-validation.** Vérification du schéma live de l'API ADEME
(230 champs) : ni type de plancher bas ni orientation des baies n'y sont exposés (ils vivent
dans le XML DPE, pas dans `dpe03existant`) — l'hypothèse du backlog était fausse. Champs
réellement exploitables : `classe_inertie_batiment` (→ notre nouvelle entrée inertie, choix
M-8), position/traversant des appartements, et tout le bloc confort d'été (téléchargé
d'avance). Échantillon maisons v2 re-téléchargé (11 708 lignes), campagne v3 : ±1 classe
90,3 %, biais +12,1 — l'inertie mappée est quasi neutre (les deux effets officiels
opposés se compensent). `results_v3_inertia.json`.

**#15 — appartements (sortie assumée du périmètre V1 §2.2, demande explicite).** Moteur :
`DwellingType` + variantes officielles (Nadeq collectif §11.1, Q4Pa appartement §4 p.39,
Pvent collectif §5 p.41, I0 immeuble/chauffage individuel §8 p.56, e/f façade unique,
b = 0,35 mur sur circulation §3.1). Bridge + formulaire : type de logement, position
(RDC/intermédiaire/dernier étage/je ne sais pas), traversant/mono-orienté ; niveaux et
mitoyenneté masqués pour les appartements. **Campagne dédiée** (11 057 lignes téléchargées,
8 895 « dpe appartement individuel » mappés) : première passe catastrophique (GV
prédit/observé 0,60, ±1 classe 76,2 %) → diagnostic poste à poste avec les colonnes
`deperditions_*` (position manquante à 99 %, murs ×0,54, ponts ×0,22) → conventions de
reconstruction calibrées (`apartment_reconstruction` : murs ×1,85, b espérés plafond
0,45/plancher 0,10 si position inconnue, ponts 25 %) → **GV 0,99, biais −0,2 kWhep/m²,
±1 classe 87,9 %, exact 45,0 %**. Écart D-18 complet (méthode, calibration, limites :
installations collectives traitées comme individuelles, bouclage ECS non modélisé).

**Confort d'été — proposition (idée de Noé).** Document `docs/proposal_confort_ete.md` :
3 briques — (1) indicateur officiel de confort d'été passif de l'annexe 4 (inertie,
protections solaires ext., traversant, toiture, brasseurs ; ~1 j, validable immédiatement
contre `indicateur_confort_ete`), (2) besoin/conso de refroidissement §10 (⚠️ lève D-02,
tables été à extraire, ~3-5 j), (3) gestes « été » (volets/BSO en 7ᵉ geste). Backlog #16.

**État des tests :** moteur 148/148 verts (couverture 94,7 %), ruff + format + mypy strict
OK, `npm run build` OK, wheel régénéré. Vérification navigateur : appartement 60 m² dernier
étage mono-orienté H1c → « Appartement de 60 m² », classe F (398 kWhep/m²), toiture 44 % des
déperditions sur la maison interactive, auxiliaires collectifs comptés. NB : l'artefact
rAF/AnimatePresence de l'environnement de preview gèle l'affichage du Wizard (l'état avance,
la section affichée non) — navigation testée via l'import d'URL de partage ; non
reproductible en usage réel (déjà noté le 06/07).

**Prochaines étapes :** décision sur la proposition #16 (brique 1 recommandée en premier) ;
Phase 5 (README, note de validation — y intégrer les chapitres v2 auxiliaires, v3 inertie et
appartements —, billet de blog, tag v1.0).

## 2026-07-11 (suite) — #16 Confort d'été : les 3 briques + correctif C1 hiver

**#16 brique 1 — indicateur de confort d'été passif** (annexe 9 du document consolidé des
annexes DPE habitation — la proposition disait « annexe 4 » ; grille extraite verbatim,
pages 22-26). `summer_comfort.json` + module pur `summer_comfort.py` (insuffisant si baies
S/E/O/toiture sans protection extérieure ou toiture non isolée sous plafond déperditif ;
bon si ≥ 2 de {inertie lourde, traversant, brasseurs fixes} ; défaut officiel toiture
inconnue pré/post-1975). Nouveaux champs moteur (protections, brasseurs, clim,
roof_insulated, through_dwelling) + 3 questions au formulaire + carte « Confort d'été
(sans climatisation) » sur l'écran Situation (pastille officielle 3 niveaux, leviers
passifs, avertissement « l'étiquette DPE mesure l'hiver »). Le geste toiture bascule le
critère été. Simplifications D-19 (déclaratif global, maisons supposées traversantes).
**Campagne dédiée** (`run_summer_comfort.py`, M-10) : la base mélange les millésimes de la
grille officielle (DPE 2021 : 16 % d'accord — ancienne grille) ; sur les DPE ≥ 2025 :
maisons **95,5 %** exact / 98,6 % ±1 (n = 7 943), appartements **91,0 %** / 98,3 %
(n = 4 284). Choix M-10 clé : « qualité insuffisante » ≠ « non isolée » (+5,5 pts).

**#16 brique 2 — besoin/conso de refroidissement §10 (⚠️ lève D-02, écart D-20).**
Tables été extraites de l'annexe 1 (§18.2 : DH28/Nref28/E_fr28 par zone × altitude × mois —
piège de parsing : les valeurs 100-199 ressemblaient aux numéros de page ; §18.5 : C1 été
verticaux juin→sept ; §10.3 : SEER par zone × période, avant-2008 = EER direct) +
`cooling.json`. Bfr mensuel verbatim §10.2 (Rbth, fut avec Cin par inertie, DH28 ≡
(Textmoy_clim−28)·Nref28 aux arrondis près — évite la coquille H2d/mai de la table
publiée) ; Sse été = 0,5 calibré rebasé par C1_été/moyenne_C1_hiver_verticale. Cfr =
0,9·Bfr/EER seulement si clim déclarée (question période au formulaire) ; Bfr affiché pour
tous (« ce que coûterait votre été »). Ordres de grandeur : maison non isolée 4 kWh/m²
(H1a) → 28 kWh/m² (H3) ; est/ouest > sud > nord. **Validation** (M-11, 2 383 maisons
climatisées) : besoin −13 % (H2d +15 kWh/2 401, H3 −66/2 371), conso EP +28 % (surface
refroidie 100 % = majorant, D-20). **Campagne v4** : ±1 classe 90,2 %, biais +12,9
(`results_v4_cooling.json`) — quasi neutre, D-02 RÉSOLU.

**#16 brique 3 — 7ᵉ geste « volets/BSO extérieurs »** (gain été pur, 200-750 €/m² de baie
sourcé guides pro, exclu de la recherche d'étiquette cible), colonne « Confort d'été
passif » avant → après dans le tableau des scénarios + badge sur les cartes. Vérifié
navigateur : maison H3 volets absents + toiture nue → ni geste seul ne suffit, le bouquet
combles+volets passe Insuffisant → Moyen ; clim avant 2008 = 684 kWh (0,9·2468/3,25 ✓).

**Correctif C1 hiver (demande explicite, D-06).** `c1_heating_season_vertical` encodait la
colonne inclinée 25-75° du §18.5 au lieu de la verticale ≥ 75° (sud H1a 1,857 au lieu de
1,00). Corrigé (modificateurs sud 1,52 → 1,67, nord 0,61 → 0,58) ; **neutre pour la
calibration** : l'échantillon ADEME n'a pas d'orientation des baies, campagne v4
re-exécutée bit-identique. NB : une session parallèle (worktree) a été lancée sur le même
sujet — sa correction sera redondante avec celle-ci.

**État :** moteur 188/188 verts (couverture 95,0 %), ruff + format + mypy strict OK,
wheel 0.5.0 régénéré, `npm run build` OK. Vérification navigateur des 3 écrans (import
par URL de partage — artefact Wizard/preview connu). Schéma 0.1 additif (blocs `summer`,
`needs.cooling_kwh`, `summer_comfort`, `summer_comfort_after`, 7ᵉ geste).

**Prochaines étapes :** Phase 5 (README, note de validation — chapitres confort d'été /
refroidissement / v4 —, billet de blog, tag v1.0) ; réconcilier la session parallèle C1 ;
option V2 : question « surface refroidie » pour lever le majorant D-20.

## 2026-11-25 — Audit complet (moteur, validation, app) vs RT2012 / RE2020

Audit sans modification de code, rapport dans **`docs/audit_2026-11-25.md`**. Dossier
`Annexes` (raccourci vers RT2012 complète + RE2020 complète, décrets 2026 inclus) extrait ;
NB : les fascicules Th-U/Th-I/Th-S/Th-L sont des scans sans couche texte (OCR nécessaire).

**Vérifié conforme :** zonage département → zone (96/96 identique à l'annexe I de l'arrêté RT2012
du 26/10/2010) ; facteurs CO₂ identiques à l'art. 10 de l'arrêté RE2020 du 04/08/2021.

**Constats P0 :** 79 fichiers non commités depuis le 05/07 ; défaut app `dpe_2021` alors que
1,9 est en vigueur depuis le 01/01/2026 ; prix énergie 2021 (TODO bloquant non levé) ;
calibration et métriques sur le même échantillon (pas de hold-out), note de validation
restée en v1 (biais +7,8 → +12,9, ±1 classe 90,2 %).

**Bugs moteur démontrés :** ECS couplée qui suit un poêle à granulés (2 450 kWh d'ECS « au
poêle ») ; chaudière bois = rendement poêle avec circulateur mais Rd = 1 ; PAC sur passoire
non dimensionnée (≈ 18 kW requis, coût forfaitaire). Autres : HSP saisie ignorée pour
infiltration/intermittence, tranches d'âge ancrées implicitement sur 2026, constantes métier
en dur, écart fenêtres non documenté.

**État des tests :** 188/188 verts, couverture 95,0 %, ruff/format/mypy OK, `npm run build` OK.

**Prochaines étapes :** décider de la feuille de route §9 du rapport (Sprint 0 sécurisation →
prix/validation → Phase 5/v1.0 → v1.1 « conformité »).

## 2026-11-25 (suite) — Sprint 0 de l'audit (branche `feat/v1-consolidation`)

**Fait :**
1. **Sécurisation** : le travail de juillet (79 fichiers) est commité ; `*.lnk` ignoré.
2. **DPE 2026 par défaut** : clé `default_regulation_vintage` dans `emission_factors.json`, lue
   par `simulate`, `assess_scenario`, le bridge et l'app (« En vigueur (2026) » /
   « DPE 2021-2025 »). Validation inchangée (millésime par date de DPE). D-13 màj.
3. **Bug ECS/poêle** : un générateur sans réseau hydraulique bascule l'ECS couplée sur un
   ballon électrique (un CET explicite reste prioritaire) ; message sur la carte du geste.
4. **HSP** : `Building.ceiling_height_m` (optionnel) alimente le facteur d'intermittence ;
   les tests montrent que Hsp se simplifie dans l'infiltration §4.
5. **Constantes métier → `tables/conventions.json`** (+ coefficients chaudières, pertes de
   stockage ECS, part fixe électricité). Campagne v4 relancée : **bit-identique**.
6. **Écarts** : D-01, D-03, D-05, D-17 mis à jour ; nouveaux D-21 (fenêtres) et D-22
   (chaudière bois).

**Non fait (reporté) :** correction de la chaudière bois — elle modifie les métriques (≈ 2 400
maisons bois bûche, M-5) et exige les rendements du §13 de l'annexe 1 ⇒ v1.1 (D-22).

**État des tests :** 199/199 verts, couverture 96,3 %, ruff/format/mypy strict (26 fichiers)
OK, wheel 0.5.0 régénéré, `npm run build` OK. Vérif navigateur (lien de partage) : DPE 2026
sélectionné par défaut, maison fioul 1970 → G (443 kWhep/m²), geste poêle → message ECS et
scénario G → G (430 kWhep/m², 1 393 €/an).

**Prochaines étapes :** Sprint 1 de l'audit (prix de l'énergie à jour, échantillon test
indépendant, note de validation v2).

## 2026-11-25 (suite 2) — PR #1 fusionnée, Sprint 1 de l'audit (branche `feat/sprint1-prices-validation`)

**Fait :**
1. **Prix de l'énergie** : barème officiel de l'annexe 7 de l'arrêté du 25 mars 2024 (en
   vigueur au 01/07/2024, aucune modification ultérieure) à la place du barème 2021. Valeurs lues
   en texte intégral dans le texte du ministère et concordantes avec le JO, sauf les granulés
   (0,09897 au JO contre 0,10701 dans le projet) : à confirmer sur l'extrait authentifié du JO.
2. **Convention 2027** : coefficient électricité **1,7 au 1er janvier 2027** (arrêté publié au JO
   le 31/08/2026, communiqué du ministère ; NOR à compléter). Calendrier daté dans
   `emission_factors.json` : sans choix explicite, la convention du jour s'applique. L'app
   propose « En vigueur / DPE 2026 / DPE 2021-2025 » et affiche le coefficient appliqué et la
   source des prix. D-13 réécrit.
3. **Coûts de travaux indexés** sur l'indice INSEE BT01 (sept. 2026 = 139,1 ; moyennes 2019 =
   111,05 et 2025 = 133,01, relevées sur insee.fr) : ×1,253 (ONRE) et ×1,046 (guides).
4. **Validation v5** : échantillon **test indépendant** tiré au hasard (`sort=_rand`), disjoint
   de la calibration (11 549 lignes) ; bootstrap à 1 000 tirages ; repondération selon les
   effectifs ADEME par strate (4,7 M DPE de maisons). **Le critère n'est pas atteint au test :
   ±1 classe 86,7 % [86,1 ; 87,4]**, contre 90,2 % en calibration ; repondéré, 71,4 %. Cause
   principale : l'échantillon de calibration contenait 61 % de DPE de 2026 ; sur les DPE de
   2022-2025, le moteur surestime d'environ +40 kWhep/m² dans les deux échantillons ; segments
   faibles : électricité et bâti d'avant 1975. Note de validation v2, et chiffres de l'app et du
   README remplacés par ceux du test.
5. Moteur 0.6.0, wheel régénéré.

**État :** 202/202 tests, couverture 96,3 %, ruff/format/mypy OK, `npm run build` OK.
Vérifié dans le navigateur (landing, convention, facture, coûts indexés).

**Prochaines étapes :** télécharger `version_dpe` et analyser le biais par version de méthode ;
tirer un nouvel échantillon de calibration aléatoire ; ne jamais régler sur le test v1 ;
électricité poste par poste ; leviers v1.1 sur le bâti ancien ; mention « A0 » (arrêté du
11/06/2026, à partir du 01/01/2027).

## 2026-11-25 (suite 3) — Analyse de l'écart 2022-2025 par version de méthode

- Nouveaux scripts : `validation/enrich_sample.py` (version de méthode, date de modification et
  consommations par usage en EF/EP, récupérées par `numero_dpe`) et `validation/analyze_bias.py` ;
  résultats agrégés dans `validation/report/bias_analysis_v5.json`.
- **Pas de recalcul rétroactif à 1,9** : le rapport EP/EF de l'éclairage vaut 2,3 pour les DPE
  2021-2025 et 1,9 pour 2026. Le mapping par date est correct.
- **La rupture suit `version_dpe`** : biais ≈ +40 pour les versions 2.1 à 2.5, +4 pour la 2.6.
  Les déperditions (0,98-0,99) et le besoin de chauffage (1,03-1,05) du moteur collent aux DPE
  dans toutes les versions : l'écart vient de la chaîne qui passe du besoin à la consommation
  (chauffage et ECS ×1,19 en v2.4-2.5 contre ×1,04 en v2.6). L'effet n'est pas uniforme (stable
  pour le gaz et le fioul, variable pour le bois et l'ECS) : analyse par type de générateur à
  faire.
- **DPE v2.6 du test indépendant** : ±1 classe 93,6 % [92,5 ; 94,7], biais +3,7 (n = 1 885) ;
  repondéré 86,3 % [81,9 ; 90,2].
- **Éclairage** : +41 % constant (2,7 contre 1,9 kWh_ef/m²), à vérifier contre §16 de l'annexe 1.
- Note de validation v2.1 (§5.4) ; panneau méthode et README complétés. Aucun réglage du moteur
  (le test reste vierge).

**Prochaines étapes :** forfait d'éclairage ; annoncer la référence « version de méthode en
vigueur » puis tirer un échantillon de calibration aléatoire limité à la v2.6 ; analyse par
type de générateur (électricité, PAC, bois) ; leviers v1.1 sur le bâti ancien.

## 2026-11-25 (suite 4) — Correction de l'éclairage (D-10 résolu)

- Lecture du §16.1 de l'annexe 1 3CL consolidée (p.102-103, dans le navigateur, le site refusant
  les accès automatisés) : Nh est tabulé par zone et par mois (1 445 à 1 566 h/an). Le moteur
  utilisait 2 123 h, d'où +41 %.
- Table mensuelle encodée telle que publiée (les totaux annuels sont vérifiés par un test),
  `lighting_kwh` corrigé, 3 tests calculés à la main (H1a 100 m² = 189,0 kWh ; H2c = 197,3 kWh).
- Campagne v6 : éclairage moteur/DPE 1,000-1,007 ; test : biais +35,0 → +33,3, ±1 classe
  86,7 → 87,0 %, exact 44,4 → 44,9 % ; DPE v2.6 du test : 93,6 %, biais +2,3. Note de validation
  v2.2, D-10, app et README mis à jour.
- État : 205/205 tests, ruff/format/mypy OK.

## 2026-11-26 — Sprint 2 de l'audit : Phase 5 (consolidation v1.0)

- **Note de validation v3** (version finale v1.0) : 4 figures générées à partir des seuls
  fichiers de résultats versionnés (`validation/make_figures.py`, matplotlib : matrice de
  confusion, accord par époque et énergie, biais par version de méthode, historique des
  itérations) ; **protocole de la calibration v1.1 annoncé avant de la faire** (référence = DPE
  de la méthode en vigueur, échantillon aléatoire limité à cette version, une seule mesure
  finale, critères bruts et repondérés). Aucun changement de moteur ni de chiffre.
- **Rendu Quarto** (`validation/report/_quarto.yml`, page HTML autonome) publié par le workflow
  de déploiement à `<site>/validation/` ; liens depuis le panneau méthode et le pied de page.
- **README v1.0** : badges, captures (maison de 1970 au fioul), tableau de validation complet
  (calibration, test, version en vigueur, repondéré), « ce que cet outil n'est pas », périmètre
  réel, reproduction de la validation, feuille de route v1.1.
- **Brief** : nouveau §2.3 « Périmètre effectif de la v1.0 » (appartements, confort d'été,
  refroidissement, 7e geste, convention datée), comme le recommandait l'audit (§8).
- **App** : panneau méthode (limites à jour : appartements, confort d'été, bâti ancien),
  landing « 7 gestes », lien vers la note.
- **Billet de blog** (al-folio) : `docs/blog/2026-11-26-renosim.md`, brouillon à relire.
- Audit : cases des Sprints 0 à 2 cochées ; `validation/README.md` réécrit.

**État :** 205/205 tests, couverture 96,3 %, `npm run build` OK, note rendue et vérifiée dans
l'aperçu.

**Prochaines étapes :** fusion puis tag `v1.0` ; v1.1 « conformité » (ponts thermiques par
liaison et ITE/ITI, murs anciens, inertie Th-I, Ujn, chaudières bois D-22, ECS des PAC, PAC
dimensionnée, plancher bas, alertes RT existante), puis une seule recalibration selon le
protocole annoncé. Constat à traiter en v1.1 (capture du README) : une PAC seule sur une maison
G non isolée affiche G → D et un retour de 2 à 5 ans (audit §4.4).

## 2026-11-26 (suite) — v1.0 publiée ; v1.1, étape 1 : puissance de chauffage et PAC

- **v1.0** : PR #3 fusionnée, tag `v1.0` poussé, déploiement vérifié (note en ligne à
  `/renosim/validation/`).
- **Puissance nécessaire au point de base** `Pnc = GV·(20 − Tbase)/1000` (3CL §15.2.2) extraite
  dans `systems.design_heat_load_kw` et réutilisée par le circulateur (température intérieure de
  dimensionnement déplacée dans `system_efficiencies.json`). Test calculé à la main : maison de
  référence 29,348 kW en H1a, 27,358 kW en H3 > 800 m.
- **Contrôle PAC** (`economics.heat_pump_sizing`) : puissance après les gestes d'enveloppe du
  même bouquet, comparée à la gamme 10-12 kW du coût. Source lue dans le document : guide
  ADEME « Choisir sa pompe à chaleur » (déc. 2025), p.8 (14 900 € HT + 2 060 € HT de pose,
  Observ'ER 2025) et p.7 (« faites isoler votre logement avant de changer de chauffage »).
  Aucune source publique par tranche de puissance trouvée (étude Observ'ER 2022 : une seule
  référence 4-6 kW) : pas d'extrapolation du coût au kW. Test : PAC seule 29,3 kW (alerte),
  après murs + toit + fenêtres 11,6 kW (dans la gamme).
- **Bridge** : `baseline.design_heat_load_kw`, `heat_pump_sizing` par scénario et par aperçu
  de geste. **App** : puissance affichée sur la situation (avec aide), alerte sur la carte
  chauffage et encart sous le comparatif (« PAC à dimensionner » ou « Enveloppe d'abord, PAC
  ensuite : 19 → 5 kW »). Moteur 0.7.0.
- Nouvel écart D-23 (ni appoint ni coût au kW). Campagne v6 du test rejouée : identique au bit
  près (aucun effet sur les consommations).

**État :** 209/209 tests, ruff/format/mypy OK, `npm run build` OK, vérifié dans l'aperçu
(maison de 1970 au fioul : 19 kW ; PAC seule → alerte ; bouquet complet → 5 kW).

**Prochaines étapes v1.1 :** rendements officiels des chaudières bois (D-22), matériau des murs
anciens et inertie Th-I, ponts thermiques par liaison et ITE/ITI, Ujn, ECS des PAC, appoint des
PAC, geste plancher bas, alertes RT existante ; puis la recalibration unique selon le protocole
annoncé.

## 2026-11-27 — v1.1, étape 2 : chauffage au bois (poêles et inserts à bûches)

- Branche longue `feat/v1.1-conformity` : les étapes qui modifient les consommations y
  restent jusqu'à la recalibration unique (le site et la note gardent les chiffres de la v1.0).
- **Diagnostic sur la calibration** (jamais sur le test) des maisons « bois » par libellé de
  générateur : poêles/inserts à bûches 429 (consommation/besoin DPE 1,46), chaudières 263,
  libellé absent 2 087, et **1 121 lignes bois avec une PAC comme générateur principal**
  (consommation/besoin 0,59-0,70 : PAC + appoint bois, simulées en tout-bois, biais +39 à +49).
- **Moteur :** générateur `WOOD_LOG_STOVE` (rendements §13.1, tranches d'âge dans
  `conventions.json`), test calculé à la main (Rg 0,50/0,60/0,70/0,75 ; chaîne 0,532 à 10 ans ;
  pas d'auxiliaire). **Mapping M-5 révisé** (libellés poêle bûche, insert, foyer fermé,
  cuisinière). **App :** choix « Poêle ou insert à bûches ».
- Calibration : biais +11,3 → +12,5, ±1 classe 90,3 % inchangé ; le rendement corrigé dévoile
  un besoin surestimé de 14 % sur les maisons anciennes au bois. D-22 partiellement levé.
- Lecture du §13.2 (chaudières bois) reportée : le lecteur PDF ne s'affiche pas quand le volet
  navigateur est masqué.

**Prochaines étapes :** installations PAC + appoint bois (deux générateurs, §9 de l'annexe) ;
rendements des chaudières bois (§13.2) ; murs anciens et inertie ; ponts thermiques.

## 2026-11-27 (suite) — v1.1, étape 3 : appoint bois et chaudières bois

- Lecture dans le navigateur de l'annexe 1 : §9.3 (appoint bois, p.62 : 75 % / 25 % du besoin)
  et §13.2.2.3 (chaudières bois, p.89-90 : Rpn/Rpint par combustible et année).
- **Appoint bois** (`Building.heating_backup`, D-24) : test calculé à la main (joule + poêle
  bûches, Bch 1 000 kWh : 509,95 kWh élec + 300,51 kWh bois), test de bout en bout, bridge
  (`heating_backup`) et app (question « Poêle ou insert en appoint ? », masquée si le chauffage
  principal est déjà au bois ; ligne dans le récapitulatif imprimable). Vérifié dans l'aperçu :
  PAC seule 198 kWhep/m², avec poêle à bûches 244.
- **Mapping M-12** : « énergie bois + générateur PAC » → PAC + appoint bois. Calibration : biais
  du groupe +39/+49 → +2/+7. Les libellés « radiateur/convecteur » sont exclus (cas salle de
  bains §9.4-9.5, résultats mitigés).
- **Chaudières bois** officielles (D-22 levé) : test à la main (bûches > 2019 : Rg 0,89260 ;
  2004-2012 : 0,65981 ; avant 2004 : 0,55981 ; granulés 2013-2019 : 0,81627 ; chaîne 0,73307).
  Mapping : libellés « Chaudière bois » → WOOD_BOILER ; libellés absents → approximation
  explicite « poêle à granulés ». App : « Chaudière à granulés ».
- **Calibration cumulée de la branche** (jamais le test) : ±1 classe 90,3 → 91,2 %, exact
  50,0 → 51,6 %, biais +11,3 → +8,8 ; bois bûches ±1 87,9 → 90,5 %.

**État :** 217 tests, ruff/format/mypy OK, `npm run build` OK.

**Prochaines étapes :** murs anciens (table Umur0 §3.2.1) et inertie (§7, p.53) ; ponts
thermiques par liaison (§3.4) ; Ujn (§3.3.3).

## 2026-11-27 (suite 2) — v1.1, étape 4 : inertie déterminée par la méthode (§7)

- Lecture du §7 de l'annexe 1 (p.53-54) : définitions des parois lourdes et tableau §7.4.
- Moteur : `inertia_class_from_heavy_elements` (règle et défauts dans
  `occupancy_conventional.json`), test des 8 combinaisons et des défauts ; bridge :
  `inertia_elements` prioritaire sur `inertia`.
- App : la question « type de construction » est remplacée par trois questions Oui/Non/Je ne
  sais pas avec les définitions officielles en aide ; récapitulatif imprimable à jour ; les
  sessions enregistrées gardent leur ancienne réponse tant que les trois questions sont à « Je
  ne sais pas ». Vérifié dans l'aperçu : maison de 1970, trois parois lourdes 435 kWhep/m²
  contre 427 sans réponse (effets opposés de l'exposant et de l'intermittence, D-14).
- Validation : non concernée (classe ADEME lue directement, M-8).
- Incident d'aperçu : un rechargement à chaud a réinitialisé la session locale de l'app ; elle a
  été restaurée depuis la copie faite au début des vérifications.

**Prochaines étapes :** murs anciens (table Umur0 §3.2.1, matériau et épaisseur) ; ponts
thermiques par liaison (§3.4) ; Ujn (§3.3.3).

## 2026-11-27 (suite 3) — v1.1, étape 5 : matériau des murs anciens (Umur0)

- Lecture du §3.2.1.2 de l'annexe 1 (p.14-15) : Umur0 par matériau et épaisseur.
- Moteur : `uninsulated_wall_u` (dix matériaux, plafond 2,5), tests calculés à la main (pierre
  50 cm 2,05 ; 15 cm 3,2 → 2,5 ; brique creuse 30 cm → 1,68 ; pisé 60 cm 1,35…). Bridge :
  `wall_material`, appliqué au mur non isolé, à la composition avec un isolant connu
  (1/(1/2,05 + 2,5) = 0,33469) et au min(Umur_nu ; Umur_tab) quand l'isolation est d'origine.
- App : « Matériau des murs » et « Épaisseur du mur » à l'étape Enveloppe (masqués si les murs
  ont été rénovés), épaisseur proposée selon le matériau, ligne dans le récapitulatif.
  Vérifié dans l'aperçu : maison de 1970, pierre 60 cm 430 kWhep/m² contre 440 sans réponse.
- Écart D-25 ; validation non concernée (pas de matériau dans la base ADEME).

**Prochaines étapes :** ponts thermiques par liaison (§3.4) et ITE/ITI ; Ujn (§3.3.3) ; puis la
recalibration unique.

