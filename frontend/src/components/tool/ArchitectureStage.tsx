import { ArrowRight, RefreshCw, Settings2 } from "lucide-react";
import type { ArchitecturePreset, ResourceEstimator, TargetConfig, TargetPreview } from "../../api/types";
import type { ModalityKey, ModalitySettings } from "../../state/defaults";
import { modalityPresets } from "../../state/defaults";
import { PanelCard, SectionLabel, SurfaceMetric } from "./ToolPrimitives";

type GateGroup = "sq_gates" | "two_q_gates" | "inter_device_gates";

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
      <input type="number" min={min} step={step} value={value} onChange={(event) => onChange(Number(event.target.value) || min)} />
    </label>
  );
}

function AssumptionField({
  label,
  value,
  step = "any",
  min,
  onChange,
}: {
  label: string;
  value: unknown;
  step?: string;
  min?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={min} step={step} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SupportStatusChip({ status }: { status: string }) {
  const tone = status === "unsupported" ? "unsupported" : status === "approximate" ? "approximate" : "supported";
  return <span className={`support-status-chip status-${tone}`}>{status.replace(/_/g, " ")}</span>;
}

function OperationList({ items }: { items: string[] }) {
  if (!items.length) {
    return <div className="chip-list-empty">No operation metadata loaded</div>;
  }

  return (
    <div className="chip-list">
      {items.map((name) => (
        <span key={name}>{name}</span>
      ))}
    </div>
  );
}

function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  if (typeof value !== "number") {
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

function humanizeKey(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function friendlyImplementedAs(value: string): string {
  const labels: Record<string, string> = {
    tiled_k_nearest: "Nearest-neighbor tile layout",
    heavy_hex: "Heavy-hex coupling graph",
    heavy_square: "Heavy-square coupling graph",
    unsupported: "Reference only",
  };
  return labels[value] ?? humanizeKey(value);
}

function friendlyHardwareModel(key: string): string {
  return key === "neutral_atom" ? "Neutral-atom hardware model" : "Gate-based hardware model";
}

function getProfileGroup(config: TargetConfig, group: GateGroup): Record<string, Record<string, number>> {
  return (config.profile[group] ?? {}) as Record<string, Record<string, number>>;
}

function cloneConfig(config: TargetConfig): TargetConfig {
  return JSON.parse(JSON.stringify(config)) as TargetConfig;
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
  const fields = group === "sq_gates" ? ["logical_weight", "logical_preference"] : ["logical_weight", "routing_preference"];

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
            <span key={field}>{field.replace(/_/g, " ")}</span>
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
                value={asNumber(values[field])}
                onChange={(event) => updateGate(gateName, field, Number(event.target.value) || 0)}
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

function TargetGraph({ preview }: { preview?: TargetPreview }) {
  if (!preview || !preview.nodes.length) {
    return <div className="graph-empty">Preview the target to inspect the coupling graph.</div>;
  }

  const fallbackRadius = 120;
  const nodes = preview.nodes.map((node, index) => {
    if (typeof node.x === "number" && typeof node.y === "number") {
      return { ...node, x: node.x, y: node.y };
    }
    const angle = (index / preview.nodes.length) * Math.PI * 2;
    return { ...node, x: Math.cos(angle) * fallbackRadius, y: Math.sin(angle) * fallbackRadius };
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
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const viewBox = `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`;

  return (
    <svg className="target-graph" viewBox={viewBox} role="img" aria-label="Target coupling graph">
      {preview.edges.map((edge, index) => {
        const source = nodeById.get(edge.source);
        const target = nodeById.get(edge.target);
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
      {nodes.map((node) => (
        <circle key={node.id} cx={node.x} cy={node.y} r="0.95" className={`node block-${node.block % 6}`} />
      ))}
    </svg>
  );
}

export function ArchitectureStage(props: {
  architecturePresets: ArchitecturePreset[];
  selectedArchitectureId: string;
  selectedArchitecture?: ArchitecturePreset;
  selectedModality: ModalityKey;
  inferredModality: ModalityKey;
  modalitySettings: ModalitySettings;
  targetConfig: TargetConfig;
  targetPreview?: TargetPreview;
  showAdvancedArchitecture: boolean;
  resourceEstimator: ResourceEstimator;
  architectureIsUnsupported: boolean;
  architectureLimitations: string[];
  status: "idle" | "loading" | "ready" | "error";
  onApplyArchitecturePreset: (value: string) => void;
  onSetResourceEstimator: (value: ResourceEstimator) => void;
  onToggleAdvanced: () => void;
  onHandlePreview: () => void;
  onRun: () => void;
  onUpdateTopology: (key: string, value: string | number) => void;
  onUpdateModalitySetting: (key: string, value: number) => void;
  onSetTargetConfig: (config: TargetConfig) => void;
  onProceed: () => void;
  referenceUrl: (reference: string) => string | null;
  formatReferenceLabel: (reference: string) => string;
}) {
  const {
    architecturePresets,
    selectedArchitectureId,
    selectedArchitecture,
    selectedModality,
    inferredModality,
    modalitySettings,
    targetConfig,
    targetPreview,
    showAdvancedArchitecture,
    resourceEstimator,
    architectureIsUnsupported,
    architectureLimitations,
    status,
    onApplyArchitecturePreset,
    onSetResourceEstimator,
    onToggleAdvanced,
    onHandlePreview,
    onRun,
    onUpdateTopology,
    onUpdateModalitySetting,
    onSetTargetConfig,
    onProceed,
    referenceUrl,
    formatReferenceLabel,
  } = props;

  const topology = targetConfig.topology;
  return (
    <section id="architecture" className="workspace-section">
      <div className="section-header">
        <div>
          <SectionLabel>Stage 2</SectionLabel>
          <h2>Architecture &amp; compiler</h2>
          <p className="section-copy">Select your target hardware topology and compiler-facing logical basis, then preview the architecture graph before moving on.</p>
        </div>
        <div className="section-actions">
          <button type="button" className="secondary" onClick={onHandlePreview} disabled={status === "loading"}>
            <RefreshCw aria-hidden="true" /> Preview target
          </button>
          <button type="button" onClick={onProceed} disabled={architectureIsUnsupported}>
            Proceed to Estimation <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="tool-grid tool-grid-architecture">
        <div className="stack-column">
          <PanelCard label="Hardware target" title="Architecture preset" className="architecture-preset-card">
            <div className="form-grid architecture-form-grid">
              <label className="field field-span-full">
                <span>Hardware architecture</span>
                <div className="field-select-shell">
                  <select
                    value={selectedArchitectureId}
                    title={selectedArchitecture?.display_name ?? selectedArchitectureId}
                    onChange={(event) => onApplyArchitecturePreset(event.target.value)}
                  >
                    {architecturePresets.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              </label>
              <div className="field static-field architecture-span-wide">
                <span>Hardware family</span>
                <strong title={selectedArchitecture ? humanizeKey(selectedArchitecture.category) : "Loading"}>
                  {selectedArchitecture ? humanizeKey(selectedArchitecture.category) : "Loading"}
                </strong>
              </div>
              <div className="field static-field architecture-span-compact">
                <span>Model status</span>
                <strong>{selectedArchitecture ? <SupportStatusChip status={selectedArchitecture.support_status} /> : "Loading"}</strong>
              </div>
              <div className="field static-field architecture-span-wide">
                <span>Connectivity model</span>
                <strong title={selectedArchitecture ? friendlyImplementedAs(selectedArchitecture.implemented_as) : "Loading"}>
                  {selectedArchitecture ? friendlyImplementedAs(selectedArchitecture.implemented_as) : "Loading"}
                </strong>
              </div>
              <div className="field static-field architecture-span-compact">
                <span>Compiler basis</span>
                <strong title={modalityPresets[inferredModality].label}>{modalityPresets[inferredModality].label}</strong>
              </div>
              <label className="field field-span-full">
                <span>Estimation route</span>
                <div className="field-select-shell">
                  <select value={resourceEstimator} onChange={(event) => onSetResourceEstimator(event.target.value as ResourceEstimator)}>
                    <option value="native_qre">Fault-tolerant estimate</option>
                    <option value="qiskit_compatibility">Compatibility estimate</option>
                  </select>
                </div>
              </label>
            </div>

            {selectedArchitecture ? (
              <div className="subsection-block">
                <h4>{selectedArchitecture.display_name}</h4>
                <p className="body-copy">{selectedArchitecture.limitations[0] ?? "No architecture notes available."}</p>
                <div className="detail-list architecture-reference-list">
                  {selectedArchitecture.references.map((reference) => (
                    <div key={reference}>
                      <dt>Paper</dt>
                      <dd>
                        {referenceUrl(reference) ? (
                          <a href={referenceUrl(reference) ?? "#"} target="_blank" rel="noreferrer">
                            {formatReferenceLabel(reference)}
                          </a>
                        ) : (
                          formatReferenceLabel(reference)
                        )}
                      </dd>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="insight-strip">
              <div className="inline-note">
                <p>
                  `FTarget` is the architecture contract the compiler obeys. It defines which qubits may interact, which gate
                  families are native, and what routing constraints Pandora or Qiskit must respect.
                </p>
              </div>
            </div>

            <div className="subsection-block">
              <button type="button" className="secondary" onClick={onToggleAdvanced}>
                <Settings2 aria-hidden="true" /> {showAdvancedArchitecture ? "Hide graph generator settings" : "Show graph generator settings"}
              </button>
              {showAdvancedArchitecture ? (
                <div className="advanced-block">
                  <p className="field-hint">These controls expose the backend graph generator. Leave them alone unless you are intentionally modifying the preset for a custom study.</p>
                  <div className="form-grid">
                    <label className="field">
                      <span>Backend graph model</span>
                      <select value={String(topology.type ?? "tiled_k_nearest")} onChange={(event) => onUpdateTopology("type", event.target.value)}>
                        <option value="tiled_k_nearest">Nearest-neighbor tile layout</option>
                        <option value="heavy_hex">Heavy-hex graph</option>
                        <option value="heavy_square">Heavy-square graph</option>
                      </select>
                    </label>
                    <NumericField label="Tile rows" value={asNumber(topology.n_blocks_row, 1)} onChange={(value) => onUpdateTopology("n_blocks_row", value)} />
                    <NumericField label="Tile columns" value={asNumber(topology.n_blocks_col, 1)} onChange={(value) => onUpdateTopology("n_blocks_col", value)} />
                    {topology.type === "tiled_k_nearest" ? (
                      <>
                        <NumericField label="Qubits per tile row" value={asNumber(topology.n, 1)} onChange={(value) => onUpdateTopology("n", value)} />
                        <NumericField label="Qubits per tile column" value={asNumber(topology.m, 1)} onChange={(value) => onUpdateTopology("m", value)} />
                        <NumericField label="Neighbor reach inside tile" value={asNumber(topology.k_intra, 1)} onChange={(value) => onUpdateTopology("k_intra", value)} />
                        <NumericField label="Neighbor reach between tiles" value={asNumber(topology.k_inter, 1)} onChange={(value) => onUpdateTopology("k_inter", value)} />
                        <NumericField label="Inter-tile connectors" value={asNumber(topology.connector_local, 1)} onChange={(value) => onUpdateTopology("connector_local", value)} />
                      </>
                    ) : (
                      <>
                        <NumericField label="Code distance or scale" value={asNumber(topology.d, 3)} onChange={(value) => onUpdateTopology("d", value)} />
                        <NumericField label="Inter-block coupling count" value={asNumber(topology.k_inter, 1)} onChange={(value) => onUpdateTopology("k_inter", value)} />
                      </>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </PanelCard>

          <PanelCard label="Compiler basis" title={modalityPresets[selectedModality].label} description={modalityPresets[selectedModality].description}>
            <p className="field-hint">These weights bias the compiler toward cheaper native operations for the selected hardware family.</p>
            <div className="form-grid">
              {modalityPresets[selectedModality].fields.map((field) => (
                <NumericField
                  key={field.key}
                  label={field.label}
                  value={asNumber(modalitySettings[field.key], field.min ?? 0)}
                  min={field.min ?? 0}
                  step={field.step}
                  onChange={(value) => onUpdateModalitySetting(field.key, value)}
                />
              ))}
            </div>
          </PanelCard>
        </div>

        <div className="stack-column">
          <PanelCard
            label="Topology preview"
            title={targetPreview?.architecture_id ?? selectedArchitecture?.display_name ?? "Architecture graph"}
            className="topology-preview-card"
          >
            <div className="summary-strip architecture-preview-strip">
              <SurfaceMetric label="Qubits" value={targetPreview?.total_qubits ?? "-"} />
              <SurfaceMetric label="Edges" value={targetPreview?.total_edges ?? "-"} />
              <SurfaceMetric label="Gate family" value={modalityPresets[selectedModality].label} />
              <SurfaceMetric label="Native gates" value={targetPreview?.operation_names.length ?? "-"} />
            </div>
            <TargetGraph preview={targetPreview} />
            <div className="subsection-block">
              <h4>Supported interactions</h4>
              <OperationList items={targetPreview?.operation_names ?? []} />
            </div>
            <div className="subsection-block">
              <h4>Architecture limitations</h4>
              {architectureLimitations.length ? (
                <ul className="translation-note-list">
                  {architectureLimitations.map((note) => (
                    <li key={note}>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="detail-empty">Preview the target to inspect the architecture notes.</p>
              )}
            </div>
          </PanelCard>

          <PanelCard label="Fault-tolerant estimation profile" title="Physical and QEC assumptions">
            <p className="body-copy">Physical hardware and QEC settings are configured on the next screen so the compilation stage stays focused on target selection, routing, and legal interactions.</p>
            <div className="inline-note">
              <p>Use the `Proceed to Estimation` action once the architecture graph and compiler basis look correct.</p>
            </div>
          </PanelCard>
        </div>
      </div>

      <div className="gate-grid">
        <GateTable title="Single-qubit gates" group="sq_gates" config={targetConfig} onChange={onSetTargetConfig} />
        <GateTable title="Two-qubit gates" group="two_q_gates" config={targetConfig} onChange={onSetTargetConfig} />
        <GateTable title="Inter-device gates" group="inter_device_gates" config={targetConfig} onChange={onSetTargetConfig} />
      </div>
    </section>
  );
}
