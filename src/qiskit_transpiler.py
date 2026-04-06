from qiskit import transpile, QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager, coupling_map, PassManager
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit.transpiler.passes import (
    Optimize1qGatesDecomposition,
    CommutativeCancellation,
    Collect2qBlocks,
    ConsolidateBlocks,
    UnitarySynthesis,
)
from error_correction.surface_codes import evaluate_ft_cost


## currently just uses the basic transpile function, but we can customize the pass manager to further optimize the circuit for the specific hardware...

def transpile_circuit_generic(circuit, optimization_level=3, backend_name = None, connectivity=None, native_gate_list=None):
    # uses the generic qiskit transpiler with their premade pass managers for different optimization levels 
    
    assert (backend_name is not None) or ((connectivity is not None) and (native_gate_list is not None)), "Either entire backend or the connectivity and native gate set must be provided."

    # Generate pass manager for the specified optimization level and backend
    if backend_name is not None:
        service = QiskitRuntimeService()
        backend = service.backend(backend_name)
        connectivity = coupling_map(backend)
        transpiled_qc = transpile(circuit, coupling_map=connectivity, optimization_level=optimization_level)
    else:
        transpiled_qc = transpile(circuit, optimization_level=optimization_level, coupling_map=connectivity, basis_gates=native_gate_list)

    return transpiled_qc


def dynamic_ft_transpile(circuit, target_isa, threshold_runtime):
    current_circuit = circuit.copy()
    
    # Phase 1: Init, Layout, Routing, and Initial Translation
    # (Assume you have pre-defined pass managers for these mandatory steps)
    pm_mandatory = PassManager()
    # pm_mandatory.append([YourLayoutPass(), YourRoutingPass(), YourTranslationPass()])
    # current_circuit = pm_mandatory.run(current_circuit)
    
    # Evaluate baseline
    current_cost = evaluate_ft_cost(current_circuit, target_isa, error_budget=1e-4)
    if current_cost <= threshold_runtime:
        return current_circuit, current_cost
    
    # Phase 2: Dynamic Optimization Loop
    # Define a pass manager for a single "round" of optimization
    pm_opt = PassManager([
        CommutativeCancellation(),
        Optimize1qGatesDecomposition(target_isa),
        Collect2qBlocks(),
        ConsolidateBlocks(),
        UnitarySynthesis(target_isa)
    ])
    
    max_iterations = 10
    for i in range(max_iterations):
        # Apply one round of optimization
        new_circuit = pm_opt.run(current_circuit)
        
        # Check if the circuit actually changed (to prevent infinite loops)
        # will need to make a better way around direct comparison of circuits, maybe by comparing their cost or some hash of their structure instead
        if new_circuit == current_circuit:
            print(f"Convergence reached at iteration {i}.")
            break
            
        current_circuit = new_circuit
        current_cost = evaluate_ft_cost(current_circuit, target_isa, error_budget=1e-4)
        
        print(f"Iteration {i}: Cost = {current_cost}")
        
        # EARLY STOPPING: If the circuit is "good enough" for benchmarking
        if current_cost <= threshold_runtime:
            print("Acceptable runtime achieved. Halting optimization early.")
            break

    return current_circuit, current_cost




## TODO:
# FOCUS CUSTOM PASS MANAGER ON REDUCING T-GATE COUNT AND DEPTH, AS THESE ARE CRITICAL FOR FT PERFORMANCE
# represent logical topology of the connectivity