from typing import Tuple
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import Target
from qiskit.circuit import Gate


def count_network_operations(qc: QuantumCircuit, n: int, m: int) -> dict:
    """
    Scans a transpiled physical circuit to count total 2-qubit gates 
    and how many of those cross between different block modules.
    """
    n_block = n * m
    total_2q_gates = 0
    inter_block_gates = 0
    
    for inst in qc.data:
        # Check if the operation is a Gate (ignores barriers, delays, measures)
        # and if it acts on exactly 2 qubits
        if isinstance(inst.operation, Gate) and len(inst.qubits) == 2:
            total_2q_gates += 1
            
            # Get the physical integer indices of the qubits
            idx1 = qc.find_bit(inst.qubits[0]).index
            idx2 = qc.find_bit(inst.qubits[1]).index
            
            # Check if they belong to different blocks
            if (idx1 // n_block) != (idx2 // n_block):
                inter_block_gates += 1
                
    return {
        "total_2q_gates": total_2q_gates,
        "inter_block_gates": inter_block_gates
    }


def calculate_circuit_success_chance(transpiled_qc: QuantumCircuit, target) -> float:
    """Calculate overall circuit fidelity based on the specific mapped edges."""
    success_chance = 1.0
    
    for instruction in transpiled_qc.data:
        op_name = instruction.operation.name
        
        # Skip operations that don't have physical error rates
        if op_name in ["barrier", "measure", "delay"]:
            continue
            
        # Get the physical qubit indices this gate was mapped to
        phys_qubits = tuple(transpiled_qc.find_bit(q).index for q in instruction.qubits)
        
        # Retrieve the specific error for this physical gate from our Target
        # The Target object is a nested mapping: target[instruction_name][qargs]
        if op_name in target and phys_qubits in target[op_name]:
            props = target[op_name][phys_qubits]
            
            # props is an InstructionProperties object, which has an .error attribute
            if props and props.error is not None:
                success_chance *= (1 - props.error)
            
    return success_chance

def get_total_duration(qc: QuantumCircuit) -> float:
    """Safely retrieves duration from a scheduled circuit."""
    if hasattr(qc, "duration") and qc.duration is not None:
        return qc.duration
    
    # Fallback for newer Qiskit versions if .duration is missing
    try:
        return max(start + inst.operation.duration 
                   for inst, start, _ in qc.scheduled_instructions)
    except (ValueError, AttributeError):
        return 0.0

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