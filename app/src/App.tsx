import { useState } from "react";
import { Wizard } from "./components/form/Wizard";
import { Landing } from "./components/landing/Landing";
import { Footer } from "./components/layout/Footer";
import { Header } from "./components/layout/Header";
import { MethodPanel } from "./components/layout/MethodPanel";
import { ResultsScreen } from "./components/results/ResultsScreen";
import { ScenariosScreen } from "./components/scenarios/ScenariosScreen";
import { useAppState } from "./state/AppState";

function App() {
  const { view } = useAppState();
  const [methodOpen, setMethodOpen] = useState(false);

  return (
    <div className="flex min-h-dvh flex-col">
      <Header onOpenMethod={() => setMethodOpen(true)} />
      <main className="flex-1">
        {view === "landing" && <Landing onOpenMethod={() => setMethodOpen(true)} />}
        {view === "form" && <Wizard />}
        {view === "results" && <ResultsScreen />}
        {view === "scenarios" && <ScenariosScreen />}
      </main>
      <Footer />
      <MethodPanel open={methodOpen} onClose={() => setMethodOpen(false)} />
    </div>
  );
}

export default App;
