// Writes public/wheels/manifest.json pointing at the renosim wheel so the
// Pyodide loader can micropip-install it without hardcoding the version.
// Run after building the wheel:  python -m build --wheel ../engine --outdir public/wheels
import { readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const wheelsDir = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "wheels");

const wheels = readdirSync(wheelsDir)
  .filter((f) => f.startsWith("renosim-") && f.endsWith(".whl"))
  .sort((a, b) => statSync(join(wheelsDir, b)).mtimeMs - statSync(join(wheelsDir, a)).mtimeMs);

if (wheels.length === 0) {
  console.error(`No renosim wheel found in ${wheelsDir}. Build one first:`);
  console.error("  python -m build --wheel ../engine --outdir public/wheels");
  process.exit(1);
}

writeFileSync(join(wheelsDir, "manifest.json"), JSON.stringify({ wheel: wheels[0] }, null, 2));
console.log(`manifest.json -> ${wheels[0]}`);
