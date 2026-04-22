from __future__ import annotations

from dataclasses import dataclass

from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import Target


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
