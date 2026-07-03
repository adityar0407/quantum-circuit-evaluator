import { useEffect, useRef, useState } from "react";
import { ArrowRight, Play, RotateCcw } from "lucide-react";
import { fetchArchitectureCapabilities, fetchResourceCapabilities, previewTarget, transpileCircuit, validateCircuit } from "./api/client";
import type {
  ArchitecturePreset,
  CircuitPreview,
  CircuitSummary,
  CompilerBackend,
  EstimationProfiles,
  ResourceCapabilities,
  ResourceEstimator,
  TargetConfig,
  TargetPreview,
  TranspileResponse,
} from "./api/types";
import { ArchitectureStage } from "./components/tool/ArchitectureStage";
import { CircuitStage } from "./components/tool/CircuitStage";
import { EstimationStage } from "./components/tool/EstimationStage";
import { ResultsStage } from "./components/tool/ResultsStage";
import { ToolShell } from "./components/tool/ToolShell";
import { SectionLabel } from "./components/tool/ToolPrimitives";
import { GuidePage } from "./pages/GuidePage";
import {
  buildProfile,
  cloneEstimationProfiles,
  cloneModalitySettings,
  defaultModality,
  defaultQasm,
  defaultTargetConfig,
  type ModalityKey,
  type QecModelKey,
} from "./state/defaults";

type WorkStatus = "idle" | "loading" | "ready" | "error";
type AppView = "landing" | "credits" | "guide" | "tool";
type ToolView = "circuit" | "architecture" | "estimation" | "results";
type ActionState = "idle" | "loading" | "success" | "error";

function cloneConfig(config: TargetConfig): TargetConfig {
  return JSON.parse(JSON.stringify(config)) as TargetConfig;
}

function clonePresetConfig(preset: ArchitecturePreset): TargetConfig {
  return JSON.parse(JSON.stringify({ architecture_preset: preset.id, ...preset.target_config })) as TargetConfig;
}

function asNumber(value: unknown, fallback = 0): number {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (typeof value !== "number") {
    if (typeof value === "boolean") {
      return value ? "Yes" : "No";
    }
    return String(value);
  }
  if (value === 0) {
    return "0";
  }
  if (Math.abs(value) < 0.001 || Math.abs(value) >= 10000) {
    return value.toExponential(3);
  }
  return value.toLocaleString(undefined, { maximumSignificantDigits: 6 });
}

function modalityForPreset(preset?: ArchitecturePreset): ModalityKey {
  if (!preset) {
    return defaultModality;
  }
  if (preset.category.includes("neutral_atom")) {
    return "neutral_atom";
  }
  if (preset.category.includes("trapped_ion") || preset.category.includes("any_to_any")) {
    return "trapped_ion";
  }
  if (preset.category.includes("superconducting") || preset.id.includes("heavy_hex") || preset.id.includes("modular_superconducting")) {
    return "superconducting";
  }
  return "ft_logical";
}

function hardwareModelForPreset(preset?: ArchitecturePreset): string {
  if (!preset) {
    return "gate_based";
  }
  return preset.category.includes("neutral_atom") ? "neutral_atom" : "gate_based";
}

function formatReferenceLabel(reference: string): string {
  const match = reference.match(/_(\d{4}\.\d{4,5})\.pdf$/);
  if (match) {
    return `arXiv ${match[1]}`;
  }
  return reference.split("/").at(-1)?.replace(/_/g, " ").replace(/\.pdf$/i, "") ?? reference;
}

function referenceUrl(reference: string): string | null {
  const match = reference.match(/_(\d{4}\.\d{4,5})\.pdf$/);
  if (!match) {
    return null;
  }
  return `https://arxiv.org/abs/${match[1]}`;
}

function cleanOptionalProfileFields(profile: EstimationProfiles): EstimationProfiles {
  const cleanRecord = (record: Record<string, unknown>): Record<string, unknown> =>
    Object.fromEntries(
      Object.entries(record)
        .filter(([, value]) => value !== "" && value !== undefined)
        .map(([key, value]) => [key, cleanProfileValue(value)]),
    );

  const cleanProfileValue = (value: unknown): unknown => {
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      return cleanRecord(value as Record<string, unknown>);
    }
    return value;
  };

  const cleaned: EstimationProfiles = {
    physical_hardware: cleanRecord(profile.physical_hardware),
    qec: cleanRecord(profile.qec),
  };
  if (profile.network) {
    cleaned.network = cleanRecord(profile.network);
  }
  return cleaned;
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function extractQasmFromJsonValue(value: unknown): string | null {
  if (typeof value === "string" && value.includes("OPENQASM")) {
    return value;
  }
  if (Array.isArray(value)) {
    for (const entry of value) {
      const nested = extractQasmFromJsonValue(entry);
      if (nested) {
        return nested;
      }
    }
    return null;
  }
  if (typeof value === "object" && value !== null) {
    const record = value as Record<string, unknown>;
    const preferredKeys = ["qasm", "openqasm", "open_qasm", "source", "program"];
    for (const key of preferredKeys) {
      const candidate = record[key];
      if (typeof candidate === "string" && candidate.includes("OPENQASM")) {
        return candidate;
      }
    }
    for (const candidate of Object.values(record)) {
      const nested = extractQasmFromJsonValue(candidate);
      if (nested) {
        return nested;
      }
    }
  }
  return null;
}

function parseCircuitFileContent(fileName: string, content: string): string {
  const normalizedName = fileName.toLowerCase();
  if (normalizedName.endsWith(".qasm")) {
    return content;
  }
  if (normalizedName.endsWith(".json")) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(content);
    } catch {
      throw new Error("Uploaded JSON file is not valid JSON.");
    }
    const qasm = extractQasmFromJsonValue(parsed);
    if (!qasm) {
      throw new Error("Uploaded JSON file does not contain an OpenQASM circuit string.");
    }
    return qasm;
  }
  throw new Error("Unsupported file type. Upload a .qasm or .json circuit file.");
}

function resolveViewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, "");
  if (key === "credits") {
    return "credits";
  }
  if (key === "guide") {
    return "guide";
  }
  if (["tool", "circuit", "architecture", "estimation", "results"].includes(key)) {
    return "tool";
  }
  return "landing";
}

function resolveToolViewFromHash(hash: string): ToolView {
  const key = hash.replace(/^#/, "");
  if (key === "architecture") return "architecture";
  if (key === "estimation") return "estimation";
  if (key === "results") return "results";
  return "circuit";
}

function buildInterpretation({
  runResult,
  physicalCounts,
  logicalCounts,
  qreAssumptions,
}: {
  runResult?: TranspileResponse;
  physicalCounts: Record<string, unknown>;
  logicalCounts: Record<string, unknown>;
  qreAssumptions: Record<string, unknown>;
}) {
  if (!runResult) {
    return {
      headline: "No run has been executed yet.",
      summary: "Validate the circuit, configure the target, and run the analysis to produce a compiled circuit plus QRE estimate.",
      bottleneck: "No bottleneck can be identified before a compiled result exists.",
      nextStep: "Start with target preview if you want to inspect the architecture before estimation.",
      assumption: "QRE assumption translation becomes visible only after an estimate is produced.",
    };
  }

  const breakdown = asRecord(physicalCounts.breakdown);
  const tCount = asNumber(logicalCounts.tCount, 0);
  const physicalQubits = asNumber(physicalCounts.physicalQubits, 0);
  const numTFactories = asNumber(breakdown.numTfactories, 0);
  const compiledDepth = runResult.transpiled.depth;
  const originalDepth = runResult.original.depth;
  const modality = String(qreAssumptions.ftarget_modality ?? "custom");

  const headline =
    physicalQubits > 0
      ? `Compiled workload maps to roughly ${formatNumber(physicalQubits)} physical qubits under the current QRE translation.`
      : "A compiled result exists, but the physical estimate could not be interpreted.";

  let bottleneck = "The current result looks width-dominated rather than distillation-dominated.";
  if (numTFactories > 0 || tCount > 0) {
    bottleneck = `Magic-state demand is active: ${formatNumber(tCount)} T gates and ${formatNumber(numTFactories)} T factories are shaping the estimate.`;
  } else if (compiledDepth > originalDepth) {
    bottleneck = `Compilation increased the depth from ${formatNumber(originalDepth)} to ${formatNumber(compiledDepth)}, which suggests routing or decomposition overhead is dominating.`;
  }

  let nextStep = "Compare an alternative topology or modality preset to see whether the compiled depth and physical width move in the same direction.";
  if (modality === "logical_clifford_t") {
    nextStep = "Focus next on reducing T-bearing structure or rerouting the circuit, because the logical Clifford+T model is what QRE is currently pricing.";
  } else if (compiledDepth > originalDepth) {
    nextStep = "Try changing connectivity or gate assumptions first, since routing pressure appears to be adding depth before estimation begins.";
  }

  return {
    headline,
    summary: `The current run preserved the full compilation flow and then estimated the compiled circuit through Azure QRE using the translated ${modality} assumption set.`,
    bottleneck,
    nextStep,
    assumption: "FTarget is interpreted as a logical architecture profile. Native QRE consumes LogicalIR and estimates through QRE lattice-surgery transforms. Unsupported and remote operations fail explicitly.",
  };
}

function TopToolbar({ view }: { view: AppView }) {
  return (
    <header className="top-toolbar">
      <div className="top-toolbar-inner">
        <button type="button" className="toolbar-brand" onClick={() => (window.location.hash = "home")}>
          <span>Quantum circuit evaluator</span>
        </button>
        <nav className="top-toolbar-nav" aria-label="Primary">
          <a href="#home" className={view === "landing" ? "active" : undefined}>
            Home
          </a>
          <a href="#guide" className={view === "guide" ? "active" : undefined}>
            Overview
          </a>
          <a href="#tool" className={view === "tool" ? "active" : undefined}>
            Tool
          </a>
        </nav>
      </div>
    </header>
  );
}

function AppFooter({ view, status }: { view: AppView; status?: string; message?: string | null }) {
  return (
    <footer className="app-footer">
      <div className="app-footer-inner">
        <div className="app-footer-left">
          <span>© 2024 Quantum Research Labs</span>
          {view === "tool" ? (
            <>
              <span className="footer-status-dot" />
              <span>{status ?? "Idle"}</span>
            </>
          ) : null}
        </div>
        <nav className="app-footer-links">
          <a href="#credits">Credits</a>
          <a href="#guide">Documentation</a>
        </nav>
      </div>
    </footer>
  );
}

function LandingPage() {
  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <SectionLabel>Local research workspace</SectionLabel>
          <h1>Evaluate compiled circuits against the hardware assumptions that actually matter.</h1>
          <p>
            Compare how an OpenQASM circuit behaves across architecture presets, compiler paths, and fault-tolerant
            estimation assumptions. Inspect routing pressure, resource overhead, and architecture-specific tradeoffs
            before committing to a hardware profile.
          </p>
          <div className="landing-actions">
            <button type="button" onClick={() => (window.location.hash = "tool")}>
              Launch evaluator <ArrowRight aria-hidden="true" />
            </button>
            <button type="button" className="secondary" onClick={() => (window.location.hash = "guide")}>
              Read workflow overview
            </button>
          </div>
        </div>
        <div className="landing-hero-panel">
          <SectionLabel>What the workspace gives you</SectionLabel>
          <div className="landing-points">
            <article>
              <strong>Architecture-aware comparison</strong>
              <p>Preview coupling constraints and topology assumptions before estimation, using built-in presets or custom target settings.</p>
            </article>
            <article>
              <strong>Compilation-first reasoning</strong>
              <p>Validate the circuit, inspect the gate mix, and carry the compiled artifact forward into the estimation path instead of skipping directly to abstract metrics.</p>
            </article>
            <article>
              <strong>Reproducible run records</strong>
              <p>Keep architecture, compiler, and estimator assumptions tied to each run so exported comparisons stay traceable.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="landing-research-strip">
        <article className="landing-research-card">
          <SectionLabel>Typical use</SectionLabel>
          <h2>Test one circuit across multiple hardware assumptions.</h2>
          <p>Start with a circuit, validate it once, then compare how compilation overhead and QRE translation shift when connectivity, modality, or error-correction assumptions change.</p>
        </article>
        <article className="landing-research-card">
          <SectionLabel>Why it exists</SectionLabel>
          <h2>Turn architecture choices into visible tradeoffs.</h2>
          <p>The workspace is built for researchers who need to reason about routing pressure, physical width, and compiled depth without hiding the assumptions that produced those numbers.</p>
        </article>
      </section>

      <section className="landing-footer-cta">
        <div>
          <h2>Open the workspace and start with the circuit.</h2>
          <p>Validate the input first, inspect the gate mix, then move into architecture preview and estimation once the circuit is structurally ready.</p>
        </div>
        <div className="landing-actions">
          <button type="button" onClick={() => (window.location.hash = "tool")}>Get started now</button>
          <button type="button" className="secondary" onClick={() => (window.location.hash = "guide")}>See stage-by-stage guide</button>
        </div>
      </section>
    </main>
  );
}

function CreditsPage() {
  return (
    <main className="credits-shell">
      <section className="credits-header">
        <SectionLabel>Documentation / Resource acknowledgements</SectionLabel>
        <h1>Credits &amp; Research Frameworks</h1>
        <p>
          The Quantum Architecture Evaluator leverages several open-source libraries, research compilers, and hardware
          abstraction layers to provide high-fidelity circuit analysis.
        </p>
      </section>

      <section className="credits-layout">
        <div className="credits-main-stack">
          <article className="credits-card">
            <div className="credits-card-header">
              <h2>Core Frameworks</h2>
              <span className="credits-chip">v2.4.0 Engine</span>
            </div>
            <div className="framework-list">
              <div className="framework-row">
                <div>
                  <h3>Qiskit (IBM Quantum)</h3>
                  <p>Used for circuit decomposition, noise modeling, and OpenQASM transpilation strategies.</p>
                  <div className="framework-tags">
                    <span>CIRCUIT_OPT</span>
                    <span>TRANSPILE_V3</span>
                  </div>
                </div>
                <div className="framework-meta">
                  <span>Apache-2.0</span>
                  <strong>Documentation</strong>
                </div>
              </div>
              <div className="framework-row">
                <div>
                  <h3>Microsoft QDK (Azure Quantum)</h3>
                  <p>Resource estimation engine for fault-tolerant architectural benchmarks and T-gate counts.</p>
                  <div className="framework-tags">
                    <span>QSHARP_INTEROP</span>
                    <span>RESOURCE_EST</span>
                  </div>
                </div>
                <div className="framework-meta">
                  <span>MIT License</span>
                  <strong>Repository</strong>
                </div>
              </div>
              <div className="framework-row">
                <div>
                  <h3>Pandora Compiler</h3>
                  <p>Specialized research compiler for topological quantum error correction and surface-code mapping.</p>
                  <div className="framework-tags">
                    <span>SURFACE_CODE</span>
                    <span>LAT_SURGERY</span>
                  </div>
                </div>
                <div className="framework-meta">
                  <span>BSD-3-Clause</span>
                  <strong>ArXiv Paper</strong>
                </div>
              </div>
            </div>
          </article>

          <article className="credits-card">
            <h2>Hardware Datasets</h2>
            <p>Hardware specifications and calibration data pulled from real-time provider APIs.</p>
            <div className="dataset-grid">
              <div><strong>Rigetti Aspen-M</strong><span>Cal. 2024-10-12</span></div>
              <div><strong>Quantinuum H1</strong><span>Ion Trap Profile</span></div>
              <div><strong>IBM Eagle r3</strong><span>127 Qubits</span></div>
              <div><strong>Google Sycamore</strong><span>Bristlecone Spec</span></div>
            </div>
          </article>

          <article className="credits-card credits-doc-card">
            <div className="credits-doc-image" />
            <div className="credits-doc-copy">
              <h2>Comprehensive Documentation</h2>
              <p>
                Access full technical specifications, installation guides for local evaluators, and API references for all supported frameworks.
              </p>
              <div className="landing-actions">
                <button type="button" className="secondary">View Docs</button>
                <button type="button" className="secondary">CLI Reference</button>
              </div>
            </div>
          </article>
        </div>

        <div className="credits-side-stack">
          <article className="credits-card">
            <h2>Compute Credits</h2>
            <p>Simulations accelerated via NVIDIA cuQuantum on A100 GPU clusters provided by Research Lab Theta.</p>
            <div className="credits-status">ACCELERATION ACTIVE</div>
          </article>

          <article className="credits-card">
            <h2>Visualization &amp; UI</h2>
            <div className="viz-list">
              <div><span>Three.js</span><strong>3D VIZ</strong></div>
              <div><span>Tailwind CSS</span><strong>STYLING</strong></div>
              <div><span>D3.js</span><strong>GRAPH_OPS</strong></div>
              <div><span>JetBrains Mono</span><strong>TYPEFACE</strong></div>
            </div>
          </article>

          <article className="credits-card credits-contributor-card">
            <h3>Contributor Program</h3>
            <p>Want to list your framework? Submit a PR to our research manifest.</p>
            <button type="button">Apply Integration</button>
          </article>
        </div>
      </section>
    </main>
  );
}

export function App() {
  const [view, setView] = useState<AppView>(() => resolveViewFromHash(window.location.hash));
  const [toolView, setToolView] = useState<ToolView>(() => resolveToolViewFromHash(window.location.hash));
  const [qasm, setQasm] = useState(defaultQasm);
  const [targetConfig, setTargetConfig] = useState<TargetConfig>(defaultTargetConfig);
  const [selectedModality, setSelectedModality] = useState<ModalityKey>(defaultModality);
  const compilerBackend: CompilerBackend = "auto";
  const [resourceEstimator, setResourceEstimator] = useState<ResourceEstimator>("native_qre");
  const [estimationProfiles, setEstimationProfiles] = useState<EstimationProfiles>(() => cloneEstimationProfiles());
  const [resourceCapabilities, setResourceCapabilities] = useState<ResourceCapabilities>();
  const [architecturePresets, setArchitecturePresets] = useState<ArchitecturePreset[]>([]);
  const [showAdvancedArchitecture, setShowAdvancedArchitecture] = useState(false);
  const [modalitySettings, setModalitySettings] = useState(() => cloneModalitySettings(defaultModality));
  const [circuitSummary, setCircuitSummary] = useState<CircuitSummary>();
  const [circuitPreview, setCircuitPreview] = useState<CircuitPreview>();
  const [targetPreview, setTargetPreview] = useState<TargetPreview>();
  const [runResult, setRunResult] = useState<TranspileResponse>();
  const [status, setStatus] = useState<WorkStatus>("idle");
  const [message, setMessage] = useState<string>();
  const [validateState, setValidateState] = useState<ActionState>("idle");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const metrics = asRecord(runResult?.metrics);
  const logicalCounts = asRecord(metrics.logical_counts);
  const physicalCounts = asRecord(metrics.physical_counts);
  const breakdown = asRecord(physicalCounts.breakdown);
  const qreAssumptions = asRecord(metrics.qre_assumptions);
  const routingArtifacts = asRecord(runResult?.artifacts);
  const reproducibleExport = asRecord(routingArtifacts.reproducible_run_export);
  const reportData = asRecord(metrics.report_data);
  const translationNotes = asStringArray(qreAssumptions.translation_notes);
  const selectedArchitectureId = String(targetConfig.architecture_preset ?? defaultTargetConfig.architecture_preset ?? "");
  const selectedArchitecture = architecturePresets.find((preset) => preset.id === selectedArchitectureId);
  const architectureMetadata = asRecord(targetConfig.architecture_metadata);
  const architectureLimitations = asStringArray(targetPreview?.architecture_limitations ?? architectureMetadata.limitations ?? selectedArchitecture?.limitations);
  const architectureReferences = asStringArray(architectureMetadata.references ?? selectedArchitecture?.references);
  const architectureSupportStatus = String(architectureMetadata.support_status ?? selectedArchitecture?.support_status ?? "supported");
  const architectureIsUnsupported = architectureSupportStatus === "unsupported";
  const canShowSidebarRunAction =
    (toolView === "estimation" || toolView === "results") &&
    qasm.trim().length > 0 &&
    selectedArchitectureId.length > 0 &&
    !!selectedArchitecture &&
    !!resourceCapabilities &&
    !architectureIsUnsupported;
  const inferredModality = modalityForPreset(selectedArchitecture);
  const interpretation = buildInterpretation({ runResult, physicalCounts, logicalCounts, qreAssumptions });

  useEffect(() => {
    function syncViewFromHash() {
      setView(resolveViewFromHash(window.location.hash));
      setToolView(resolveToolViewFromHash(window.location.hash));
    }
    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  useEffect(() => {
    setValidateState("idle");
    setCircuitSummary(undefined);
    setCircuitPreview(undefined);
  }, [qasm]);

  useEffect(() => {
    fetchResourceCapabilities().then(setResourceCapabilities).catch(() => setResourceCapabilities(undefined));
  }, []);

  useEffect(() => {
    fetchArchitectureCapabilities()
      .then((payload) => {
        setArchitecturePresets(payload.architectures);
        const initialPreset = payload.architectures.find((preset) => preset.id === targetConfig.architecture_preset) ?? payload.architectures[0];
        if (initialPreset) {
          applyArchitecturePreset(initialPreset.id, payload.architectures);
        }
      })
      .catch(() => setArchitecturePresets([]));
  }, []);

  function updateTopology(key: string, value: string | number) {
    setTargetConfig((current) => ({
      ...current,
      topology: {
        ...current.topology,
        [key]: value,
      },
    }));
  }

  function applyArchitecturePreset(presetId: string, presets = architecturePresets) {
    const preset = presets.find((entry) => entry.id === presetId);
    if (!preset) {
      return;
    }
    const nextModality = modalityForPreset(preset);
    const nextSettings = cloneModalitySettings(nextModality);
    const nextHardwareModel = hardwareModelForPreset(preset);
    setSelectedModality(nextModality);
    setModalitySettings(nextSettings);
    setTargetConfig(clonePresetConfig(preset));
    setEstimationProfiles((current) => ({
      ...current,
      physical_hardware: {
        ...current.physical_hardware,
        qdk_hardware_model: nextHardwareModel,
        physical_modality: nextHardwareModel,
      },
    }));
    setTargetPreview(undefined);
    setRunResult(undefined);
  }

  function updateModalitySetting(key: string, value: number) {
    const next = { ...modalitySettings, [key]: value };
    setModalitySettings(next);
    setTargetConfig((config) => ({
      ...config,
      profile: buildProfile(selectedModality, next),
    }));
    setTargetPreview(undefined);
    setRunResult(undefined);
  }

  function updateProfileSection(section: keyof EstimationProfiles, key: string, value: unknown) {
    setEstimationProfiles((current) => ({
      ...current,
      [section]: {
        ...(current[section] ?? {}),
        [key]: value,
      },
    }));
    setRunResult(undefined);
  }

  function updateQecModelSource(value: string) {
    setEstimationProfiles((current) => ({
      ...current,
      qec: {
        ...current.qec,
        qec_model_source: value,
        qec_model_parameters: value === "custom" ? current.qec.qec_model_parameters ?? {} : {},
      },
    }));
    setRunResult(undefined);
  }

  function updateQecModelName(value: QecModelKey) {
    setEstimationProfiles((current) => ({
      ...current,
      qec: {
        ...current.qec,
        qec_scheme: value,
        qec_model_name: value,
        qec_model_parameters: {},
      },
    }));
    setRunResult(undefined);
  }

  function updateQecModelParameter(key: string, value: unknown) {
    setEstimationProfiles((current) => ({
      ...current,
      qec: {
        ...current.qec,
        qec_model_parameters: {
          ...asRecord(current.qec.qec_model_parameters),
          [key]: value,
        },
      },
    }));
    setRunResult(undefined);
  }

  function updatePhysicalProfileMode(value: string) {
    setEstimationProfiles((current) => ({
      ...current,
      physical_hardware: {
        ...current.physical_hardware,
        physical_profile_mode: value,
      },
    }));
    setRunResult(undefined);
  }

  function updateHardwareModel(value: string) {
    const defaults = resourceCapabilities?.physical_hardware.verified_builtin_models.find((model) => model.key === value)?.defaults ?? {};
    setEstimationProfiles((current) => ({
      ...current,
      physical_hardware: {
        ...current.physical_hardware,
        ...defaults,
        physical_profile_mode: current.physical_hardware.physical_profile_mode ?? "built_in",
        qdk_hardware_model: value,
      },
    }));
    setRunResult(undefined);
  }

  async function handleCircuitFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setStatus("loading");
    setMessage(`Loading ${file.name}`);
    try {
      const content = await file.text();
      const nextQasm = parseCircuitFileContent(file.name, content);
      setQasm(nextQasm);
      setRunResult(undefined);
      setTargetPreview(undefined);
      setStatus("ready");
      setMessage(`Loaded ${file.name}`);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Failed to load circuit file");
    } finally {
      event.target.value = "";
    }
  }

  async function handleValidate() {
    setStatus("loading");
    setMessage("Validating circuit");
    setValidateState("loading");
    try {
      const preview = await validateCircuit(qasm);
      setCircuitPreview(preview);
      setCircuitSummary(preview);
      setStatus("ready");
      setMessage("Circuit validated");
      setValidateState("success");
    } catch (error) {
      setCircuitSummary(undefined);
      setCircuitPreview(undefined);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Circuit validation failed");
      setValidateState("error");
    }
  }

  async function handlePreview() {
    if (architectureIsUnsupported) {
      setStatus("error");
      setMessage("This architecture is documented as unsupported and cannot be previewed or compiled yet.");
      return;
    }
    setStatus("loading");
    setMessage("Building target");
    try {
      const preview = await previewTarget(targetConfig);
      setTargetPreview(preview);
      setStatus("ready");
      setMessage("Target ready");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Target preview failed");
    }
  }

  async function handleRun() {
    if (architectureIsUnsupported) {
      setStatus("error");
      setMessage("This architecture is documented as unsupported and cannot be compiled yet.");
      return;
    }
    setStatus("loading");
    setMessage("Running compilation and resource estimation");
    try {
      const result = await transpileCircuit(qasm, targetConfig, compilerBackend, resourceEstimator, cleanOptionalProfileFields(estimationProfiles));
      setCircuitSummary(result.original);
      setRunResult(result);
      setStatus("ready");
      setMessage("Run complete");
      window.location.hash = "results";
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Compilation failed");
    }
  }

  function resetDefaults() {
    setQasm("");
    const defaultPreset = architecturePresets.find((preset) => preset.id === defaultTargetConfig.architecture_preset);
    if (defaultPreset) {
      applyArchitecturePreset(defaultPreset.id);
    } else {
      setTargetConfig(cloneConfig(defaultTargetConfig));
      setSelectedModality(defaultModality);
    }
    setResourceEstimator("native_qre");
    setEstimationProfiles(cloneEstimationProfiles());
    setModalitySettings(cloneModalitySettings(defaultModality));
    setCircuitSummary(undefined);
    setCircuitPreview(undefined);
    setTargetPreview(undefined);
    setRunResult(undefined);
    setStatus("idle");
    setMessage(undefined);
    setValidateState("idle");
    window.location.hash = "circuit";
  }

  function handleDownloadRunExport() {
    if (!runResult || Object.keys(reproducibleExport).length === 0) {
      return;
    }
    const runId = String(reproducibleExport.run_id ?? "run");
    downloadJson(`${runId}_qre_export.json`, reproducibleExport);
  }

  if (view === "landing") {
    return (
        <>
        <TopToolbar view={view} />
        <LandingPage />
        <AppFooter view={view} />
      </>
    );
  }
  if (view === "credits") {
    return (
        <>
        <TopToolbar view={view} />
        <CreditsPage />
        <AppFooter view={view} />
      </>
    );
  }
  if (view === "guide") {
    return (
        <>
        <TopToolbar view={view} />
        <GuidePage />
        <AppFooter view={view} />
      </>
    );
  }

  return (
    <>
      <TopToolbar view={view} />
      <ToolShell
        stages={[
          { id: "circuit", label: "Stage 1", title: "Circuit input" },
          { id: "architecture", label: "Stage 2", title: "Architecture and compiler" },
          { id: "estimation", label: "Stage 3", title: "Estimation profile" },
          { id: "results", label: "Stage 4", title: "Results" },
        ]}
        activeStage={toolView}
        runAction={canShowSidebarRunAction ? (
          <button type="button" onClick={handleRun} disabled={status === "loading"}>
            <Play aria-hidden="true" /> Run evaluation
          </button>
        ) : null}
        secondaryAction={
          <button type="button" className="secondary" onClick={resetDefaults}>
            <RotateCcw aria-hidden="true" /> Reset
          </button>
        }
      >
        <header className="app-header tool-header-panel">
          <div>
            <SectionLabel>Research workflow</SectionLabel>
            <h1>Architecture-aware compilation workspace</h1>
            <p>{message ?? "Configure the circuit, target, and estimation profile, then run the compilation and resource-estimation flow one checkpoint at a time."}</p>
          </div>
        </header>
        {status === "error" && message && !(toolView === "circuit" && validateState === "error") ? (
          <div className="tool-feedback tool-feedback-error">{message}</div>
        ) : null}
        {toolView === "circuit" ? (
          <CircuitStage
            qasm={qasm}
            onQasmChange={setQasm}
            summary={circuitSummary}
            circuitPreview={circuitPreview}
            validateState={validateState}
            status={status}
            fileInputRef={fileInputRef}
            onFileSelected={handleCircuitFileSelected}
            onValidate={handleValidate}
            canProceed={validateState === "success"}
            onProceed={() => (window.location.hash = "architecture")}
          />
        ) : null}

        {toolView === "architecture" ? (
          <ArchitectureStage
            architecturePresets={architecturePresets}
            selectedArchitectureId={selectedArchitectureId}
            selectedArchitecture={selectedArchitecture}
            selectedModality={selectedModality}
            inferredModality={inferredModality}
            modalitySettings={modalitySettings}
            targetConfig={targetConfig}
            targetPreview={targetPreview}
            showAdvancedArchitecture={showAdvancedArchitecture}
            resourceEstimator={resourceEstimator}
            architectureIsUnsupported={architectureIsUnsupported}
            architectureLimitations={architectureLimitations}
            status={status}
            onApplyArchitecturePreset={applyArchitecturePreset}
            onSetResourceEstimator={setResourceEstimator}
            onToggleAdvanced={() => setShowAdvancedArchitecture((current) => !current)}
            onHandlePreview={handlePreview}
            onRun={handleRun}
            onUpdateTopology={updateTopology}
            onUpdateModalitySetting={updateModalitySetting}
            onSetTargetConfig={setTargetConfig}
            onProceed={() => (window.location.hash = "estimation")}
            referenceUrl={referenceUrl}
            formatReferenceLabel={formatReferenceLabel}
          />
        ) : null}

        {toolView === "estimation" ? (
          <EstimationStage
            resourceCapabilities={resourceCapabilities}
            estimationProfiles={estimationProfiles}
            status={status}
            onUpdateProfileSection={updateProfileSection}
            onUpdateQecModelSource={updateQecModelSource}
            onUpdateQecModelName={updateQecModelName}
            onUpdateQecModelParameter={updateQecModelParameter}
            onUpdatePhysicalProfileMode={updatePhysicalProfileMode}
            onUpdateHardwareModel={updateHardwareModel}
            onRun={handleRun}
            onProceed={() => (window.location.hash = "results")}
          />
        ) : null}

        {toolView === "results" ? (
          <ResultsStage
            runResult={runResult}
            metrics={metrics}
            logicalCounts={logicalCounts}
            physicalCounts={physicalCounts}
            breakdown={breakdown}
            qreAssumptions={qreAssumptions}
            routingArtifacts={routingArtifacts}
            reportData={reportData}
            translationNotes={translationNotes}
            selectedArchitectureName={selectedArchitecture?.display_name}
            selectedArchitectureId={selectedArchitectureId}
            architectureSupportStatus={architectureSupportStatus}
            architectureReferences={architectureReferences}
            architectureLimitations={architectureLimitations}
            reproducibleExport={reproducibleExport}
            interpretation={interpretation}
            status={status}
            compiledCircuitPreview={runResult?.artifacts?.compiled_circuit_preview}
            onRun={handleRun}
            onDownloadRunExport={handleDownloadRunExport}
          />
        ) : null}
      </ToolShell>
      <AppFooter view={view} status={status} message={message} />
    </>
  );
}
