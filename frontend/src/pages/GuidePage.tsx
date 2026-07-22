import { useState } from "react";

const architectureSteps = [
  "Frontend",
  "FastAPI routes",
  "QCE backend services",
  "Compiler backends",
  "Logical IR",
  "Resource estimators",
  "Results and export",
];

const docTopics = [
  ["docs-top", "Overview"],
  ["docs-integrations", "Open-source integrations"],
  ["docs-estimator-assumptions", "Estimator assumptions"],
  ["docs-backend", "Backend reference"],
  ["docs-research", "Research basis"],
  ["docs-glossary", "Glossary"],
];

type DocTopic = (typeof docTopics)[number][0];

const integrations = [
  {
    name: "Qiskit",
    tool: "Circuit parsing, transpilation, basis translation, and target-aware compilation.",
    sends: "OpenQASM circuits, basis gates, optimization settings, coupling data, and FTarget-derived target information.",
    receives: "Validated circuits, transpiled circuits, layouts, gate counts, routing metadata, and Qiskit text previews.",
    adapter: "backend/services/circuit_service.py, backend/services/transpilation_service.py, backend/services/compilers/qiskit_ftarget.py",
  },
  {
    name: "Pandora",
    tool: "Optional compiler backend used when the selected path can be translated and validated cleanly.",
    sends: "A topology-legalized circuit and architecture connectivity exported from the selected FTarget.",
    receives: "Optimized circuit output when Pandora succeeds, or a structured fallback warning when it cannot safely compile.",
    adapter: "backend/services/compilers/pandora_compiler.py, backend/services/compilers/pandora_runner.py, backend/services/compilers/pandora_topology.py",
  },
  {
    name: "FTarget model",
    tool: "The architecture object that keeps gate support, timing, error profile, topology, and routing preferences together.",
    sends: "Architecture presets and user-edited physical profile settings.",
    receives: "A validated target object plus exported topology data used by compilers and estimators.",
    adapter: "backend/target_creation/target.py, backend/services/target_service.py",
  },
  {
    name: "Native QRE estimator",
    tool: "QCE's local resource-estimation path for fault-tolerant overhead, runtime, RQOps, and qubit counts.",
    sends: "Logical IR, physical hardware profile, QEC settings, compiler metadata, and selected surface-code assumptions.",
    receives: "Resource metrics, logical and physical count breakdowns, warnings, and export-ready estimator payloads.",
    adapter: "backend/services/resource_estimators/native_qre.py, backend/services/estimation_context.py",
  },
];

const routeFlows = [
  {
    route: "/api/circuits/validate",
    service: "preview_qasm(...)",
    data: "Frontend sends source QASM and receives parsed metadata plus a Qiskit text preview.",
  },
  {
    route: "/api/targets/preview",
    service: "preview_target(...)",
    data: "Frontend sends architecture configuration and receives supported gates, topology, and profile summaries.",
  },
  {
    route: "/api/runs/compile",
    service: "compile_qasm(...)",
    data: "Frontend sends the full run request and receives compiler artifacts, Logical IR, estimator metrics, warnings, and export payloads.",
  },
  {
    route: "/api/capabilities/*",
    service: "capability route handlers",
    data: "Frontend receives available architectures, compiler options, and estimator capability metadata for local form controls.",
  },
];

const functionGroups = [
  {
    module: "Circuit intake and preview",
    functions: [
      {
        name: "circuit_from_qasm(...)",
        purpose: "Parses user-provided OpenQASM into the common Qiskit circuit layer.",
        inputs: "OpenQASM source text.",
        output: "QuantumCircuit or validation error.",
        usedBy: "preview_qasm(...), compile_qasm(...).",
        assumptions: "The intake layer treats Qiskit as the canonical in-memory circuit representation.",
      },
      {
        name: "circuit_preview(...)",
        purpose: "Builds the small-circuit text preview used by the UI before and after compilation.",
        inputs: "QuantumCircuit.",
        output: "Preview diagram and circuit metadata.",
        usedBy: "Circuit validation routes and compilation artifacts.",
        assumptions: "Large circuits are summarized rather than drawn inline.",
      },
    ],
  },
  {
    module: "Target and architecture services",
    functions: [
      {
        name: "build_target(...)",
        purpose: "Constructs the selected FTarget from preset and physical-profile configuration.",
        inputs: "Architecture preset, gate set, connectivity, timing, and error settings.",
        output: "Validated FTarget.",
        usedBy: "Target preview and compiler services.",
        assumptions: "FTarget owns architecture data; compiler backends consume it but do not replace it.",
      },
      {
        name: "export_target_topology(...)",
        purpose: "Normalizes architecture connectivity into a graph-like shape that compilers and validators can share.",
        inputs: "FTarget.",
        output: "Topology metadata with coupling edges and architecture labels.",
        usedBy: "Pandora routing, topology validation, Logical IR metadata, and run export.",
        assumptions: "Topology validation is structural, not pulse-level calibration.",
      },
    ],
  },
  {
    module: "Compiler selection and routing",
    functions: [
      {
        name: "compile_qasm(...)",
        purpose: "Coordinates the backend run: parse circuit, build target, select compiler, build Logical IR, estimate resources, and prepare artifacts.",
        inputs: "Run request with QASM, compiler settings, architecture configuration, and estimator settings.",
        output: "Compiled circuit artifacts, Logical IR, estimator metrics, warnings, and export data.",
        usedBy: "Run evaluation route.",
        assumptions: "Fallbacks must be explicit so the UI can report which compiler path actually produced results.",
      },
      {
        name: "QiskitFTargetCompiler.compile(...)",
        purpose: "Compiles and routes a circuit against the selected FTarget using Qiskit.",
        inputs: "QuantumCircuit, FTarget, optimization level, and compiler options.",
        output: "Compiled circuit, layout information, routing metadata, and warnings.",
        usedBy: "Compiler fallback and automatic compiler selection.",
        assumptions: "Qiskit remains the reliable baseline when an optional compiler cannot complete safely.",
      },
      {
        name: "PandoraCompiler.compile(...)",
        purpose: "Attempts the Pandora path, then validates the result against the selected architecture topology.",
        inputs: "QuantumCircuit, FTarget, topology export, and Pandora execution payload.",
        output: "Pandora compilation result or structured failure information.",
        usedBy: "Automatic and Pandora-selected compiler paths.",
        assumptions: "Unsupported gates, translation failures, or invalid topology results must not be hidden.",
      },
      {
        name: "route_circuit_with_target(...)",
        purpose: "Legalizes circuit operations against the target connectivity before Pandora translation.",
        inputs: "QuantumCircuit, FTarget, and exported topology.",
        output: "Topology-aware routing result and metadata.",
        usedBy: "Pandora compiler adapter.",
        assumptions: "Routing metadata is part of the evidence trail for architecture comparisons.",
      },
    ],
  },
  {
    module: "Logical IR and estimation",
    functions: [
      {
        name: "build_logical_ir(...)",
        purpose: "Turns the compiled circuit and target context into QCE's backend-neutral Logical IR.",
        inputs: "Compiled QuantumCircuit, FTarget, compiler name, and compiler artifacts.",
        output: "Logical IR with operations, counts, architecture metadata, and validation.",
        usedBy: "Resource estimators and run export.",
        assumptions: "The IR is the boundary between compilation and estimation.",
      },
      {
        name: "NativeQreEstimator.estimate(...)",
        purpose: "Computes local resource-estimation metrics from the Logical IR and surface-code settings.",
        inputs: "Compilation result with Logical IR, target profile, and QEC parameters.",
        output: "Physical qubits, runtime, RQOps, logical/physical count breakdowns, and warnings.",
        usedBy: "Estimator registry during run evaluation.",
        assumptions: "Native operation support is validated before estimation so unsupported gates do not silently disappear.",
      },
    ],
  },
];

const researchAreas = [
  {
    area: "Architecture-aware compilation",
    reference: "Qiskit Target abstractions and QCE's FTarget model.",
    contribution: "Keeps gate availability, coupling, timing, error rates, and architecture labels in one inspectable object.",
    influence: "target_service.py, target_creation/target.py, qiskit_ftarget.py.",
  },
  {
    area: "Routing and topology",
    reference: "Heavy-hex, heavy-square, grid, and modular architecture references used by the preset library.",
    contribution: "Shapes the coupling maps and the topology-validation checks used before comparing compiler output.",
    influence: "hardware/architecture_presets.py, pandora_router.py, pandora_topology.py.",
  },
  {
    area: "Fault-tolerant resource estimation",
    reference: "Surface-code overhead models and resource-estimation methodology.",
    contribution: "Connects logical operations to distance, cycles, physical-qubit overhead, and runtime estimates.",
    influence: "native_qre.py, estimation_context.py, run_export.py.",
  },
  {
    area: "Intermediate representations",
    reference: "Compiler-to-estimator separation patterns used in quantum toolchains.",
    contribution: "Prevents the estimator from depending directly on one compiler's private circuit object shape.",
    influence: "IR/logical_ir.py and estimator adapters.",
  },
  {
    area: "Benchmarking methodology",
    reference: "Circuit-benchmark workflows for comparing architecture-dependent compilation and estimation assumptions.",
    contribution: "Keeps source circuit, compiler path, target profile, warnings, and export metadata together for reproducible runs.",
    influence: "transpilation_service.py, run_export.py, frontend results views.",
  },
];

const glossaryGroups = [
  {
    group: "Circuit terms",
    terms: [
      ["OpenQASM", "The text circuit format accepted by the intake stage."],
      ["Qiskit circuit", "The common in-memory circuit representation used between intake, compilation, and preview."],
      ["Barrier", "A scheduling marker from the source circuit; it should not be treated as a physical multi-qubit operation during routing."],
    ],
  },
  {
    group: "Compiler terms",
    terms: [
      ["Compiler backend", "The service that transforms the input circuit into a target-compatible compiled circuit."],
      ["Fallback", "A deliberate switch to Qiskit when an optional compiler cannot complete or validate safely."],
      ["Compiler weight", "A relative preference or cost value used when judging gate choices in a target profile."],
    ],
  },
  {
    group: "Architecture terms",
    terms: [
      ["FTarget", "QCE's target object for supported gates, physical profile, coupling map, and architecture metadata."],
      ["Physical profile", "The gate timing and error-rate assumptions attached to a selected architecture."],
      ["Routing preference", "A target-level hint used to describe which gates or paths are preferred during compilation."],
    ],
  },
  {
    group: "Routing terms",
    terms: [
      ["Coupling map", "The graph of physical qubit connections that two-qubit operations must respect."],
      ["SWAP legalization", "The process of replacing or routing non-adjacent interactions so the circuit respects topology."],
      ["Topology validation", "A structural check that compiled two-qubit operations match the selected architecture graph."],
    ],
  },
  {
    group: "Fault-tolerance terms",
    terms: [
      ["Surface code", "The QEC model used to translate logical operations into physical-resource overhead."],
      ["Logical failure probability", "The target failure budget used by the estimator when sizing or evaluating QEC assumptions."],
      ["Code distance", "The surface-code distance parameter controlling protection level and overhead."],
    ],
  },
  {
    group: "Estimator outputs",
    terms: [
      ["RQOps", "Resource-qualified operations counted after compiler and estimator assumptions are applied."],
      ["Logical IR", "QCE's compiler-neutral operation list passed into resource-estimation services."],
      ["Physical qubits", "The estimated physical-qubit footprint after applying the selected QEC model."],
    ],
  },
];

export function DocsPage() {
  const [activeTopic, setActiveTopic] = useState<DocTopic>("docs-top");

  function showTopic(topic: DocTopic) {
    setActiveTopic(topic);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="guide-shell docs-shell">
      <div className="docs-layout">
        <aside className="docs-sidebar" aria-label="Documentation topics">
          <strong>Docs topics</strong>
          <nav>
            {docTopics.map(([id, label]) => (
              <button
                type="button"
                className={activeTopic === id ? "is-active" : undefined}
                aria-current={activeTopic === id ? "page" : undefined}
                onClick={() => showTopic(id)}
                key={id}
              >
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <div className="docs-content">
          <section className={`docs-section-card docs-hero-card ${activeTopic === "docs-top" ? "is-active" : ""}`} id="docs-top">
            <h1>QCE architecture overview</h1>
            <div className="docs-prose">
              <p>
                QCE connects multiple open-source quantum tools through one backend workflow.
                Qiskit acts as the common circuit layer so circuits can move between intake, compilation, target configuration, and resource estimation without creating a dependency maze.
              </p>
            </div>
            <div className="docs-overview-block">
              <h2>From circuit input to export</h2>
              <div className="docs-architecture-flow" aria-label="QCE backend workflow">
                {architectureSteps.map((step, index) => (
                  <div className="docs-flow-item" key={step}>
                    <span>{step}</span>
                    {index < architectureSteps.length - 1 ? <i aria-hidden="true" /> : null}
                  </div>
                ))}
              </div>
              <p className="docs-muted">
                The interface collects the circuit and run settings. Backend services compile the circuit into Logical IR, estimate its resources, and prepare the results for export.
              </p>
            </div>
            <div className="docs-actions">
              <a
                className="docs-link-button"
                href="https://github.com/adityar0407/quantum-circuit-evaluator"
                target="_blank"
                rel="noreferrer"
              >
                View GitHub repository
              </a>
              <button type="button" className="secondary" onClick={() => showTopic("docs-glossary")}>
                Browse glossary
              </button>
            </div>
          </section>

          <section className={`docs-section-card ${activeTopic === "docs-integrations" ? "is-active" : ""}`} id="docs-integrations">
            <h2>How external tools connect</h2>
            <div className="docs-grid two-column">
              {integrations.map((integration) => (
                <article className="docs-detail-card" key={integration.name}>
                  <h3>{integration.name}</h3>
                  <dl>
                    <div>
                      <dt>Used for</dt>
                      <dd>{integration.tool}</dd>
                    </div>
                    <div>
                      <dt>QCE sends</dt>
                      <dd>{integration.sends}</dd>
                    </div>
                    <div>
                      <dt>QCE receives</dt>
                      <dd>{integration.receives}</dd>
                    </div>
                    <div>
                      <dt>Adapter</dt>
                      <dd>{integration.adapter}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          <section className={`docs-section-card ${activeTopic === "docs-estimator-assumptions" ? "is-active" : ""}`} id="docs-estimator-assumptions">
            <h2>Why Stage 2 and Stage 3 both ask about hardware</h2>
            <div className="docs-prose">
              <p>
                Stage 2 defines where gates can run and how the compiler routes them. Stage 3 supplies the error rates and operation times used to estimate the compiled circuit's cost. These settings are separate because two devices can share a layout while having different performance.
              </p>
              <p>
                <strong>Example:</strong> In Stage 2, you can select a heavy-hex layout so the compiler respects its allowed qubit connections. In Stage 3, you can enter a two-qubit error rate and gate time measured from a particular device. The layout controls compilation; the measured values control the estimate.
              </p>
              <p>
                <strong>Hardware type</strong> selects the calculation method. Neutral-atom estimates include atom-movement costs; standard estimates do not. This setting does not change the architecture selected in Stage 2.
              </p>
              <p>
                <strong>Recommended values</strong> are QCE's included starting values. They are useful for exploration, not a claim about a specific physical device. Choose custom values when reproducing a paper, using calibration data, or testing a specific assumption.
              </p>
              <p>
                <strong>Force code-cycle count</strong> replaces the calculated number of error-correction cycles with a fixed number. Leave it blank unless a controlled experiment requires that override.
              </p>
            </div>
            <h3>Frontend-to-backend values</h3>
            <div className="docs-term-table" aria-label="Frontend labels and backend values">
              <div><strong>Frontend label</strong><strong>Backend value</strong></div>
              <div><span>Recommended values</span><code>built_in</code></div>
              <div><span>Enter my own values</span><code>custom</code></div>
              <div><span>Standard quantum hardware</span><code>gate_based</code></div>
              <div><span>Neutral-atom hardware</span><code>neutral_atom</code></div>
              <div><span>Force code-cycle count</span><code>code_cycle_override</code></div>
            </div>
          </section>

          <section className={`docs-section-card ${activeTopic === "docs-backend" ? "is-active" : ""}`} id="docs-backend">
            <h2>Backend reference</h2>
            <div className="docs-section-intro">
              <h3>API routes</h3>
              <p className="docs-muted">The frontend uses these routes to validate circuits, preview architectures, run compilation, and load supported options.</p>
            </div>
            <div className="docs-route-list">
              {routeFlows.map((flow) => (
                <article className="docs-route-card" key={flow.route}>
                  <code>{flow.route}</code>
                  <strong>{flow.service}</strong>
                  <p>{flow.data}</p>
                </article>
              ))}
            </div>
            <div className="docs-section-intro docs-section-divider">
              <h3>Internal services</h3>
              <p className="docs-muted">These functions carry a run from circuit parsing through compilation and resource estimation.</p>
            </div>
            <div className="docs-function-list">
              {functionGroups.map((group) => (
                <article className="docs-function-group" key={group.module}>
                  <h3>{group.module}</h3>
                  {group.functions.map((fn) => (
                    <div className="docs-function-card" key={fn.name}>
                      <code>{fn.name}</code>
                      <p>{fn.purpose}</p>
                      <dl>
                        <div>
                          <dt>Inputs</dt>
                          <dd>{fn.inputs}</dd>
                        </div>
                        <div>
                          <dt>Output</dt>
                          <dd>{fn.output}</dd>
                        </div>
                        <div>
                          <dt>Used by</dt>
                          <dd>{fn.usedBy}</dd>
                        </div>
                        <div>
                          <dt>Assumption</dt>
                          <dd>{fn.assumptions}</dd>
                        </div>
                      </dl>
                    </div>
                  ))}
                </article>
              ))}
            </div>
          </section>

          <section className={`docs-section-card ${activeTopic === "docs-research" ? "is-active" : ""}`} id="docs-research">
            <h2>What influenced the implementation</h2>
            <div className="docs-grid two-column">
              {researchAreas.map((item) => (
                <article className="docs-detail-card" key={item.area}>
                  <h3>{item.area}</h3>
                  <p><strong>Reference:</strong> {item.reference}</p>
                  <p><strong>What it contributes:</strong> {item.contribution}</p>
                  <p><strong>How it influenced QCE:</strong> {item.influence}</p>
                </article>
              ))}
            </div>
          </section>

          <section className={`docs-section-card ${activeTopic === "docs-glossary" ? "is-active" : ""}`} id="docs-glossary">
            <h2>Terms used across QCE</h2>
            <div className="docs-grid two-column">
              {glossaryGroups.map((group) => (
                <article className="docs-glossary-card" key={group.group}>
                  <h3>{group.group}</h3>
                  <dl>
                    {group.terms.map(([term, definition]) => (
                      <div key={term}>
                        <dt>{term}</dt>
                        <dd>{definition}</dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
