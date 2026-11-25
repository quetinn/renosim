/**
 * Engine loader: spawns the Pyodide Web Worker (engine.worker.ts) and exposes
 * an async `runSimulation`. The heavy runtime download and every Python call
 * happen off the main thread, so the UI never freezes.
 */

import type { SimulationOutput, SimulationPayload } from "../types/schema";
import type { WorkerRequest, WorkerResponse } from "./messages";

export interface EngineHandle {
  /** Engine identification read back from the wheel, for the method panel. */
  engineVersion: string;
  runSimulation: (payload: SimulationPayload) => Promise<SimulationOutput>;
}

interface PendingCall {
  resolve: (resultJson: string) => void;
  reject: (error: Error) => void;
}

export async function loadEngine(): Promise<EngineHandle> {
  const worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });
  const pending = new Map<number, PendingCall>();
  let nextId = 1;

  const ready = new Promise<string>((resolve, reject) => {
    worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (message.type === "ready") {
        resolve(message.engineVersion);
      } else if (message.type === "init-error") {
        reject(new Error(message.message));
      } else {
        const call = pending.get(message.id);
        if (!call) return;
        pending.delete(message.id);
        if (message.type === "result") call.resolve(message.resultJson);
        else call.reject(new Error(message.message));
      }
    };
    worker.onerror = (event) => {
      reject(new Error(event.message || "Échec du chargement du moteur (worker)."));
    };
  });

  const base = new URL(import.meta.env.BASE_URL, window.location.href).href;
  const initMessage: WorkerRequest = { type: "init", baseUrl: base };
  worker.postMessage(initMessage);
  const engineVersion = await ready;

  return {
    engineVersion,
    runSimulation: (payload) =>
      new Promise<SimulationOutput>((resolve, reject) => {
        const id = nextId++;
        pending.set(id, {
          resolve: (resultJson) => resolve(JSON.parse(resultJson) as SimulationOutput),
          reject,
        });
        const message: WorkerRequest = {
          type: "simulate",
          id,
          payloadJson: JSON.stringify(payload),
        };
        worker.postMessage(message);
      }),
  };
}
