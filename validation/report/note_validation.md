# Note technique de validation — moteur RénoSim vs base DPE ADEME (v1)

**Date :** 4 juillet 2026 · **Moteur :** `renosim` 0.3.0 (méthode 3CL-DPE 2021 simplifiée) ·
**Auteur :** Noé Quetin

> Cette note sera mise en forme (Quarto, figures) en Phase 5. Elle documente la campagne v1 :
> méthode, choix de mapping, itérations de calibration et résultats, conformément au CLAUDE.md §7.2.

## 1. Objectif et principe

Confronter les prédictions du moteur (mode conventionnel) aux DPE officiels de la base ADEME
« DPE Logements existants (depuis juillet 2021) » (data.ademe.fr, jeu `dpe03existant`,
~15,1 M lignes, Licence Ouverte v2.0, consulté le 04/07/2026) sur des **maisons individuelles**.

Métriques : biais moyen, MAE et MAPE sur la consommation d'énergie primaire (kWhep/m²/an) ;
matrice de confusion des étiquettes ; taux d'accord exact et à ±1 classe ; déclinaison par
époque, zone climatique et énergie de chauffage.

**Critères de succès V1 (CLAUDE.md §7.2) : ≥ 60 % d'accord exact, ≥ 90 % à ±1 classe.**

## 2. Échantillon

- Échantillonnage **stratifié** par époque de construction (10) × zone climatique (8) × énergie
  principale de chauffage (5), ≤ 30 lignes par strate, via l'API data-fair
  (`validation/download_dpe.py`). Les données brutes ne sont jamais committées.
- **11 708 lignes** téléchargées ; **11 624 retenues** (99,3 %). Rejets : surface hors
  bornes 30-400 m² (83), surface manquante (1). Filtre amont : `methode_application_dpe =
  "dpe maison individuelle"`.
- Limite assumée : à l'intérieur d'une strate, les lignes sont prises dans l'ordre du jeu de
  données (pas de tirage aléatoire) ; la stratification large (368 strates renseignées) limite
  le biais de sélection.

## 3. Mapping ADEME → modèle (choix M-1 à M-7)

Le jeu ADEME ne fournit ni les surfaces de parois ni les U : le mapping reconstruit une
description à partir des champs disponibles (`validation/mapping.py`, choix documentés
M-1 à M-7 dans le module) :

- **M-1 Géométrie reconstruite** : emprise carrée `Sh/niveaux`, murs = périmètre × hauteur,
  fenêtres = Sh/6 (convention DPE historique), toiture = plancher = emprise.
- **M-2/M-6 Qualité d'isolation → U** : les libellés (`insuffisante`/`moyenne`/`bonne`/`très
  bonne`) sélectionnent une ligne des tables U officielles — jamais de valeur inventée.
  « Insuffisante » sur une construction ≥ 1975 renvoie à la ligne d'époque (l'isolation
  réglementaire existait) ; murs anciens réellement non isolés : U = 2,0 (milieu de la table
  Umur0 officielle).
- **M-3 Menuiseries** : qualité → type de vitrage des défauts V1.
- **M-4 Âge du générateur** : extrait du libellé (« …2001-2015 ») sinon année de construction.
- **M-5 Bois bûches** : évalué avec les rendements granulés (limite moteur V1).
- **M-7 Plancher bas** : coefficient Ue officiel des planchers sur terre-plein/vide sanitaire
  (annexe 1 p.18, ligne 2S/P=5) appliqué via le coefficient b.
- **Millésime réglementaire** : les DPE établis à partir du 01/01/2026 sont comparés en
  convention EP électricité **1,9** (arrêté du 13/08/2025), les antérieurs en **2,3**.

## 4. Itérations de calibration

Chaque itération est un choix documenté, jamais un ajustement aveugle :

| It. | Changement | Biais CEP | MAE | Exact | ±1 classe |
|----:|---|---:|---:|---:|---:|
| 1 | Mapping initial naïf (« insuffisante » = non isolé) | +99,1 | 108,5 | 27,4 % | 62,1 % |
| 2 | M-2 : « insuffisante » ≥ 1975 → U d'époque | +41,7 | 64,3 | 42,1 % | 82,9 % |
| 3 | M-6 : qualité manquante = « moyenne » ; murs anciens U 2,0 | +36,7 | 59,9 | 42,7 % | 84,1 % |
| 4 | M-7 : Ue officiel planchers sur terre-plein | +18,5 | 50,0 | 48,1 % | 88,7 % |
| 5 | Millésime EP 2,3/1,9 selon date du DPE | +10,1 | 45,9 | 50,2 % | 90,3 % |
| 6 | Hypothèses conventionnelles : émetteurs joule NF (Rr 0,99), ECS en volume habitable (Rd 0,93) | **+7,8** | **45,2** | **50,5 %** | **90,8 %** |

Enseignements notables : (a) l'essentiel du biais initial venait du **mapping**, pas du moteur ;
(b) l'oubli du coefficient Ue des planchers bas pesait ~160 W/K sur les maisons anciennes ;
(c) la base ADEME **mélange déjà deux conventions EP** (2,3 avant 2026, 1,9 après) — toute
validation qui l'ignore surestime les maisons électriques de ~21 %.

## 5. Résultats finaux (itération 6, n = 11 624)

- **Biais CEP : +7,8 kWhep/m²/an** · MAE : 45,2 · MAPE : 29,5 %
- **Accord exact : 50,5 %** (cible 60 % — non atteinte)
- **Accord ±1 classe : 90,8 %** (cible 90 % — **atteinte**)

Matrice de confusion (lignes = observé, colonnes = prédit) :

| obs\pred | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **A** | 256 | 434 | 160 | 7 | 4 | 0 | 0 |
| **B** | 97 | 549 | 673 | 80 | 16 | 9 | 2 |
| **C** | 11 | 275 | 2437 | 933 | 176 | 34 | 10 |
| **D** | 0 | 16 | 680 | 1814 | 640 | 172 | 63 |
| **E** | 0 | 1 | 52 | 384 | 479 | 218 | 120 |
| **F** | 0 | 0 | 10 | 67 | 154 | 180 | 133 |
| **G** | 0 | 0 | 0 | 14 | 48 | 62 | 154 |

Par énergie de chauffage :

| Énergie | n | Exact | ±1 |
|---|---:|---:|---:|
| Gaz naturel | 2 385 | 65,9 % | 96,1 % |
| Fioul domestique | 2 090 | 53,9 % | 91,9 % |
| Bois granulés | 2 389 | 47,6 % | 90,7 % |
| Bois bûches | 2 391 | 43,2 % | 88,8 % |
| Électricité | 2 369 | 42,2 % | 86,4 % |

Par époque : quasi-nul de 1975 à 2021 (|biais| < 8), résiduel sur l'ancien
(avant 1948 : +74 ; 1948-1974 : +49) et le très récent (après 2021 : +19).

## 6. Analyse du critère non atteint

L'accord exact plafonne à ~50 % pour une raison **structurelle d'information, pas de
physique** : le gradient de biais par étiquette observée (+33 sur les A, −84 sur les G)
est la signature d'une dispersion prédite plus faible que la dispersion réelle. Le mapping
ne dispose que de 4 classes de qualité d'isolation par paroi — il ne peut pas distinguer une
maison de 1930 rénovée BBC d'une maison de 1930 simplement « moyenne », ni une passoire
authentique (simple vitrage + murs nus + infiltrations record) d'une maison ancienne banale.
Le gaz — population la plus homogène — atteint d'ailleurs 65,9 % d'exact, au-dessus de la cible.

Point important pour l'application : **le parcours utilisateur collecte une information plus
riche que le mapping de validation** (état d'isolation déclaré par paroi, R connu, type précis
de vitrage et de générateur). La précision en usage réel devrait donc être meilleure que sur
cette campagne, qui minore la performance atteignable.

## 7. Limites et pistes

- Bois bûches évalué avec les rendements granulés (M-5) → surclassement des poêles anciens ;
  ajouter les rendements bûches officiels (§13.1) au moteur.
- Maisons « après 2021 » : encoder une ligne U RE2020 dédiée (actuellement assimilées ≥ 2013).
- Électricité : affiner l'ECS électrique (volume réel du ballon disponible dans la base) et
  les émetteurs (colonne `type_generateur_chauffage_principal` plus fine que le mapping V1).
- Échantillonnage aléatoire intra-strate (paramètre `sample` de l'API ou tirage sur `numero_dpe`).
- Étalonner aussi l'étiquette climat (EGES) — données déjà téléchargées.

## 8. Reproductibilité

```bash
python validation/download_dpe.py --per-stratum 30   # ~5 min, ~12 000 lignes
python validation/run_validation.py                  # ~1 min, résultats JSON + console
```

Résultats intermédiaires : `validation/report/results_iter*.json` (uniquement le dernier est
committé ; les données brutes ne le sont jamais).
