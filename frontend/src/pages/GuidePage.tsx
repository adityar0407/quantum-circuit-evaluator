type GuideSection = {
  id: string;
  kicker: string;
  title: string;
  summary: string;
  bullets: string[];
  functions: Array<{ name: string; detail: string }>;
  links: Array<{ label: string; href: string }>;
};

const sections: GuideSection[] = [
  {
    id: "ftarget",
    kicker: "1. FTarget",
    title: "How FTarget accepts architecture input",
    summary:
      "FTarget is the architecture object that turns user choices into a compile-time target. It defines which gates are allowed, which qubits can interact, and what connectivity pattern the compiler must obey.",
    bullets: [
      "The user picks a hardware architecture preset, and the frontend sends that into the backend target builder.",
      "Preset resolution happens before compilation, so the compiler always sees a concrete architecture rather than a vague label.",
      "The target preview and routing checks both come from the same FTarget-backed description, which keeps the compiler and preview consistent.",
    ],
    functions: [
      {
        name: "backend/services/target_service.py::build_target",
        detail: "Builds the concrete FTarget object from the selected preset and any advanced overrides.",
      },
      {
        name: "backend/services/target_service.py::preview_target",
        detail: "Exports the qubit layout, edges, supported operations, and architecture metadata used by the preview panel.",
      },
      {
        name: "backend/target_creation/target.py::FTarget.__init__",
        detail: "Instantiates the logical architecture object that Qiskit and Pandora compile against.",
      },
      {
        name: "backend/target_creation/target.py::FTarget._validate_and_parse_profile",
        detail: "Validates the gate profile and converts configured gate names into Qiskit gate objects.",
      },
      {
        name: "backend/target_creation/target.py::FTarget._populate_instructions_network / _populate_instructions_hex",
        detail: "Populates the target with the allowed instructions and the selected connectivity pattern.",
      },
    ],
    links: [
      { label: "IBM Qiskit Target documentation", href: "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.Target" },
      { label: "Qiskit transpiler API", href: "https://quantum.cloud.ibm.com/docs/en/api/qiskit/transpiler" },
    ],
  },
  {
    id: "compilation",
    kicker: "2. Compilation",
    title: "What Qiskit does and what Pandora does",
    summary:
      "This tool has two compiler backends. Qiskit handles the standard FTarget transpilation path. Pandora handles the topology-aware large-circuit path, including routing and architecture validation before optimization.",
    bullets: [
      "Qiskit is the stable FTarget compiler path and is used whenever the selected route or fallback logic chooses it.",
      "Pandora is used as the research compiler path for larger topology-aware workloads and is validated against the selected architecture before its output is accepted.",
      "The compile flow always checks architecture legality before LogicalIR and resource estimation continue.",
    ],
    functions: [
      {
        name: "backend/services/transpilation_service.py::select_compiler_backend",
        detail: "Chooses which compiler path to use based on the requested mode and the target/compiler capabilities.",
      },
      {
        name: "backend/services/compilers/qiskit_ftarget.py::QiskitFTargetCompiler.compile",
        detail: "Runs the Qiskit-backed FTarget compilation path.",
      },
      {
        name: "backend/services/compilers/pandora_compiler.py::PandoraCompiler.compile",
        detail: "Runs the Pandora-backed compilation flow for supported architectures.",
      },
      {
        name: "backend/services/compilers/pandora_router.py::route_circuit_with_target",
        detail: "Performs Pandora-side routing against the selected architecture graph.",
      },
      {
        name: "backend/services/compilers/pandora_topology.py::build_pandora_topology_payload / validate_compiled_circuit_against_architecture",
        detail: "Exports the target contract to Pandora and rejects illegal Pandora output before downstream analysis.",
      },
    ],
    links: [
      { label: "Pandora repository", href: "https://github.com/ioanamoflic/pandora" },
      { label: "Qiskit transpiler Target docs", href: "https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.Target" },
    ],
  },
  {
    id: "inputs",
    kicker: "3. Inputs",
    title: "What the user must provide",
    summary:
      "At minimum, the user provides a circuit and chooses the hardware architecture they want to compile against. Everything else refines compilation or estimation.",
    bullets: [
      "Circuit input: OpenQASM is the main input format.",
      "Architecture input: choose the hardware preset that matches the study you want to run.",
      "Estimation input: choose whether to keep the recommended physical/QEC defaults or override them with your own assumptions.",
      "Advanced graph settings are optional and are only for users intentionally editing the backend graph model.",
    ],
    functions: [
      {
        name: "backend/services/circuit_service.py::circuit_from_qasm / circuit_summary",
        detail: "Parses the input circuit and computes the basic statistics shown in the intake panel.",
      },
      {
        name: "backend/hardware/architecture_presets.py::resolve_architecture_config",
        detail: "Turns the selected architecture preset into a concrete backend target configuration.",
      },
      {
        name: "backend/services/estimation_context.py::build_estimation_context",
        detail: "Combines the architecture, physical assumptions, QEC assumptions, and network assumptions for estimation.",
      },
    ],
    links: [
      { label: "OpenQASM and Qiskit API docs", href: "https://quantum.cloud.ibm.com/docs/en/api/qiskit" },
    ],
  },
  {
    id: "basis",
    kicker: "4. Compiler basis",
    title: "What compiler basis means here",
    summary:
      "Compiler basis is the gate family and cost model the compiler uses for the selected hardware family. It is not a separate architecture. It is the native gate vocabulary the compiler prefers while respecting the selected target.",
    bullets: [
      "Superconducting presets switch into a superconducting-style gate basis.",
      "Neutral-atom presets switch into a neutral-atom style gate basis.",
      "Ion-style presets switch into an ion-style gate basis.",
      "The user can still tune the weights, but the hardware family decides the default basis automatically.",
    ],
    functions: [
      {
        name: "frontend/src/state/defaults.ts::modalityPresets",
        detail: "Defines the user-facing compiler basis families and the parameters shown for each one.",
      },
      {
        name: "frontend/src/state/defaults.ts::cloneModalitySettings",
        detail: "Loads the default tuning values for the selected compiler basis.",
      },
      {
        name: "frontend/src/state/defaults.ts::buildProfile",
        detail: "Builds the FTarget gate profile from the selected basis and user-edited weights.",
      },
    ],
    links: [
      { label: "Qiskit gate and transpiler API", href: "https://quantum.cloud.ibm.com/docs/en/api/qiskit" },
    ],
  },
  {
    id: "qec",
    kicker: "5. FT estimation profile and QEC",
    title: "How physical assumptions and QEC models are used",
    summary:
      "The estimation profile is separate from FTarget. FTarget is the logical architecture. The estimation profile tells Azure QDK how to price time, error, and qubit overhead once the compiled logical circuit is ready.",
    bullets: [
      "Physical hardware assumptions control gate error rates, gate times, measurement time, and related parameters.",
      "QEC model selection chooses the error-correcting-code model used by QDK during estimation.",
      "The recommended-default mode uses built-in assumptions, while the advanced mode exposes deeper QEC parameters.",
    ],
    functions: [
      {
        name: "backend/services/resource_estimators/physical_qdk_adapter.py::physical_profile_to_qdk_model",
        detail: "Converts the user’s physical-assumption payload into a QDK-compatible physical model.",
      },
      {
        name: "backend/services/resource_estimators/physical_qdk_adapter.py::physical_profile_capabilities",
        detail: "Provides the frontend with the supported hardware-model and parameter metadata.",
      },
      {
        name: "backend/services/resource_estimators/native_qre.py::_build_qec_model",
        detail: "Instantiates the selected QDK QEC model before the estimate runs.",
      },
      {
        name: "backend/services/resource_estimators/qre_params.py::build_qre_params",
        detail: "Builds the QDK estimator parameter payload for the compatibility estimation path.",
      },
    ],
    links: [
      { label: "Azure Quantum resource estimator introduction", href: "https://learn.microsoft.com/en-us/azure/quantum/intro-to-resource-estimation" },
      { label: "Azure Quantum error-correction concepts", href: "https://learn.microsoft.com/en-us/azure/quantum/concepts-error-correction" },
    ],
  },
  {
    id: "resource-estimation",
    kicker: "6. Resource estimation",
    title: "How compiled circuits become resource estimates",
    summary:
      "Once compilation is complete, the backend builds LogicalIR and then runs one of two estimation flows. The native path builds a QDK trace directly. The compatibility path lowers the compiled result back into a Qiskit circuit for QDK.",
    bullets: [
      "LogicalIR is the internal architecture-aware intermediate representation shared by the compiler and estimator layers.",
      "The native QRE path uses QDK trace objects and lattice-surgery transforms directly.",
      "The compatibility path exists as a secondary route when you want the explicit Qiskit-to-QDK flow.",
    ],
    functions: [
      {
        name: "backend/IR/logical_ir.py::build_logical_ir / serialize_logical_ir",
        detail: "Builds and records the architecture-respecting intermediate representation used for downstream analysis.",
      },
      {
        name: "backend/services/resource_estimators/native_qre.py::NativeQreEstimator.estimate",
        detail: "Runs the native QDK trace-based estimation path.",
      },
      {
        name: "backend/services/resource_estimators/native_qre.py::logical_ir_to_native_qre_trace",
        detail: "Lowers LogicalIR into a QDK trace for native estimation.",
      },
      {
        name: "backend/services/resource_estimators/qiskit_compatibility.py::QiskitCompatibilityQreEstimator.estimate",
        detail: "Runs the compatibility estimation path through a Qiskit circuit representation.",
      },
      {
        name: "backend/services/run_export.py::build_reproducible_run_export",
        detail: "Packages the run configuration, compiled artifacts, and estimation assumptions into the reproducible export.",
      },
    ],
    links: [
      { label: "Azure Quantum resource estimator docs", href: "https://learn.microsoft.com/en-us/azure/quantum/intro-to-resource-estimation" },
      { label: "Pandora repository", href: "https://github.com/ioanamoflic/pandora" },
    ],
  },
];

export function GuidePage() {
  return (
    <main className="landing-shell guide-shell">
      <section className="landing-hero guide-hero">
        <div className="landing-hero-copy">
          <p className="section-label">Guide</p>
          <h1>Overview of how the evaluator works</h1>
          <p>
            This page is the quick-start guide for new users. It explains what the major layers do, what inputs matter,
            which open-source packages are involved, and what custom wrappers this repo adds on top.
          </p>
        </div>
        <div className="landing-hero-panel">
          <p className="section-label">What you get here</p>
          <div className="landing-points">
            <article>
              <strong>Architecture model</strong>
              <p>How FTarget turns architecture choices into a target the compiler must obey.</p>
            </article>
            <article>
              <strong>Compiler split</strong>
              <p>What Qiskit handles, what Pandora handles, and where the custom routing and validation logic lives.</p>
            </article>
            <article>
              <strong>Estimation path</strong>
              <p>How the compiled result becomes LogicalIR and then turns into a QDK resource estimate.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-section-header">
          <div>
            <p className="section-label">Overview sections</p>
            <h2>Get up to speed quickly</h2>
          </div>
        </div>
        <div className="guide-grid">
          {sections.map((section) => (
            <article key={section.id} className="surface-card guide-card">
              <p className="section-label">{section.kicker}</p>
              <h3>{section.title}</h3>
              <p className="guide-summary">{section.summary}</p>

              <div className="subsection-block">
                <h4>What this means</h4>
                <ul className="guide-list">
                  {section.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              </div>

              <div className="subsection-block">
                <h4>Functions and wrappers used here</h4>
                <dl className="detail-list">
                  {section.functions.map((entry) => (
                    <div key={entry.name}>
                      <dt>{entry.name}</dt>
                      <dd>{entry.detail}</dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="subsection-block">
                <h4>Learn more</h4>
                <div className="guide-links">
                  {section.links.map((link) => (
                    <a key={link.href + link.label} href={link.href} target="_blank" rel="noreferrer">
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
