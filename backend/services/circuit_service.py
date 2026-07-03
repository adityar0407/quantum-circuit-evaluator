from __future__ import annotations

from qiskit import QuantumCircuit


class CircuitValidationError(ValueError):
    """Raised when user-provided circuit input cannot be parsed."""


def circuit_summary(circuit: QuantumCircuit) -> dict:
    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "depth": circuit.depth(),
        "gate_count": circuit.size(),
        "operation_counts": dict(circuit.count_ops()),
    }


def circuit_from_qasm(qasm: str) -> QuantumCircuit:
    try:
        return QuantumCircuit.from_qasm_str(qasm)
    except Exception as exc:
        raise CircuitValidationError(f"Invalid OpenQASM input: {exc}") from exc


def summarize_qasm(qasm: str) -> dict:
    return circuit_summary(circuit_from_qasm(qasm))


def circuit_preview(circuit: QuantumCircuit) -> dict:
    return {
        "format": "qiskit_text",
        "diagram": circuit.draw(output="text").single_string(),
        **circuit_summary(circuit),
        "warnings": [],
    }


def preview_qasm(qasm: str) -> dict:
    return circuit_preview(circuit_from_qasm(qasm))
