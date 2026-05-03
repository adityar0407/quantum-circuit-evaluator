from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class CircuitMetrics:
    """
    Metrics that depend on optional Target instruction properties.

    A None value means the target did not define enough data for that metric.
    """

    independent_error_success_proxy: float | None
    scheduled_duration_estimate_seconds: float | None
    missing_error_data_count: int
    missing_duration_data_count: int
    unsupported_operation_count: int


def evaluate_circuit_metrics(circuit: QuantumCircuit, target: Target) -> CircuitMetrics:
    """
    Evaluate first-order target-dependent metrics for a mapped circuit.

    The success proxy multiplies independent per-instruction success
    probabilities, when target errors are defined. The duration estimate tracks
    per-qubit clock times, when target durations are defined.
    
    Args:
        circuit: The mapped/routed QuantumCircuit.
        target: The Qiskit Target object containing instruction properties.
        
    Returns:
        CircuitMetrics with None for metrics whose required target properties
        are missing.
    """
    independent_error_success_proxy = 1.0
    missing_error_data_count = 0
    missing_duration_data_count = 0
    unsupported_operation_count = 0
    
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
        
        # Look up this exact gate and qubit combination in the target.
        if gate_name in target and q_args in target[gate_name]:
            props = target[gate_name][q_args]
        else:
            unsupported_operation_count += 1
            missing_error_data_count += 1
            missing_duration_data_count += 1
            continue

        if props is None or getattr(props, "error", None) is None:
            missing_error_data_count += 1
        else:
            independent_error_success_proxy *= 1.0 - props.error

        if props is None or getattr(props, "duration", None) is None:
            missing_duration_data_count += 1
            duration = 0.0
        else:
            duration = props.duration
        
        # Update the scheduled duration estimate critical path.
        # The gate can only execute once ALL involved qubits are free
        start_time = max(qubit_times[q] for q in q_args)
        end_time = start_time + duration
        
        # Advance the clock for all qubits involved in this gate
        for q in q_args:
            qubit_times[q] = end_time
            
    if missing_error_data_count:
        independent_error_success_proxy = None

    # The total circuit execution time is the time the very last qubit finishes.
    scheduled_duration_estimate_seconds = None
    if not missing_duration_data_count:
        scheduled_duration_estimate_seconds = max(qubit_times.values())
    
    return CircuitMetrics(
        independent_error_success_proxy=independent_error_success_proxy,
        scheduled_duration_estimate_seconds=scheduled_duration_estimate_seconds,
        missing_error_data_count=missing_error_data_count,
        missing_duration_data_count=missing_duration_data_count,
        unsupported_operation_count=unsupported_operation_count,
    )
