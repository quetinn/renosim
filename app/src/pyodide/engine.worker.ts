/// <reference lib="webworker" />
/**
 * Pyodide Web Worker: loads the runtime from the official CDN, installs the
 * local renosim wheel with micropip and answers `simulate` messages with the
 * JSON produced by `renosim.bridge.run_simulation`. Running in a worker keeps
 * the UI thread free during the ~10 s runtime download and during each
 * simulation (CLAUDE.md §3.2 — strict JSON interface, no business logic here).
 */

import type { WorkerRequest, WorkerResponse } from "./messages";

const PYODIDE_VERSION = "0.28.3";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

interface PyodideBridgeModule {
  run_simulation: (payloadJson: string) => string;
}

interface PyodideRuntime {
  loadPackage: (name: string) => Promise<void>;
  pyimport: (module: string) => unknown;
}

let bridge: PyodideBridgeModule | null = null;

function post(message: WorkerResponse): void {
  self.postMessage(message);
}

async function init(baseUrl: string): Promise<string> {
  // Dynamic import of the CDN ESM build (module workers have no importScripts).
  const pyodideModule = (await import(/* @vite-ignore */ `${PYODIDE_INDEX_URL}pyodide.mjs`)) as {
    loadPyodide: (options: { indexURL: string }) => Promise<PyodideRuntime>;
  };
  const pyodide = await pyodideModule.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  await pyodide.loadPackage("micropip");

  const manifestResponse = await fetch(`${baseUrl}wheels/manifest.json`);
  if (!manifestResponse.ok) {
    throw new Error(
      "Manifest du moteur introuvable. En développement : lancez `npm run wheel` dans app/.",
    );
  }
  const manifest = (await manifestResponse.json()) as { wheel: string };

  const micropip = pyodide.pyimport("micropip") as {
    install: (url: string) => Promise<void>;
  };
  await micropip.install(`${baseUrl}wheels/${manifest.wheel}`);

  bridge = pyodide.pyimport("renosim.bridge") as PyodideBridgeModule;
  const info = pyodide.pyimport("renosim") as { __version__: string };
  return info.__version__;
}

async function handle(message: WorkerRequest): Promise<void> {
  if (message.type === "init") {
    try {
      post({ type: "ready", engineVersion: await init(message.baseUrl) });
    } catch (err) {
      post({ type: "init-error", message: err instanceof Error ? err.message : String(err) });
    }
    return;
  }
  if (!bridge) {
    post({ type: "error", id: message.id, message: "Moteur non initialisé." });
    return;
  }
  try {
    post({ type: "result", id: message.id, resultJson: bridge.run_simulation(message.payloadJson) });
  } catch (err) {
    post({ type: "error", id: message.id, message: err instanceof Error ? err.message : String(err) });
  }
}

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  void handle(event.data);
};
