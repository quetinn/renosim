/**
 * Pyodide runtime loader: fetches the official CDN build, installs the local
 * renosim wheel with micropip and exposes the single JSON entry point
 * `renosim.bridge.run_simulation` (CLAUDE.md §3.2 — strict JSON interface,
 * no business logic on the JS side).
 */

import type { SimulationOutput, SimulationPayload } from "../types/schema";

const PYODIDE_VERSION = "0.28.3";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

interface PyodideBridgeModule {
  run_simulation: (payloadJson: string) => string;
}

interface PyodideRuntime {
  loadPackage: (name: string) => Promise<void>;
  pyimport: (module: string) => unknown;
}

declare global {
  interface Window {
    loadPyodide?: (options: { indexURL: string }) => Promise<PyodideRuntime>;
  }
}

export interface EngineHandle {
  /** Engine identification read back from the wheel, for the method panel. */
  engineVersion: string;
  runSimulation: (payload: SimulationPayload) => SimulationOutput;
}

function injectScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Échec du chargement de ${src}`));
    document.head.appendChild(script);
  });
}

export async function loadEngine(): Promise<EngineHandle> {
  await injectScript(`${PYODIDE_INDEX_URL}pyodide.js`);
  if (!window.loadPyodide) {
    throw new Error("Pyodide indisponible après chargement du script.");
  }
  const pyodide = await window.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  await pyodide.loadPackage("micropip");

  const base = new URL(import.meta.env.BASE_URL, window.location.href).href;
  const manifestResponse = await fetch(`${base}wheels/manifest.json`);
  if (!manifestResponse.ok) {
    throw new Error(
      "Manifest du moteur introuvable. En développement : lancez `npm run wheel` dans app/.",
    );
  }
  const manifest = (await manifestResponse.json()) as { wheel: string };

  const micropip = pyodide.pyimport("micropip") as {
    install: (url: string) => Promise<void>;
  };
  await micropip.install(`${base}wheels/${manifest.wheel}`);

  const bridge = pyodide.pyimport("renosim.bridge") as PyodideBridgeModule;
  const info = pyodide.pyimport("renosim") as { __version__: string };

  return {
    engineVersion: info.__version__,
    runSimulation: (payload) =>
      JSON.parse(bridge.run_simulation(JSON.stringify(payload))) as SimulationOutput,
  };
}
