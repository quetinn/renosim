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

## 4. Paramètres autorisés à bouger

Seuls des paramètres **de convention ou de calibration** bougent, chacun dans une plage justifiée.
Les valeurs officielles de la méthode (tables de U, k de ponts thermiques, rendements, Umur0…) ne
sont jamais retouchées.

| # | Paramètre | Valeur actuelle | Plage autorisée | Justification de la plage | Cible du diagnostic |
|---|---|---:|---|---|---|
| P1 | Surface de baies reconstituée (`conventions.geometry.window_area_fraction`) | 1/6 | 1/8 à 1/5 | ordre de grandeur des maisons ; non sourcé par un texte | enveloppe avant 1975 |
| P2 | U des murs anciens non isolés sans matériau connu (M-6, `wall_u_nu_traditional`) | 2,0 | 1,5 à 2,5 | plage de la table Umur0 pour les maçonneries traditionnelles épaisses ; 2,5 = plafond officiel | enveloppe avant 1975 |
| P3 | Qualité d'isolation absente (M-6) | « moyenne » | « moyenne » ou règle du §3.4 (non isolé avant 1975) | règle officielle des parois d'état inconnu | enveloppe avant 1975 |
| P4 | Coefficient orientation × masques (`calibrated.solar_orientation_shading_coefficient`, D-06) | 0,5 | 0,4 à 1,0 | 1,0 = aucune réduction ; seuil bas déjà calibré | besoin des maisons récentes |
| P5 | Poids de la pleine charge du Rg saisonnier des chaudières (D-08) | 0,3 | 0,2 à 0,5 | approximation des profils de charge §13.2.1.1 | chaîne chaudières |

Le forfait de ponts thermiques des maisons (0,08) n'est plus un paramètre : il est remplacé par le
modèle officiel. Les choix structurels (mapping M-1 à M-13) peuvent être corrigés s'ils sont faux,
mais pas utilisés comme leviers de réglage.

## 5. Méthode

1. **Sensibilités une à une** de P1 à P5 sur la calibration v3 (métriques brutes et repondérées,
   diagnostic par étape), pour vérifier que chaque paramètre agit sur l'étape visée et pas
   ailleurs.
2. **Réglage conjoint** sur une grille des paramètres retenus, sur la calibration v3 uniquement.
   Objectif principal : l'accord à ±1 classe **repondéré selon le parc**, pour ne pas sur-ajuster
   les segments rares. Objectifs secondaires : l'accord exact et la MAE. Contrainte : le biais
   brut reste entre −5 et +5 kWhep/m². En cas d'égalité à 0,5 point près, garder la valeur la plus
   proche de la valeur actuelle.
3. **Journal de chaque essai** dans `validation/report/` (valeurs testées, métriques), repris
   dans la note.
4. **Mesure finale, une seule fois** : test v1 (sous-ensemble v2.6) et test v2 tiré à ce moment,
   métriques brutes et repondérées avec intervalles de confiance, par époque, énergie et
   version. Aucun retour en arrière après cette mesure.
5. Note de validation v4, chiffres de l'app et du README, moteur 0.8.0, fusion de la branche v1.1.

## 6. Hors réglage, à l'étude séparément

- Électricité : ECS électrique ×1,10 (stockage) et auxiliaires ×0,86, à confronter aux
  formules officielles avant toute calibration.
- Granulés : chauffage ×1,22 malgré des déperditions à ×1,07 ; vérifier la répartition poêle /
  chaudière et l'appoint dans les DPE v2.6.
