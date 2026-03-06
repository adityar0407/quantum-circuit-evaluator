from qiskit import QuantumCircuit
def qasm_to_ir(qasm_string):
    return QuantumCircuit.from_qasm_str(qasm_string)