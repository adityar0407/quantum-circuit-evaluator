from typing import Dict, Any, List, Tuple
from qiskit.transpiler import Target, InstructionProperties, CouplingMap
from qiskit.circuit.library import (
    RXGate, RZGate, RYGate, CXGate, CZGate, RXXGate, TGate, HGate, SGate, Measure
)

def create_custom_target(
    ## TODO: see if I can create local variables that just call on the coupling map instead of having to define them in the main pipeline and then 
    # pass them in here.
    num_qubits: int,
    basis_gates: List[Any],
    gate_specs: Dict[str, Dict[str, float]],
    coupling_map: CouplingMap = None
) -> Target:
    """
    Creates a highly customizable Qiskit Target for user-defined architectures.
    
    Args:
        num_qubits: Total number of qubits in the system.
        basis_gates: List of Qiskit gate classes (e.g., [RXGate, CXGate]).
        gate_specs: Dictionary mapping gate names to their 'duration' and 'error'.
                    Example: {'cx': {'duration': 300e-9, 'error': 0.01}}
        coupling_map: The allowed connectivity. If None, assumes all-to-all.
        
    Returns:
        A configured Qiskit Target object.
    """
    target = Target(num_qubits=num_qubits)
    print(f"Creating custom target with {num_qubits} qubits and basis gates: {[gate().name for gate in basis_gates]}")
    print("if no coupling map is provided, the target will assume all-to-all connectivity between qubits.")
    print("if no specs are provided for a given gate, it will be assumed to be perfect and instantaneous (duration=0.0, error=0.0)")
    # Define the edges for 2-qubit gates based on the coupling map
    if coupling_map:
        ## TODO: see if adi can create a callable for the coupling map so i don't ahve to call get_edges in here too
        edges = list(coupling_map.get_edges())
    else:
        # All-to-all connectivity if no map is provided
        edges = [(i, j) for i in range(num_qubits) for j in range(num_qubits) if i != j]
        
    for gate_class in basis_gates:
        gate_name = gate_class().name
        
        # Check if the user provided specs for this gate; if not, assume perfect/instant
        specs = gate_specs.get(gate_name, {'duration': 0.0, 'error': 0.0})
        duration = specs['duration']
        error = specs['error']
        
        props = InstructionProperties(duration=duration, error=error)
        
        if gate_class().num_qubits == 1:
            # Apply 1-qubit gates to all individual qubits
            instruction_map = {(q,): props for q in range(num_qubits)}
        elif gate_class().num_qubits == 2:
            # Apply 2-qubit gates only to connected edges
            instruction_map = {edge: props for edge in edges}
        else:
            continue # Skip 3+ qubit gates for this simple builder. TODO: maybe add support for multi-qubit gates in the future.
            
        target.add_instruction(gate_class(), instruction_map)
        
    # Always add measurement capabilities (assuming standard error/duration)
    measure_props = InstructionProperties(duration=1e-6, error=0.02)
    target.add_instruction(Measure(), {(q,): measure_props for q in range(num_qubits)})
        
    return target


def get_benchmark_target(architecture: str, num_qubits: int, coupling_map: CouplingMap = None) -> Target:
    """
    Returns a pre-configured Target for specific quantum hardware modalities.
    Durations are in seconds, errors are probabilities (0.0 to 1.0).
    """
    
    if architecture.lower() == "superconducting":
        # Fast execution times, moderate error rates, limited connectivity
        # Single qubit gates ~30ns, Two qubit gates ~300ns
        gate_specs = {
            'rz': {'duration': 0.0, 'error': 0.0},           # Virtual Z is free
            'rx': {'duration': 30e-9, 'error': 0.001},       # 0.1% error
            'cx': {'duration': 300e-9, 'error': 0.01}        # 1.0% error
        }
        return create_custom_target(
            num_qubits, [RZGate, RXGate, CXGate], gate_specs, coupling_map
        )
        
    elif architecture.lower() == "trapped_ion":
        # TODO: find more accurate specs for trapped ion systems, these are just placeholders based on general knowledge of the field.
        # Slow execution times, very low error rates, native all-to-all connectivity
        # Single qubit gates ~10 microseconds, Two qubit gates ~100 microseconds
        gate_specs = {
            'rz': {'duration': 0.0, 'error': 0.0},
            'rx': {'duration': 10e-6, 'error': 0.0001},      # 0.01% error
            'rxx': {'duration': 100e-6, 'error': 0.005}      # 0.5% error
        }
        # Trapped ions typically feature all-to-all connectivity natively
        return create_custom_target(
            num_qubits, [RZGate, RXGate, RXXGate], gate_specs, coupling_map=None 
        )
        
    elif architecture.lower() == "logical_surface_code":
        # Theoretical Fault-Tolerant profile. TODO: find more accurate specs based on current literature for surface code implementations, 
        # these are just illustrative placeholders.
        
        # Cliffords (H, S, CX) are cheap/fast via lattice surgery.
        # Non-Cliffords (T) are incredibly slow/expensive due to magic state distillation.
        gate_specs = {
            'h': {'duration': 1e-6, 'error': 1e-8},
            's': {'duration': 1e-6, 'error': 1e-8},
            'cx': {'duration': 2e-6, 'error': 1e-7},
            't': {'duration': 50e-6, 'error': 1e-6}  # 25x slower than a CX
        }
        return create_custom_target(
            num_qubits, [HGate, SGate, CXGate, TGate], gate_specs, coupling_map
        )
        
    else:
        raise ValueError(f"Unknown architecture profile: {architecture}")