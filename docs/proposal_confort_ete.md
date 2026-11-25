# Proposition #16 — Confort d'été : « bon DPE l'hiver, fournaise l'été »

> Proposition d'implémentation rédigée le 11/07/2026, en réponse à l'idée de Noé : un logement
> peut être très performant pour retenir la chaleur en hiver et pourtant invivable en canicule.
> L'outil doit rendre visible cette asymétrie en tenant compte de l'ensoleillement, de
> l'isolation, des fenêtres, des volets, de la climatisation, etc.
> Rien n'est codé : ce document décrit le **quoi**, le **comment** et le **coût** de chaque
> brique, pour décision.

## 1. Ce que dit la méthode officielle (et pourquoi ça tombe bien)

Le DPE 2021 contient déjà **deux dispositifs distincts** pour l'été — c'est exactement le
découpage que l'idée appelle :

1. **L'indicateur de confort d'été « passif »** (annexe 4 de l'arrêté du 31/03/2021 modifié,
   affiché sur tous les DPE depuis 2021) : une évaluation qualitative à **trois niveaux**
   (insuffisant / moyen / bon), **sans climatisation**, construite à partir de critères
   simples : inertie du bâtiment, **protections solaires extérieures** des baies (volets,
   BSO…), logement **traversant**, **isolation de la toiture**, présence de **brasseurs
   d'air**. C'est le « votre logement tiendra-t-il la canicule ? » de l'utilisateur.
2. **La consommation de refroidissement** (§10 de l'annexe 1) : un besoin de froid mensuel
   calculé par la même mécanique que le chauffage (degrés-heures de climatisation §18.4,
   apports solaires d'été, facteur d'utilisation par inertie), converti en consommation via
   l'EER/SEER conventionnel du générateur de froid. Elle fait partie des **5 usages** du DPE :
   un logement climatisé la paie en énergie primaire, en CO₂ et en euros.

Conséquence méthodologique importante : notre moteur compare aujourd'hui ses 4 usages aux
« conso_5_usages » de la base ADEME (écart D-02) — implémenter le point 2 **résorbe un biais
structurel existant** de la validation, en plus de répondre à l'idée.

## 2. Les trois briques proposées

### Brique 1 — Indicateur de confort d'été passif (~1 jour, aucune physique nouvelle)

- **Entrées déjà disponibles** dans le parcours : inertie (#10), orientation des vitrages,
  masques solaires, traversant/mono-orienté (#15), état d'isolation de la toiture, zone
  climatique.
- **Nouvelles questions** (étape Systèmes ou Enveloppe, 3 champs simples) :
  protections solaires extérieures (volets/BSO : oui / partiellement / non), brasseurs d'air
  (oui/non), climatisation (oui/non — utile aussi pour la brique 2).
- **Algorithme** : grille officielle de l'annexe 4 (à extraire verbatim de l'arrêté au moment
  du codage — règle 7 du brief), encodée dans une table `summer_comfort.json` sourcée.
- **UI** : pastille 3 niveaux sur l'écran Situation à côté de l'étiquette (« Confort d'été :
  moyen »), avec les leviers passifs expliqués (volets extérieurs, ventilation nocturne
  traversante, isolation de toiture, brasseur) et l'avertissement pédagogique clé :
  *« l'étiquette DPE mesure l'hiver ; un A peut être étouffant en été »*.
- **Validation immédiate possible** : la colonne `indicateur_confort_ete` est **déjà dans nos
  échantillons re-téléchargés** (maisons v2 et appartements) — une matrice de confusion
  3×3 contre l'indicateur officiel, comme pour les étiquettes.

### Brique 2 — Besoin et consommation de refroidissement (~3-5 jours, moteur ⚠️)

- **Physique** (symétrique du chauffage, donc réutilise toute l'architecture existante) :
  `Bfr_j = GV × DHfr_j × (1 − F'_j)` où `DHfr` sont les degrés-heures de climatisation
  (tables §18.4 à encoder dans `climate_zones.json`), les apports solaires utilisent les C1
  d'été (§18.5, à ajouter à `solar_orientation.json` — nous n'avons encodé que la saison de
  chauffe) et `F'` est le facteur inversé : en été, les apports sont la charge et les
  déperditions le secours, avec les mêmes exposants d'inertie.
- **Systèmes** : nouveau champ « climatisation » (type + période d'installation) → EER/SEER
  conventionnel (tableau §10), `Cfr = Bfr / SEER`, ajoutée aux usages (EP ×2,3 ou 1,9, CO₂,
  €) et donc à l'étiquette. Sans clim déclarée : `Cfr = 0` mais le **besoin** `Bfr` est
  affiché comme indicateur physique (« ce que coûterait votre été si vous climatisiez » et
  intrant du confort passif).
- **⚠️ Calibration** : c'est un changement de périmètre des usages → re-campagne obligatoire.
  Les colonnes `besoin_refroidissement`, `conso_refroidissement_ep` et
  `type_generateur_froid` sont **déjà dans nos échantillons** : on peut valider le besoin de
  froid poste à poste, comme on vient de le faire pour l'enveloppe des appartements. Lève
  l'écart D-02.

### Brique 3 — Gestes de rénovation « été » (~1-2 jours, après brique 2)

- Étendre les gestes existants avec leur double effet hiver/été : l'isolation de toiture
  améliore les deux ; les fenêtres performantes réduisent aussi le facteur solaire ; **ajout
  d'un 7ᵉ geste « protections solaires extérieures »** (volets/BSO, coût faible, gain été
  pur) et éventuellement « climatisation performante » (remplacement d'un vieux split par un
  SEER récent).
- L'écran Scénarios afficherait alors deux colonnes d'impact : € d'hiver économisés et
  niveau de confort d'été avant/après — le message pédagogique de l'idée d'origine.

## 3. Ordre recommandé et effort

| Étape | Effort | Risque calibration | Valeur |
|---|---|---|---|
| Brique 1 (indicateur passif) | ~1 j | aucun (indicateur séparé) | immédiate, très visible |
| Brique 2 (besoin/conso froid) | ~3-5 j | ⚠️ re-campagne (données déjà prêtes) | lève D-02, étiquette plus juste |
| Brique 3 (gestes été) | ~1-2 j | faible | boucle le récit rénovation |

Commencer par la brique 1 : elle répond à 80 % de l'idée (« mon logement tiendra-t-il
l'été ? ») pour une journée de travail, avec une validation quantitative possible dès
maintenant grâce aux colonnes déjà téléchargées.

## 4. Points de vigilance

- **Ne pas toucher à l'étiquette hiver** tant que la brique 2 n'est pas validée : l'indicateur
  passif (brique 1) est affiché à côté de l'étiquette, jamais fusionné avec elle.
- Les tables été (§10, §18.4, C1 été §18.5, grille annexe 4) doivent être extraites du PDF
  officiel au moment du codage — l'annexe consolidée est déjà téléchargée et l'outillage
  d'extraction (PyMuPDF) est en place.
- Le brief V1 (§2.2) excluait le confort d'été (D-02) : cette proposition acte une extension
  de périmètre explicite, comme #15.
