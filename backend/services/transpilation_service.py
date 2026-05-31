from __future__ import annotations

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from backend.metrics.metrics_evaluator import count_network_operations, evaluate_circuit_metrics
from backend.services.circuit_service import circuit_from_qasm, circuit_summary
from backend.services.target_service import build_target


class TranspilationError(RuntimeError):
    """Raised when Qiskit cannot transpile a valid circuit for a valid target."""


def transpile_qasm(qasm: str, target_config: dict) -> dict:
    circuit = circuit_from_qasm(qasm)
    target = build_target(target_config)

    try:
        pass_manager = generate_preset_pass_manager(
            optimization_level=3,
            target=target,
            scheduling_method="alap",
            seed_transpiler=1738,
        )
        transpiled = pass_manager.run(circuit)
    except Exception as exc:
        raise TranspilationError(f"Transpilation failed: {exc}") from exc

    metrics = evaluate_circuit_metrics(transpiled, target)
    metric_payload = {
        "independent_error_success_proxy": metrics.independent_error_success_proxy,
        "scheduled_duration_estimate_seconds": metrics.scheduled_duration_estimate_seconds,
        "missing_error_data_count": metrics.missing_error_data_count,
        "missing_duration_data_count": metrics.missing_duration_data_count,
        "unsupported_operation_count": metrics.unsupported_operation_count,
    }

    if hasattr(target, "n") and hasattr(target, "m"):
        metric_payload.update(count_network_operations(transpiled, target.n, target.m))

    return {
        "original": circuit_summary(circuit),
        "transpiled": circuit_summary(transpiled),
        "metrics": metric_payload,
    }
