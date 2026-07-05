/** Libellés et aides contextuelles en français (public cible : particuliers). */

import type {
  AltitudeClass,
  Adjacency,
  ConstructionPeriod,
  DHWGeneratorType,
  DpeClass,
  Glazing,
  MeasureType,
  VentilationType,
} from "../types/schema";
import type { HeatingAgeChoice, HeatingChoice } from "../state/model";

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

export const ADJACENCY_LABELS: Record<Adjacency, string> = {
  detached: "Indépendante",
  one_shared_wall: "Mitoyenne d'un côté",
  two_shared_walls: "Mitoyenne des deux côtés",
};

export const INSULATION_STATE_LABELS = {
  uninsulated: "Non isolé",
  period_default: "Isolation d'origine / je ne sais pas",
  renovated: "Rénové récemment",
  known_r: "Je connais la résistance R",
} as const;

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
  wood_boiler: "Chaudière bois (bûches)",
  district_heating: "Réseau de chaleur",
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
  insulation:
    "« Rénové récemment » = isolation aux standards actuels. Si vous connaissez la résistance R (indiquée sur les factures de travaux), choisissez la dernière option.",
  glazing: "En cas de doute : les fenêtres d'origine d'une maison d'avant 1990 sont souvent du simple vitrage ou un double vitrage ancien.",
  heatingAge: "Le rendement d'un générateur se dégrade avec l'âge ; l'année figure souvent sur la plaque de l'appareil.",
  dhw: "« Produit par le chauffage » : votre chaudière ou votre PAC fait aussi l'eau chaude.",
  ventilation: "Si vous entendez un léger souffle dans les bouches de la salle de bain, vous avez probablement une VMC simple flux.",
  conventionalMode:
    "Le mode conventionnel applique le scénario réglementaire du DPE (19 °C, occupation standard). C'est lui qui détermine l'étiquette.",
  personalizedMode:
    "Le mode personnalisé ajuste les consommations à VOS habitudes (température, occupants, prix). L'étiquette DPE, elle, ne change pas : c'est une règle du diagnostic.",
} as const;
