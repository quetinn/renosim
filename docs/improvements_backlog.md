# Backlog d'améliorations proposées (post pré-Phase 5)

> Liste de 15 pistes d'amélioration discutées en session, classées par faisabilité puis par
> catégorie (design, conseils/scénarios, fiabilité de la simulation, nouveautés). Rien n'est
> planifié ni engagé : ce document sert de mémoire pour prioriser les prochaines itérations.
>
> Rappel de contrainte projet (CLAUDE.md §2.2) : les aides financières (MaPrimeRénov', CEE)
> restent strictement hors périmètre — lien France Rénov' uniquement, jamais de calcul d'aides.
>
> ⚠️ = modifie les résultats produits par défaut par le moteur → à coupler à une itération de
> calibration documentée (`docs/deviations.md` + éventuellement une nouvelle campagne ADEME)
> avant de la considérer comme définitive.

---

## 🟢 Quasi immédiat (quelques heures chacune)

### 1. Alerte « passoire thermique » et calendrier d'interdiction de location — ✅ FAIT (07/07/2026)
- **Catégorie :** conseils/scénarios
- Si l'étiquette est E, F ou G, afficher un encart sourcé rappelant le calendrier de la loi
  Climat & Résilience (G interdit à la location depuis 2025, F en 2028, E en 2034).
- Purement informatif, aucune modification du moteur.
- **Implémenté :** composant `PassoireAlert` dans `ResultsScreen.tsx` (encart avec message
  différencié passoire F/G vs. E, lien France Rénov', mention « location, pas propriétaire
  occupant »).

### 2. Seuils DPE des petites surfaces (≤ 40 m²) — ✅ FAIT (07/07/2026)
- **Catégorie :** fiabilité de la simulation
- Lève l'écart documenté **D-12** : l'arrêté du 25 mars 2024 introduit des seuils progressifs
  selon la surface habitable.
- **Implémenté :** tableaux officiels §1.2.2.1 (altitude < 800 m) et §1.2.2.2 (zones froides
  d'altitude, E/F relâchés) encodés verbatim dans `dpe_thresholds.json` (lecture directe du
  PDF officiel via rendu image), interpolation linéaire en surface dans `outputs.py`,
  6 tests calculés à la main. D-12 marqué RÉSOLU.

### 3. Rapport imprimable — ✅ FAIT (07/07/2026)
- **Catégorie :** design du site
- Feuille de style d'impression sur les écrans Situation et Scénarios (masquer la navigation,
  forcer les couleurs des étiquettes DPE à l'impression).
- 80 % de la valeur d'un export PDF pour une fraction de l'effort ; base pour #11.
- **Implémenté :** variantes Tailwind `print:hidden` sur tout le chrome interactif (header,
  footer, boutons, cartes de gestes, bouquets, toggle de mode, InfoTips), bloc `@media print`
  dans `index.css` (`print-color-adjust: exact` pour les couleurs DPE, fond blanc,
  `break-inside: avoid`), ligne d'en-tête print-only (date, mode, avertissement) sur l'écran
  Situation, bouton « Imprimer » (`PageActions.tsx`) sur les deux écrans.

### 4. Classement « par où commencer » — ✅ FAIT (07/07/2026)
- **Catégorie :** conseils/scénarios
- Badges sur les cartes de gestes (« le plus rentable », « le plus gros gain CO₂ »).
- **Implémenté :** le bridge renvoie désormais `measure_previews` (évaluation conventionnelle
  autonome des 6 gestes sur le logement courant : économies, retour, ΔCO₂, étiquette après),
  ce qui permet de badger les cartes **avant** activation. Sélection front-only dans
  `ScenariosScreen.tsx` (`pickMeasureBadges`). Ajout additif au schéma 0.1 (rétro-compatible),
  2 tests bridge.

### 5. Auxiliaires de chauffage et d'ECS ⚠️ — ✅ FAIT (10/07/2026, re-validé)
- **Catégorie :** fiabilité de la simulation
- Lève l'écart documenté **D-11** : les circulateurs de chauffage et auxiliaires ECS (§15 de
  l'annexe 1) ne sont pas comptés, sous-estimation ~1-3 kWhep/m²/an.
- Tables officielles + tests ; à faire juste avant une re-validation (matière pour la note).
- **Implémenté :** §15 extrait de l'annexe 1 consolidée (téléchargée le 10/07/2026) :
  auxiliaires de génération `Paux_g = G + H·Pn` et circulateur de chauffage (formule complète
  §15.2.1 avec Tbase §18.1), table `auxiliaries` sourcée dans `system_efficiencies.json`,
  `heating_auxiliary_kwh`/`dhw_auxiliary_kwh` dans `systems.py`, 5 tests calculés à la main.
  **Re-validation immédiate** sur l'échantillon local (11 624 maisons) : ±1 classe
  90,8 % → 90,5 %, biais +7,8 → +10,8 kWhep/m² — dégradation marginale, auxiliaires officiels
  conservés (D-11 RÉSOLU, `results_v2_aux.json`).

---

## 🟡 Moyen (1 à 3 jours chacune)

### 6. Mode sombre — ✅ FAIT (10/07/2026)
- **Catégorie :** design du site
- Les couleurs sont déjà des variables CSS (`--color-*`) ; Tailwind v4 gère
  `prefers-color-scheme` proprement.
- Effort principal : re-décliner la palette et vérifier les contrastes des étiquettes DPE.
- **Implémenté :** palette complète re-déclarée sous `@media screen and
  (prefers-color-scheme: dark)` dans `index.css` (`screen` exclut l'impression, qui reste
  claire). Nouveaux tokens `--color-on-pine`/`--color-on-amber` : pine/amber s'éclaircissent
  en sombre, le texte posé dessus bascule en encre foncée (remplacement des `text-white`
  concernés). Gamme DPE et panneau CTA `pine-ink` volontairement inchangés ; pastilles C/D en
  encre foncée fixe. Graphiques Recharts sur variables (rampe « pertes » déclinée), tooltips
  thématisés, `theme-color`/`color-scheme` dans `index.html`.

### 7. Partage par URL — ✅ FAIT (07/07/2026)
- **Catégorie :** nouveauté
- Sérialiser l'état du formulaire dans l'URL (base64 dans le hash) — rien ne quitte le
  navigateur. Permet de partager une simulation (conjoint, conseiller France Rénov').
- La persistance localStorage existante fournit déjà la sérialisation à réutiliser.
- **Implémenté :** bouton « Partager » (`PageActions.tsx`, copie dans le presse-papier) qui
  encode l'instantané persisté en base64 URL-safe dans le fragment `#s=…` (jamais envoyé à un
  serveur). À l'ouverture d'un lien partagé : import prioritaire sur localStorage, arrivée
  directe sur l'écran Situation, hash nettoyé (`history.replaceState`). Lien malformé →
  session locale inchangée.

### 8. Objectif d'étiquette : « que faut-il pour atteindre C ? » — ✅ FAIT (07/07/2026)
- **Catégorie :** conseils/scénarios
- Avec 6 gestes il n'y a que 63 combinaisons ; le moteur (dans son Web Worker) peut toutes les
  évaluer en ~1 s. Afficher le(s) bouquet(s) les moins chers atteignant l'étiquette visée.
- Gros différenciateur pédagogique ; aucune physique nouvelle, juste de l'orchestration.
- **Implémenté :** entrée optionnelle `label_targets` du schéma 0.1 (additive) → le bridge
  évalue les 63 combinaisons (avec les paramètres des cartes) et renvoie, par classe meilleure
  que l'étiquette actuelle, la combinaison la moins chère (départage à l'investissement médian)
  qui l'atteint. Section « Viser une étiquette » dans `ScenariosScreen` (`LabelTargets.tsx`) :
  puces de classes cibles (désactivées si hors de portée), bouquet gagnant détaillé, bouton
  « Activer ce bouquet ». Demandé uniquement sur l'écran Scénarios pour garder l'écran
  Situation instantané. 4 tests bridge (dont monotonie du coût selon l'ambition).

### 9. Intermittence 3CL (facteur INT) ⚠️ — ✅ DÉJÀ EN PLACE, complété (10/07/2026)
- **Catégorie :** fiabilité de la simulation
- Le mode conventionnel applique une consigne continue ; la méthode officielle module par un
  facteur d'intermittence selon régulation/émetteurs.
- Rapproche le moteur de la 3CL réelle ; à coupler à une itération de calibration documentée.
- **Constat (10/07/2026) :** l'item était périmé — `systems.py` applique déjà
  `Cch = Bch·INT/(Rg·Re·Rd·Rr)` avec les I0 officiels §8 (calibré en Phase 3). Complément
  apporté : la table I0 possédait les colonnes « inertie lourde » sans les exploiter ; la
  classe d'inertie déclarée (#10) sélectionne désormais la bonne colonne (`_i0`,
  `systems.py`). Effet net documenté dans D-14 (deux effets officiels opposés).

### 10. Inertie paramétrée — ✅ FAIT (07/07/2026)
- **Catégorie :** fiabilité de la simulation
- Lève partiellement l'écart **D-14** : l'exposant du facteur d'utilisation est figé sur
  « inertie moyenne ». Une question simple (« murs anciens épais en pierre ? ») permettrait de
  choisir lourde/moyenne/légère avec les exposants officiels.
- « Je ne sais pas » reste le comportement actuel → neutre pour la calibration, même principe
  que les champs orientation/plancher ajoutés en pré-Phase 5.
- **Implémenté :** enum `InertiaClass` (`models.py`), exposants officiels §6.1 déjà tabulés
  (légère 2,5 / moyenne 2,9 / lourde 3,6) branchés dans `needs.py`, champ additif `inertia`
  du schéma 0.1, question « Type de construction (inertie) » à l'étape Enveloppe. Défaut
  « Je ne sais pas » = moyenne (identique au comportement calibré). D-14 marqué partiellement
  levé ; tests moteur (ordre lourde < moyenne < légère, unknown ≡ medium) et bridge.

### 11. Export PDF du rapport — ✅ FAIT (10/07/2026, impression pilotée)
- **Catégorie :** nouveauté (backlog déjà listé au brief §8, post-V1)
- Génération côté navigateur (impression pilotée ou lib type pdf-lib) du rapport de
  simulation complet : situation, scénarios, hypothèses, avertissements.
- S'appuie directement sur #3.
- **Implémenté :** option « impression pilotée » (aucune dépendance) : bouton
  « Imprimer / PDF » avec l'astuce « Enregistrer en PDF », et surtout bloc print-only
  « Hypothèses de la simulation » (`PrintHypotheses.tsx`) qui récapitule toutes les entrées
  du formulaire — le rapport imprimé/exporté porte ainsi ses hypothèses et l'avertissement.
  Une génération pdf-lib native reste possible en V2 si besoin.

### 12. Multi-projets — ✅ FAIT (10/07/2026)
- **Catégorie :** nouveauté
- Sauvegarder plusieurs logements/variantes nommés (la clé localStorage versionnée s'y prête)
  et les comparer côte à côte.
- Cas d'usage : comparer 2-3 annonces immobilières.
- **Implémenté :** magasin `renosim:projects:v1` (localStorage), panneau « Mes logements »
  sur l'écran Situation (`ProjectsPanel.tsx`) : enregistrement nommé de l'instantané complet
  + résumé conventionnel figé à la sauvegarde (étiquette, kWhep/m², €/an, CO₂), tableau
  comparatif avec la simulation courante, actions Charger/Supprimer. Rien ne quitte le
  navigateur.

---

## 🔴 Ambitieux (une semaine ou plus)

### 13. Maison interactive « par où part la chaleur » — ✅ FAIT (10/07/2026)
- **Catégorie :** design du site
- Schéma SVG de maison où toiture/murs/fenêtres/plancher sont colorés selon leur part des
  déperditions et cliquables (le clic active le geste de rénovation correspondant).
- Fort impact visuel pour le portfolio ; vrai chantier d'illustration + interaction.
- **Implémenté :** `HouseLossMap.tsx` — coupe SVG (toiture, murs, fenêtres, plancher,
  renouvellement d'air, ponts thermiques) colorée du vert au rouge selon la part de chaque
  zone dans GV (échelle relative au poste dominant). Les zones couvertes par un geste V1 sont
  des boutons accessibles (aria-pressed, clavier) qui basculent le geste ; retour visuel
  (contour pointillé) + lien « Voir l'impact dans mes scénarios ». Plancher et ponts
  thermiques informatifs (pas de geste V1 / traités par l'isolation). Affiché à côté du
  graphique en barres sur l'écran Situation.

### 14. Re-validation ADEME v2 exploitant les nouveaux champs — ✅ FAIT (11/07/2026)
- **Complété le 11/07/2026 :** le schéma live de l'API ne porte ni type de plancher bas ni
  orientation des baies (champs du XML DPE non exposés dans `dpe03existant`) — le champ
  exploitable est **`classe_inertie_batiment`**, mappé sur la nouvelle entrée inertie
  (choix M-8). Échantillon maisons re-téléchargé enrichi (`data/dpe_sample_v2.jsonl`,
  11 708 lignes + colonnes position/traversant/confort été pour les campagnes futures),
  campagne v3 : ±1 classe 90,3 %, biais +12,1 (`results_v3_inertia.json`) — l'inertie mappée
  est quasi neutre (les deux effets officiels opposés se compensent), documenté dans D-14.

#### (historique) 🟡 PARTIEL (10/07/2026)
- **Catégorie :** fiabilité de la simulation (le plus valorisant académiquement)
- La base ADEME contient le type de plancher bas et l'orientation des baies : mapper ces
  champs (au lieu des défauts neutres actuels), relancer la campagne, mesurer si l'accord
  d'étiquette progresse au-delà de 90,8 %.
- Intégrer #5 et #9 dans la même itération de calibration.
- Un chapitre entier de plus pour la note de validation.
- **Fait (10/07/2026) :** la partie « itération de calibration #5/#9 » — campagne relancée
  sur l'échantillon local (11 624 maisons) avec les auxiliaires §15 :
  `validation/report/results_v2_aux.json` (±1 classe 90,5 %, biais +10,8 kWhep/m²,
  détail dans D-11).
- **Reste à faire :** l'échantillon local (`data/dpe_sample.jsonl`) ne contient pas les
  colonnes plancher bas / orientation des baies — re-télécharger un échantillon enrichi via
  `download_dpe.py` (colonnes `type_adjacence_plancher_bas`-like et orientations des baies à
  vérifier dans le schéma ADEME du moment), étendre `mapping.py`, relancer, et rédiger le
  chapitre correspondant de la note.

### 15. Appartements — ✅ FAIT (11/07/2026, sur demande explicite — sortie du périmètre V1)
- **Catégorie :** nouveauté (backlog officiel du brief §2.2/§8)
- Le plus gros morceau : parois donnant sur circulations/logements chauffés (coefficients b
  dédiés, déjà extraits de l'annexe 1 au passage), position dans l'immeuble, ventilation
  collective, validation sur le segment appartements de la base ADEME.
- À réserver pour une V2 après le tag `v1.0`.
- **Implémenté :** `DwellingType` moteur avec les variantes officielles (Nadeq collectif
  §11.1, Q4Pa appartement §4, Pvent collectif §5, I0 immeuble §8, e/f façade unique,
  b = 0,35 mur sur circulation §3.1), position dans l'immeuble (RDC / intermédiaire /
  dernier étage) et traversant/mono-orienté dans le moteur, le bridge (schéma 0.1 additif)
  et le formulaire (étape Général, niveaux/mitoyenneté masqués). **Campagne dédiée** sur
  8 895 « dpe appartement individuel » avec calibration poste à poste des conventions de
  reconstruction (`apartment_reconstruction`) : GV prédit/observé 0,60 → 0,99, biais CEP
  −0,2 kWhep/m², ±1 classe **87,9 %** dès la première itération. Détail et limites : D-18.

---

### 16. Confort d'été (indicateur passif + refroidissement) — ✅ FAIT, 3 briques (11/07/2026)
- **Catégorie :** fiabilité de la simulation + conseils (idée de Noé : un bon DPE d'hiver
  peut cacher une fournaise d'été).
- Proposition détaillée en 3 briques dans **`docs/proposal_confort_ete.md`** : indicateur
  officiel de confort d'été passif (annexe 9 du document consolidé — la proposition disait
  « annexe 4 », ~1 j), besoin/conso de refroidissement §10 (⚠️, lève D-02, ~3-5 j), gestes
  « été » (volets/BSO, ~1-2 j).
- **Brique 1 implémentée (11/07/2026) :** grille annexe 9 verbatim (`summer_comfort.json`),
  module `summer_comfort.py` (pur, sans effet sur l'étiquette), 3 nouvelles questions
  (volets/BSO à l'étape Enveloppe ; brasseurs d'air et climatisation à l'étape Systèmes),
  carte « Confort d'été (sans climatisation) » sur l'écran Situation (pastille officielle
  3 niveaux + leviers passifs + mention clim annexe 9 §4), le geste toiture bascule le
  critère été. **Campagne dédiée** (`run_summer_comfort.py`, M-10, D-19) : sur les DPE
  ≥ 2025 (grille en vigueur), maisons 95,5 % d'accord exact / 98,6 % à ±1 niveau
  (n = 7 943), appartements 91,0 % / 98,3 % (n = 4 284). Les DPE 2021-2022 suivaient la
  version initiale de l'annexe (16 % d'accord en 2021), d'où 82 % tous millésimes.
- **Brique 2 implémentée (11/07/2026, ⚠️ lève D-02, écart D-20) :** chaîne §10 complète —
  Bfr mensuel (DH28/Nref28/E_fr28 encodés verbatim de §18.2, C1 été §18.5, fut par inertie
  Cin §10.2), `Cfr = 0,9·Bfr/EER` (SEER zone × période, `cooling.json`), question
  « climatisation + période » ; le besoin Bfr est affiché pour tous (« ce que coûterait votre
  été »), la conso n'existe que si clim déclarée. **Validation** (M-11, 2 383 maisons
  climatisées) : besoin −13 % de biais (H2d/H3 quasi parfaits), conso EP +28 % (surface
  refroidie = 100 %, majorant documenté) ; campagne étiquettes v4 quasi neutre
  (±1 classe 90,2 %, `results_v4_cooling.json`).
- **Brique 3 implémentée (11/07/2026) :** 7ᵉ geste « Poser des volets ou brise-soleil
  extérieurs » (gain été pur, coût 200-750 €/m² de baie sourcé, exclu de la recherche
  d'étiquette cible), colonne « Confort d'été passif » avant → après dans le tableau
  comparatif des scénarios, badge « Confort d'été » sur les cartes qui améliorent le niveau.
  Cas pédagogique vérifié : combles seuls et volets seuls ne changent rien, le bouquet des
  deux passe Insuffisant → Moyen.

## Ordre d'attaque recommandé

1. ~~**#1, #2, #4** avant la Phase 5~~ — fait le 07/07/2026.
2. ~~**#3, #7, #8, #10** (rapport imprimable, partage URL, objectif d'étiquette, inertie)~~ —
   fait, tous calibration-neutres par défaut.
3. ~~**#5, #6, #9, #11, #12, #13**~~ — fait le 10/07/2026 (#5 avec re-validation immédiate,
   #9 constaté déjà en place et complété par la colonne d'inertie des I0).
4. Reste : **#14** (volet « nouveaux champs » : re-téléchargement d'un échantillon ADEME
   enrichi plancher/orientation, extension de `mapping.py`, chapitre de note) et **#15**
   (appartements — V2 après le tag `v1.0`, hors périmètre V1 du brief §2.2).
