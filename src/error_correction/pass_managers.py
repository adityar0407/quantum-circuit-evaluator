from qiskit.transpiler import PassManager, CouplingMap
from qiskit.transpiler.passes import (
    TrivialLayout,
    BasicSwap,
    CommutativeCancellation,
    Optimize1qGatesDecomposition
)

def get_mapping_pm(coupling_map: CouplingMap) -> PassManager:
    """
    Creates a PassManager that enforces logical topology.
    This resolves the connectivity constraints by assigning qubits to physical 
    (or logical) nodes and inserting SWAP gates where necessary.
    """
    return PassManager([
        # Maps virtual qubits directly to physical qubits (q0 -> node 0, etc.)
        TrivialLayout(coupling_map),
        # Inserts SWAP gates to satisfy the CouplingMap edges
        BasicSwap(coupling_map)
    ])

def get_optimization_pm(basis_gates: list[str] = None) -> PassManager:
    """
    Creates a PassManager for the dynamic optimization loop.
    Focuses on reducing gate counts (especially single qubit gates) and depth.
    """
    # Default FT basis gates if none are provided
    if basis_gates is None:
        basis_gates = ['', 'u2', 'u3', 'cx', 'swap', 't', 'tdg', 'h', 's']
    
    return PassManager([
        # Cancels self-inverse gates (like H-H or CX-CX) and pushes commuting gates
        CommutativeCancellation(),
        # Compresses adjacent single-qubit gates into the provided basis
        Optimize1qGatesDecomposition(basis=basis_gates)
    ])