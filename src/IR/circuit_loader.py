# Load a circuit of your choice defined by Pennylane 
import pennylane as qml
from qiskit import QuantumCircuit

def input_test_circuit (): 
    dev = qml.device("default.qubit", wires = 2)
    @qml.qnode(dev)
    def circuit():
        qml.Hadamard(wires = 0)
        qml.CNOT(wires = [0,1])
        return qml.state()
    return circuit


def get_toffoli_cascade(num_qubits: int) -> QuantumCircuit:
    """
    Generates a ladder of Toffoli gates across the entire qubit register.
    This creates an extreme stress test for routing (SWAPs) and fault-tolerant 
    gate synthesis (T gates).
    """
    qc = QuantumCircuit(num_qubits)
    
    # Sweep down the register
    for i in range(num_qubits - 2):
        qc.ccx(i, i+1, i+2)
        
    # Sweep back up the register (adds depth and forces variables back across the chip)
    for i in reversed(range(num_qubits - 2)):
        qc.ccx(i, i+1, i+2)
        
    return qc



