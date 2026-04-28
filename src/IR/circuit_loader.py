# Load a circuit of your choice defined by Pennylane 
import pennylane as qml
from qiskit import QuantumCircuit

# Simple test circut 
def input_test_circuit (): 
    dev = qml.device("default.qubit", wires = 2)
    @qml.qnode(dev)
    def circuit():
        qml.Hadamard(wires = 0)
        qml.CNOT(wires = [0,1])
        return qml.state()
    return circuit

# Other input circuits 
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


def get_trotterized_spin_chain(num_qubits: int = 100, steps: int = 2) -> QuantumCircuit:
    """
    Simulates the time evolution of a 1D Heisenberg/Ising material.
    A cornerstone of quantum simulation in chemistry and physics.
    """
    qc = QuantumCircuit(num_qubits)
    
    # Interaction angle (represents time step * coupling strength)
    theta = 0.1 
    
    for _ in range(steps):
        # Even-Odd Layering (Parallel CX interactions)
        # Even bonds
        for i in range(0, num_qubits - 1, 2):
            qc.cx(i, i+1)
            qc.rz(theta, i+1)
            qc.cx(i, i+1)
            
        qc.barrier() # Prevent the transpiler from artificially merging layers
            
        # Odd bonds
        for i in range(1, num_qubits - 1, 2):
            qc.cx(i, i+1)
            qc.rz(theta, i+1)
            qc.cx(i, i+1)
            
        qc.barrier()
        
    return qc
