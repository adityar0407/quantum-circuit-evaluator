import { useMemo, useState } from "react";
import {
  Activity,
  Binary,
  CheckCircle2,
  Cpu,
  Network,
  Play,
  RefreshCw,
  RotateCcw,
  Settings2,
  Zap,
} from "lucide-react";
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

const compilerLabels: Record<CompilerBackend, string> = {
  auto: "Automatic routing",
  qiskit_ftarget: "Qiskit FTarget",
  pandora: "Pandora",
};

const estimatorLabels: Record<ResourceEstimator, string> = {
  simple_logical: "Logical Metrics",
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

function formatNumber(value: unknown): string {
  if (typeof value !== "number") {
    return String(value ?? "Unavailable");
  }
  if (value === 0) {
    return "0";
  }
  if (Math.abs(value) < 0.001 || Math.abs(value) >= 10000) {
    return value.toExponential(3);
  }
  return value.toLocaleString(undefined, { maximumSignificantDigits: 6 });
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  );
}

function StatusLine({ status, message }: { status: WorkStatus; message?: string }) {
  if (!message) {
    return null;
  }

  return <p className={`status-line ${status}`}>{message}</p>;
}

function CircuitSummaryStrip({ summary }: { summary?: CircuitSummary }) {
  if (!summary) {
    return (
      <div className="metric-grid">
        <Metric label="Qubits" value="-" />
        <Metric label="Depth" value="-" />
        <Metric label="Gates" value="-" />
      </div>
    );
  }

  return (
    <div className="metric-grid">
      <Metric label="Qubits" value={summary.num_qubits} />
      <Metric label="Classical Bits" value={summary.num_clbits} />
      <Metric label="Depth" value={summary.depth} />
      <Metric label="Gates" value={summary.gate_count} />
    </div>
  );
}

function OperationList({ counts }: { counts?: Record<string, number> }) {
  const entries = Object.entries(counts ?? {});

  if (!entries.length) {
    return <div className="quiet-row">No operations loaded</div>;
  }

  return (
    <div className="chips">
      {entries.map(([name, count]) => (
        <span key={name}>
          {name} <strong>{count}</strong>
        </span>
      ))}
    </div>
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
    return <div className="graph-empty">Preview not loaded</div>;
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
        <circle key={node.id} cx={node.x} cy={node.y} r="0.85" className={`node block-${node.block % 6}`} />
      ))}
    </svg>
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
    <section className="gate-section">
      <div className="subhead">{title}</div>
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

export function App() {
  const [qasm, setQasm] = useState(defaultQasm);
  const [targetConfig, setTargetConfig] = useState<TargetConfig>(defaultTargetConfig);
  const [selectedModality, setSelectedModality] = useState<ModalityKey>(defaultModality);
  const compilerBackend: CompilerBackend = "auto";
  const [resourceEstimator, setResourceEstimator] = useState<ResourceEstimator>("simple_logical");
  const [modalitySettings, setModalitySettings] = useState<ModalitySettings>(() =>
    cloneModalitySettings(defaultModality),
  );
  const [circuitSummary, setCircuitSummary] = useState<CircuitSummary>();
  const [targetPreview, setTargetPreview] = useState<TargetPreview>();
  const [runResult, setRunResult] = useState<TranspileResponse>();
  const [status, setStatus] = useState<WorkStatus>("idle");
  const [message, setMessage] = useState<string>();

  const topology = targetConfig.topology;

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

  async function handleValidate() {
    setStatus("loading");
    setMessage("Validating circuit");
    try {
      const summary = await validateCircuit(qasm);
      setCircuitSummary(summary);
      setStatus("ready");
      setMessage("Circuit loaded");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Circuit validation failed");
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
    setMessage("Running compilation");
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
    setResourceEstimator("simple_logical");
    setModalitySettings(cloneModalitySettings(defaultModality));
    setCircuitSummary(undefined);
    setTargetPreview(undefined);
    setRunResult(undefined);
    setStatus("idle");
    setMessage(undefined);
  }

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
            <Network aria-hidden="true" /> Target
          </a>
          <a href="#results">
            <Zap aria-hidden="true" /> Results
          </a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p>Local evaluator</p>
            <h1>Quantum Circuit Evaluator</h1>
          </div>
          <div className="toolbar">
            <button type="button" className="secondary" onClick={resetDefaults}>
              <RotateCcw aria-hidden="true" /> Reset
            </button>
            <button type="button" onClick={handleRun} disabled={status === "loading"}>
              <Play aria-hidden="true" /> Run
            </button>
          </div>
        </header>

        <StatusLine status={status} message={message} />

        <section id="circuit" className="panel circuit-panel">
          <div className="panel-heading">
            <div>
              <p>Circuit</p>
              <h2>OpenQASM input</h2>
            </div>
            <button type="button" className="secondary" onClick={handleValidate} disabled={status === "loading"}>
              <CheckCircle2 aria-hidden="true" /> Validate
            </button>
          </div>
          <textarea
            aria-label="OpenQASM circuit input"
            spellCheck={false}
            value={qasm}
            onChange={(event) => setQasm(event.target.value)}
          />
          <CircuitSummaryStrip summary={circuitSummary} />
          <OperationList counts={circuitSummary?.operation_counts} />
        </section>

        <section id="architecture" className="panel">
          <div className="panel-heading">
            <div>
              <p>Architecture</p>
              <h2>Target configuration</h2>
            </div>
            <button type="button" className="secondary" onClick={handlePreview} disabled={status === "loading"}>
              <RefreshCw aria-hidden="true" /> Preview
            </button>
          </div>

          <div className="config-grid">
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
                {Object.entries(estimatorLabels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
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

          <section className="modality-card">
            <div>
              <div className="subhead">Modality assumptions</div>
              <p>{modalityPresets[selectedModality].description}</p>
            </div>
            <div className="modality-grid">
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
          </section>

          <p className="helper-text">
            Topology controls the coupling geometry. Modality controls the native gate set and model assumptions.
          </p>

          <div className="gate-grid">
            <GateTable title="Single qubit gates" group="sq_gates" config={targetConfig} onChange={setTargetConfig} />
            <GateTable title="Two qubit gates" group="two_q_gates" config={targetConfig} onChange={setTargetConfig} />
            <GateTable title="Inter-device gates" group="inter_device_gates" config={targetConfig} onChange={setTargetConfig} />
          </div>
        </section>

        <section id="preview" className="panel">
          <div className="panel-heading">
            <div>
              <p>Target</p>
              <h2>Coupling map</h2>
            </div>
            <Settings2 aria-hidden="true" className="heading-icon" />
          </div>
          <div className="preview-grid">
            <TargetGraph preview={targetPreview} />
            <div className="target-summary">
              <Metric label="Topology" value={targetPreview ? displayTopology(targetPreview.topology_type) : "-"} />
              <Metric label="Modality" value={modalityPresets[selectedModality].label} />
              <Metric label="Qubits" value={targetPreview?.total_qubits ?? "-"} />
              <Metric label="Edges" value={targetPreview?.total_edges ?? "-"} />
              <Metric label="Block size" value={targetPreview?.n_block ?? "-"} />
              <div className="subhead">Operations</div>
              <OperationList
                counts={Object.fromEntries((targetPreview?.operation_names ?? []).map((name) => [name, 1]))}
              />
            </div>
          </div>
        </section>

        <section id="results" className="panel">
          <div className="panel-heading">
            <div>
              <p>Results</p>
              <h2>Compilation metrics</h2>
            </div>
            <button type="button" onClick={handleRun} disabled={status === "loading"}>
              <Play aria-hidden="true" /> Run
            </button>
          </div>
          <div className="results-grid">
            <Metric label="Compiler" value={runResult ? compilerLabels[runResult.compiler as CompilerBackend] ?? runResult.compiler : "-"} />
            <Metric label="Route" value={runResult?.artifacts.routing_mode ?? "-"} />
            <Metric label="Estimator" value={runResult ? estimatorLabels[runResult.resource_estimator as ResourceEstimator] ?? runResult.resource_estimator : "-"} />
            <Metric label="Original depth" value={runResult?.original.depth ?? "-"} />
            <Metric label="Compiled depth" value={runResult?.transpiled.depth ?? "-"} />
            <Metric label="Compiled gates" value={runResult?.transpiled.gate_count ?? "-"} />
            <Metric label="Success proxy" value={runResult?.metrics.independent_error_success_proxy ?? "-"} />
            <Metric label="Duration estimate" value={runResult?.metrics.scheduled_duration_estimate_seconds ?? "-"} />
            <Metric label="2Q gates" value={runResult?.metrics.total_2q_gates ?? "-"} />
            <Metric label="Inter-block gates" value={runResult?.metrics.inter_block_gates ?? "-"} />
            <Metric label="Unsupported ops" value={runResult?.metrics.unsupported_operation_count ?? "-"} />
          </div>
          {runResult?.warnings.length ? <div className="warning-box">{runResult.warnings.join(" ")}</div> : null}
          <OperationList counts={runResult?.transpiled.operation_counts} />
        </section>
      </section>
    </main>
  );
}
