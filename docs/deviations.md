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

## D-02 — Confort d'été non traité — RÉSOLU (11/07/2026, #16)

- **Statut :** RÉSOLU — l'indicateur de confort d'été passif (annexe 9, D-19) et le calcul
  besoin/consommation de refroidissement (§10, D-20) sont implémentés ; le moteur compare
  désormais bien 5 usages aux « conso_5_usages » de la base ADEME.
- **Historique :** le brief V1 (§2.2) excluait le confort d'été ; l'absence de refroidissement
  créait un biais structurel de la validation pour les ~21 % de maisons climatisées. Levé par
  la proposition #16 (`docs/proposal_confort_ete.md`), campagne v4 du 11/07/2026.

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

## D-10 — Éclairage : heures moyennes nationales

- **Statut :** codé (`systems.py`, `lighting_kwh`)
- **3CL officielle :** Nh mensuel par zone climatique (croisement lever/coucher du soleil).
- **RénoSim :** forfait annuel Nh = 2123 h (moyenne nationale citée §6.1 de l'annexe).
- **Impact :** négligeable (l'éclairage pèse ~2-3 kWhep/m²/an).

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
- **Justification :** mêmes hypothèses que la campagne de validation — les métriques publiées
  (90,8 % à ±1 classe) restent donc représentatives de ce que produit l'app avec les défauts.
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

*Les choix de mapping de la validation (M-1 à M-11, dont le coefficient Ue des planchers sur
terre-plein, l'inertie ADEME, la reconstruction appartement et les entrées confort d'été /
refroidissement) sont documentés dans `validation/mapping.py` et la note de validation.*
