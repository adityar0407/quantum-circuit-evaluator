from qiskit import transpile, QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager, coupling_map
from qiskit_ibm_runtime import QiskitRuntimeService


## currently just uses the basic transpile function, but we can customize the pass manager to further optimize the circuit for the specific hardware...

def transpile_circuit(circuit, optimization_level=3, backend_name = None, connectivity=None, native_gate_list=None):
    # Load account
    
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

