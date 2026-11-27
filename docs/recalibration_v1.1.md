# Plan de recalibration v1.1 (préparé le 27/11/2026)

Ce document applique le protocole annoncé au §7 de la note de validation (v3) **avant** toute
recalibration. Il fixe l'échantillon, la mesure de départ, les paramètres autorisés à bouger, la
méthode et la mesure finale. Il ne sera modifié que pour consigner les résultats, pas pour changer
les règles après coup.

## 1. Échantillons

| Rôle | Fichier (non versionné) | Tirage | Lignes |
|---|---|---|---:|
| **Calibration v3** | `data/dpe_calib_v3.jsonl` | aléatoire (`--random`), **version de méthode 2.6 uniquement** (`--method-version 2.6`), 30 maisons par strate, disjoint de tous les échantillons existants | 11 192 (11 135 évaluées) |
| Test v1, sous-ensemble v2.6 | `data/dpe_test_v1.jsonl` | déjà tiré le 25/11/2026, jamais utilisé pour régler | 1 885 |
| Test v2 | à tirer **au moment de la mesure finale**, même commande que la calibration v3, en excluant v3 et tous les autres échantillons | — | ≈ 11 000 |

Commande de la calibration v3 (reproductible ; la base ADEME évolue, un nouveau tirage ne redonne
pas les mêmes lignes) :

```bash
python validation/download_dpe.py --random --method-version 2.6 --per-stratum 30 \
    --out data/dpe_calib_v3.jsonl \
    --exclude data/dpe_sample.jsonl data/dpe_sample_v2.jsonl data/dpe_test_v1.jsonl data/dpe_apartments.jsonl
python validation/enrich_sample.py data/dpe_calib_v3.jsonl
```

Vérifications faites : 100 % des lignes en version 2.6 (11 184 DPE de 2026, 8 de fin 2024-2025),
aucun recouvrement avec les échantillons existants.

## 2. Mesure de départ (moteur de la branche v1.1, sans aucun réglage)

Fichier : `validation/report/results_v7_calib_v3_baseline.json` (intervalles bootstrap à 95 %,
1 000 tirages, graine 2026).

| | Brut | Repondéré selon le parc |
|---|---:|---:|
| Accord à ±1 classe (critère 90 %) | **93,2 %** [92,7 ; 93,7] | 86,1 % [84,6 ; 87,6] |
| Accord exact (critère 60 %) | 53,2 % [52,3 ; 54,1] | 42,6 % [40,7 ; 44,6] |
| Biais Cep (kWhep/m²/an) | +12,3 [11,1 ; 13,5] | +39,3 [35,6 ; 43,2] |

Sur les DPE de la méthode en vigueur, le moteur de la branche tient déjà le critère à ±1 classe
en brut. Ce qui manque : le critère exact, et les segments qui pèsent lourd dans le parc (avant
1975 : ±1 classe 77,7 % et 83,6 % ; électricité : 89,8 %).

## 3. Diagnostic par étape de calcul

Fichier : `validation/report/diagnosis_calib_v3_baseline.json`
(`validation/diagnose_components.py`). Rapports moteur/DPE agrégés.

| Époque | Déperditions | Besoin chauffage | Conso chauffage | Biais Cep |
|---|---:|---:|---:|---:|
| avant 1948 | 1,118 | 1,167 | 1,292 | +66,7 |
| 1948-1974 | 1,166 | 1,269 | 1,183 | +41,0 |
| 1975-1977 | 0,935 | 0,967 | 0,934 | −11,3 |
| 1978-2012 (5 tranches) | 0,962-0,988 | 0,994-1,030 | 0,998-1,027 | −0,8 à +2,2 |
| 2013-2021 | 0,985 | 1,055 | 1,105 | +10,4 |
| après 2021 | 1,030 | 1,133 | 1,212 | +14,9 |

Le besoin d'ECS est exact partout (1,000). Par énergie (consommation par usage, kWh_ef/m²) :
chauffage au bois granulés ×1,22, bois bûches ×1,12, gaz ×1,07, électricité ×1,07 ; ECS
électrique ×1,10, ECS fioul ×0,91.

**Lecture :**
1. **Avant 1975, tout part de l'enveloppe** (déperditions +12 à +17 %). Les ponts thermiques ne
   sont pas en cause (vérifié le 27/11/2026). Restent les surfaces reconstituées et les U par
   défaut.
2. **Après 2013, le besoin dérive plus que l'enveloppe** (×1,07 à ×1,10 entre les deux) : les
   apports gratuits sont sous-estimés pour les maisons récentes.
3. **La chaîne besoin → consommation** ajoute encore 1 à 7 % pour le bois et les maisons
   récentes (agrégats), mais retire 7 % pour 1948-1974 et 3 % pour 1975-1977.

## 4. Paramètres autorisés à bouger (révision 1 du 27/11/2026, avant tout réglage)

La révision 1 remplace la version initiale de cette section après deux constats faits **avant
tout réglage** : les plages ont été sourcées, et la base ADEME publie les déperditions **par
poste** et les apports, ce qui permet de caler les entrées sur des données observées plutôt que
sur le résultat. Diagnostic par poste : `validation/diagnose_envelope.py`,
`validation/report/diagnosis_envelope_calib_v3.json`.

| Poste (moteur / DPE, calibration v3) | 1948-1974 | avant 1948 | tout le parc |
|---|---:|---:|---:|
| Murs | 1,40 | 1,08 | 1,09 |
| Plancher haut | 1,87 | 1,71 | 1,20 |
| Plancher bas | 0,56 | 0,62 | 0,71 |
| Baies et portes | 0,96 | 1,17 | 1,00 |
| Ponts thermiques | 0,96 | 1,22 | 1,04 |
| Renouvellement d'air | 1,03 | 1,05 | 1,02 |

Les écarts viennent surtout de la **traduction des étiquettes de qualité d'isolation ADEME en U**
(choix de mapping M-2/M-6) : par exemple, une toiture d'avant 1975 « insuffisante » est traitée
comme non isolée (165 W/K en moyenne) alors que les DPE publient 78 W/K. Le recalage se fait donc
en deux temps.

### Étape A — reconstitution des entrées (mapping, validation seulement)

- **A1. U par étiquette de qualité (M-14).** Pour chaque paroi (murs, plancher haut, plancher
  bas), chaque étiquette (insuffisante, moyenne, bonne, très bonne, absente) et chaque époque
  (avant/après 1975), un facteur multiplie le U du mapping actuel pour que les déperditions
  agrégées de la paroi égalent celles publiées par les DPE de la **calibration v3**. Calage sur
  les déperditions par poste, **jamais sur la consommation** ; cellules d'au moins 30 lignes,
  facteur 1 sinon. Script `validation/fit_quality_labels.py`, résultat versionné
  `validation/report/quality_label_factors_v3.json`. Les seuils officiels de qualité (annexe 8.2
  de l'arrêté DPE) n'ont pas pu être relus dans le texte aujourd'hui : ce calage empirique les
  remplace et sera confronté à ces seuils plus tard.
- A1 n'affecte pas l'application (elle ne lit pas d'étiquettes ADEME) ; elle rend la validation
  plus fidèle aux entrées réelles des DPE, de sorte que l'écart restant mesure le moteur.

### Étape B — conventions du moteur (calées sur la consommation, calibration v3)

| # | Paramètre | Valeur actuelle | Plage autorisée | Source de la plage |
|---|---|---:|---|---|
| P1 | Surface de baies reconstituée (`window_area_fraction`) | 1/6 (0,167) | **0,084 à 0,211** | Surface de baies implicite des DPE de la calibration v3 (déperditions des baies / U de la baie / Sh) : médiane 0,133, déciles p10 0,084 et p90 0,211. Repère : l'arrêté RE2020 du 4 août 2021, art. 23-II, impose au moins 1/6 de la surface de référence dans le neuf. |
| P2 | U d'un mur non isolé de matériau inconnu (app, `wall_u_nu_traditional`) | 2,0 | **1,5 à 2,5** | Table Umur0 §3.2.1.2 (pierre 40-80 cm : 2,3 à 1,5 ; brique pleine 34 cm : 2,0) ; 2,5 = plafond officiel Umur_nu. Valeur retenue = U implicite des murs « insuffisants » d'avant 1975 après l'étape A, bornée à la plage. |
| P4 | Coefficient orientation × masques (`solar_orientation_shading_coefficient`, D-06) | 0,5 | **0,45 à 0,62** | Borne haute : moyenne des coefficients C1 verticaux des quatre orientations en saison de chauffe, sans masque (§18.5 ; 0,56 à 0,62 selon la zone, `solar_orientation.json`). Borne basse : la même moyenne avec un masque partiel (facteur 0,8 de la table Fe2), soit 0,45 à 0,50 selon la zone. |
| P5 | Poids de la pleine charge du Rg saisonnier des chaudières (D-08) | 0,3 | **0,10 à 0,30** | Profil de charge conventionnel §13.2.1.1 (p.79), avec interpolation du rendement entre Rpint (30 % de charge) et Rpn (100 %) : poids effectif ≈ 0,13 pour une chaudière dimensionnée au plus juste, moins si elle est surdimensionnée ; 0,30 = valeur actuelle, borne haute. |

L'ancien P3 (étiquette absente) est traité par l'étape A. Les valeurs officielles de la méthode
(tables de U, k, rendements, Umur0, C1) ne sont jamais retouchées.

## 5. Méthode

1. **Étape A** sur la calibration v3, puis nouvelle mesure et nouveau diagnostic par étape.
2. **Sensibilités une à une** de P1, P4 et P5 dans leurs plages.
3. **Réglage conjoint** sur une grille de P1, P4 et P5, sur la calibration v3 uniquement.
   Objectif principal : l'accord à ±1 classe **repondéré selon le parc** ; objectifs secondaires :
   l'accord exact et la MAE. Contrainte : biais brut entre −5 et +5 kWhep/m². En cas d'égalité à
   0,5 point près, garder la valeur la plus proche de la valeur actuelle. P2 est fixé par
   l'étape A (il ne sert qu'à l'application).
4. **Journal de chaque essai** dans `validation/report/recalibration_v1.1_grid.json`.
5. **Mesure finale, une seule fois** : test v1 (sous-ensemble v2.6) et test v2 tiré à ce moment,
   métriques brutes et repondérées avec intervalles de confiance. Aucun retour en arrière après
   cette mesure.
6. Note de validation v4, chiffres de l'app et du README, moteur 0.8.0, fusion de la branche v1.1.

## 6. Hors réglage, à l'étude séparément

- Électricité : ECS électrique ×1,10 (stockage) et auxiliaires ×0,86, à confronter aux
  formules officielles avant toute calibration.
- Granulés : chauffage ×1,22 malgré des déperditions à ×1,07 ; vérifier la répartition poêle /
  chaudière et l'appoint dans les DPE v2.6.

## 7. Résultats du réglage (calibration v3) et écart au plan — consignés avant la mesure finale

**Étape A** (`quality_label_factors_v3.json`, `results_v7_calib_v3_stepA.json`) : ±1 classe
93,2 → 94,8 % brut, 86,1 → 89,9 % repondéré ; biais brut +12,3 → +10,6.

**Étape B** (`recalibration_v1.1_grid.json`, 100 essais) : la surface de baies (P1) et la
pondération des chaudières (P5) n'ont presque aucun effet (±0,1 point) ; seul le coefficient
solaire (P4) agit (biais brut moyen +12,5 à 0,45 → +5,8 à 0,62). **Aucun essai ne respecte la
contrainte de biais brut dans [−5 ; +5]** : la règle de sélection du §5 ne désigne donc aucun
essai.

**Écart au plan, décidé par l'auteur le 27/11/2026 :** P4 = 0,62 (borne haute sourcée, « aucun
masque »), P1 et P5 inchangés (1/6 et 0,3, valeurs actuelles, faute d'effet). Le biais brut de
calibration (+5,9) dépasse la contrainte de 0,9 point. P2 = 1,7 (U implicite des murs
« insuffisants » d'avant 1975 après l'étape A ; utilisé par l'application seulement).

**Calibration v3 finale** (`results_v8_calib_v3_final.json`) : ±1 classe 95,2 % [94,7 ; 95,6]
brut, 90,5 % [89,2 ; 91,8] repondéré ; exact 54,8 % brut, 47,5 % repondéré ; biais +5,9 brut,
+20,1 repondéré.

Mesure finale unique : test v1 (sous-ensemble v2.6, 1 895 lignes) et test v2 (tiré le
27/11/2026, même commande que la calibration v3, en excluant v3 et tous les autres échantillons).
