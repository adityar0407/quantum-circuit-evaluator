from __future__ import annotations

from pathlib import Path

from qiskit import QuantumCircuit
from qiskit import qasm2

def ingest_qasm_string(qasm_string: str) -> str:
    return qasm_string.strip()


def ingest_qasm_file(file_path: str | Path) -> str:
    return Path(file_path).read_text().strip()


def load_qasm_circuit(qasm_string: str) -> QuantumCircuit:
    return QuantumCircuit.from_qasm_str(ingest_qasm_string(qasm_string))


def validate_qasm(qasm_string: str) -> tuple[bool, QuantumCircuit | str]:
    try:
        return True, load_qasm_circuit(qasm_string)
    except Exception as exc:
        return False, str(exc)


def export_circuit_to_qasm(circuit: QuantumCircuit) -> str:
    if hasattr(circuit, "qasm"):
        return circuit.qasm()

    try:
        return qasm2.dumps(circuit)
    except Exception as exc:
        raise ValueError("The installed Qiskit version cannot export OPENQASM 2 from QuantumCircuit.") from exc
