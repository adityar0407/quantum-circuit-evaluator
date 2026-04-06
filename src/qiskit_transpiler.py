from typing import Callable, Tuple
from qiskit import transpile, QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime import QiskitRuntimeService

from error_correction.surface_codes import create_gate_cost_evaluator
from error_correction.pass_managers import get_mapping_pm, get_optimization_pm

def transpile_circuit_generic(circuit, optimization_level=3, backend_name=None, connectivity=None, native_gate_list=None):
    """Uses the generic Qiskit transpiler with their premade pass managers."""
    assert (backend_name is not None) or ((connectivity is not None) and (native_gate_list is not None)), \
        "Either entire backend or the connectivity and native gate set must be provided."

    if backend_name is not None:
        service = QiskitRuntimeService()
        backend = service.backend(backend_name)
        transpiled_qc = transpile(circuit, backend=backend, optimization_level=optimization_level)
    else:
        transpiled_qc = transpile(circuit, optimization_level=optimization_level, coupling_map=connectivity, basis_gates=native_gate_list)

    return transpiled_qc

def dynamic_weight_transpile(
    circuit: QuantumCircuit,
    coupling_map: CouplingMap,
    cost_evaluator: Callable[[QuantumCircuit], float],
    target_weight_threshold: float,
    max_iterations: int = 5,
    basis_gates: list = None
) -> Tuple[QuantumCircuit, float]:
    """
    Iteratively optimizes a mapped circuit until a target weight is achieved 
    or convergence is reached.
    """
    
    # We must satisfy the connectivity map BEFORE evaluating the cost
    # since all optimization passes assume the circuit is already mapped to the hardware topology
    print("Mapping circuit to logical topology...")
    mapping_pm = get_mapping_pm(coupling_map)
    current_circuit = mapping_pm.run(circuit)
    
    # Baseline Evaluation
    current_weight = cost_evaluator(current_circuit)
    print(f"Baseline Circuit Weight (Post-Mapping): {current_weight}")
    
    if current_weight <= target_weight_threshold:
        print("  -> Circuit already meets threshold after mapping.")
        return current_circuit, current_weight

    # Setup Optimization Pass Manager
    opt_pm = get_optimization_pm(basis_gates)

    # Dynamic Checking Loop
    print("Beginning dynamic optimization loop...")
    for i in range(max_iterations):
        # Run one pass of optimization
        new_circuit = opt_pm.run(current_circuit)
        
        # Check convergence (if the passes didn't change anything, stop early)
        # will need to adjust this to be more robust for larger circuits (e.g., by comparing weights instead of exact circuit equality)
        if new_circuit == current_circuit:
            print(f"  -> Optimization converged at iteration {i + 1}. Stopping.")
            break
            
        current_circuit = new_circuit
        
        # Check the new weight
        current_weight = cost_evaluator(current_circuit)
        print(f"  -> Iteration {i} completed. New Circuit Weight: {current_weight}")
        
        # Evaluate against the user's threshold
        if current_weight <= target_weight_threshold:
            print("  -> Target weight achieved! Halting optimization early.")
            break

    return current_circuit, current_weight