import { FileUp, Play } from "lucide-react";
import type { CircuitPreview, CompilerBackend, ResourceEstimator, TranspileResponse } from "../../api/types";
import { PanelCard, SectionLabel, SurfaceMetric } from "./ToolPrimitives";

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

function formatRuntimeMetric(metrics: Record<string, unknown>): string {
  if (metrics.estimated_runtime_seconds !== undefined && metrics.estimated_runtime_seconds !== null) {
    return `${formatNumber(metrics.estimated_runtime_seconds)} s`;
  }
  return formatDuration(metrics.runtime);
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

function DetailBlock({ title, values }: { title: string; values: Record<string, unknown> }) {
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

const compilerLabels: Record<CompilerBackend, string> = {
  auto: "Automatic routing",
  qiskit_ftarget: "Qiskit FTarget",
  pandora: "Pandora",
};

const estimatorLabels: Record<ResourceEstimator, string> = {
  native_qre: "Fault-tolerant estimate",
  qiskit_compatibility: "Compatibility estimate",
};

export function ResultsStage({
  runResult,
  metrics,
  logicalCounts,
  physicalCounts,
  breakdown,
  qreAssumptions,
  routingArtifacts,
  reportData,
  translationNotes,
  selectedArchitectureName,
  selectedArchitectureId,
  architectureSupportStatus,
  architectureReferences,
  architectureLimitations,
  reproducibleExport,
  interpretation,
  status,
  compiledCircuitPreview,
  onRun,
  onDownloadRunExport,
}: {
  runResult?: TranspileResponse;
  metrics: Record<string, unknown>;
  logicalCounts: Record<string, unknown>;
  physicalCounts: Record<string, unknown>;
  breakdown: Record<string, unknown>;
  qreAssumptions: Record<string, unknown>;
  routingArtifacts: Record<string, unknown>;
  reportData: Record<string, unknown>;
  translationNotes: string[];
  selectedArchitectureName?: string;
  selectedArchitectureId: string;
  architectureSupportStatus: string;
  architectureReferences: string[];
  architectureLimitations: string[];
  reproducibleExport: Record<string, unknown>;
  interpretation: {
    headline: string;
    summary: string;
    bottleneck: string;
    nextStep: string;
    assumption: string;
  };
  status: "idle" | "loading" | "ready" | "error";
  compiledCircuitPreview?: CircuitPreview;
  onRun: () => void;
  onDownloadRunExport: () => void;
}) {
  return (
    <section id="results" className="workspace-section">
      <div className="section-header">
        <div>
          <SectionLabel>Stage 4</SectionLabel>
          <h2>Compiled output and resource estimates</h2>
          <p className="section-copy">Review what the compiler changed, what the estimator inferred, and which assumptions are driving the numbers.</p>
        </div>
        <div className="section-actions">
          <button type="button" className="secondary" onClick={onDownloadRunExport} disabled={!runResult || Object.keys(reproducibleExport).length === 0}>
            <FileUp aria-hidden="true" /> Download JSON export
          </button>
          <button type="button" onClick={onRun} disabled={status === "loading"}>
            <Play aria-hidden="true" /> Run evaluation
          </button>
        </div>
      </div>

      <div className="summary-strip metric-board">
        <SurfaceMetric label="Compiler" value={runResult ? compilerLabels[runResult.compiler as CompilerBackend] ?? runResult.compiler : "-"} tone="signal" />
        <SurfaceMetric label="Estimator" value={runResult ? estimatorLabels[runResult.resource_estimator as ResourceEstimator] ?? runResult.resource_estimator : "-"} tone="signal" />
        <SurfaceMetric label="Physical qubits" value={formatNumber(metrics.physical_qubits ?? metrics.total_physical_qubits ?? "-")} tone="emphasis" />
        <SurfaceMetric label="Runtime" value={runResult ? formatRuntimeMetric(metrics) : "-"} tone="emphasis" />
      </div>

      <div className="tool-grid tool-grid-results">
        <PanelCard label="Interpretation" title={interpretation.headline} description={interpretation.summary}>
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
        </PanelCard>

        <PanelCard label="Compiled circuit" title="Operation profile">
          <div className="summary-strip compact-summary">
            <SurfaceMetric label="Original depth" value={formatNumber(runResult?.original.depth ?? "-")} />
            <SurfaceMetric label="Compiled depth" value={formatNumber(runResult?.transpiled.depth ?? "-")} />
            <SurfaceMetric label="Compiled gates" value={formatNumber(runResult?.transpiled.gate_count ?? "-")} />
            <SurfaceMetric label="Route mode" value={String(routingArtifacts.routing_mode ?? "-")} />
          </div>
          <div className="subsection-block">
            <h4>Compiled text diagram</h4>
            {compiledCircuitPreview?.diagram ? (
              <>
                <pre className="circuit-preview">{compiledCircuitPreview.diagram}</pre>
                <p className="field-hint">Text preview is for circuit sanity checking. Large circuits may be easier to inspect through exported run records.</p>
              </>
            ) : (
              <p className="detail-empty">Run compilation to inspect the compiled circuit diagram.</p>
            )}
          </div>
          <div className="subsection-block">
            <h4>Compiled operations</h4>
            <OperationList counts={runResult?.transpiled.operation_counts} />
          </div>
          {runResult?.warnings.length ? <div className="warning-block">{runResult.warnings.join(" ")}</div> : null}
        </PanelCard>

        <PanelCard label="Estimator notes" title="QRE translation">
          {translationNotes.length ? (
            <ul className="translation-note-list">
              {translationNotes.map((note) => (
                <li key={note}>
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="detail-empty">Run the estimator to inspect translation assumptions.</p>
          )}
        </PanelCard>

        <PanelCard label="Trace summary" title="Key metrics">
          <div className="summary-strip compact-summary">
            <SurfaceMetric label="RQOps" value={formatNumber(metrics.rqops ?? "-")} />
            <SurfaceMetric label="Measurement added" value={formatNumber(metrics.measurement_added_for_qre ?? "-")} />
            <SurfaceMetric label="Logical qubits" value={formatNumber(breakdown.algorithmicLogicalQubits ?? "-")} />
            <SurfaceMetric label="T factories" value={formatNumber(breakdown.numTfactories ?? "-")} />
          </div>
        </PanelCard>

        <DetailBlock title="QRE assumptions" values={qreAssumptions} />
        <DetailBlock
          title="Architecture metadata"
          values={{
            architecture_preset: selectedArchitectureId,
            architecture_name: selectedArchitectureName,
            support_status: architectureSupportStatus,
            references: architectureReferences,
            limitations: architectureLimitations,
          }}
        />
        <DetailBlock title="Logical counts" values={logicalCounts} />
        <DetailBlock title="Physical counts" values={physicalCounts} />
        <DetailBlock title="Breakdown" values={breakdown} />
        <DetailBlock title="Routing artifacts" values={routingArtifacts} />
        <DetailBlock title="Report data" values={reportData} />
      </div>
    </section>
  );
}
