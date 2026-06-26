from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.services.circuit_service import circuit_from_qasm
from backend.services.circuit_service import circuit_summary
from backend.services.compilers import get_compiler_backend
from backend.services.compilers.base import CompilerError
from backend.services.estimation_context import build_estimation_context
from backend.IR.logical_ir import build_logical_ir
from backend.IR.logical_ir import serialize_logical_ir
from backend.services.resource_estimators import get_resource_estimator
from backend.services.resource_estimators.base import ResourceEstimatorError

PANDORA_GATE_THRESHOLD = 1_000
PANDORA_QUBIT_THRESHOLD = 50
DEFAULT_RESOURCE_ESTIMATOR = "native_qre"


class TranspilationError(RuntimeError):
    """Raised when compilation or resource estimation fails."""


def select_compiler_backend(qasm: str, requested_backend: str) -> tuple[str, dict[str, Any]]:
    if requested_backend != "auto":
        return requested_backend, {"routing_mode": "manual"}

    circuit = circuit_from_qasm(qasm)
    if circuit.size() >= PANDORA_GATE_THRESHOLD or circuit.num_qubits >= PANDORA_QUBIT_THRESHOLD:
        selected = "pandora"
    else:
        selected = "qiskit_ftarget"

    return selected, {
        "routing_mode": "auto",
        "routing_policy": {
            "pandora_gate_threshold": PANDORA_GATE_THRESHOLD,
            "pandora_qubit_threshold": PANDORA_QUBIT_THRESHOLD,
        },
        "routing_input": {
            "gate_count": circuit.size(),
            "num_qubits": circuit.num_qubits,
        },
        "selected_compiler": selected,
    }


def compile_qasm(
    qasm: str,
    target_config: dict[str, Any],
    compiler_backend: str = "auto",
    resource_estimator: str = DEFAULT_RESOURCE_ESTIMATOR,
    estimation_profiles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        selected_backend, routing_artifacts = select_compiler_backend(qasm, compiler_backend)
        compiler = get_compiler_backend(selected_backend)
        compilation = compiler.compile(qasm, target_config)
        if compilation.target is not None:
            estimation_context = build_estimation_context(compilation.target, estimation_profiles)
            logical_ir = build_logical_ir(
                compilation.compiled_circuit,
                compilation.target,
                compilation.compiler,
                artifacts=compilation.artifacts,
                original_circuit=compilation.original_circuit,
            )
            compilation = replace(compilation, estimation_context=estimation_context, logical_ir=logical_ir)
            compilation.artifacts["logical_ir"] = serialize_logical_ir(logical_ir)
        compilation.artifacts.update(routing_artifacts)
        normalized_estimator = _select_resource_estimator(resource_estimator)
        estimator = get_resource_estimator(normalized_estimator)
        metrics = estimator.estimate(compilation)
    except (CompilerError, ResourceEstimatorError, ValueError) as exc:
        raise TranspilationError(str(exc)) from exc

    compiled_summary = circuit_summary(compilation.compiled_circuit)

    return {
        "compiler": compilation.compiler,
        "resource_estimator": estimator.key,
        "original": circuit_summary(compilation.original_circuit),
        "transpiled": compiled_summary,
        "compiled": compiled_summary,
        "metrics": metrics,
        "artifacts": compilation.artifacts,
        "warnings": compilation.warnings,
    }


def transpile_qasm(qasm: str, target_config: dict[str, Any]) -> dict[str, Any]:
    return compile_qasm(qasm, target_config)


def _select_resource_estimator(requested_estimator: str) -> str:
    if requested_estimator in {"", "auto", DEFAULT_RESOURCE_ESTIMATOR}:
        return DEFAULT_RESOURCE_ESTIMATOR

    return requested_estimator
