/** Message protocol between the main thread and the Pyodide Web Worker. */

export type WorkerRequest =
  | { type: "init"; baseUrl: string }
  | { type: "simulate"; id: number; payloadJson: string };

export type WorkerResponse =
  | { type: "ready"; engineVersion: string }
  | { type: "init-error"; message: string }
  | { type: "result"; id: number; resultJson: string }
  | { type: "error"; id: number; message: string };
