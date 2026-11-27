# Écarts à la méthode 3CL-DPE 2021

Ce document trace **chaque simplification ou écart** du moteur `renosim` par rapport à la méthode
réglementaire 3CL-DPE 2021 (arrêté du 31 mars 2021 modifié). Règle de travail : tout écart est
consigné ici **au moment où il est codé**, avec sa justification et son impact attendu
(CLAUDE.md §4, règle 4). Ce document alimente directement la note technique de validation.

Format : un écart = une entrée. Statut : `décidé` (au niveau du brief, pas encore codé) /
`codé` (implémenté, référence du module) / `calibré` (ajusté suite à la validation ADEME).

---

## D-01 — Périmètre : maisons individuelles et appartements, pas d'immeuble entier

- **Statut :** codé — mis à jour le 25/11/2026 (le texte initial « maisons uniquement » était
  devenu faux depuis D-18).
- **3CL officielle :** couvre maisons, appartements et immeubles collectifs (DPE à l'immeuble).
- **RénoSim :** maisons individuelles (périmètre initial du brief §2.1) et, depuis le
  11/07/2026, appartements traités logement par logement (D-18, sur demande explicite).
  Les DPE « à l'immeuble » et les installations collectives restent hors périmètre.
- **Justification :** l'échantillon de validation maisons est filtré sur les maisons ;
  les appartements ont leur propre campagne (D-18).

## D-02 — Confort d'été non traité — RÉSOLU (11/07/2026, #16)

- **Statut :** RÉSOLU — l'indicateur de confort d'été passif (annexe 9, D-19) et le calcul
  besoin/consommation de refroidissement (§10, D-20) sont implémentés ; le moteur compare
  désormais bien 5 usages aux « conso_5_usages » de la base ADEME.
- **Historique :** le brief V1 (§2.2) excluait le confort d'été ; l'absence de refroidissement
  créait un biais structurel de la validation pour les ~21 % de maisons climatisées. Levé par
  la proposition #16 (`docs/proposal_confort_ete.md`), campagne v4 du 11/07/2026.

## D-03 — Ponts thermiques forfaitaires

- **Statut :** calibré (`envelope.py`, valeur dans `tables/conventions.json` depuis le
  25/11/2026)
- **3CL officielle :** calcul des ponts thermiques par métrés de linéaires × ψ tabulés.
- **RénoSim :** majoration forfaitaire de **8 %** des déperditions surfaciques, faute de métrés
  dans un parcours utilisateur simplifié ; conservée par la calibration Phase 3.
- **Impact :** le forfait réagit peu à une isolation par l'intérieur, alors que c'est le cas où
  les ponts thermiques pèsent le plus. Piste v1.1 (audit 2026-11-25 §4.5) : linéaires estimés
  depuis la géométrie reconstruite × ψ tabulés (3CL §3.4, règles Th-U fascicule 5), ce qui
  permettrait aussi de lever D-04.

## D-04 — ITE/ITI non distingués

- **Statut :** décidé (brief §2.2)
- **3CL officielle :** l'isolation par l'extérieur vs l'intérieur influe sur les ponts thermiques
  et l'inertie.
- **RénoSim :** un seul geste « isolation murs » avec résistance ajoutée paramétrable.

## D-05 — Besoins de chauffage par degrés-heures mensuels

- **Statut :** codé (`needs.py`, `tables/climate_zones.json`) — texte mis à jour le
  25/11/2026 (il datait d'avant le codage).
- **3CL officielle :** besoins mensuels à partir des données conventionnelles par zone
  climatique × classe d'altitude (annexe 1 §18 : DH, Nref, ensoleillement, eau froide) et du
  facteur d'utilisation des apports du §6.1.
- **RénoSim :** mêmes séries mensuelles, encodées depuis le §18, et même forme du facteur
  d'utilisation. Écart restant, limité au mode personnalisé : une consigne autre que 19 °C est
  obtenue par interpolation (ou extrapolation) linéaire entre les tables DH19 et DH21
  (`occupancy.degree_hours_factor`). L'étiquette, calculée en mode conventionnel, n'est pas
  concernée.
- **Impact :** nul en mode conventionnel ; approximation linéaire en mode personnalisé.

## D-06 — Apports solaires : coefficient d'orientation/masques forfaitaire, modulé

- **Statut :** codé (`needs.py`, `SOLAR_ORIENTATION_SHADING_COEFFICIENT = 0,5` +
  `solar_orientation_modifier` / `solar_shading_factor`)
- **3CL officielle :** surface sud équivalente Sse = Σ A·Sw·Fe·C1 avec C1 mensuel par
  baie/orientation/inclinaison (§18.5) et facteurs d'ensoleillement Fe par type de masque.
- **RénoSim :** le parcours collecte une orientation *dominante* des vitrages et un niveau de
  masque *global* (pas de saisie par baie). Sse = Σ A·Sw × 0,5 × modificateur d'orientation ×
  facteur de masque. Le modificateur est le **ratio** du C1 vertical moyen d'octobre à avril de
  l'orientation déclarée sur la moyenne des 4 orientations (table `solar_orientation.json`,
  calculée depuis §18.5) — constant sur l'année (pas de C1 mensuel). Les masques utilisent les
  Fe2 « obstacle homogène » moyennés sur les orientations (15-30° → 0,8 ; 30-60° → 0,4).
  Les défauts « réparti/je ne sais pas » et « dégagé » sont neutres : ils reproduisent
  exactement le coefficient 0,5 calibré en Phase 3.
- **Impact :** ±quelques % sur les besoins ; l'absolu reste calibré, seule la sensibilité à
  l'orientation/aux masques est ajoutée.
- **Correctif (11/07/2026) :** la table encodait par erreur la colonne *inclinée*
  (75° > x ≥ 25°) du §18.5 au lieu de la colonne *verticale* (≥ 75°, la bonne pour des
  fenêtres) — ex. sud H1a 1,857 au lieu de 1,00. Corrigé (`notes_correction` de la table) :
  modificateur sud H1a 1,52 → 1,67, nord 0,61 → 0,58. **Sans effet sur la calibration ni sur
  les métriques publiées** : l'échantillon ADEME ne porte pas d'orientation des baies
  (modificateur = 1,0 partout), campagne v4 re-exécutée bit-identique. La saison été (D-20)
  utilisait déjà la colonne verticale.

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

## D-10 — Éclairage : heures de fonctionnement — RÉSOLU (25/11/2026)

- **Statut :** RÉSOLU — conforme (`systems.py`, `lighting_kwh` ; table `lighting` de
  `system_efficiencies.json`).
- **3CL officielle :** §16.1 de l'annexe 1 (p.102-103) : `Cecl = Σj C·Pecl·Nhj/1000` avec C = 0,9,
  Pecl = 1,4 W/m² et Nhj tabulé par zone climatique et par mois (1 445 à 1 566 h/an).
- **Historique :** jusqu'au 25/11/2026, le moteur utilisait une durée unique de 2 123 h
  présentée comme une « moyenne nationale », soit +41 % par rapport aux DPE publiés.
  L'analyse par usage (note de validation v2.1, §5.4) l'a révélé.
- **RénoSim :** table mensuelle encodée telle que publiée ; seule la somme annuelle sert, car
  l'éclairage n'interagit avec aucun autre poste dans le moteur.
- **Impact mesuré (campagne v6) :** éclairage moteur/DPE 1,41 → 1,00 ; biais Cep test
  +35,0 → +33,3 kWhep/m², ±1 classe 86,7 → 87,0 %.

## D-11 — Auxiliaires de chauffage et d'ECS — RÉSOLU (10/07/2026, simplifications documentées)

- **Statut :** codé et re-validé (`systems.py` : `heating_auxiliary_kwh`, `dhw_auxiliary_kwh` ;
  table `auxiliaries` de `system_efficiencies.json`)
- **3CL officielle :** §15 — auxiliaires de génération `Paux_g = G + H·Pn` (tableau p.97),
  `Qaux_g = Paux_g·B_g/Pn` (§15.1.1-15.1.2), circulateur de chauffage §15.2.1-15.2.2
  (`Pcirc = max(30 ; 6,44·(ΔPem_nom·qv)^0,676)`, `Caux_dist_ch = Pcirc·Nref`), Tbase §18.1.
- **RénoSim :** formules officielles avec simplifications documentées dans la table :
  radiateurs non-monotube (ΔPem 10 kPa), Fcot « autre », δθdim 7,5 °C (réseau basse/moyenne
  température, cohérent avec la ligne Rd retenue), un seul niveau desservi, générateur unique
  (rat = 1), Pn = 24 kW (défaut chaudières). Qaux_g nul pour PAC (inclus au SCOP), réseau
  urbain (convention §15.1), effet Joule et poêles ; chaudière bois traitée en tirage naturel.
  Distribution ECS individuelle nulle (§15.2.3) ; seul subsiste l'auxiliaire de génération
  d'une ECS couplée à une chaudière.
- **Impact mesuré (campagne v2 du 10/07/2026, `validation/report/results_v2_aux.json`) :**
  biais CEP +7,8 → +10,8 kWhep/m² ; accord exact 50,5 % → 50,2 % ; ±1 classe 90,8 % → 90,5 %.
  Dégradation marginale, critère ±1 ≥ 90 % toujours atteint : les auxiliaires officiels sont
  conservés (fidélité méthodologique, ordre de grandeur +3 à +6 kWhep/m² sur les réseaux
  hydrauliques anciens).

## D-12 — Seuils DPE des petites surfaces (≤ 40 m²) — RÉSOLU

- **Statut :** codé et conforme (`outputs.py`, `tables/dpe_thresholds.json`)
- **3CL officielle :** l'arrêté du 25 mars 2024 (JORFTEXT000049446315) introduit des seuils
  d'étiquette progressifs selon la surface de référence pour les logements ≤ 40 m² (annexe 5
  §1.2.2), afin de corriger le poids de l'ECS sur les petits logements.
- **RénoSim :** les tableaux officiels §1.2.2.1 (altitude < 800 m) et §1.2.2.2 (> 800 m, zones
  froides H1b/H1c/H2d — seuls E et F relâchés) sont encodés verbatim dans `dpe_thresholds.json`
  (lecture directe du PDF officiel). Pour une surface ≤ 40 m², les bornes CEP/EGES sont
  interpolées linéairement entre les lignes entières (surface ≤ 8 m² → ligne « ≤ 8 ») ;
  au-dessus de 40 m², les tables standards inchangées s'appliquent. La surface de référence est
  approximée par la surface habitable (le parcours ne distingue pas vérandas chauffées / pièces
  transformées).
- **Impact :** étiquette désormais conforme pour les petits logements ; comportement inchangé
  pour les maisons > 40 m² (le cas d'usage dominant). Reste une légère discontinuité officielle
  à 40 m² exactement (EGES_d = 55 côté ≤ 40 vs 50 au-delà), reproduite fidèlement.

## D-13 — Coefficient d'énergie primaire électricité : calendrier réglementaire

- **Statut :** codé (`outputs.py`, `regulation_vintage_in_force`) — défaut daté depuis le
  25/11/2026
- **Contexte :** le coefficient de conversion EP de l'électricité vaut **2,3** pour les DPE
  établis jusqu'au 31/12/2025, **1,9** en 2026 (arrêté du 13 août 2025,
  JORFTEXT000052134589) et **1,7** à partir du 1er janvier 2027 (arrêté publié au JO le
  31 août 2026 d'après le communiqué du ministère du même jour ; référence NOR à compléter).
  Le brief (rédigé avant) mentionnait 2,3. Les seuils d'étiquette A-G ne changent pas.
- **RénoSim :** les trois conventions sont encodées (`dpe_2021`, `dpe_2026`, `dpe_2027`) avec
  leur date d'entrée en vigueur (`regulation_vintage_schedule` de `emission_factors.json`).
  Sans choix explicite, **la convention en vigueur à la date de la simulation** s'applique
  (dans l'app : le jour où la page est ouverte) ; l'app propose « En vigueur », « DPE 2026 » et
  « DPE 2021-2025 » et affiche le coefficient appliqué. La campagne de validation applique à
  chaque DPE la convention de sa date d'établissement (itération 5, `validation/mapping.py`),
  donc les métriques publiées ne dépendent pas du défaut. Historique : défaut 2,3 jusqu'au
  25/11/2026 (choix hérité de la Phase 1), puis 1,9 fixe, puis daté.
- **Impact :** un logement tout-électrique gagne ~17 % de Cep en convention 2026 et ~26 % en
  convention 2027 par rapport à 2021 (souvent une à deux classes).

## D-14 — Tables U par groupe de zone et inertie fixe — PARTIELLEMENT LEVÉ (07/07/2026)

- **Statut :** codé (`envelope.py`, `needs.py`) ; inertie paramétrable depuis le 07/07/2026
- **3CL officielle :** tables U par défaut par groupe H1/H2/H3 (conforme) ; inertie déterminée
  par la composition des parois (§18.3 pour parois anciennes, variantes climatiques dédiées).
- **RénoSim :** l'inertie est désormais déclarée par l'utilisateur via une question simple à
  l'étape Enveloppe (« type de construction ») et sélectionne l'exposant officiel du facteur
  d'utilisation (§6.1 : légère 2,5 / moyenne 2,9 / lourde-très lourde 3,6, table
  `occupancy_conventional.json`). **« Je ne sais pas » (défaut) = inertie moyenne**, soit
  exactement le comportement calibré en Phase 3 — neutre pour la calibration, même principe
  que les champs orientation/plancher ajoutés en pré-Phase 5. Depuis le 10/07/2026, la classe
  déclarée sélectionne aussi la **colonne d'inertie de la table I0 d'intermittence** (§8 p.55 :
  lourde/très lourde vs légère/moyenne, `system_efficiencies.json`) — les deux effets officiels
  opposés (exposant plus élevé → besoins réduits ; I0 plus grand → intermittence moins
  efficace) sont donc modélisés. Restent en écart : la détermination réglementaire de la classe
  à partir de la composition des parois (ici déclarative) et les données climatiques §18.3
  « parois anciennes », non encodées.
- **Impact :** modéré ; à réexaminer si la validation montre un biais sur le bâti ancien.
- **Mise à jour du 27/11/2026 (branche v1.1) — classe déterminée comme dans la méthode :**
  le parcours pose désormais les trois questions du §7 (plancher bas lourd, plafond lourd,
  murs lourds, avec les définitions des §7.1-7.3 en aide) et le moteur en déduit la classe par
  le tableau §7.4 (`models.inertia_class_from_heavy_elements`, table
  `occupancy_conventional.json`) : 3 parois lourdes → très lourde, 2 → lourde, 1 → moyenne,
  0 → légère ; inconnu = défauts officiels (plafond léger, plancher bas lourd, murs légers),
  soit « moyenne » quand rien n'est renseigné, comme avant. Simplifications : l'exception
  « plancher sur terre-plein » du défaut n'est pas modélisée ; lourde et très lourde sont
  confondues (même exposant et même colonne I0). La validation lit toujours la classe ADEME
  (M-8) : aucun effet sur ses métriques.

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

## D-17 — Parcours applicatif : géométrie reconstituée et états d'isolation

- **Statut :** codé (`engine/renosim/bridge.py`, consommé par l'app via Pyodide)
- **3CL officielle :** métrés réels des parois, baies et linéaires saisis par le diagnostiqueur.
- **RénoSim :** le parcours guidé ne demande ni métrés ni plans. Le bridge JSON reconstruit la
  géométrie avec les conventions **calibrées en phase 3** (choix M-1/M-6/M-7 de
  `validation/mapping.py`) : emprise carrée `Sh/niveaux`, murs = périmètre exposé × 2,5 m ×
  niveaux − baies, baies = `Sh/6`, toiture = plancher = emprise ; mitoyenneté = −25 % de
  périmètre exposé par façade partagée ; murs anciens non isolés à U = 2,0 (médiane Umur0
  officielle). Les états d'isolation du formulaire (« non isolé / d'origine / rénové /
  isolant connu ») sélectionnent les lignes des tables U officielles (rénové → ligne ≥ 2013 ;
  isolant connu → 1/(1/U0 + e/λ), λ sourcé dans `insulation_materials.json`).
  Depuis la révision pré-Phase 5 : l'utilisateur peut **surcharger chaque surface** (murs,
  baies, toiture, plancher, hauteur sous plafond) via le bloc optionnel `geometry` — la
  reconstruction M-1 ne sert alors que de repli champ à champ.
- **Plancher bas :** le type d'adjacence est demandé (optionnel). Terre-plein → tables Ue
  officielles p.19 (avant/après 2001) ; vide sanitaire / sous-sol non chauffé → table Ue p.18 ;
  garage/local non chauffé → b forfaitaire 0,95 (table b §3.1, UV,ue = 3, Aiu/Aue ≤ 1, parois
  non isolées — configuration conventionnelle, pas de saisie Aiu/Aue). « Je ne sais pas »
  conserve la table p.18 (choix M-7), qui est l'hypothèse de la calibration Phase 3. Toutes les
  variantes Ue restent sur la ligne 2S/P = 5 (convention M-7).
- **Hauteur sous plafond (25/11/2026) :** une hauteur saisie par l'utilisateur
  (`geometry.ceiling_height_m`) sert à la reconstruction des murs et, désormais, au facteur
  d'intermittence (G = GV/(Hsp·Sh), §8). Elle n'a pas d'effet sur l'infiltration : Hsp se
  simplifie dans la formule du §4. Sans saisie, la valeur conventionnelle de 2,5 m
  (`tables/conventions.json`) s'applique, comme dans la campagne de validation, qui ne
  transmet pas la hauteur ADEME au facteur d'intermittence.
- **Justification :** mêmes hypothèses que la campagne de validation — les métriques publiées
  restent donc représentatives de ce que produit l'app avec les défauts (note v2 du
  25/11/2026, campagne v6 : 87,0 % à ±1 classe sur l'échantillon test indépendant, 90,3 %
  sur la calibration).
- **Impact :** incertitude géométrique de l'ordre de ±10-15 % sur les surfaces déperditives pour
  les maisons de forme atypique quand les métrés ne sont pas saisis.

## D-18 — Appartements : modèle V1.1 simplifié (11/07/2026)

- **Statut :** codé et calibré (campagne appartements du 11/07/2026) — sortie du périmètre V1
  du brief (§2.2 réservait les appartements à une V2) sur demande explicite de l'auteur.
- **3CL officielle :** traitement complet de l'appartement dans son immeuble : métrés réels
  des parois par adjacence (extérieur, lnc, logements chauffés), coefficients b par local non
  chauffé (Aiu/Aue), installations collectives (chauffage, ECS avec bouclage), ventilation
  collective.
- **RénoSim :** valeurs officielles utilisées — Nadeq « logements collectifs » (§11.1, seuils
  10/50 m², pente 0,035), Q4Pa-conv appartement (§4 p.39), auxiliaires de ventilation
  collectifs `Pvent × Qvarep × Sh` (§5 p.41), table I0 « immeuble collectif, chauffage
  individuel » (§8 p.56), coefficients e/f « une seule façade exposée » pour les logements
  mono-orientés, b = 0,35 pour le mur sur circulation commune (table b §3.1, UV,ue = 0,
  Aiu/Aue 10-25). Géométrie reconstruite : emprise carrée Sh, 2 façades opposées exposées si
  traversant sinon 1 + circulation ; plafond/plancher selon la position déclarée (b = 0 sur
  logements chauffés, RDC = traitement plancher maison, dernier étage = toiture exposée).
- **Conventions calibrées** (table `apartment_reconstruction`, comparaison poste à poste avec
  les colonnes `deperditions_*` de la base ADEME, 8 895 « dpe appartement individuel ») :
  facteur de murs déperditifs ×1,85 (pignons, refends sur lnc, façades multiples — ratio
  murs prédits/observés 0,54 → 0,97), b espérés plafond 0,45 / plancher 0,10 quand la
  position est inconnue, majoration de ponts thermiques 25 % (liaisons refends × façades ;
  ratio 0,22 → 1,16). GV total prédit/observé : 0,60 → 0,99.
- **Restent hors modèle :** installations collectives de chauffage (traitées comme
  individuelles), bouclage ECS collectif, DPE « générés à partir de l'immeuble » (rejetés de
  la validation), positions multiples (duplex).
- **Résultat campagne** (`validation/report/results_apartments_v1.json`) : biais CEP
  −0,2 kWhep/m², accord exact 45,0 %, ±1 classe 87,9 % (critère maisons §7.2 : 90 % —
  presque atteint dès la première itération, chapitre à part dans la note).

## D-19 — Confort d'été passif : entrées déclaratives simplifiées (11/07/2026, #16 brique 1)

- **Statut :** codé et validé (campagne dédiée du 11/07/2026). Extension de périmètre
  explicite : le brief V1 (§2.2) excluait le confort d'été ; la proposition #16
  (`docs/proposal_confort_ete.md`) acte sa levée progressive. Cette brique 1 n'affecte NI
  l'étiquette NI les consommations : l'indicateur est purement qualitatif, affiché à côté de
  l'étiquette, jamais fusionné avec elle.
- **Méthode officielle :** annexe 9 de l'arrêté du 31/03/2021 (version consolidée
  rt-re-batiment, p. 22-26) : niveau « insuffisant » si une baie S/E/O/toiture est sans
  protection solaire extérieure (exception baies < 0,7 m² et < 10 % de la surface totale) ou
  si le plafond déperditif est sous une toiture non isolée ; « bon » si non-insuffisant et
  ≥ 2 critères parmi {inertie lourde/très lourde, logement traversant (surface de baies
  < 75 % par orientation), brasseurs d'air fixes} ; « moyen » sinon. Grille encodée dans
  `tables/summer_comfort.json` (verbatim).
- **RénoSim (simplifications) :** pas de métrés par baie → (a) la question protections
  solaires est déclarative globale (oui / partiellement / non), « partiellement » vaut
  condition d'insuffisance comme dans la grille, l'exception petites baies est laissée au
  jugement de l'utilisateur ; (b) le caractère traversant est déclaré (appartements, champ
  #15) ou supposé vrai pour les maisons (88 % de « traversant » sur l'échantillon maisons
  ADEME) ; (c) « je ne sais pas » sur les protections (état moteur `unknown`) est traité
  comme « protégé » — le formulaire n'offre pas cette réponse (équipement directement
  observable). L'état « toiture isolée » réutilise l'état d'isolation déclaré pour l'hiver ;
  s'il est inconnu, défaut officiel de l'annexe 9 (non isolée avant 1975, isolée après). Le
  geste « isolation toiture » bascule le critère été (double effet hiver/été).
- **Validation** (`validation/run_summer_comfort.py`, choix M-10) : la base mélange les
  millésimes de la grille officielle elle-même — les DPE 2021-2022 appliquent la version
  initiale de l'annexe (accord 16 % en 2021), la version consolidée implémentée ici ne se
  stabilise sur le terrain qu'en 2025. Sur les DPE ≥ 2025 : maisons **95,5 %** d'accord
  exact / 98,6 % à ±1 niveau (n = 7 943), appartements **91,0 %** / 98,3 % (n = 4 284)
  (`results_summer_comfort_v1.json`, `results_summer_comfort_apartments_v1.json`).
- **Impact :** indicateur pédagogique conforme à la grille en vigueur, sans effet sur les
  consommations ; le refroidissement lui-même est traité par la brique 2 (D-20).

## D-20 — Refroidissement §10 : chaîne conventionnelle simplifiée (11/07/2026, #16 brique 2)

- **Statut :** codé et validé (campagnes du 11/07/2026). Lève D-02.
- **3CL officielle (§10, §6.1, §18.2) :** besoin mensuel
  `Bfr_j = (Ai_fr_j + As_fr_j)/1000 − fut_j·GV/1000·(Tint − Textmoy_clim_j)·Nref_j` avec le
  facteur d'utilisation `fut` (constante de temps `t = Cin/3600·GV`, Cin tabulé par inertie),
  au choix consigne 28 °C (conventionnel) ou 26 °C (dépensier) ; `Cfr = 0,9·Bfr/EER`,
  `EER = 0,95·SEER` tabulé zone × période d'installation ; prorata de la surface refroidie.
- **RénoSim (simplifications) :**
  1. **Consigne 28 °C uniquement** (conventionnel) — pas de variante dépensière, y compris en
     mode personnalisé.
  2. **DH28 au lieu de Textmoy_clim × Nref** : les deux sont équivalents aux arrondis près
     (vérifié numériquement) et la table Textmoy_clim publiée porte une coquille évidente
     (H2d mai « 0,0 ») ; séries `dh28_fr_ch`, `nref28_fr_h`, `e_fr28_kwh_m2` encodées
     verbatim dans `climate_zones.json` (y compris les répétitions du bloc 400-800 m telles
     que publiées).
  3. **Apports solaires d'été** : le coefficient hivernal calibré 0,5 (D-06) est rebasé sur
     les C1 d'été officiels : `0,5 × C1_été(orientation)/moyenne_C1_hiver_verticale(zone)`
     (moyennes juin→septembre de la colonne verticale §18.5, `solar_orientation.json`).
  4. **Surface refroidie = 100 % du logement** (le prorata officiel exige une donnée non
     collectée) — la conso de froid est donc un majorant.
  5. Le besoin Bfr est calculé pour TOUS les logements (indicateur « ce que coûterait votre
     été ») ; la consommation Cfr n'existe que si une climatisation est déclarée (période
     d'installation → tranche SEER ; inconnue → tranche récente, parc résidentiel récent).
- **Validation** (`validation/run_cooling_validation.py`, mapping M-11, 2 383 maisons
  climatisées) : besoin de froid biais **−229 kWh/an** (−13 %, MAE 605, très bien calé dans
  les zones chaudes : H2d +15 kWh sur 2 401 observés, H3 −66 sur 2 371) ; conso EP
  **+112 kWhep/an** (+28 %) — surestimation attendue par l'hypothèse 4 (surface refroidie).
  **Campagne étiquettes v4** (11 625 maisons, `results_v4_cooling.json`) : ±1 classe
  90,2 % (v3 : 90,3 %), exact 49,8 %, biais +12,9 kWhep/m² (v3 : +12,1) — quasi neutre au
  global, apples-to-apples pour les logements climatisés.
- **Impact :** conso, EP, CO₂ et étiquette des logements déclarant une clim ; ~+5 kWhep/m²
  pour une clim récente en zone chaude, ~+12 pour une clim d'avant 2008.

---

## D-21 — Fenêtres : Uw représentatif par type de vitrage, sans volets en hiver

- **Statut :** codé (`tables/u_values_default.json`, `window_defaults`) — écart présent depuis
  la Phase 1 mais documenté seulement le 25/11/2026 (audit §4.8).
- **3CL officielle :** Uw lu selon le vitrage (Ug), le type et le matériau de menuiserie
  (§3.3.2), puis Ujn (U jour-nuit) quand la baie a des fermetures (volets), à partir de leur
  résistance additionnelle ; facteur solaire Sw selon le vitrage et la menuiserie (§6.2.1).
- **RénoSim :** un Uw et un Sw médians par type de vitrage, toutes menuiseries confondues
  (simple 4,8 ; double ancien 3,1 ; double récent 1,8 ; double faiblement émissif 1,4 ;
  triple 1,0). Les volets, déjà demandés pour le confort d'été (D-19), n'interviennent pas en
  hiver : Ujn n'est pas calculé.
- **Impact :** déperditions des baies légèrement surestimées pour les logements équipés de
  volets ; dispersion selon la menuiserie (bois/PVC vs alu sans rupteur) non représentée.
  Piste v1.1 : brancher la résistance additionnelle des volets (règles Th-U fascicule 3) sur
  la réponse existante, avec une itération de calibration.

## D-22 — Chaudière bois évaluée comme un poêle à granulés — LEVÉ (27/11/2026, branche v1.1)

- **Statut :** codé (`systems.py`, `heating_system_efficiency`) — écart déjà décrit par le
  choix de mapping M-5 (`validation/mapping.py`), formalisé ici le 25/11/2026 (audit §4.3).
- **Levé le 27/11/2026 (branche v1.1) pour les poêles et inserts à bûches :** nouveau générateur
  `WOOD_LOG_STOVE` avec les rendements officiels du §13.1 (0,50 avant 1990 ; 0,60 en
  1990-2004 ; 0,70 en 2005-2017 avec label ; 0,75 à partir de 2018 avec label), proposé dans
  l'app (« Poêle ou insert à bûches ») et utilisé par le mapping quand le libellé du générateur
  l'indique (M-5 révisé). Simplification : le label Flamme Verte n'est pas demandé ; la tranche
  « à partir de 2005 sans label » (0,65) est assimilée à la tranche avec label (0,70).
  Mesure sur la calibration (429 poêles étiquetés) : la chaîne de rendement rejoint celle du
  DPE (consommation/besoin 1,54 contre 1,46) et fait apparaître un besoin surestimé de 14 % sur
  ces maisons anciennes (biais Cep −16 → +17), à traiter avec les murs anciens et les ponts
  thermiques. Calibration globale : biais +11,3 → +12,5, ±1 classe inchangé (90,3 %).
- **Levé le 27/11/2026 pour les chaudières bois :** rendements officiels du §13.2.2.3
  (p.89-90) par combustible (bûches/plaquettes, granulés) et année d'installation, Rg saisonnier
  avec la même pondération 0,3/0,7 que les chaudières gaz et fioul (D-08), chaîne hydraulique
  complète (Rd, Rr, circulateur). App : « Chaudière bois (bûches) » et « Chaudière à granulés ».
  Calibration (263 chaudières étiquetées) : la chaîne rejoint celle du DPE (consommation/besoin
  1,38 contre 1,48 pour les bûches) ; le biais restant (+49 pour les bûches) vient du besoin
  (+30 %, maisons très anciennes).
- **Appoint bois (§9.3) :** voir D-24.
- **Reste (choix de mapping M-5, pas un écart du moteur) :** les lignes ADEME bois sans libellé
  de générateur (≈ 40 %) gardent l'approximation « rendements de poêle à granulés » : dans le
  DPE, elles ne se comportent ni comme des poêles ni comme des chaudières étiquetés.
- **3CL officielle :** rendements de génération propres aux chaudières bois (bûches,
  granulés, plaquettes) selon leur classe et leur ancienneté (§13), avec distribution
  hydraulique (Rd), régulation des radiateurs (Rr) et auxiliaires.
- **RénoSim :** `WOOD_BOILER` reprend les rendements des poêles à granulés, avec Rd = 1 et
  Rr « poêle/insert », alors qu'un circulateur de chauffage lui est compté (§15.2, D-11) :
  la chaîne est incohérente (auxiliaires hydrauliques sans pertes de distribution).
- **Impact :** les ~2 400 maisons au bois bûche de l'échantillon de validation passent par ce
  chemin (accord exact 43,2 %, le plus faible avec l'électricité). La correction change donc
  les métriques publiées : elle est reportée à la v1.1, avec les rendements officiels du §13
  (annexe 1 consolidée à récupérer) et une itération de calibration documentée.

## D-23 — Pompe à chaleur : ni appoint ni coût selon la puissance (26/11/2026)

- **Statut :** partiellement levé (`systems.design_heat_load_kw`,
  `economics.heat_pump_sizing`, sorties `design_heat_load_kw` et `heat_pump_sizing` du bridge).
- **3CL officielle :** une PAC peut être associée à un appoint (installation « PAC + appoint »),
  avec une part des besoins couverte par chaque générateur selon le dimensionnement.
- **RénoSim :** la PAC couvre 100 % des besoins avec le SCOP de la zone, quelle que soit la
  puissance nécessaire. Depuis le 26/11/2026, la puissance nécessaire au point de base
  `Pnc = GV·(20 − Tbase)/1000` (§15.2.2, déjà utilisée pour le circulateur) est affichée et
  comparée à la gamme 10-12 kW à laquelle se rapporte le coût de la PAC (guide ADEME de
  décembre 2025, d'après Observ'ER 2025). Au-delà, l'app signale un coût probablement
  sous-estimé et conseille d'isoler d'abord. Le coût n'est pas extrapolé au kW, faute de source
  publique par tranche de puissance.
- **Impact :** aucun sur les consommations ni sur la validation (campagne v6 rejouée à
  l'identique). Reste à faire en v1.1, avec la recalibration : part de l'appoint quand
  `Pnc` dépasse la puissance installée, coût selon la puissance si une source le permet.

## D-24 — Appoint bois : part forfaitaire de 25 % (27/11/2026, branche v1.1)

- **Statut :** codé conformément au §9.3 (`Building.heating_backup`,
  `systems.heating_backup_consumption`, `main_heating_share`).
- **3CL officielle :** avec un insert ou un poêle bois en appoint, `Cch1 = 0,75·Bch·INT1·Ich1`
  (système principal) et `Cch2 = 0,25·Bch·INT2·Ich2` (appoint) (p.62).
- **RénoSim :** idem, appoint limité aux poêles et inserts (bûches ou granulés). Simplifications :
  les cas §9.4-9.7 (poêle principal avec chauffage électrique de salle de bains, chaudière en
  relève de PAC, etc.) ne sont pas modélisés ; l'ECS reste sur le générateur principal ; les
  auxiliaires de génération sont comptés sur la part du principal.
- **Validation :** choix de mapping M-12 : une ligne ADEME « énergie principale bois » avec une
  **PAC** comme générateur principal devient PAC + appoint bois (1 121 lignes de la calibration).
  Effet mesuré sur la calibration : biais de ce groupe +39/+49 → +2/+7 kWhep/m² ; globalement
  ±1 classe 90,3 → 91,1 %. Les libellés d'émetteurs à effet Joule ne sont pas traités ainsi
  (cas §9.4-9.5 probable, résultats mitigés).

---

*Les choix de mapping de la validation (M-1 à M-11, dont le coefficient Ue des planchers sur
terre-plein, l'inertie ADEME, la reconstruction appartement et les entrées confort d'été /
refroidissement) sont documentés dans `validation/mapping.py` et la note de validation.*
