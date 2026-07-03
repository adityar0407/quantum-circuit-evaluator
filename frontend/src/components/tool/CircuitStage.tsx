import { CheckCircle2, FileUp } from "lucide-react";
import type { CircuitPreview, CircuitSummary } from "../../api/types";
import { PanelCard, SectionLabel, SurfaceMetric } from "./ToolPrimitives";

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

export function CircuitStage({
  qasm,
  onQasmChange,
  summary,
  circuitPreview,
  validateState,
  status,
  fileInputRef,
  onFileSelected,
  onValidate,
  canProceed,
  onProceed,
}: {
  qasm: string;
  onQasmChange: (value: string) => void;
  summary?: CircuitSummary;
  circuitPreview?: CircuitPreview;
  validateState: "idle" | "loading" | "success" | "error";
  status: "idle" | "loading" | "ready" | "error";
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelected: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onValidate: () => void;
  canProceed: boolean;
  onProceed: () => void;
}) {
  return (
    <section id="circuit" className="workspace-section">
      <div className="section-header">
        <div>
          <SectionLabel>Stage 1</SectionLabel>
          <h2>Circuit input</h2>
          <p className="section-copy">Load OpenQASM, validate it, and inspect the gate mix before architecture-aware compilation begins.</p>
        </div>
        <div className="section-actions">
          <input
            ref={fileInputRef}
            className="visually-hidden"
            type="file"
            accept=".qasm,.json,application/json,text/plain"
            onChange={onFileSelected}
          />
          <button type="button" className="secondary" onClick={() => fileInputRef.current?.click()} disabled={status === "loading"}>
            <FileUp aria-hidden="true" /> Import circuit
          </button>
          <button type="button" className={`secondary action-button state-${validateState}`} onClick={onValidate} disabled={status === "loading"}>
            <CheckCircle2 aria-hidden="true" /> Validate circuit
          </button>
          <button type="button" onClick={onProceed} disabled={!canProceed}>
            Proceed to Architecture
          </button>
        </div>
      </div>

      {validateState === "success" ? <div className="tool-feedback tool-feedback-success">Circuit validation passed. The input is structurally ready for architecture-aware compilation.</div> : null}
      {validateState === "error" ? <div className="tool-feedback tool-feedback-error">Circuit validation failed. Fix the QASM input before continuing to compilation.</div> : null}
      {validateState === "idle" ? <div className="tool-feedback tool-feedback-pending">Start by importing or editing the circuit, then validate it before the architecture stage unlocks.</div> : null}

      <div className="tool-grid tool-grid-circuit">
        <PanelCard label="OpenQASM editor" className="technical-card">
          <textarea
            className="qasm-editor"
            aria-label="OpenQASM circuit input"
            spellCheck={false}
            value={qasm}
            onChange={(event) => onQasmChange(event.target.value)}
          />
          <p className="field-hint">Accepted inputs: raw `.qasm` files, or `.json` files that contain an OpenQASM string.</p>
        </PanelCard>

        <div className="stack-column">
          <PanelCard label="Static analysis" title="Circuit summary">
            <SummaryStrip summary={summary} />
            <div className="subsection-block">
              <h4>Operation counts</h4>
              <OperationList counts={summary?.operation_counts} />
            </div>
          </PanelCard>

          <PanelCard label="Circuit visualization" title="Qiskit text preview">
            {validateState === "success" && circuitPreview?.num_qubits && circuitPreview.num_qubits > 25 ? (
              <div className="graph-empty circuit-visualization-empty">Circuit is too large to generate a diagram preview right now.</div>
            ) : validateState === "success" && circuitPreview?.diagram ? (
              <>
                <pre className="circuit-preview">{circuitPreview.diagram}</pre>
                <p className="field-hint">Text preview is for circuit sanity checking. Large circuits may be easier to inspect through exported run records.</p>
              </>
            ) : (
              <div className="graph-empty circuit-visualization-empty">Validate the circuit to load the Qiskit text preview.</div>
            )}
          </PanelCard>
        </div>
      </div>
    </section>
  );
}
