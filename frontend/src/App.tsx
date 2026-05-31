import { Activity, Binary, Cpu, Network } from "lucide-react";
import { ArchitectureBuilderPage } from "./pages/ArchitectureBuilderPage";
import { CircuitInputPage } from "./pages/CircuitInputPage";
import { ResultsPage } from "./pages/ResultsPage";
import { TargetPreviewPage } from "./pages/TargetPreviewPage";

export function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Binary aria-hidden="true" />
          <span>QCE Tool</span>
        </div>
        <nav>
          <a href="#circuit">
            <Activity aria-hidden="true" /> Circuit
          </a>
          <a href="#architecture">
            <Cpu aria-hidden="true" /> Architecture
          </a>
          <a href="#preview">
            <Network aria-hidden="true" /> Preview
          </a>
          <a href="#results">
            <Activity aria-hidden="true" /> Results
          </a>
        </nav>
      </aside>
      <section className="workspace">
        <CircuitInputPage />
        <ArchitectureBuilderPage />
        <TargetPreviewPage />
        <ResultsPage />
      </section>
    </main>
  );
}

