import type { ClimateZone } from "../types/schema";

/**
 * Zone climatique par département (métropole).
 *
 * Source : annexe à l'article R172-4 du code de la construction et de
 * l'habitation, chapitre IV « Définition des zones climatiques »
 * (https://www.legifrance.gouv.fr/codes/id/LEGISCTA000043886688/2022-01-01,
 * consulté le 05/07/2026) — zonage identique à celui de la méthode 3CL-DPE 2021.
 * Les DOM (971-976) relèvent d'un DPE spécifique, hors périmètre V1.
 */
export const CLIMATE_ZONE_BY_DEPARTMENT: Record<string, ClimateZone> = {
  "01": "H1c",
  "02": "H1a",
  "03": "H1c",
  "04": "H2d",
  "05": "H1c",
  "06": "H3",
  "07": "H2d",
  "08": "H1b",
  "09": "H2c",
  "10": "H1b",
  "11": "H3",
  "12": "H2c",
  "13": "H3",
  "14": "H1a",
  "15": "H1c",
  "16": "H2b",
  "17": "H2b",
  "18": "H2b",
  "19": "H1c",
  "2A": "H3",
  "2B": "H3",
  "21": "H1c",
  "22": "H2a",
  "23": "H1c",
  "24": "H2c",
  "25": "H1c",
  "26": "H2d",
  "27": "H1a",
  "28": "H1a",
  "29": "H2a",
  "30": "H3",
  "31": "H2c",
  "32": "H2c",
  "33": "H2c",
  "34": "H3",
  "35": "H2a",
  "36": "H2b",
  "37": "H2b",
  "38": "H1c",
  "39": "H1c",
  "40": "H2c",
  "41": "H2b",
  "42": "H1c",
  "43": "H1c",
  "44": "H2b",
  "45": "H1b",
  "46": "H2c",
  "47": "H2c",
  "48": "H2d",
  "49": "H2b",
  "50": "H2a",
  "51": "H1b",
  "52": "H1b",
  "53": "H2b",
  "54": "H1b",
  "55": "H1b",
  "56": "H2a",
  "57": "H1b",
  "58": "H1b",
  "59": "H1a",
  "60": "H1a",
  "61": "H1a",
  "62": "H1a",
  "63": "H1c",
  "64": "H2c",
  "65": "H2c",
  "66": "H3",
  "67": "H1b",
  "68": "H1b",
  "69": "H1c",
  "70": "H1b",
  "71": "H1c",
  "72": "H2b",
  "73": "H1c",
  "74": "H1c",
  "75": "H1a",
  "76": "H1a",
  "77": "H1a",
  "78": "H1a",
  "79": "H2b",
  "80": "H1a",
  "81": "H2c",
  "82": "H2c",
  "83": "H3",
  "84": "H2d",
  "85": "H2b",
  "86": "H2b",
  "87": "H1c",
  "88": "H1b",
  "89": "H1b",
  "90": "H1b",
  "91": "H1a",
  "92": "H1a",
  "93": "H1a",
  "94": "H1a",
  "95": "H1a",
};

/**
 * Département depuis un code postal métropolitain.
 * Corse : 20000-20199 → 2A (Corse-du-Sud), 20200+ → 2B (approximation d'usage ;
 * les deux départements sont de toute façon en zone H3).
 */
export function departmentFromPostalCode(postalCode: string): string | null {
  if (!/^\d{5}$/.test(postalCode)) return null;
  const prefix = postalCode.slice(0, 2);
  if (prefix === "20") return postalCode < "20200" ? "2A" : "2B";
  return prefix in CLIMATE_ZONE_BY_DEPARTMENT ? prefix : null;
}

export function climateZoneFromPostalCode(postalCode: string): ClimateZone | null {
  const dept = departmentFromPostalCode(postalCode);
  return dept ? CLIMATE_ZONE_BY_DEPARTMENT[dept] : null;
}
