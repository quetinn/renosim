# Écarts à la méthode 3CL-DPE 2021

Ce document trace **chaque simplification ou écart** du moteur `renosim` par rapport à la méthode
réglementaire 3CL-DPE 2021 (arrêté du 31 mars 2021 modifié). Règle de travail : tout écart est
consigné ici **au moment où il est codé**, avec sa justification et son impact attendu
(CLAUDE.md §4, règle 4). Ce document alimente directement la note technique de validation.

Format : un écart = une entrée. Statut : `décidé` (au niveau du brief, pas encore codé) /
`codé` (implémenté, référence du module) / `calibré` (ajusté suite à la validation ADEME).

---

## D-01 — Périmètre : maisons individuelles uniquement

- **Statut :** décidé (brief §2.1)
- **3CL officielle :** couvre maisons, appartements et immeubles collectifs.
- **RénoSim :** maisons individuelles uniquement en V1.
- **Justification :** périmètre V1 ; l'échantillon de validation ADEME est filtré en conséquence.

## D-02 — Confort d'été non traité

- **Statut :** décidé (brief §2.2)
- **3CL officielle :** la méthode 2021 intègre un volet confort d'été / refroidissement.
- **RénoSim :** aucun calcul de refroidissement ni d'indicateur de confort d'été.
- **Impact :** sous-estimation possible de la consommation totale pour les logements climatisés ;
  sans effet sur la validation (menée sur les usages chauffage + ECS + auxiliaires + éclairage).

## D-03 — Ponts thermiques forfaitaires

- **Statut :** codé (`envelope.py`, `THERMAL_BRIDGE_SURCHARGE`)
- **3CL officielle :** calcul des ponts thermiques par métrés de linéaires × ψ tabulés.
- **RénoSim :** majoration forfaitaire de **8 %** des déperditions surfaciques, faute de métrés
  dans un parcours utilisateur simplifié.
- **Impact :** à quantifier lors de la validation ; le forfait est un candidat de calibration
  prioritaire (Phase 3).

## D-04 — ITE/ITI non distingués

- **Statut :** décidé (brief §2.2)
- **3CL officielle :** l'isolation par l'extérieur vs l'intérieur influe sur les ponts thermiques
  et l'inertie.
- **RénoSim :** un seul geste « isolation murs » avec résistance ajoutée paramétrable.

## D-05 — Besoins de chauffage par degrés-heures mensuels

- **Statut :** décidé (brief §4.1) — à préciser lors du codage (Phase 1)
- **3CL officielle :** calcul mensuel détaillé avec données climatiques départementales corrigées.
- **RénoSim :** degrés-heures mensuels par zone climatique (H1a…H3) et 3 classes d'altitude,
  facteur d'utilisation des apports type ISO 13790.
- **Impact :** lissage des variations locales de climat ; à quantifier lors de la validation.

## D-06 — Apports solaires : coefficient d'orientation/masques forfaitaire

- **Statut :** codé (`needs.py`, `SOLAR_ORIENTATION_SHADING_COEFFICIENT = 0,5`)
- **3CL officielle :** surface sud équivalente Sse = Σ A·Sw·Fe·C1 avec C1 mensuel par
  orientation/inclinaison (§18.5) et facteurs d'ensoleillement Fe par type de masque.
- **RénoSim :** le parcours simplifié ne collecte ni l'orientation des baies ni les masques ;
  Sse = Σ A·Sw × 0,5 (répartition moyenne des orientations ≈ 0,55, masques ≈ 0,9).
- **Impact :** ±quelques % sur les besoins ; candidat de calibration Phase 3.

## D-07 — Pertes récupérées ignorées

- **Statut :** codé (`needs.py`)
- **3CL officielle :** Bch_j déduit les pertes récupérées de distribution/stockage ECS et de
  génération (Qrec, §9.1).
- **RénoSim :** Bch_j = GV·(1−F_j)·DH_j/1000, sans déduction des pertes récupérées.
- **Impact :** légère surestimation des besoins de chauffage (ordre de 1-3 %).

## D-08 — Rendement saisonnier des chaudières simplifié

- **Statut :** codé (`systems.py`, `_boiler_seasonal_rg`)
- **3CL officielle :** rendement de génération calculé sur profil de charge conventionnel
  (pondérations §13.2.1.1) avec pertes à l'arrêt Qp0 et veilleuse.
- **RénoSim :** Rg ≈ 0,3·Rpn + 0,7·Rpint (formules officielles §13.2.2, Pn = 24 kW par défaut),
  avec abattement multiplicatif pour les chaudières anciennes (approximation des Qp0 élevés).
- **Impact :** écart de quelques points de rendement selon la puissance réelle et l'usage.

## D-09 — Configuration d'émetteurs conventionnelle par générateur

- **Statut :** codé (`systems.py`, `heating_system_efficiency`)
- **3CL officielle :** Re/Rd/Rr saisis selon l'installation réelle (émetteurs, réseau, régulation).
- **RénoSim :** chaque type de générateur est associé à une configuration type (chaudières/PAC →
  réseau d'eau individuel + radiateurs ; joule → émetteurs divisés ; poêle → sans réseau), avec
  robinets thermostatiques supposés absents pour les systèmes > 25 ans.
- **Impact :** faible pour les cas types ; les valeurs Re/Rd/Rr elles-mêmes sont les valeurs
  officielles (§12.1-12.3).

## D-10 — Éclairage : heures moyennes nationales

- **Statut :** codé (`systems.py`, `lighting_kwh`)
- **3CL officielle :** Nh mensuel par zone climatique (croisement lever/coucher du soleil).
- **RénoSim :** forfait annuel Nh = 2123 h (moyenne nationale citée §6.1 de l'annexe).
- **Impact :** négligeable (l'éclairage pèse ~2-3 kWhep/m²/an).

## D-11 — Auxiliaires de chauffage et d'ECS non comptés

- **Statut :** codé (périmètre `simulation.py`)
- **3CL officielle :** consommations des circulateurs de chauffage et auxiliaires ECS (§15).
- **RénoSim :** seuls les auxiliaires de ventilation (§5, valeurs officielles) et l'éclairage
  sont comptés en V1.
- **Impact :** sous-estimation de ~1-3 kWhep/m²/an pour les systèmes hydrauliques ; à ajouter si
  la validation montre un biais systématique.

## D-12 — Seuils DPE des petites surfaces (≤ 40 m²) non modélisés

- **Statut :** codé (`outputs.py` utilise les seuils standards)
- **3CL officielle :** l'arrêté du 25 mars 2024 (JORFTEXT000049446315) introduit des seuils
  progressifs selon la surface pour les logements ≤ 40 m².
- **RénoSim :** seuils standards appliqués quelle que soit la surface (cas limite testé dans
  `test_reference_cases.py`).
- **Impact :** étiquette potentiellement trop sévère pour les très petites maisons.

## D-13 — Coefficient d'énergie primaire électricité : choix du millésime

- **Statut :** codé (`outputs.py`, paramètre `regulation_vintage`)
- **Contexte :** l'arrêté du 13 août 2025 (JORFTEXT000052134589) abaisse le coefficient de
  conversion EP de l'électricité de 2,3 à **1,9 au 1er janvier 2026**. Le brief (rédigé avant)
  mentionnait 2,3.
- **RénoSim :** les deux conventions sont encodées ; **défaut V1 = 2,3 (`dpe_2021`)** pour rester
  cohérent avec la base ADEME de validation (DPE émis 2021-2025). Le mode `dpe_2026` (1,9) est
  disponible et sera exposé dans l'UI en Phase 4.
- **Impact :** un logement tout-électrique gagne ~17 % de Cep en convention 2026 (souvent une
  classe). Ce choix devra être affiché clairement dans l'app.

## D-14 — Tables U par groupe de zone et inertie fixe

- **Statut :** codé (`envelope.py`, `needs.py`)
- **3CL officielle :** tables U par défaut par groupe H1/H2/H3 (conforme) ; inertie déterminée
  par la composition des parois (§18.3 pour parois anciennes, variantes climatiques dédiées).
- **RénoSim :** inertie **moyenne** figée pour le facteur d'utilisation (exposant 2,9) et données
  climatiques §18.2 standard (la variante §18.3 « parois anciennes » n'est pas encodée).
- **Impact :** modéré ; à réexaminer si la validation montre un biais sur le bâti ancien.

## D-15 — Débits de ventilation indexés sur l'époque de construction

- **Statut :** codé (`envelope.py`, `conventional_airflows`)
- **3CL officielle :** débits conventionnels selon l'année d'installation de la VMC.
- **RénoSim :** l'année d'installation est approximée par l'époque de construction (le parcours
  ne pose pas la question séparément) ; les gestes de rénovation VMC (Phase 2) utiliseront la
  tranche récente.
- **Impact :** faible.

## D-16 — Hypothèses conventionnelles issues de la calibration (itération 6)

- **Statut :** calibré (campagne ADEME du 04/07/2026, voir `validation/report/note_validation.md`)
- **3CL officielle :** Rr et Rd ECS saisis selon l'installation réelle.
- **RénoSim :** deux hypothèses conventionnelles fixées après calibration : émetteurs joule
  supposés certifiés NF (Rr = 0,99, valeur officielle §12.3) et production ECS individuelle
  en volume habitable avec pièces contiguës (Rd = 0,93, valeur officielle §11.5.1).
- **Impact :** biais CEP global ramené à +7,8 kWhep/m²/an sur 11 624 maisons.

---

*Les choix de mapping de la validation (M-1 à M-7, dont le coefficient Ue des planchers sur
terre-plein) sont documentés dans `validation/mapping.py` et la note de validation.*
