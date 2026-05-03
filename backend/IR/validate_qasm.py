# Validate the exported QASM string doesnt have any issues with Qisket
from qiskit import QuantumCircuit

def validate_qasm(qasm_string):
    try:
        qc = QuantumCircuit.from_qasm_str(qasm_string)
        return True, qc
    except Exception as e:
        return False, str(e)
