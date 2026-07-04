// Phase 0 placeholder — the guided form, results and scenario screens arrive in Phase 4.
function App() {
  return (
    <main className="shell">
      <h1>RénoSim</h1>
      <p className="tagline">Simulateur de rénovation énergétique pour maisons individuelles</p>
      <p>
        🚧 Application en construction. Le moteur de calcul (méthode 3CL-DPE 2021 simplifiée) et le
        parcours de simulation arrivent bientôt.
      </p>
      <p className="disclaimer">
        Outil pédagogique — ne remplace ni un DPE officiel ni un audit énergétique.{" "}
        <a href="https://france-renov.gouv.fr" target="_blank" rel="noreferrer">
          France Rénov'
        </a>
      </p>
      <p className="privacy">🔒 Vos données restent dans votre navigateur : aucun serveur.</p>
    </main>
  );
}

export default App;
