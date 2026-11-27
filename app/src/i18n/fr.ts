/** Libellés et aides contextuelles en français (public cible : particuliers). */

import type {
  AltitudeClass,
  Adjacency,
  ApartmentPosition,
  ConstructionPeriod,
  CoolingPeriod,
  DwellingType,
  DHWGeneratorType,
  DpeClass,
  FloorType,
  Glazing,
  GlazingOrientation,
  InertiaClass,
  InsulationMaterial,
  MeasureType,
  SolarProtectionLevel,
  SolarShading,
  SummerComfortLevel,
  VentilationType,
} from "../types/schema";
import type {
  HeatingAgeChoice,
  HeatingBackupChoice,
  HeatingChoice,
  TriState,
} from "../state/model";

export const PERIOD_LABELS: Record<ConstructionPeriod, string> = {
  before_1948: "Avant 1948",
  "1948_1974": "1948 – 1974",
  "1975_1977": "1975 – 1977",
  "1978_1982": "1978 – 1982",
  "1983_1988": "1983 – 1988",
  "1989_2000": "1989 – 2000",
  "2001_2005": "2001 – 2005",
  "2006_2012": "2006 – 2012",
  after_2013: "Après 2013",
};

export const ALTITUDE_LABELS: Record<AltitudeClass, string> = {
  low: "Moins de 400 m",
  medium: "400 à 800 m",
  high: "Plus de 800 m",
};

export const DWELLING_LABELS: Record<DwellingType, string> = {
  house: "Maison",
  apartment: "Appartement",
};

export const APARTMENT_POSITION_LABELS: Record<ApartmentPosition, string> = {
  unknown: "Je ne sais pas",
  ground: "Rez-de-chaussée",
  intermediate: "Étage intermédiaire",
  top: "Dernier étage (sous toiture)",
};

export const ADJACENCY_LABELS: Record<Adjacency, string> = {
  detached: "Indépendante",
  one_shared_wall: "Mitoyenne d'un côté",
  two_shared_walls: "Mitoyenne des deux côtés",
};

export const INSULATION_STATE_LABELS = {
  uninsulated: "Non isolé",
  period_default: "Isolation d'origine / je ne sais pas",
  renovated: "Rénové récemment",
  known_r: "Je connais l'isolant posé",
} as const;

export const INSULATION_MATERIAL_LABELS: Record<InsulationMaterial, string> = {
  glass_wool: "Laine de verre",
  rock_wool: "Laine de roche",
  cellulose: "Ouate de cellulose",
  wood_fiber: "Fibre de bois",
  eps: "Polystyrène expansé (PSE)",
  xps: "Polystyrène extrudé (XPS)",
  polyurethane: "Polyuréthane (PUR/PIR)",
  unknown: "Autre / je ne sais pas",
};

export const FLOOR_TYPE_LABELS: Record<FloorType, string> = {
  unknown: "Je ne sais pas",
  terre_plein: "Sur terre-plein (dalle au sol)",
  vide_sanitaire: "Sur vide sanitaire",
  sous_sol_non_chauffe: "Sur sous-sol / cave non chauffés",
  local_non_chauffe: "Sur garage ou local non chauffé",
};

export const GLAZING_ORIENTATION_LABELS: Record<GlazingOrientation, string> = {
  unknown: "Réparties / je ne sais pas",
  south: "Plutôt au sud",
  east_west: "Plutôt à l'est ou à l'ouest",
  north: "Plutôt au nord",
};

export const SOLAR_SHADING_LABELS: Record<SolarShading, string> = {
  clear_or_unknown: "Dégagé / je ne sais pas",
  partial: "Partiellement masqué",
  heavy: "Très masqué",
};

export const SOLAR_PROTECTION_LABELS: Record<Exclude<SolarProtectionLevel, "unknown">, string> = {
  full: "Oui, sur toutes les fenêtres",
  partial: "Sur une partie seulement",
  none: "Non, aucune",
};

/** Niveaux officiels de l'indicateur de confort d'été passif (annexe 9). */
export const SUMMER_COMFORT_LEVEL_LABELS: Record<SummerComfortLevel, string> = {
  insufficient: "Insuffisant",
  medium: "Moyen",
  good: "Bon",
};

/** Tranches SEER officielles (§10.3) ; « je ne sais pas » = tranche récente. */
export const COOLING_PERIOD_LABELS: Record<Exclude<CoolingPeriod, "unknown">, string> = {
  from_2015: "2015 ou après",
  "2008_2014": "Entre 2008 et 2014",
  before_2008: "Avant 2008",
};

export const TRI_STATE_LABELS: Record<TriState, string> = {
  yes: "Oui",
  no: "Non",
  unknown: "Je ne sais pas",
};

export const INERTIA_LABELS: Record<InertiaClass, string> = {
  unknown: "Je ne sais pas",
  heavy: "Murs épais en pierre ou béton, sols lourds",
  medium: "Construction classique (parpaing, brique)",
  light: "Ossature bois / structure légère",
};

export const GLAZING_LABELS: Record<Glazing, string> = {
  single_glazing: "Simple vitrage",
  double_glazing_old: "Double vitrage ancien (avant ~2000)",
  double_glazing_recent: "Double vitrage récent",
  double_glazing_low_e: "Double vitrage performant (faible émissivité)",
  triple_glazing: "Triple vitrage",
};

export const HEATING_LABELS: Record<HeatingChoice, string> = {
  gas_standard: "Chaudière gaz classique",
  gas_condensing: "Chaudière gaz à condensation",
  oil_boiler: "Chaudière fioul",
  electric_joule: "Radiateurs électriques",
  heat_pump_air_water: "Pompe à chaleur air/eau",
  heat_pump_air_air: "Pompe à chaleur air/air",
  wood_pellet_stove: "Poêle à granulés",
  wood_log_stove: "Poêle ou insert à bûches",
  wood_boiler: "Chaudière bois (bûches)",
  wood_pellet_boiler: "Chaudière à granulés",
  district_heating: "Réseau de chaleur",
};

export const HEATING_BACKUP_LABELS: Record<HeatingBackupChoice, string> = {
  none: "Non",
  wood_log_stove: "Poêle ou insert à bûches",
  wood_pellet_stove: "Poêle à granulés",
};

export const HEATING_AGE_LABELS: Record<HeatingAgeChoice, string> = {
  recent: "Moins de 5 ans",
  mid: "5 à 15 ans",
  old: "Plus de 15 ans",
  unknown: "Je ne sais pas",
};

export const DHW_LABELS: Record<DHWGeneratorType, string> = {
  electric_storage: "Ballon électrique",
  gas_storage_or_instant: "Chauffe-eau gaz",
  heat_pump_water_heater: "Chauffe-eau thermodynamique",
  coupled_to_heating_system: "Produit par le chauffage",
};

export const VENTILATION_LABELS: Record<VentilationType, string> = {
  natural: "Ventilation naturelle (pas de VMC)",
  exhaust_only_manual: "VMC simple flux autoréglable",
  exhaust_only_hygro_a: "VMC hygroréglable A",
  exhaust_only_hygro_b: "VMC hygroréglable B",
  balanced_heat_recovery: "VMC double flux",
};

export const MEASURE_LABELS: Record<MeasureType, { title: string; description: string }> = {
  solar_protection_installation: {
    title: "Poser des volets ou brise-soleil extérieurs",
    description:
      "Gain « été pur » : bloque le soleil avant la vitre et améliore le confort d'été passif. Aucun effet sur la facture d'hiver.",
  },
  roof_insulation: {
    title: "Isoler les combles / la toiture",
    description: "Jusqu'à 30 % des pertes de chaleur passent par le toit. Souvent le geste le plus rentable.",
  },
  wall_insulation: {
    title: "Isoler les murs",
    description: "Par l'intérieur ou l'extérieur : on ajoute une résistance thermique aux murs existants.",
  },
  window_replacement: {
    title: "Remplacer les fenêtres",
    description: "Passage à un vitrage plus performant, qui réduit aussi les sensations de paroi froide.",
  },
  heating_replacement: {
    title: "Changer le chauffage",
    description: "Remplacer le générateur : pompe à chaleur, chaudière gaz à condensation ou poêle à granulés.",
  },
  dhw_upgrade: {
    title: "Eau chaude thermodynamique",
    description: "Un chauffe-eau thermodynamique consomme 2 à 3 fois moins qu'un ballon électrique.",
  },
  ventilation_upgrade: {
    title: "Améliorer la ventilation",
    description: "VMC hygroréglable ou double flux : renouveler l'air en perdant moins de chaleur.",
  },
};

export const BUNDLE_LABELS: Record<string, { title: string; description: string }> = {
  enveloppe_d_abord: {
    title: "Enveloppe d'abord",
    description: "Isolation combles + murs + fenêtres : on réduit les besoins avant de toucher au chauffage.",
  },
  sortie_du_fioul: {
    title: "Sortie du fioul",
    description: "Pompe à chaleur air/eau + chauffe-eau thermodynamique : décarboner sans toucher à l'enveloppe.",
  },
  renovation_globale: {
    title: "Rénovation globale",
    description: "Les six gestes combinés : le scénario le plus ambitieux, aux économies maximales.",
  },
};

export const USE_LABELS: Record<string, string> = {
  heating: "Chauffage",
  dhw: "Eau chaude",
  cooling: "Climatisation",
  auxiliaries: "Auxiliaires",
  lighting: "Éclairage",
};

export const LOSS_LABELS: Record<string, string> = {
  walls: "Murs",
  roof: "Toiture",
  floor: "Plancher",
  windows: "Fenêtres",
  thermal_bridges: "Ponts thermiques",
  ventilation: "Ventilation",
  infiltration: "Infiltrations d'air",
};

export const DPE_CLASS_DESCRIPTIONS: Record<DpeClass, string> = {
  A: "Extrêmement performant",
  B: "Très performant",
  C: "Assez performant",
  D: "Assez peu performant",
  E: "Peu performant",
  F: "Très peu performant",
  G: "Extrêmement peu performant",
};

export const HELP_TEXTS = {
  postalCode:
    "Le code postal détermine la zone climatique officielle (H1a à H3) utilisée par la méthode de calcul.",
  altitude:
    "En altitude, les hivers sont plus rudes : la méthode applique des données climatiques plus sévères au-delà de 400 m.",
  livingArea: "Surface habitable, comme sur votre avis de taxe foncière ou votre bail.",
  period:
    "L'année de construction permet d'estimer l'isolation d'origine grâce aux valeurs réglementaires de chaque époque.",
  levels: "Nombre de niveaux chauffés (rez-de-chaussée = 1, avec étage = 2…).",
  adjacency: "Un mur partagé avec un voisin chauffé ne perd presque pas de chaleur.",
  dwellingType:
    "Un appartement partage murs, plancher et plafond avec des logements chauffés : ses déperditions sont très différentes de celles d'une maison.",
  apartmentPosition:
    "Au dernier étage, la toiture perd de la chaleur ; au rez-de-chaussée, c'est le plancher. À un étage intermédiaire, les deux donnent sur des logements chauffés.",
  apartmentTraversant:
    "Traversant = des fenêtres sur deux façades opposées. Un logement mono-orienté n'a qu'une façade sur l'extérieur (l'autre donne souvent sur le couloir).",
  insulation:
    "« Rénové récemment » = isolation aux standards actuels. Si vous savez quel isolant a été posé et son épaisseur (souvent sur la facture des travaux), choisissez la dernière option : la résistance thermique est calculée pour vous.",
  glazing: "En cas de doute : les fenêtres d'origine d'une maison d'avant 1990 sont souvent du simple vitrage ou un double vitrage ancien.",
  floorType:
    "Le sol sous la maison amortit plus ou moins les pertes : un vide sanitaire ou une cave tempèrent le plancher, un garage non chauffé beaucoup moins. En cas de doute, laissez « Je ne sais pas ».",
  glazingOrientation:
    "Des fenêtres au sud captent plus de soleil en hiver et réduisent le chauffage. Choisissez l'orientation où se trouve la plus grande surface vitrée.",
  solarShading:
    "Immeubles, collines ou arbres proches réduisent le soleil reçu. « Très masqué » = obstacles hauts qui bouchent l'horizon la majeure partie de la journée.",
  inertia:
    "Des murs et planchers lourds stockent la chaleur et valorisent mieux les apports du soleil : c'est l'inertie thermique. En cas de doute, laissez « Je ne sais pas » : le calcul applique une inertie moyenne.",
  inertiaFloor:
    "Sol en dalle béton (10 cm ou plus), poutrelles et hourdis béton ou terre cuite, ou matériau lourd ancien (pierre, brique, terre), sans isolant posé dessus. Dans le doute, le DPE le considère lourd.",
  inertiaCeiling:
    "Plafond du dernier niveau en béton plein ou en poutrelles et hourdis, sans faux plafond et sans isolation par l'intérieur (combles perdus sur dalle, par exemple). Dans le doute, le DPE le considère léger.",
  inertiaWalls:
    "Murs en pierre, brique pleine ou perforée, parpaing ou béton, non isolés ou isolés par l'extérieur. Un doublage intérieur isolant les rend « légers ». Dans le doute, le DPE les considère légers.",
  geometry:
    "Facultatif : si vous connaissez vos surfaces réelles (plans, diagnostic précédent), elles remplacent l'estimation automatique déduite de la surface habitable.",
  heatingAge: "Le rendement d'un générateur se dégrade avec l'âge ; l'année figure souvent sur la plaque de l'appareil.",
  heatingBackup:
    "Un poêle ou un insert utilisé en complément du chauffage principal (en mi-saison, le soir…). Comme dans le DPE, on considère qu'il fournit un quart de la chaleur.",
  dhw: "« Produit par le chauffage » : votre chaudière ou votre PAC fait aussi l'eau chaude.",
  ventilation: "Si vous entendez un léger souffle dans les bouches de la salle de bain, vous avez probablement une VMC simple flux.",
  solarProtections:
    "Volets roulants, battants ou coulissants, brise-soleil orientables… posés à l'EXTÉRIEUR des fenêtres exposées au sud, à l'est, à l'ouest ou en toiture. Les stores intérieurs ne comptent pas : le soleil est déjà entré.",
  fixedAirCirculators:
    "Ventilateurs de plafond ou muraux installés à demeure. Les ventilateurs mobiles ne sont pas pris en compte par la méthode officielle.",
  airConditioning:
    "La climatisation garantit le confort mais consomme de l'électricité : sa consommation conventionnelle entre dans le calcul (énergie primaire, CO₂, étiquette), comme dans le DPE officiel. Elle n'entre pas dans l'indicateur de confort d'été « passif », évalué sans clim.",
  airConditioningPeriod:
    "L'efficacité saisonnière (SEER) des climatiseurs a beaucoup progressé : un appareil d'avant 2008 consomme environ deux fois plus qu'un modèle récent pour le même service.",
  coolingNeed:
    "Besoin de froid conventionnel (consigne 28 °C, méthode 3CL §10) : la chaleur qu'il faudrait extraire pour garder le logement à 28 °C en été. Calculé même sans climatisation — c'est « ce que coûterait votre été si vous climatisiez ».",
  summerComfort:
    "Indicateur officiel du DPE (annexe 9 de l'arrêté), évalué SANS climatisation à partir de cinq critères : protections solaires extérieures, isolation de la toiture, inertie, logement traversant, brasseurs d'air fixes. Il est indépendant de l'étiquette : un logement très performant l'hiver peut être étouffant l'été.",
  conventionalMode:
    "Le mode conventionnel applique le scénario réglementaire du DPE (19 °C, occupation standard). C'est lui qui détermine l'étiquette.",
  personalizedMode:
    "Le mode personnalisé ajuste les consommations à VOS habitudes (température, occupants, prix). L'étiquette DPE, elle, ne change pas : c'est une règle du diagnostic.",
} as const;
