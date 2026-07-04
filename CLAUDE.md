# CLAUDE.md — RénoSim : Simulateur de rénovation & décarbonation résidentielle

> Document de référence du projet. À lire intégralement avant toute implémentation.
> Toute décision d'architecture qui s'écarte de ce brief doit être signalée et justifiée avant d'être codée.

---

## 1. Vision du projet

**RénoSim** est un simulateur open-source de rénovation énergétique pour maisons individuelles françaises. L'utilisateur décrit son logement via un parcours guidé ; l'outil estime sa performance énergétique actuelle (consommation, émissions CO₂, étiquette DPE), puis simule des gestes de rénovation seuls ou en bouquets, avec pour chaque scénario : coût d'investissement, économies annuelles (kWh, €), réduction de CO₂, temps de retour simple, et nouvelle étiquette estimée.

**Ce qui distingue ce projet d'un énième calculateur :**
1. Un **moteur physique** inspiré de la méthode réglementaire 3CL-DPE 2021 (version simplifiée, écarts documentés), implémenté comme un package Python testé et documenté.
2. Une **validation quantitative** du moteur contre la base des DPE de l'ADEME (comparaison prédictions vs diagnostics officiels sur un échantillon de plusieurs milliers de logements), produisant une note technique de validation.
3. Une **architecture sans backend** : le moteur Python s'exécute dans le navigateur via Pyodide. Une seule implémentation du moteur, une app 100 % statique déployée sur GitHub Pages.

**Auteur / contexte :** projet personnel d'un étudiant ingénieur en dernière année, spécialité énergies renouvelables et efficacité énergétique. Objectif de valorisation : CV, site académique personnel, dossiers de candidature M2/doctorat. La rigueur méthodologique (validation, limites assumées, reproductibilité) prime sur l'exhaustivité fonctionnelle.

**Langue :** code, docstrings, noms de variables et commentaires en **anglais**. Interface utilisateur, note de validation et README orientés utilisateur en **français** (le public cible est français). Un README.md racine bilingue ou anglais avec section française est acceptable.

---

## 2. Périmètre

### 2.1 Inclus (V1)

- **Typologie : maison individuelle uniquement** (pas d'appartement, pas de collectif).
- **Deux modes de calcul :**
  - **Mode conventionnel** (défaut) : scénario d'occupation normalisé au sens du DPE — consignes, durées de chauffe et surface de référence conventionnelles. C'est le mode utilisé pour la validation contre la base ADEME et pour l'étiquette.
  - **Mode personnalisé** : l'utilisateur peut ajuster température de consigne, période/plage de chauffe, nombre d'occupants (impact ECS). L'étiquette DPE affichée reste TOUJOURS celle du mode conventionnel ; le mode personnalisé n'affecte que les kWh, € et CO₂ affichés « pour votre usage ». Cette distinction doit être visible dans l'UI.
- **Six gestes de rénovation :**
  1. Isolation des combles / toiture
  2. Isolation des murs (ITE/ITI non distingués en V1 : un seul geste « isolation murs » avec résistance ajoutée paramétrable)
  3. Remplacement des fenêtres (simple → double/triple vitrage)
  4. Remplacement du système de chauffage (matrice : depuis chaudière gaz/fioul/effet Joule → vers PAC air-eau, chaudière gaz condensation, poêle à granulés)
  5. ECS : passage à un chauffe-eau thermodynamique ou couplage au nouveau générateur
  6. Ventilation : installation/remplacement VMC (simple flux autoréglable → hygroréglable B → double flux)
- **Bouquets** : combinaisons libres des six gestes, avec recalcul cohérent (l'ordre logique enveloppe → systèmes doit être respecté dans le calcul : le nouveau système est dimensionné/évalué sur le bâtiment post-isolation).
- **Sorties par scénario** : conso énergie finale et primaire (kWh/m²/an), émissions (kgCO₂/m²/an), étiquettes énergie et climat, coût des travaux (fourchette basse/haute), économies annuelles en €, temps de retour simple, ΔCO₂ annuel.
- **Validation** : campagne quantitative contre la base DPE ADEME + note technique.

### 2.2 Exclus (V1) — à mentionner dans le README comme extensions futures

- Appartements et immeubles collectifs.
- Aides financières (MaPrimeRénov', CEE) : uniquement un lien vers France Rénov' dans l'UI. Ne JAMAIS implémenter de calcul d'aides.
- Confort d'été / climatisation (la 3CL 2021 en tient compte ; hors périmètre ici, à documenter comme écart).
- Photovoltaïque et autoconsommation.
- Distinction ITE/ITI, ponts thermiques détaillés (traitement forfaitaire).
- Actualisation financière (VAN, TRI) : temps de retour simple uniquement en V1.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────┐
│  Navigateur                                     │
│  ┌───────────────┐      ┌───────────────────┐  │
│  │  App React    │◄────►│  Pyodide runtime  │  │
│  │  (Vite, TS)   │      │  └─ renosim (py)  │  │
│  └───────────────┘      └───────────────────┘  │
│         100 % statique — GitHub Pages           │
└─────────────────────────────────────────────────┘

Hors navigateur (développement / recherche) :
  renosim (même package) + notebooks de validation + base DPE ADEME
```

**Principe cardinal : une seule implémentation du moteur.** Le package Python `renosim` est l'unique source de vérité du calcul. Il est consommé (a) par les notebooks/scripts de validation côté développement, (b) par l'app via Pyodide côté production. Aucune logique métier (calcul énergétique, coûts, étiquettes) ne doit être dupliquée en TypeScript. Le front ne fait que : collecter les entrées, appeler le moteur, afficher les sorties.

### 3.1 Structure du dépôt

```
renosim/
├── CLAUDE.md                  # ce document
├── README.md                  # vitrine du projet
├── LICENSE                    # MIT
├── pyproject.toml             # package engine, deps, config outils
├── engine/
│   └── renosim/
│       ├── __init__.py        # API publique
│       ├── models.py          # dataclasses : Building, Wall, Window, HeatingSystem…
│       ├── envelope.py        # déperditions enveloppe + ponts thermiques + ventilation
│       ├── needs.py           # besoins chauffage (DH par zone, apports gratuits) + ECS
│       ├── systems.py         # rendements génération/distribution/émission, conso finale
│       ├── outputs.py         # énergie primaire, CO₂, étiquettes, coûts énergie
│       ├── renovation.py      # définition des 6 gestes, application, scénarios, bouquets
│       ├── economics.py       # coûts travaux, économies, temps de retour
│       ├── occupancy.py       # scénarios conventionnel vs personnalisé
│       └── tables/            # données tabulées (voir §5) en JSON/CSV embarqués
├── tests/
│   ├── test_envelope.py
│   ├── test_needs.py
│   ├── test_systems.py
│   ├── test_renovation.py
│   └── test_reference_cases.py   # cas types de bout en bout (voir §7.1)
├── validation/
│   ├── download_dpe.py        # téléchargement échantillon base ADEME (API)
│   ├── mapping.py             # champs ADEME → modèles renosim
│   ├── run_validation.py      # campagne : moteur vs DPE officiels
│   ├── notebooks/             # exploration, figures
│   └── report/                # note technique de validation (Quarto ou LaTeX)
├── app/
│   ├── index.html
│   ├── package.json           # Vite + React + TS
│   ├── src/
│   │   ├── pyodide/           # chargement runtime, bridge JS↔Python
│   │   ├── components/        # formulaire-parcours, résultats, comparateur
│   │   ├── state/             # état du logement + scénarios
│   │   └── i18n/              # libellés FR
│   └── public/
├── data/
│   └── README.md              # provenance des données ; AUCUNE donnée brute committée
└── .github/workflows/
    ├── ci.yml                 # lint + tests engine à chaque push
    └── deploy.yml             # build app + wheel renosim → GitHub Pages
```

### 3.2 Intégration Pyodide

- Le package `renosim` est buildé en **wheel pure-Python** (aucune dépendance compilée dans le moteur : pas de numpy/pandas DANS le package engine — la stdlib + `math` suffisent pour les calculs unitaires ; pandas est réservé au code de validation hors navigateur).
- L'app charge Pyodide depuis le CDN officiel, installe le wheel local via `micropip`, puis expose une fonction `simulate(building_json, scenario_json, mode) -> results_json`.
- **Interface JS↔Python : JSON strict.** Définir un schéma d'entrée/sortie unique et versionné (`schema_version`). Le front sérialise l'état du formulaire vers ce schéma ; le moteur ne connaît rien du front.
- Le chargement de Pyodide (~10 s la première fois) doit être masqué par un écran de chargement soigné et déclenché dès l'arrivée sur la page, pendant que l'utilisateur remplit le formulaire.
- Prévoir un fallback d'erreur propre si Pyodide échoue à charger (message + lien vers le dépôt).

---

## 4. Spécification du moteur de calcul

Moteur **statique annuel/mensuel** inspiré de la méthode 3CL-DPE 2021, simplifié. Chaque écart à la méthode officielle doit être tracé dans `docs/deviations.md` (créer ce fichier dès le début et l'alimenter au fil de l'eau).

### 4.1 Chaîne de calcul (mode conventionnel)

1. **Déperditions enveloppe** : `GV [W/K] = Σ (U_i × S_i × b_i) + PT + H_vent`
   - Parois : murs, plancher bas, plafond/combles, fenêtres/portes. `b` = coefficient de réduction pour parois sur locaux non chauffés (valeurs forfaitaires 3CL).
   - `U` : saisi si connu, sinon valeurs par défaut par **époque de construction** (tables 3CL, voir §5).
   - **Ponts thermiques `PT`** : traitement forfaitaire — majoration des déperditions surfaciques selon le niveau d'isolation (à défaut de métrés de linéaires). Documenter comme écart.
   - **Ventilation `H_vent`** : `0.34 × Q_air [m³/h]`, avec débits conventionnels selon type de VMC + infiltrations forfaitaires selon étanchéité/époque.
2. **Besoins de chauffage** : approche mensuelle par **degrés-heures** : `B_ch [kWh] = Σ_mois GV × DH_mois × (1 − F_mois)` où `F` = taux de couverture des besoins par les apports gratuits (solaires + internes), calculé via le ratio apports/déperditions et l'inertie (méthode du facteur d'utilisation, type ISO 13790 / 3CL). DH par **zone climatique** (H1a…H3) et altitude (3 classes).
3. **Besoins ECS** : formule conventionnelle 3CL fonction de la surface habitable (mode conventionnel) ou du nombre d'occupants (mode personnalisé), eau froide par zone/mois.
4. **Consommations finales** : `C = B / (η_génération × η_distribution × η_émission × η_régulation)` par usage (chauffage, ECS) et par générateur. Rendements tabulés par type et âge de système (tables 3CL). Auxiliaires (VMC, circulateurs) : valeurs forfaitaires. Éclairage : forfait 3CL.
5. **Conversions** :
   - Énergie primaire : coefficient **2,3** pour l'électricité, 1,0 pour les autres énergies (convention DPE 2021).
   - CO₂ : facteurs d'émission par énergie de la **Base Carbone ADEME** (utiliser les valeurs conventionnelles du DPE 2021, notamment ~79 gCO₂e/kWh pour l'électricité chauffage — vérifier les valeurs exactes dans l'arrêté DPE, elles diffèrent de la Base Carbone générale ; sourcer précisément dans `tables/`).
   - Euros : prix des énergies dans `tables/energy_prices.json` avec date de référence explicite, modifiable par l'utilisateur en mode personnalisé.
6. **Étiquettes** : double seuil énergie primaire (kWhep/m²/an) ET climat (kgCO₂/m²/an), seuils officiels DPE 2021 (A→G), l'étiquette finale étant la plus défavorable des deux.

### 4.2 Mode personnalisé

Paramètres exposés : température de consigne (défaut conventionnel 19 °C), réduit de nuit/absence, nombre d'occupants, prix des énergies. Implémentation : `occupancy.py` fournit un objet `OccupancyScenario` injecté dans la chaîne ; le mode conventionnel est une instance figée de ce même objet. **Interdiction** de dupliquer la chaîne de calcul pour le mode personnalisé.

### 4.3 Gestes de rénovation

Chaque geste est un objet `RenovationMeasure` qui transforme un `Building` en un nouveau `Building` (immutabilité : jamais de mutation en place) :
- Isolation (combles/murs) : ajout d'une résistance `ΔR` → nouveau `U = 1/(1/U_avant + ΔR)`. Valeurs par défaut : R=7 combles, R=3,7 murs (niveaux « performants » usuels), paramétrables.
- Fenêtres : remplacement du `Uw` (et facteur solaire).
- Chauffage : remplacement du générateur → nouveaux rendements ; pour les PAC, utiliser un **SCOP saisonnier** tabulé par zone climatique (pas le COP nominal). Le changement d'énergie modifie EP, CO₂ et €.
- ECS : idem via rendement/COP du nouveau générateur ECS.
- VMC : modifie `Q_air` (hygro B réduit les débits moyens ; double flux ajoute un rendement de récupération ~70-85 % sur l'air extrait) ET la conso d'auxiliaires (à ne pas oublier — le double flux consomme plus d'électricité).
- **Bouquets** : application séquentielle enveloppe d'abord, systèmes ensuite. Les économies d'un bouquet ne sont PAS la somme des économies individuelles (interactions) — c'est un point pédagogique à faire ressortir dans l'UI.

### 4.4 Économie

- Coûts de travaux : `tables/renovation_costs.json` — fourchettes €/m² ou €/unité par geste, **sourcées** (ADEME, observatoires des coûts de la rénovation ; chaque valeur porte sa source et sa date). Afficher systématiquement des fourchettes, jamais un chiffre unique.
- Économies annuelles : `Δ€ = coût_énergie(avant) − coût_énergie(après)` au périmètre chauffage+ECS+auxiliaires.
- Temps de retour simple : `investissement / Δ€`, borné et affiché « > 30 ans » au-delà.

---

## 5. Données et tables

Toutes les valeurs tabulées vivent dans `engine/renosim/tables/` en JSON/CSV, chacune avec un champ `source` et `date`. Ne jamais coder de constante métier en dur dans le code Python.

| Table | Contenu | Source à utiliser |
|---|---|---|
| `u_values_default.json` | U par paroi × époque de construction | Tables méthode 3CL-DPE 2021 (annexe arrêté) |
| `climate_zones.json` | DH mensuels, températures, ensoleillement par zone H1a…H3 + altitude | Données conventionnelles 3CL |
| `system_efficiencies.json` | Rendements par générateur × âge ; SCOP PAC par zone | Tables 3CL |
| `ventilation.json` | Débits conventionnels par type de VMC | Tables 3CL |
| `emission_factors.json` | gCO₂e/kWh par énergie | Convention DPE 2021 / Base Carbone ADEME |
| `energy_prices.json` | €/kWh par énergie, date de référence | Tarifs réglementés / bases publiques, à dater |
| `renovation_costs.json` | Fourchettes de coûts par geste | ADEME / observatoires, sourcé ligne à ligne |
| `dpe_thresholds.json` | Seuils étiquettes EP et CO₂ | Arrêté DPE 2021 |

**Base DPE ADEME (validation uniquement, jamais embarquée dans l'app) :**
- Source : data.ademe.fr, jeu « DPE logements existants (depuis juillet 2021) », accessible par API (ODS/API tabulaire). Vérifier le nom exact et l'URL de l'API au moment de l'implémentation (elles évoluent).
- Échantillonnage : maisons individuelles uniquement, DPE 2021+, champs techniques suffisamment renseignés ; viser 5 000–20 000 lignes après nettoyage, stratifiées par époque × zone climatique × énergie de chauffage.
- Les données brutes ne sont **jamais** committées (`data/` contient les scripts et un README, `.gitignore` couvre les fichiers).

---

## 6. Application web

### 6.1 Stack

Vite + React + TypeScript. Styling : Tailwind (ou CSS modules — au choix, mais cohérent). Graphiques : Recharts. Pas de state manager lourd (Context/useReducer suffisent). Déploiement : GitHub Pages via Actions.

### 6.2 Parcours utilisateur (3 écrans)

1. **Décrire mon logement** — formulaire-parcours par étapes (stepper), pas un tableau de champs : Localisation (code postal → zone climatique + altitude) → Général (surface, année, niveaux, mitoyenneté simple) → Enveloppe (état d'isolation par paroi : « non isolé / isolation d'origine / rénové récemment / je connais le R », type de vitrage) → Systèmes (chauffage, ECS, ventilation, âge). Chaque champ technique a une aide contextuelle en français simple. Tout champ a un défaut raisonnable dérivé de l'époque : l'utilisateur pressé doit pouvoir obtenir un résultat en < 2 min.
2. **Ma situation actuelle** — étiquette DPE (visuel officiel), décomposition des déperditions (graphique : par où part la chaleur), conso et coût annuels, CO₂. Toggle conventionnel/personnalisé (voir §2.1 — l'étiquette ne bouge pas en mode personnalisé, l'UI doit l'expliquer).
3. **Mes scénarios** — sélection de gestes (cartes activables) et bouquets pré-définis (« Enveloppe d'abord », « Sortie du fioul », « Rénovation globale ») ; tableau/graphique comparatif : coût (fourchette), économies €/an, ΔCO₂, temps de retour, étiquette après. Graphique coût vs gain. Message pédagogique sur la non-additivité des gestes.

### 6.3 Exigences transverses

- **Transparence** : un panneau « Comment est-ce calculé ? » accessible partout, résumant méthode, hypothèses et limites, avec lien vers la note de validation et le dépôt.
- **Avertissement** visible : « Outil pédagogique — ne remplace ni un DPE officiel ni un audit énergétique ». Lien France Rénov'.
- Responsive (mobile OK), français, accessible (labels, contrastes).
- Aucune donnée utilisateur ne quitte le navigateur (argument à afficher : « vos données restent chez vous »).

---

## 7. Qualité, tests, validation

### 7.1 Tests du moteur (pytest, CI obligatoire)

- Tests unitaires par module (déperditions, DH, rendements, étiquettes) avec valeurs calculées à la main en commentaire.
- `test_reference_cases.py` : au moins 5 cas de bout en bout avec résultats attendus et tolérances, p. ex. :
  - Maison ~1970, 100 m², non isolée, chaudière fioul ancienne, zone H1 → étiquette F–G attendue.
  - Même maison après bouquet complet (isolation + PAC) → C–D attendu, économies > 60 %.
  - Maison RT2012, 100 m², PAC → B–C attendu.
  - Cas limite : très petite surface (< 40 m²) — vérifier le traitement des seuils DPE surfaciques si implémentés, sinon documenter l'écart.
- Propriétés invariantes : ajouter de l'isolation ne doit JAMAIS augmenter les besoins ; un bouquet ne doit jamais être moins performant que le meilleur de ses gestes ; conso strictement positive.
- Couverture cible engine : ≥ 85 %.

### 7.2 Campagne de validation (le différenciateur du projet)

1. Échantillon base ADEME (voir §5), mapping champs ADEME → `Building` (documenter chaque choix de mapping dans `validation/mapping.py` — c'est la partie la plus délicate, les champs ADEME sont hétérogènes et partiellement remplis ; journaliser les taux de rejet et raisons).
2. Exécution du moteur en mode conventionnel sur chaque logement.
3. Métriques : biais moyen et MAE/MAPE sur kWhep/m²/an ; **matrice de confusion des étiquettes** ; taux d'accord exact et à ±1 classe ; analyse des écarts par époque, zone, énergie, étiquette.
4. Note technique (`validation/report/`, Quarto de préférence — cohérent avec l'écosystème existant de l'auteur) : méthode, écarts assumés vs 3CL officielle (reprendre `docs/deviations.md`), résultats, figures, limites, pistes.
5. **Critère de succès V1 : ≥ 60 % d'accord exact d'étiquette et ≥ 90 % à ±1 classe** sur l'échantillon nettoyé. Si non atteint : analyser, ajuster les forfaits (ponts thermiques, apports), re-valider — documenter chaque itération de calibration (c'est de la matière pour la note, pas un échec).

### 7.3 Conventions de code

- Python ≥ 3.11, typé (mypy strict sur `engine/`), ruff (lint + format), dataclasses immuables (`frozen=True`), docstrings NumPy style avec unités SI explicites dans chaque signature (`u_value_w_per_m2k` plutôt que `u`).
- Pas de dépendance lourde dans `engine/` (stdlib only) — contrainte Pyodide/wheel.
- TypeScript strict côté app ; les types du schéma JSON partagé sont générés ou écrits une fois dans `app/src/types/` et référencés partout.
- Commits conventionnels (`feat:`, `fix:`, `docs:`…), branches par phase, PR même en solo (auto-revue = traçabilité).

---

## 8. Plan d'implémentation par phases

Chaque phase se termine par : tests verts, CI verte, un commit/tag de phase, et une mise à jour du README. Ne pas entamer une phase si la précédente n'a pas son critère de sortie.

**Phase 0 — Scaffolding (½ journée)**
Structure du dépôt, pyproject, CI lint+tests, app Vite vide qui se déploie sur Pages, `docs/deviations.md` créé.
*Sortie : pipeline complet qui build et déploie un « hello world » des deux côtés.*

**Phase 1 — Moteur cœur (semaine 1)**
`models.py`, tables §5 (encodage soigné, sources), `envelope.py`, `needs.py`, `systems.py`, `outputs.py`, `occupancy.py` (les deux modes dès maintenant), tests §7.1.
*Sortie : notebook de démo — décrire une maison → conso, CO₂, étiquette, dans les deux modes. Cas de référence verts.*

**Phase 2 — Gestes & économie (début semaine 2)**
`renovation.py`, `economics.py`, `tables/renovation_costs.json` sourcée, tests d'invariants et de bouquets.
*Sortie : notebook — maison F + bouquet → C, coût, temps de retour.*

**Phase 3 — Validation ADEME (semaine 2)**
`download_dpe.py`, `mapping.py`, `run_validation.py`, campagne, calibration éventuelle des forfaits, note technique v1.
*Sortie : note de validation avec métriques §7.2 atteintes ou itérations documentées.*

**Phase 4 — App React + Pyodide (semaine 3)**
Bridge Pyodide + schéma JSON versionné, écran 1 (formulaire-parcours), écran 2 (situation), écran 3 (scénarios), écran de chargement, transparence & avertissements §6.3.
*Sortie : app déployée sur Pages, utilisable de bout en bout sur un cas réel.*

**Phase 5 — Consolidation (semaine 4)**
README exemplaire (captures, badge CI, section « ce que cet outil n'est pas »), docs du package, note de validation finale mise en forme, billet de blog pour le site personnel (al-folio), nettoyage, tag `v1.0`.
*Sortie : projet montrable en entretien via un seul lien.*

**Backlog post-V1 (ne pas implémenter, lister dans le README) :** appartements, ITE/ITI distincts, confort d'été, PV/autoconsommation, aides financières (lien seulement), VAN/TRI, export PDF du rapport de simulation, mode comparaison multi-logements.

---

## 9. Règles de travail avec Claude Code

1. **Lire ce document avant chaque session.** En cas de conflit entre une instruction ponctuelle et ce brief, signaler le conflit plutôt que de choisir silencieusement.
2. **Respecter les phases** : ne pas anticiper le front pendant les phases moteur ; ne pas « améliorer » le périmètre (§2.2) sans demande explicite.
3. **Toute constante métier** passe par `tables/` avec source et date. Une valeur non sourcée = un TODO bloquant, pas une valeur inventée.
4. **Écarts à la 3CL** : chaque simplification est ajoutée à `docs/deviations.md` au moment où elle est codée, avec justification.
5. **Tests d'abord sur le moteur** : pour tout nouveau module de calcul, écrire au moins un test avec valeur attendue calculée à la main avant l'implémentation.
6. **Ne jamais committer de données ADEME brutes** ni de fichiers > 1 Mo hors assets front.
7. **Vérifier les sources externes au moment de coder** (URL de l'API ADEME, valeurs exactes des facteurs CO₂ et seuils DPE dans les arrêtés en vigueur, prix des énergies) : ne pas se fier à des valeurs mémorisées, les confronter aux documents officiels et noter la référence.
8. En fin de session : résumer ce qui a été fait, l'état des tests, et les prochaines étapes dans `docs/journal.md`.

---

## 10. Définition de « terminé » (V1)

- [ ] Moteur : chaîne complète, 2 modes, 6 gestes, bouquets ; tests ≥ 85 % de couverture, cas de référence et invariants verts.
- [ ] Validation : campagne sur ≥ 5 000 DPE nettoyés, critères §7.2 atteints ou itérations documentées, note technique publiée.
- [ ] App : 3 écrans, Pyodide fonctionnel, déployée sur GitHub Pages, responsive, avertissements et panneau méthode présents.
- [ ] Docs : README exemplaire, `deviations.md` complet, sources tracées dans toutes les tables, billet de blog prêt.
- [ ] Reproductibilité : un tiers peut cloner, `pip install -e engine`, lancer les tests et relancer la validation avec les scripts fournis.
