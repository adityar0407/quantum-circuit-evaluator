from __future__ import annotations

from typing import Any

from backend.metrics.metrics_evaluator import count_network_operations, evaluate_circuit_metrics
from backend.services.compilers.base import CompilationResult
from backend.services.resource_estimators.base import ResourceEstimatorError


class SimpleLogicalEstimator:
    key = "simple_logical"

    def estimate(self, compilation: CompilationResult) -> dict[str, Any]:
        if compilation.target is None:
            raise ResourceEstimatorError("Simple logical estimator requires a target.")

        metrics = evaluate_circuit_metrics(compilation.compiled_circuit, compilation.target)
        metric_payload: dict[str, Any] = {
            "independent_error_success_proxy": metrics.independent_error_success_proxy,
            "scheduled_duration_estimate_seconds": metrics.scheduled_duration_estimate_seconds,
            "missing_error_data_count": metrics.missing_error_data_count,
            "missing_duration_data_count": metrics.missing_duration_data_count,
            "unsupported_operation_count": metrics.unsupported_operation_count,
        }

        if hasattr(compilation.target, "n") and hasattr(compilation.target, "m"):
            metric_payload.update(
                count_network_operations(
                    compilation.compiled_circuit,
                    compilation.target.n,
                    compilation.target.m,
                )
            )

        return metric_payload
