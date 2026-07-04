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

- **Statut :** décidé (brief §4.1) — à préciser lors du codage (Phase 1)
- **3CL officielle :** calcul des ponts thermiques par métrés de linéaires × ψ tabulés.
- **RénoSim :** majoration forfaitaire des déperditions surfaciques selon le niveau d'isolation,
  faute de métrés dans un parcours utilisateur simplifié.
- **Impact :** à quantifier lors de la validation ; le forfait est un candidat de calibration.

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

---

*Les entrées suivantes seront ajoutées au fil de l'implémentation (Phases 1 à 3).*
