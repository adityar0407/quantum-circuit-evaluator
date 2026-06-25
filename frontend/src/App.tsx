import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowRight, Binary, CheckCircle2, ChevronRight, FileUp, Play, RefreshCw, RotateCcw, Settings2, Target } from "lucide-react";
import { previewTarget, transpileCircuit, validateCircuit } from "./api/client";
import type {
  CircuitSummary,
  CompilerBackend,
  ResourceEstimator,
  TargetConfig,
  TargetPreview,
  TranspileResponse,
} from "./api/types";
import {
  buildProfile,
  cloneModalitySettings,
  defaultModality,
  defaultQasm,
  defaultTargetConfig,
  modalityPresets,
  type ModalityKey,
  type ModalitySettings,
} from "./state/defaults";

type WorkStatus = "idle" | "loading" | "ready" | "error";
type GateGroup = "sq_gates" | "two_q_gates" | "inter_device_gates";
type AppView = "landing" | "credits" | "tool";
type ActionState = "idle" | "loading" | "success" | "error";

const compilerLabels: Record<CompilerBackend, string> = {
  auto: "Automatic routing",
  qiskit_ftarget: "Qiskit FTarget",
  pandora: "Pandora",
};

const estimatorLabels: Record<ResourceEstimator, string> = {
  simple_logical: "Legacy alias",
  azure_qre: "Azure QRE",
};

const topologyLabels: Record<string, string> = {
  tiled_k_nearest: "Distributed Logical Tile",
  heavy_hex: "IBM Heavy Hex",
  heavy_square: "IBM Heavy Square",
  custom_coupling_map: "Custom Coupling Map",
};

function displayTopology(value: unknown): string {
  const key = String(value ?? "");
  return topologyLabels[key] ?? key;
}

function cloneConfig(config: TargetConfig): TargetConfig {
  return JSON.parse(JSON.stringify(config)) as TargetConfig;
}

function getProfileGroup(config: TargetConfig, group: GateGroup): Record<string, Record<string, number>> {
  return (config.profile[group] ?? {}) as Record<string, Record<string, number>>;
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

function formatDuration(value: unknown): string {
  if (typeof value !== "number") {
    return formatNumber(value);
  }
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(2)} s`;
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(2)} ms`;
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(2)} us`;
  }
  return `${formatNumber(value)} ns`;
}

function humanizeKey(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function renderDetailValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return formatNumber(value);
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
    } catch (error) {
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

function SurfaceMetric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: unknown;
  tone?: "default" | "emphasis" | "signal";
}) {
  return (
    <article className={`surface-metric tone-${tone}`}>
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </article>
  );
}

function SectionLabel({ children }: { children: string }) {
  return <p className="section-label">{children}</p>;
}

function resolveViewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, "");
  if (key === "credits") {
    return "credits";
  }
  if (["tool", "circuit", "architecture", "preview", "results"].includes(key)) {
    return "tool";
  }
  return "landing";
}

function goToTool(section = "tool") {
  window.location.hash = section;
}

function goToLanding() {
  window.location.hash = "home";
}

function goToCredits() {
  window.location.hash = "credits";
}

function TopToolbar({ view }: { view: AppView }) {
  return (
    <header className="top-toolbar">
      <div className="top-toolbar-inner">
        <button type="button" className="toolbar-brand" onClick={goToLanding}>
          <Binary aria-hidden="true" />
          <span>Quantum Circuit Evaluator</span>
        </button>
        <nav className="top-toolbar-nav" aria-label="Primary">
          <a href="#home" className={view === "landing" ? "active" : undefined}>
            Home
          </a>
          <a href="#credits" className={view === "credits" ? "active" : undefined}>
            Credits
          </a>
          <a href="#tool" className={view === "tool" ? "active" : undefined}>
            Tool
          </a>
        </nav>
      </div>
    </header>
  );
}

function LandingPage() {
  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <SectionLabel>Quantum circuit compilation and resource estimation</SectionLabel>
          <h1>Understand what compilation changed, what fault-tolerant resources it costs, and which assumptions drive the result.</h1>
          <p>
            Quantum Circuit Evaluator is a local research workspace for importing OpenQASM circuits, compiling them
            against logical architecture assumptions, routing larger workloads through Pandora, and estimating
            downstream fault-tolerant resources through Azure QRE.
          </p>
          <div className="landing-actions">
            <button type="button" onClick={() => goToTool()}>
              Open tool <ArrowRight aria-hidden="true" />
            </button>
            <button type="button" className="secondary" onClick={goToCredits}>
              View credits
            </button>
          </div>
        </div>

        <div className="landing-hero-panel">
          <SectionLabel>What this tool is for</SectionLabel>
          <div className="landing-points">
            <article>
              <strong>Inspect the circuit</strong>
              <p>Load OpenQASM, validate it, and inspect the workload before any transformation is applied.</p>
            </article>
            <article>
              <strong>Compile under assumptions</strong>
              <p>Compile against FTarget-defined logical architectures with automatic routing between Qiskit and Pandora.</p>
            </article>
            <article>
              <strong>Estimate fault-tolerant cost</strong>
              <p>Translate the compiled circuit into Azure QRE inputs so users can read physical qubits, runtime, RQOps, and key bottlenecks under a chosen target model.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-section-header">
          <div>
            <SectionLabel>Workflow</SectionLabel>
            <h2>From circuit input to architecture-aware estimate</h2>
          </div>
        </div>
        <div className="landing-flow">
          <article><strong>1.</strong><span>Import and validate a circuit</span></article>
          <article><strong>2.</strong><span>Configure topology, modality, and logical gate assumptions</span></article>
          <article><strong>3.</strong><span>Compile through Qiskit FTarget or Pandora based on workload size</span></article>
          <article><strong>4.</strong><span>Translate the compiled workload into Azure QRE estimation inputs</span></article>
          <article><strong>5.</strong><span>Interpret resource counts, bottlenecks, routing artifacts, and assumption sensitivity</span></article>
        </div>
      </section>

      <section className="landing-footer-cta">
        <div>
          <SectionLabel>Start analysis</SectionLabel>
          <h2>Open the workspace and run the pipeline.</h2>
        </div>
        <button type="button" onClick={() => goToTool()}>
          Go to tool <ArrowRight aria-hidden="true" />
        </button>
      </section>
    </main>
  );
}

function CreditsPage() {
  return (
    <main className="landing-shell">
      <section className="landing-section">
        <div className="landing-section-header">
          <div>
            <SectionLabel>Integrated stack</SectionLabel>
            <h2>Credits and open-source components</h2>
          </div>
        </div>
        <div className="credits-grid">
          <article className="credit-card">
            <h3>FTarget</h3>
            <p>The core target-modeling layer in this repository. It defines logical architectures, connectivity, gate properties, and the target assumptions used during compilation.</p>
          </article>
          <article className="credit-card">
            <h3>Qiskit</h3>
            <p>Used for circuit parsing, target-aware transpilation, pass management, and the Qiskit-compatible target abstraction behind FTarget.</p>
          </article>
          <article className="credit-card">
            <h3>Pandora</h3>
            <p>Integrated here as the large-circuit optimization backend. Larger workloads are routed through Pandora for translation and conservative rewrite optimization.</p>
          </article>
          <article className="credit-card">
            <h3>Azure QRE / Microsoft QDK</h3>
            <p>Used as the resource-estimation layer. Compiled circuits are translated into Azure Quantum Resource Estimator inputs so FTarget assumptions can be interpreted through a fault-tolerant physical model.</p>
          </article>
          <article className="credit-card">
            <h3>FastAPI</h3>
            <p>Provides the local backend API used by the frontend for validation, target preview, compilation, and estimation requests.</p>
          </article>
          <article className="credit-card">
            <h3>React, Vite, and Lucide</h3>
            <p>Power the local frontend workspace, build tooling, and icon system for the interface you use to configure and inspect runs.</p>
          </article>
          <article className="credit-card">
            <h3>NetworkX and Rustworkx</h3>
            <p>Support graph-oriented target and connectivity modeling used throughout the architecture and transpilation flow.</p>
          </article>
          <article className="credit-card">
            <h3>Matplotlib and related scientific Python tooling</h3>
            <p>Support technical rendering and scientific computation inside the backend environment where target construction and supporting analysis occur.</p>
          </article>
        </div>
      </section>
    </main>
  );
}

function OperationList({ counts }: { counts?: Record<string, number> }) {
  const entries = Object.entries(counts ?? {});

  if (!entries.length) {
    return <div className="chip-list-empty">No operations loaded</div>;
  }

  return (
    <div className="chip-list">
      {entries.map(([name, count]) => (
        <span key={name}>
          {name}
          <strong>{count}</strong>
        </span>
      ))}
    </div>
  );
}

function DetailBlock({
  title,
  values,
}: {
  title: string;
  values: Record<string, unknown>;
}) {
  const entries = Object.entries(values).filter(([, value]) => value !== undefined && value !== null && value !== "");

  return (
    <section className="detail-block">
      <h4>{title}</h4>
      {!entries.length ? (
        <p className="detail-empty">No data available.</p>
      ) : (
        <dl className="detail-list">
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt>{humanizeKey(key)}</dt>
              <dd>{renderDetailValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function SummaryStrip({ summary }: { summary?: CircuitSummary }) {
  return (
    <div className="summary-strip">
      <SurfaceMetric label="Qubits" value={summary?.num_qubits ?? "-"} />
      <SurfaceMetric label="Classical bits" value={summary?.num_clbits ?? "-"} />
      <SurfaceMetric label="Depth" value={summary?.depth ?? "-"} />
      <SurfaceMetric label="Gate count" value={summary?.gate_count ?? "-"} />
    </div>
  );
}

function SessionStateStrip({ status, message }: { status: WorkStatus; message?: string | null }) {
  return (
    <div className="session-state-strip">
      <div className="session-state-copy">
        <SectionLabel>Session state</SectionLabel>
        <strong>{status}</strong>
        <span>{message ?? "Idle"}</span>
      </div>
      <div className="status-chip-row">
        <span>{status}</span>
        <span>{message ?? "Idle"}</span>
      </div>
    </div>
  );
}

function NumericField({
  label,
  value,
  min = 1,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(event) => onChange(asNumber(event.target.value, min))}
      />
    </label>
  );
}

function GateTable({
  title,
  group,
  config,
  onChange,
}: {
  title: string;
  group: GateGroup;
  config: TargetConfig;
  onChange: (config: TargetConfig) => void;
}) {
  const gates = getProfileGroup(config, group);
  const entries = Object.entries(gates);
  const fields =
    group === "sq_gates"
      ? ["error", "duration"]
      : group === "two_q_gates"
        ? ["local_error", "local_duration"]
        : ["inter_error", "inter_duration"];

  function updateGate(gateName: string, field: string, value: number) {
    const next = cloneConfig(config);
    const nextGroup = getProfileGroup(next, group);
    nextGroup[gateName][field] = value;
    next.profile[group] = nextGroup;
    onChange(next);
  }

  return (
    <section className="gate-card">
      <SectionLabel>{title}</SectionLabel>
      <div className="gate-table">
        <div className="gate-row header">
          <span>Gate</span>
          {fields.map((field) => (
            <span key={field}>{field.replace("_", " ")}</span>
          ))}
        </div>
        {entries.map(([gateName, values]) => (
          <div className="gate-row" key={gateName}>
            <span className="gate-name">{gateName}</span>
            {fields.map((field) => (
              <input
                key={field}
                aria-label={`${gateName} ${field}`}
                type="number"
                step="any"
                min="0"
                value={values[field]}
                onChange={(event) => updateGate(gateName, field, asNumber(event.target.value))}
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

function TargetGraph({ preview }: { preview?: TargetPreview }) {
  const graph = useMemo(() => {
    if (!preview || !preview.nodes.length) {
      return null;
    }

    const fallbackRadius = 120;
    const nodes = preview.nodes.map((node, index) => {
      if (typeof node.x === "number" && typeof node.y === "number") {
        return { ...node, x: node.x, y: node.y };
      }
      const angle = (index / preview.nodes.length) * Math.PI * 2;
      return {
        ...node,
        x: Math.cos(angle) * fallbackRadius,
        y: Math.sin(angle) * fallbackRadius,
      };
    });

    const xs = nodes.map((node) => node.x);
    const ys = nodes.map((node) => node.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const width = Math.max(maxX - minX, 1);
    const height = Math.max(maxY - minY, 1);
    const padding = Math.max(width, height) * 0.12 + 2;

    return {
      nodes,
      nodeById: new Map(nodes.map((node) => [node.id, node])),
      viewBox: `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`,
    };
  }, [preview]);

  if (!preview || !graph) {
    return <div className="graph-empty">Preview the target to inspect the architecture graph.</div>;
  }

  return (
    <svg className="target-graph" viewBox={graph.viewBox} role="img" aria-label="Target coupling graph">
      {preview.edges.map((edge, index) => {
        const source = graph.nodeById.get(edge.source);
        const target = graph.nodeById.get(edge.target);
        if (!source || !target) {
          return null;
        }
        return (
          <line
            key={`${edge.source}-${edge.target}-${index}`}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            className={edge.local ? "edge-local" : "edge-network"}
          />
        );
      })}
      {graph.nodes.map((node) => (
        <circle key={node.id} cx={node.x} cy={node.y} r="0.95" className={`node block-${node.block % 6}`} />
      ))}
    </svg>
  );
}

export function App() {
  const [view, setView] = useState<AppView>(() => resolveViewFromHash(window.location.hash));
  const [qasm, setQasm] = useState(defaultQasm);
  const [targetConfig, setTargetConfig] = useState<TargetConfig>(defaultTargetConfig);
  const [selectedModality, setSelectedModality] = useState<ModalityKey>(defaultModality);
  const compilerBackend: CompilerBackend = "auto";
  const [resourceEstimator, setResourceEstimator] = useState<ResourceEstimator>("azure_qre");
  const [modalitySettings, setModalitySettings] = useState<ModalitySettings>(() =>
    cloneModalitySettings(defaultModality),
  );
  const [circuitSummary, setCircuitSummary] = useState<CircuitSummary>();
  const [targetPreview, setTargetPreview] = useState<TargetPreview>();
  const [runResult, setRunResult] = useState<TranspileResponse>();
  const [status, setStatus] = useState<WorkStatus>("idle");
  const [message, setMessage] = useState<string>();
  const [validateState, setValidateState] = useState<ActionState>("idle");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const topology = targetConfig.topology;
  const metrics = asRecord(runResult?.metrics);
  const logicalCounts = asRecord(metrics.logical_counts);
  const physicalCounts = asRecord(metrics.physical_counts);
  const breakdown = asRecord(physicalCounts.breakdown);
  const qreAssumptions = asRecord(metrics.qre_assumptions);
  const routingArtifacts = asRecord(runResult?.artifacts);
  const reportData = asRecord(metrics.report_data);
  const translationNotes = asStringArray(qreAssumptions.translation_notes);

  const interpretation = buildInterpretation({
    runResult,
    physicalCounts,
    logicalCounts,
    qreAssumptions,
  });

  useEffect(() => {
    function syncViewFromHash() {
      setView(resolveViewFromHash(window.location.hash));
    }

    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  useEffect(() => {
    setValidateState("idle");
    setCircuitSummary(undefined);
  }, [qasm]);

  function updateTopology(key: string, value: string | number) {
    setTargetConfig((current) => ({
      ...current,
      topology: {
        ...current.topology,
        [key]: value,
      },
    }));
  }

  function applyModality(value: ModalityKey) {
    const nextSettings = cloneModalitySettings(value);
    setSelectedModality(value);
    setModalitySettings(nextSettings);
    setTargetConfig((current) => ({
      ...current,
      profile: buildProfile(value, nextSettings),
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
      const summary = await validateCircuit(qasm);
      setCircuitSummary(summary);
      setStatus("ready");
      setMessage("Circuit loaded");
      setValidateState("success");
    } catch (error) {
      setCircuitSummary(undefined);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Circuit validation failed");
      setValidateState("error");
    }
  }

  async function handlePreview() {
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
    setStatus("loading");
    setMessage("Running compilation and resource estimation");
    try {
      const result = await transpileCircuit(qasm, targetConfig, compilerBackend, resourceEstimator);
      setCircuitSummary(result.original);
      setRunResult(result);
      setStatus("ready");
      setMessage("Run complete");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Compilation failed");
    }
  }

  function resetDefaults() {
    setQasm(defaultQasm);
    setTargetConfig(cloneConfig(defaultTargetConfig));
    setSelectedModality(defaultModality);
    setResourceEstimator("azure_qre");
    setModalitySettings(cloneModalitySettings(defaultModality));
    setCircuitSummary(undefined);
    setTargetPreview(undefined);
    setRunResult(undefined);
    setStatus("idle");
    setMessage(undefined);
  }

  if (view === "landing") {
    return (
      <>
        <TopToolbar view={view} />
        <LandingPage />
      </>
    );
  }

  if (view === "credits") {
    return (
      <>
        <TopToolbar view={view} />
        <CreditsPage />
      </>
    );
  }

  return (
    <>
      <TopToolbar view={view} />
      <main className="workspace-shell">
      <section className="workspace-main">
        <header className="app-header">
          <div>
            <SectionLabel>Quantum circuit compilation and estimation</SectionLabel>
            <h1>Quantum Circuit Evaluator</h1>
            <p>{message ?? "Configure the circuit, target, and estimator, then run the analysis."}</p>
          </div>
          <div className="app-toolbar">
            <button type="button" className="secondary" onClick={resetDefaults}>
              <RotateCcw aria-hidden="true" /> Reset
            </button>
            <button type="button" onClick={handleRun} disabled={status === "loading"}>
              <Play aria-hidden="true" /> Run analysis
            </button>
          </div>
        </header>

        <SessionStateStrip status={status} message={message} />

        <section id="circuit" className="workspace-section">
          <div className="section-header">
            <div>
              <SectionLabel>Stage 1</SectionLabel>
              <h2>Circuit intake and inspection</h2>
            </div>
            <div className="section-actions">
              <input
                ref={fileInputRef}
                className="visually-hidden"
                type="file"
                accept=".qasm,.json,application/json,text/plain"
                onChange={handleCircuitFileSelected}
              />
              <button
                type="button"
                className="secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={status === "loading"}
              >
                <FileUp aria-hidden="true" /> Upload circuit
              </button>
              <button
                type="button"
                className={`secondary action-button state-${validateState}`}
                onClick={handleValidate}
                disabled={status === "loading"}
              >
                <CheckCircle2 aria-hidden="true" /> Validate
              </button>
            </div>
          </div>

          <div className="section-grid single">
            <article className="surface-card technical-card">
              <SectionLabel>OpenQASM input</SectionLabel>
              <textarea
                className="qasm-editor"
                aria-label="OpenQASM circuit input"
                spellCheck={false}
                value={qasm}
                onChange={(event) => setQasm(event.target.value)}
              />
              <p className="field-hint">Upload a `.qasm` file directly, or a `.json` file containing an OpenQASM string.</p>
            </article>

            <article className="surface-card">
              <SectionLabel>Circuit summary</SectionLabel>
              <SummaryStrip summary={circuitSummary} />
              <div className="subsection-block">
                <h4>Operation counts</h4>
                <OperationList counts={circuitSummary?.operation_counts} />
              </div>
            </article>
          </div>
        </section>

        <section id="architecture" className="workspace-section">
          <div className="section-header">
            <div>
              <SectionLabel>Stage 2</SectionLabel>
              <h2>Architecture and logical assumptions</h2>
            </div>
            <button type="button" className="secondary" onClick={handlePreview} disabled={status === "loading"}>
              <RefreshCw aria-hidden="true" /> Preview target
            </button>
          </div>

          <div className="section-grid single">
            <article className="surface-card">
              <SectionLabel>Target controls</SectionLabel>
              <div className="form-grid">
                <label className="field">
                  <span>Topology</span>
                  <select
                    value={String(topology.type ?? "tiled_k_nearest")}
                    onChange={(event) => updateTopology("type", event.target.value)}
                  >
                    <option value="tiled_k_nearest">Distributed Logical Tile</option>
                    <option value="heavy_hex">IBM Heavy Hex</option>
                    <option value="heavy_square">IBM Heavy Square</option>
                  </select>
                </label>
                <label className="field">
                  <span>Modality</span>
                  <select
                    value={selectedModality}
                    onChange={(event) => applyModality(event.target.value as ModalityKey)}
                  >
                    {Object.entries(modalityPresets).map(([key, preset]) => (
                      <option key={key} value={key}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="field static-field">
                  <span>Compiler route</span>
                  <strong>Automatic</strong>
                </div>
                <label className="field">
                  <span>Estimator</span>
                  <select
                    value={resourceEstimator}
                    onChange={(event) => {
                      setResourceEstimator(event.target.value as ResourceEstimator);
                      setRunResult(undefined);
                    }}
                  >
                    <option value="azure_qre">Azure QRE</option>
                    <option value="simple_logical">Legacy alias</option>
                  </select>
                </label>
                <NumericField
                  label="Block rows"
                  value={asNumber(topology.n_blocks_row, 1)}
                  onChange={(value) => updateTopology("n_blocks_row", value)}
                />
                <NumericField
                  label="Block columns"
                  value={asNumber(topology.n_blocks_col, 1)}
                  onChange={(value) => updateTopology("n_blocks_col", value)}
                />
                {topology.type === "tiled_k_nearest" ? (
                  <>
                    <NumericField label="n" value={asNumber(topology.n, 1)} onChange={(value) => updateTopology("n", value)} />
                    <NumericField label="m" value={asNumber(topology.m, 1)} onChange={(value) => updateTopology("m", value)} />
                    <NumericField
                      label="k intra"
                      value={asNumber(topology.k_intra, 1)}
                      onChange={(value) => updateTopology("k_intra", value)}
                    />
                    <NumericField
                      label="k inter"
                      value={asNumber(topology.k_inter, 1)}
                      onChange={(value) => updateTopology("k_inter", value)}
                    />
                    <NumericField
                      label="connector local"
                      value={asNumber(topology.connector_local, 1)}
                      onChange={(value) => updateTopology("connector_local", value)}
                    />
                  </>
                ) : (
                  <>
                    <NumericField label="Distance" value={asNumber(topology.d, 3)} onChange={(value) => updateTopology("d", value)} />
                    <NumericField
                      label="k inter"
                      value={asNumber(topology.k_inter, 1)}
                      onChange={(value) => updateTopology("k_inter", value)}
                    />
                  </>
                )}
              </div>

              <div className="insight-strip">
                <div className="inline-note">
                  <Settings2 aria-hidden="true" />
                  <p>
                    FTarget currently describes a logical architecture profile. QRE injects a physical QEC layer
                    when estimating downstream resources.
                  </p>
                </div>
              </div>
            </article>

            <article className="surface-card">
              <SectionLabel>Modality configuration</SectionLabel>
              <p className="body-copy">{modalityPresets[selectedModality].description}</p>
              <div className="form-grid">
                {modalityPresets[selectedModality].fields.map((field) => (
                  <NumericField
                    key={field.key}
                    label={field.label}
                    value={asNumber(modalitySettings[field.key], field.min ?? 0)}
                    min={field.min ?? 0}
                    step={field.step}
                    onChange={(value) => updateModalitySetting(field.key, value)}
                  />
                ))}
              </div>
            </article>

            <div className="gate-grid">
              <GateTable title="Single qubit gates" group="sq_gates" config={targetConfig} onChange={setTargetConfig} />
              <GateTable title="Two qubit gates" group="two_q_gates" config={targetConfig} onChange={setTargetConfig} />
              <GateTable title="Inter-device gates" group="inter_device_gates" config={targetConfig} onChange={setTargetConfig} />
            </div>
          </div>
        </section>

        <section id="preview" className="workspace-section">
          <div className="section-header">
            <div>
              <SectionLabel>Stage 3</SectionLabel>
              <h2>Target preview and compiled geometry</h2>
            </div>
          </div>

          <div className="section-grid">
            <article className="surface-card chart-card">
              <SectionLabel>Coupling graph</SectionLabel>
              <TargetGraph preview={targetPreview} />
            </article>

            <article className="surface-card">
              <SectionLabel>Preview summary</SectionLabel>
              <div className="summary-strip">
                <SurfaceMetric label="Topology" value={targetPreview ? displayTopology(targetPreview.topology_type) : "-"} />
                <SurfaceMetric label="Modality" value={modalityPresets[selectedModality].label} />
                <SurfaceMetric label="Qubits" value={targetPreview?.total_qubits ?? "-"} />
                <SurfaceMetric label="Edges" value={targetPreview?.total_edges ?? "-"} />
              </div>
              <div className="subsection-block">
                <h4>Supported operations</h4>
                <OperationList
                  counts={Object.fromEntries((targetPreview?.operation_names ?? []).map((name) => [name, 1]))}
                />
              </div>
            </article>
          </div>
        </section>

        <section id="results" className="workspace-section">
          <div className="section-header">
            <div>
              <SectionLabel>Stage 4</SectionLabel>
              <h2>Compilation and resource-estimation results</h2>
            </div>
            <button type="button" onClick={handleRun} disabled={status === "loading"}>
              <Play aria-hidden="true" /> Run
            </button>
          </div>

          <div className="section-grid">
            <article className="surface-card">
              <SectionLabel>Interpretation</SectionLabel>
              <div className="interpretation-stack">
              <div className="interpretation-callout">
                  <strong>{interpretation.headline}</strong>
                  <p>{interpretation.summary}</p>
                </div>
                <div className="mini-analysis-grid">
                  <article className="mini-analysis-card">
                    <h4>Primary bottleneck</h4>
                    <p>{interpretation.bottleneck}</p>
                  </article>
                  <article className="mini-analysis-card">
                    <h4>Suggested next move</h4>
                    <p>{interpretation.nextStep}</p>
                  </article>
                  <article className="mini-analysis-card">
                    <h4>Assumption sensitivity</h4>
                    <p>{interpretation.assumption}</p>
                  </article>
                </div>
              </div>
            </article>

            <article className="surface-card">
              <SectionLabel>Metric board</SectionLabel>
              <div className="summary-strip">
                <SurfaceMetric label="Compiler" value={runResult ? compilerLabels[runResult.compiler as CompilerBackend] ?? runResult.compiler : "-"} tone="signal" />
                <SurfaceMetric label="Estimator" value={runResult ? estimatorLabels[runResult.resource_estimator as ResourceEstimator] ?? runResult.resource_estimator : "-"} tone="signal" />
                <SurfaceMetric label="Physical qubits" value={metrics.physical_qubits ?? "-"} tone="emphasis" />
                <SurfaceMetric label="Runtime" value={formatDuration(metrics.runtime)} tone="emphasis" />
                <SurfaceMetric label="Original depth" value={runResult?.original.depth ?? "-"} />
                <SurfaceMetric label="Compiled depth" value={runResult?.transpiled.depth ?? "-"} />
                <SurfaceMetric label="Compiled gates" value={runResult?.transpiled.gate_count ?? "-"} />
                <SurfaceMetric label="Route mode" value={routingArtifacts.routing_mode ?? "-"} />
                <SurfaceMetric label="Measurement added for QRE" value={metrics.measurement_added_for_qre ?? "-"} />
                <SurfaceMetric label="RQOps" value={metrics.rqops ?? "-"} />
                <SurfaceMetric label="Algorithmic logical qubits" value={breakdown.algorithmicLogicalQubits ?? "-"} />
                <SurfaceMetric label="T factories" value={breakdown.numTfactories ?? "-"} />
              </div>
            </article>

            <article className="surface-card">
              <SectionLabel>Compiled operation profile</SectionLabel>
              <OperationList counts={runResult?.transpiled.operation_counts} />
              {runResult?.warnings.length ? <div className="warning-block">{runResult.warnings.join(" ")}</div> : null}
            </article>

            <article className="surface-card">
              <SectionLabel>QRE translation notes</SectionLabel>
              {translationNotes.length ? (
                <ul className="translation-note-list">
                  {translationNotes.map((note) => (
                    <li key={note}>
                      <ChevronRight aria-hidden="true" />
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="detail-empty">Run the estimator to inspect translation assumptions.</p>
              )}
            </article>

            <DetailBlock title="QRE assumptions" values={qreAssumptions} />
            <DetailBlock title="Logical counts" values={logicalCounts} />
            <DetailBlock title="Physical counts" values={physicalCounts} />
            <DetailBlock title="Breakdown" values={breakdown} />
            <DetailBlock title="Routing artifacts" values={routingArtifacts} />
            <DetailBlock title="Report data" values={reportData} />
          </div>
        </section>
      </section>
      </main>
    </>
  );
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
    bottleneck = `Compilation increased the circuit depth from ${formatNumber(originalDepth)} to ${formatNumber(compiledDepth)}, suggesting routing or decomposition overhead is currently the dominant effect.`;
  }

  let nextStep = "Compare an alternative topology or modality preset to see whether the compiled depth and physical width move in the same direction.";
  if (modality === "logical_clifford_t") {
    nextStep = "Focus next on reducing T-bearing structure or rerouting the circuit, because the logical Clifford+T model is what QRE is currently pricing.";
  } else if (compiledDepth > originalDepth) {
    nextStep = "Try changing connectivity or gate assumptions first, since routing pressure appears to be adding depth before estimation even begins.";
  }

  const assumption =
    "FTarget is still being interpreted as a logical architecture profile. QRE injects a gate-based qubit model and a surface-code layer for physical estimation, so these numbers should be read as architecture-shaped estimates rather than a native network-code simulation.";

  return {
    headline,
    summary: `The current run preserved the full compilation workflow and then estimated the compiled circuit through Azure QRE using the translated ${modality} assumption set.`,
    bottleneck,
    nextStep,
    assumption,
  };
}
