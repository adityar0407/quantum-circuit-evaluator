import { createRef } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { CircuitStage } from "./CircuitStage";

describe("CircuitStage", () => {
  it("renders the diagram preview after successful validation", () => {
    const markup = renderToStaticMarkup(
      <CircuitStage
        qasm={`OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];`}
        summary={{
          num_qubits: 2,
          num_clbits: 0,
          depth: 2,
          gate_count: 2,
          operation_counts: { h: 1, cx: 1 },
        }}
        circuitPreview={{
          format: "qiskit_text",
          diagram: "     ┌───┐     \nq_0: ┤ H ├──■──\n     └───┘┌─┴─┐\nq_1: ─────┤ X ├\n          └───┘",
          num_qubits: 2,
          num_clbits: 0,
          depth: 2,
          gate_count: 2,
          operation_counts: { h: 1, cx: 1 },
          warnings: [],
        }}
        validateState="success"
        status="ready"
        fileInputRef={createRef<HTMLInputElement>()}
        onFileSelected={vi.fn()}
        onValidate={vi.fn()}
        canProceed
        onProceed={vi.fn()}
        onQasmChange={vi.fn()}
      />,
    );

    expect(markup).toContain("class=\"circuit-preview\"");
    expect(markup).toContain("q_0:");
    expect(markup).not.toContain("Awaiting visualization spec");
  });

  it("shows the placeholder before validation", () => {
    const markup = renderToStaticMarkup(
      <CircuitStage
        qasm=""
        summary={undefined}
        circuitPreview={undefined}
        validateState="idle"
        status="idle"
        fileInputRef={createRef<HTMLInputElement>()}
        onFileSelected={vi.fn()}
        onValidate={vi.fn()}
        canProceed={false}
        onProceed={vi.fn()}
        onQasmChange={vi.fn()}
      />,
    );

    expect(markup).toContain("Validate the circuit to load the Qiskit text preview.");
  });
});
