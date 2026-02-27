import pennylane as qml
from qiskit import QuantumCircuit, transpile


def build_test_circuit(n_qubits: int = 4):
    """Small circuit with H, CX, and T gates so FT-relevant metrics exist."""
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev)
    def circuit():
        for i in range(n_qubits):
            qml.Hadamard(wires=i)

        qml.CNOT(wires=[0, 1])
        qml.T(wires=0)
        qml.CNOT(wires=[1, 2])
        qml.T(wires=1)
        qml.CNOT(wires=[2, 3])
        qml.T(wires=2)

        return qml.state()

    return circuit


def pennylane_to_qasm(qnode):
    """
    Export QASM in a version-tolerant way.

    - Newer PennyLane: qml.to_openqasm(qnode)
    - Older PennyLane (like 0.38): qnode.qtape.to_openqasm()
    """
    if hasattr(qml, "to_openqasm"):
        
        qnode()
        return qml.to_openqasm(qnode)

    qnode()  
    if hasattr(qnode, "qtape") and qnode.qtape is not None:
        return qnode.qtape.to_openqasm()

    raise RuntimeError(
        "Could not find an OpenQASM export route. "
        "Your PennyLane version may not support QASM export the way we expect."
    )


def qasm_to_qiskit(qasm_str: str) -> QuantumCircuit:
    return QuantumCircuit.from_qasm_str(qasm_str)


def transpile_to_basis(qc: QuantumCircuit, basis_gates=None, opt_level: int = 0) -> QuantumCircuit:
    if basis_gates is None:
        basis_gates = ["h", "s", "t", "cx"]
    return transpile(qc, basis_gates=basis_gates, optimization_level=opt_level)


def extract_metrics(qc: QuantumCircuit):
    counts = qc.count_ops()
    depth = qc.depth()
    t_count = counts.get("t", 0)
    clifford_count = counts.get("h", 0) + counts.get("s", 0) + counts.get("cx", 0)

    return {
        "gate_counts": dict(counts),
        "depth": depth,
        "t_count": t_count,
        "clifford_count": clifford_count,
    }


if __name__ == "__main__":
    qnode = build_test_circuit(n_qubits=4)

    qasm = pennylane_to_qasm(qnode)
    print("\n--- OpenQASM ---\n")
    print(qasm)

    qc = qasm_to_qiskit(qasm)
    qc_t = transpile_to_basis(qc, basis_gates=["h", "s", "t", "cx"], opt_level=0)

    print("\n--- Transpiled Circuit ---\n")
    print(qc_t)

    metrics = extract_metrics(qc_t)
    print("\n--- Metrics ---\n")
    print(metrics)