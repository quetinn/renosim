import { MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { PyodideProvider } from "./pyodide/PyodideContext";
import { AppStateProvider } from "./state/AppState";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <PyodideProvider>
        <AppStateProvider>
          <App />
        </AppStateProvider>
      </PyodideProvider>
    </MotionConfig>
  </StrictMode>,
);
