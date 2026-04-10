from typing import Tuple
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import Target

def evaluate_circuit_metrics(circuit: QuantumCircuit, target: Target) -> Tuple[float, float]:
    """
    Evaluates a transpiled quantum circuit against a hardware Target to find
    the Expected Success Probability (ESP) and total execution time.
    
    Args:
        circuit: The mapped/routed QuantumCircuit.
        target: The Qiskit Target object containing hardware specs.
        
    Returns:
        A tuple of (success_probability, total_duration_in_seconds).
    """
    expected_success_prob = 1.0
    
    # Track the current "clock time" for each physical qubit
    # e.g., {0: 0.0, 1: 300e-9, 2: 0.0}
    qubit_times = {i: 0.0 for i in range(circuit.num_qubits)}
    
    for inst in circuit.data:
        gate_name = inst.operation.name
        
        # Skip compiler directives that don't take physical time/error
        if gate_name in ["barrier", "delay"]:
            continue
            
        # Find the physical indices of the qubits this gate acts on
        # (circuit.data stores Qubit objects, we need their integer IDs)
        q_args = tuple(circuit.find_bit(q).index for q in inst.qubits)
        
        # Look up this exact gate and qubit combination in the target
        if gate_name in target and q_args in target[gate_name]:
            props = target[gate_name][q_args]
            # Use 0.0 if the property is missing (perfect gate assumption)
            error = props.error if getattr(props, 'error', None) is not None else 0.0
            duration = props.duration if getattr(props, 'duration', None) is not None else 0.0
        else:
            # PENALTY: If the transpiler left an unmapped or illegal gate in the circuit
            error = 1.0   # Guaranteed failure
            duration = 0.0
            
        # 1. Update Probability
        expected_success_prob *= (1.0 - error)
        
        # 2. Update Execution Time (Critical Path)
        # The gate can only execute once ALL involved qubits are free
        start_time = max(qubit_times[q] for q in q_args)
        end_time = start_time + duration
        
        # Advance the clock for all qubits involved in this gate
        for q in q_args:
            qubit_times[q] = end_time
            
    # The total circuit execution time is the time the very last qubit finishes
    total_time = max(qubit_times.values())
    
    return expected_success_prob, total_time