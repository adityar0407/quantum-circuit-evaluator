export function ResultsPage() {
  return (
    <section id="results" className="panel">
      <header>
        <p>Results</p>
        <h1>Transpilation metrics and comparison runs</h1>
      </header>
      <div className="empty-state">Result tables and charts will connect to /api/runs/transpile.</div>
    </section>
  );
}

