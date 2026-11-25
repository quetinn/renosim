# Note technique de validation — moteur RénoSim vs base DPE ADEME (v2)

**Date :** 25 novembre 2026 (v2.1 : analyse par version de méthode, §5.4 ; v2.2 : éclairage
officiel, campagne v6) · **Moteur :** `renosim` 0.5.0 (méthode 3CL-DPE 2021 simplifiée) ·
**Auteur :** Noé Quetin · **Version précédente :** v1 du 4 juillet 2026 (§9)

> La v2 ajoute ce qui manquait à la v1 : un **échantillon de test indépendant** (jamais vu
> pendant la calibration), des **intervalles de confiance** et une **repondération** selon le parc
> réel. Elle intègre aussi les itérations v2 à v4 de juillet et les campagnes appartements, confort
> d'été et refroidissement. Mise en forme Quarto et figures : Phase 5.

## 0. Résumé

Campagne **v6** (moteur actuel, éclairage officiel §16.1) :

| | Calibration (n = 11 625) | **Test indépendant (n = 11 496)** |
|---|---:|---:|
| Biais Cep (kWhep/m²/an) | +11,3 [10,1 ; 12,5] | **+33,3** [31,9 ; 34,7] |
| MAE (kWhep/m²/an) | 45,7 | 56,3 |
| Accord exact d'étiquette | 50,0 % [49,0 ; 50,9] | **44,9 %** [44,0 ; 45,8] |
| Accord à ±1 classe | 90,3 % [89,8 ; 90,9] | **87,0 %** [86,4 ; 87,6] |
| ±1 classe, repondéré selon le parc | 81,4 % [79,6 ; 83,1] | **71,7 %** [69,6 ; 73,6] |

*Crochets : intervalle de confiance à 95 % (bootstrap percentile, 1 000 tirages, graine 2026).
Campagne v5 (avant la correction de l'éclairage), test : biais +35,0, exact 44,4 %, ±1 classe
86,7 %, repondéré 71,4 %. Les analyses détaillées des §5.1 à §5.4 portent sur la v5 ; la
correction de l'éclairage ne change pas leurs conclusions.*

1. **Le critère ±1 classe ≥ 90 % (CLAUDE.md §7.2) n'est pas atteint sur données
   indépendantes.** Le chiffre publié en v1 (90,8 %), puis en v4 (90,2 %), était mesuré sur
   l'échantillon qui avait servi à calibrer, et son intervalle de confiance chevauchait déjà le
   seuil.
2. L'écart vient surtout de **la composition des échantillons par version de la méthode DPE**.
   L'échantillon de calibration, tiré « dans l'ordre du jeu de données », contient 61 % de DPE
   établis en 2026 (version de méthode 2.6), sur lesquels le moteur est bon. Sur les DPE des
   versions 2.1 à 2.5 (2022-2025), le moteur surestime d'environ **+40 kWhep/m²** dans **les
   deux** échantillons (§5.2, §5.4).
   **Sur les DPE en version actuelle (2.6) du test indépendant, le critère est atteint :**
   ±1 classe **93,6 %** [92,4 ; 94,7], exact 55,2 %, biais +2,3 (n = 1 885, v6). Repondéré selon
   le parc : 86,3 % [81,9 ; 90,2].
3. Repondérés selon la répartition réelle des maisons diagnostiquées (58 % construites avant
   1975, 46 % chauffées à l'électricité), les résultats sont nettement moins bons, car ces
   segments sont justement les plus faibles du moteur.
4. Le gaz, le fioul et les maisons de 1975 à 2012 restent au-dessus de 90 % à ±1 classe sur le
   test. Les faiblesses sont localisées : **bâti d'avant 1975, électricité, DPE 2021-2025**.

Ces résultats ne remettent pas en cause l'architecture. Ils montrent que la calibration de
juillet était sur-ajustée à un échantillon non représentatif, et ils désignent précisément ce
qu'il faut corriger (§7).

## 1. Objectif et principe

Confronter les prédictions du moteur, en mode conventionnel, aux DPE officiels de la base ADEME
« DPE Logements existants (depuis juillet 2021) » (data.ademe.fr, jeu `dpe03existant`, Licence
Ouverte v2.0), pour des **maisons individuelles**. On mesure si le moteur **reproduit la méthode
réglementaire** à partir des champs publiés, et non s'il reproduit des consommations réelles.

Métriques : biais moyen, MAE et MAPE sur la consommation d'énergie primaire (kWhep/m²/an) ;
matrice de confusion des étiquettes ; accord exact et à ±1 classe ; déclinaisons par époque,
zone, énergie et année d'établissement du DPE.

**Critères de succès V1 (CLAUDE.md §7.2) : ≥ 60 % d'accord exact, ≥ 90 % à ±1 classe.**

## 2. Données

| Échantillon | Fichier (non committé) | Tirage | Lignes | Rôle |
|---|---|---|---:|---|
| Calibration v1 | `data/dpe_sample.jsonl` | ordre du jeu, juillet 2026 | 11 708 | itérations 1 à 6 |
| Calibration v2 | `data/dpe_sample_v2.jsonl` | ordre du jeu, 11/07/2026, colonnes enrichies | 11 709 | itérations v3 à v5 |
| **Test v1** | `data/dpe_test_v1.jsonl` | **pseudo-aléatoire** (`sort=_rand` de l'API, reproductible), **disjoint** des deux précédents, 25/11/2026 | 11 549 | évaluation seule |

- Les trois échantillons sont **stratifiés** de la même façon : époque (10) × zone (8) × énergie
  principale de chauffage (5), au plus 30 lignes par strate (`validation/download_dpe.py`).
- **Disjonction vérifiée** : aucun `numero_dpe` du test n'apparaît dans les échantillons de
  calibration (11 721 identifiants exclus au tirage).
- **Années d'établissement** : calibration v2 à 61 % de 2026 ; test réparti de 2021 à 2026 (3 %,
  16 %, 20 %, 22 %, 22 %, 16 %).
- **Population de référence** pour la repondération : nombre de DPE de maisons par strate dans la
  base (4 703 421 DPE, `validation/stratum_counts.py`, relevé du 25/11/2026,
  `validation/report/stratum_counts_maisons.json`). Ce sont les maisons **diagnostiquées**,
  pas l'ensemble du parc.
- Rejets : surface hors bornes 30-400 m² (calibration 83 + 1 surface manquante ; test 53).
- **L'échantillon test n'a servi à aucun réglage.** Toute calibration future devra se faire sans
  lui, sinon il faudra en tirer un nouveau (§7).

## 3. Mapping ADEME → modèle (choix M-1 à M-11)

Le jeu ADEME ne fournit ni les surfaces de parois ni les U ; le mapping reconstruit une
description à partir des champs publiés (`validation/mapping.py`, choix documentés dans le
module) :

- **M-1** géométrie reconstruite (emprise carrée, murs = périmètre × hauteur, baies = Sh/6) ;
- **M-2/M-6** qualité d'isolation → ligne des tables U officielles ; murs anciens non isolés
  U = 2,0 ;
- **M-3** menuiseries → type de vitrage ; **M-4** âge du générateur ;
- **M-5** bois bûches évalué comme une chaudière bois aux rendements des poêles à granulés
  (écart D-22) ;
- **M-7** Ue officiel des planchers bas ; **M-8** inertie ADEME → classe d'inertie ;
- **M-9 à M-11** appartements, confort d'été, refroidissement (campagnes dédiées, §6) ;
- **convention d'énergie primaire selon la date du DPE** : 2,3 jusqu'au 31/12/2025, 1,9 en 2026
  (1,7 à partir de 2027, aucun DPE concerné à ce jour).

## 4. Historique des itérations

Toutes les itérations jusqu'à v4 ont été mesurées sur l'échantillon de calibration.

| It. | Changement | Biais | MAE | Exact | ±1 |
|---|---|---:|---:|---:|---:|
| 1 | Mapping initial naïf | +99,1 | 108,5 | 27,4 % | 62,1 % |
| 2 | M-2 : « insuffisante » ≥ 1975 → U d'époque | +41,7 | 64,3 | 42,1 % | 82,9 % |
| 3 | M-6 : qualité manquante = « moyenne » ; murs anciens U 2,0 | +36,7 | 59,9 | 42,7 % | 84,1 % |
| 4 | M-7 : Ue officiel des planchers bas | +18,5 | 50,0 | 48,1 % | 88,7 % |
| 5 | Convention EP 2,3/1,9 selon la date du DPE | +10,1 | 45,9 | 50,2 % | 90,3 % |
| 6 | Joule NF (Rr 0,99), ECS en volume habitable (Rd 0,93) — **v1 publiée** | +7,8 | 45,2 | 50,5 % | 90,8 % |
| v2 | Auxiliaires officiels §15 (D-11) | +10,8 | 45,3 | 50,2 % | 90,5 % |
| v3 | Inertie ADEME (M-8), échantillon v2 | +12,1 | 45,7 | 50,1 % | 90,3 % |
| v4 | Refroidissement §10 (D-20) | +12,9 | 45,9 | 49,8 % | 90,2 % |
| **v5** | **Aucun changement de moteur : évaluation sur l'échantillon test** | **+35,0** | **57,0** | **44,4 %** | **86,7 %** |
| **v6** | **Éclairage : heures Nh officielles par zone et par mois (§16.1), test** | **+33,3** | **56,3** | **44,9 %** | **87,0 %** |

Les itérations v2 à v4 ajoutent des éléments officiels de la méthode. Chacune dégrade légèrement
les métriques de calibration, et elles ont été conservées par fidélité méthodologique. La v5
reprend exactement le moteur de la v4 : les bascules de convention faites depuis (défaut 2026,
prix de l'énergie, indexation des coûts) n'ont pas d'effet sur ces métriques, ce qui est vérifié
par une ré-exécution bit à bit de la v4.

## 5. Résultats v5

### 5.1 Vue d'ensemble

Voir le tableau du §0. Fichiers : `validation/report/results_v5_calibration.json` et
`results_v5_test.json`.

Matrice de confusion du **test** (lignes = observé, colonnes = prédit) :

| obs\pred | A | B | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 117 | 353 | 268 | 25 | 3 | 0 | 0 |
| **B** | 32 | 321 | 685 | 130 | 28 | 12 | 1 |
| **C** | 2 | 97 | 1 910 | 1 356 | 228 | 91 | 30 |
| **D** | 0 | 5 | 345 | 1 762 | 916 | 245 | 128 |
| **E** | 0 | 0 | 26 | 305 | 588 | 351 | 205 |
| **F** | 0 | 0 | 7 | 50 | 140 | 207 | 214 |
| **G** | 0 | 0 | 1 | 7 | 32 | 69 | 204 |

La masse au-dessus de la diagonale (prédit plus mauvais qu'observé) confirme un biais
systématique de surestimation, qui n'apparaît pas sur la calibration.

### 5.2 Effet de l'année d'établissement du DPE

| Année | Calibration n | biais | ±1 | Test n | biais | ±1 |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 1 608 | −7,4 | 90,1 % | 342 | +88,1 | 74,3 % |
| 2022 | 1 178 | +15,3 | 92,4 % | 1 862 | +40,2 | 86,1 % |
| 2023 | 525 | +32,0 | 89,1 % | 2 316 | +39,4 | 86,6 % |
| 2024 | 371 | +37,6 | 85,4 % | 2 581 | +37,7 | 85,9 % |
| 2025 | 831 | +41,4 | 82,9 % | 2 511 | +40,7 | 84,7 % |
| 2026 | 7 112 | +11,1 | 91,0 % | 1 884 | +3,7 | 93,6 % |

- Sur 2023-2026, les deux échantillons concordent année par année : le moteur ne se comporte pas
  différemment sur le test. **C'est la composition par année qui change le résultat global.**
- Les DPE de 2026 (convention 1,9) sont bien reproduits ; ceux de 2022-2025 (convention 2,3)
  sont surestimés d'environ 40 kWhep/m².
- Deux explications étaient possibles : des valeurs de la base recalculées après coup au
  coefficient 1,9, ou une évolution de la méthode entre versions. Le §5.4 tranche en faveur de
  la seconde. L'année 2021 (n = 342 au test) est trop peu représentée pour conclure.

### 5.3 Par énergie et par époque (test)

| Énergie | n | Exact | ±1 | Part du parc diagnostiqué |
|---|---:|---:|---:|---:|
| Gaz naturel | 2 370 | 57,0 % | 93,2 % | 33,7 % |
| Fioul domestique | 1 979 | 51,3 % | 91,5 % | 11,0 % |
| Bois granulés | 2 376 | 45,8 % | 89,6 % | 2,4 % |
| Bois bûches | 2 393 | 41,6 % | 89,0 % | 6,5 % |
| **Électricité** | 2 378 | **27,7 %** | **71,2 %** | **46,4 %** |

| Époque | ±1 (test) | Biais (test) | Part du parc |
|---|---:|---:|---:|
| avant 1948 | 63,8 % | +110 | 34,3 % |
| 1948-1974 | 72,1 % | +81 | 23,6 % |
| 1975-2012 (6 tranches) | 88,8 à 96,2 % | +13 à +21 | 35,8 % |
| 2013-2021 | 86,9 % | +24 | 5,1 % |
| après 2021 | 86,0 % | +28 | 1,1 % |

C'est ce croisement qui explique les résultats repondérés : les segments les plus fréquents dans
le parc (électricité, bâti ancien) sont ceux où le moteur est le moins fidèle.

### 5.4 Analyse approfondie : version de méthode et usages (v2.1)

Les deux échantillons ont été enrichis par `numero_dpe` (`validation/enrich_sample.py`) avec la
version de méthode (`version_dpe`) et les consommations **par usage** en énergie finale et
primaire. Analyse : `validation/analyze_bias.py`, résultats agrégés dans
`validation/report/bias_analysis_v5.json`.

**1. Pas de recalcul rétroactif.** Pour l'éclairage, toujours électrique, le rapport EP/EF publié
donne le coefficient réellement appliqué : **2,3 pour les DPE de 2021 à 2025** et **1,9 pour
ceux de 2026**, à quelques dizaines d'exceptions près sur ~23 000 (DPE 2021-2022 à 1,0, une
quinzaine à 2,0, et 24 DPE de fin 2025 déjà à 1,9 dans la calibration). Le choix de la
convention selon la date du DPE est donc correct : appliquer à chaque DPE son coefficient
effectif ne change pas les métriques (test identique ; biais calibration 12,9 → 12,8).

**2. La rupture suit la version de méthode.** Biais Cep sur le test :

| Version | 1 / 1.1 (2021) | 2.1 | 2.2 | 2.3 | 2.4 | 2.5 | **2.6** (2026) |
|---|---:|---:|---:|---:|---:|---:|---:|
| n | 291 | 1 040 | 1 824 | 2 550 | 2 782 | 908 | 1 885 |
| Biais | +94 | +41 | +39 | +38 | +42 | +37 | **+4** |
| ±1 classe | 73 % | 87 % | 87 % | 86 % | 85 % | 85 % | **94 %** |

Le biais est stable de la v2.1 à la v2.5 et tombe à la v2.6. À l'intérieur d'une même année, le
découpage par version donne les mêmes niveaux, et la calibration présente le même profil sur les
versions 2.3 à 2.5 (+34 à +46).

**3. L'enveloppe et les besoins ne sont pas en cause.** Rapport moteur/DPE sur le test :
déperditions totales (GV vs `deperditions_enveloppe`) **0,98 à 0,99** et besoin de chauffage
(vs `besoin_chauffage`) **1,03 à 1,05**, **identiques pour les versions 2.4, 2.5 et 2.6**. L'écart
se loge dans la chaîne qui passe du besoin à la consommation :

| Rapport moteur/DPE (énergie finale, test) | v2.4 | v2.5 | v2.6 |
|---|---:|---:|---:|
| Chauffage | 1,21 | 1,18 | 1,04 |
| ECS | 1,19 | 1,19 | 1,04 |
| Éclairage | 1,41 | 1,41 | 1,41 |
| Auxiliaires | 1,06 | 1,00 | 0,99 |

Pour un même besoin, les DPE des versions 2.4-2.5 publient environ 15 % de consommation de
chauffage et d'ECS en moins que le moteur, ceux de la version 2.6 à peine 4 %. Le rapport
consommation/besoin publié est stable pour le gaz (1,16-1,18) et le fioul (1,25-1,28) d'une
version à l'autre, mais pas pour le bois (bûches 1,03-1,06 en v2.4-2.5 contre 1,19 en v2.6) ni
pour l'ECS (1,47 contre 1,52). Ce n'est donc pas un coefficient global : il faut descendre au
**type de générateur** (champ `type_generateur_chauffage_principal`) et à la composition des
sous-populations (part des PAC dans « électricité », notamment).

**4. Un écart indépendant de la version : l'éclairage — corrigé en v6.** Le moteur comptait
2,7 kWh_ef/m² contre 1,9 publié, dans toutes les versions et pour toutes les énergies (+41 %).
Cause : une durée « moyenne nationale » de 2 123 h, alors que le §16.1 de l'annexe 1 (p.102-103)
tabule les heures de fonctionnement par zone et par mois, de 1 445 à 1 566 h/an. Avec la table
officielle, 0,9 × 1,4 × 1 500 / 1 000 = 1,89 kWh/m² en H1a, et le rapport moteur/DPE tombe à
**1,000-1,007** sur les deux échantillons (`bias_analysis_v6.json`). Effet sur les métriques :
voir la v6 du §0 (environ −1,7 kWhep/m²).

**Lecture.** Le moteur a été calé, sans que ce soit voulu, sur des DPE de la version de méthode
2.6 (2026), qui est la version en vigueur et donc **celle que l'outil doit reproduire**. Sur ces
DPE, il tient le critère sur données indépendantes (échantillon équilibré). Les DPE établis
avec les versions antérieures des logiciels ne sont pas reproduits aussi bien. Il reste une
faiblesse réelle, qui ne dépend pas de la version : une fois repondérés selon le parc, même les
DPE v2.6 restent sous le seuil (86,3 %), à cause du bâti ancien et de l'électricité.

## 6. Autres campagnes (juillet 2026, échantillons « ordre du jeu »)

Ces campagnes n'ont **pas** encore d'échantillon test indépendant. Leurs chiffres sont donc à lire
comme des résultats de calibration.

- **Appartements** (D-18, 8 895 DPE) : biais −0,2 kWhep/m², exact 45,0 %, ±1 classe 87,9 %,
  après calibration poste à poste des conventions de reconstruction.
- **Confort d'été passif** (annexe 9, D-19) : sur les DPE ≥ 2025, version de la grille en
  vigueur, maisons 95,5 % d'accord exact (n = 7 943), appartements 91,0 % (n = 4 284). Grille
  officielle reproduite, sans calibration.
- **Refroidissement** (§10, D-20, 2 383 maisons climatisées) : besoin −13 %, conso EP +28 %
  (majorant attendu : surface refroidie supposée totale).

## 7. Analyse et suites

**Ce que la v5 change.** La calibration de juillet a été réglée sur un échantillon dominé par les
DPE de version 2.6. Elle reproduit bien cette version (en vigueur), moins bien les versions
antérieures, et reste faible sur le bâti ancien et l'électricité une fois repondérée. Le constat
d'audit (« calibration et évaluation sur le même échantillon ») est confirmé, et l'analyse par
version (§5.4) en donne la cause.

**Choix méthodologique proposé :** prendre comme **référence de validation les DPE de la version
de méthode en vigueur** (2.6 aujourd'hui, la suivante à partir de 2027), puisque l'outil affiche
l'étiquette selon la réglementation du jour. Les versions antérieures sont rapportées à titre
d'information. Ce choix devra être annoncé dans la note avant la prochaine calibration, et pas
choisi après coup selon les résultats.

**Suites, par ordre de priorité** (l'éclairage, ex-priorité 1, est corrigé en v6) :
1. **Tirer un nouvel échantillon de calibration aléatoire, limité à la version en vigueur**
   (`--random`, disjoint du test). Calibrer uniquement dessus, puis mesurer une seule fois sur le
   sous-ensemble v2.6 du test v1 (et sur un test v2 tiré de la même façon).
2. **Électricité et bâti d'avant 1975** : analyse par type de générateur (part des PAC, joule,
   ECS électrique) et leviers v1.1 de l'audit (matériau des murs, ponts thermiques linéiques,
   inertie Th-I).
3. **Versions antérieures** : comprendre ce qui change dans la chaîne de génération entre les
   versions 2.5 et 2.6 (notes de version des logiciels, contrôles de cohérence ADEME), pour
   documenter l'écart plutôt que le corriger.
4. **Publier les chiffres complets** (calibration, test, version en vigueur, brut et repondéré)
   dans le README et l'app.

**Critère exact (60 %).** Il reste hors d'atteinte (44 % au test). La v1 l'attribuait à un manque
d'information du mapping, et cette explication tient toujours en partie. Mais le biais
systématique du §5.2 montre qu'il y a aussi un écart de modèle à corriger avant de conclure.

## 8. Reproductibilité

```bash
# échantillons (≈ 5 min chacun ; données jamais committées)
python validation/download_dpe.py --out data/dpe_sample_v2.jsonl
python validation/download_dpe.py --random --out data/dpe_test_v1.jsonl \
    --exclude data/dpe_sample.jsonl data/dpe_sample_v2.jsonl
python validation/stratum_counts.py              # effectifs du parc par strate (≈ 2 min)

# campagne v5
python validation/run_validation.py --sample data/dpe_test_v1.jsonl \
    --out validation/report/results_v5_test.json --bootstrap 1000 \
    --weights validation/report/stratum_counts_maisons.json --by-year

# analyse par version de méthode et par usage (§5.4, ≈ 4 min d'enrichissement)
python validation/enrich_sample.py data/dpe_test_v1.jsonl data/dpe_sample_v2.jsonl
python validation/analyze_bias.py data/dpe_test_v1.jsonl data/dpe_sample_v2.jsonl \
    --out validation/report/bias_analysis_v5.json
```

Note : la base ADEME évolue (nouveaux DPE, mises à jour). Un nouveau tirage ne redonnera pas
exactement les mêmes lignes ; les fichiers de résultats committés font foi pour cette note.

## 9. Historique

- **v1 (04/07/2026)** : itérations 1 à 6, ±1 classe 90,8 % sur l'échantillon de calibration ;
  critère déclaré atteint.
- **v2 (25/11/2026)** : chapitres v2 à v4, échantillon test indépendant, bootstrap,
  repondération ; critère **non atteint** sur données indépendantes (86,7 %).
- **v2.1 (25/11/2026)** : analyse par version de méthode et par usage ; pas de recalcul
  rétroactif ; critère atteint sur les DPE en version actuelle (93,6 %, brut) mais pas une fois
  repondéré (86,3 %) ; écart d'éclairage constant de +41 % identifié.
- **v2.2 (25/11/2026)** : éclairage corrigé (heures officielles du §16.1) ; campagne v6 : test
  ±1 classe 87,0 %, biais +33,3 ; DPE v2.6 du test 93,6 %, biais +2,3.
