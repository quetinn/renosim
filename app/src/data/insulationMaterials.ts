/**
 * Insulation materials for the dropdowns, imported straight from the engine's
 * sourced table (single source of truth for λ values — CLAUDE.md §5). The
 * R = thickness/λ conversion below is a display-only preview: the engine
 * recomputes it authoritatively from the same table (renosim.bridge).
 */

import table from "../../../engine/renosim/tables/insulation_materials.json";
import type { InsulationMaterial } from "../types/schema";

const MATERIALS = table.materials as Record<InsulationMaterial, { lambda_w_per_mk: number }>;

/** Dropdown order: mineral wools first (most common), "unknown" last. */
export const INSULATION_MATERIAL_ORDER: InsulationMaterial[] = [
  "glass_wool",
  "rock_wool",
  "cellulose",
  "wood_fiber",
  "eps",
  "xps",
  "polyurethane",
  "unknown",
];

/** Display-only preview of the added resistance in m²·K/W. */
export function addedRPreview(material: InsulationMaterial, thicknessCm: number): number {
  return thicknessCm / 100 / MATERIALS[material].lambda_w_per_mk;
}
