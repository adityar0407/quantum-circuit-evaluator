import { defaultTargetConfig } from "../state/defaults";

export function ArchitectureBuilderPage() {
  return (
    <section id="architecture" className="panel">
      <header>
        <p>Architecture Builder</p>
        <h1>Target configuration</h1>
      </header>
      <pre>{JSON.stringify(defaultTargetConfig, null, 2)}</pre>
    </section>
  );
}

