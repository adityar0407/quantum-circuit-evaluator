from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.services.circuit_service import circuit_from_qasm
from backend.services.circuit_service import circuit_summary
from backend.services.compilers import get_compiler_backend
from backend.services.compilers.pandora_compiler import PandoraCompiler
from backend.services.compilers.base import CompilerError
from backend.services.estimation_context import build_estimation_context
from backend.IR.logical_ir import build_logical_ir
from backend.IR.logical_ir import serialize_logical_ir
from backend.services.resource_estimators import get_resource_estimator
from backend.services.resource_estimators.base import ResourceEstimatorError
from backend.services.run_export import build_reproducible_run_export
from backend.services.target_service import build_target
from backend.services.target_service import export_target_topology

PANDORA_GATE_THRESHOLD = 1_000
PANDORA_QUBIT_THRESHOLD = 50
DEFAULT_RESOURCE_ESTIMATOR = "native_qre"


class TranspilationError(RuntimeError):
    """Raised when compilation or resource estimation fails."""


def select_compiler_backend(
    qasm: str,
    target_config: dict[str, Any],
    requested_backend: str,
) -> tuple[str, dict[str, Any]]:
    if requested_backend != "auto":
        return requested_backend, {"routing_mode": "manual"}

    circuit = circuit_from_qasm(qasm)
    target = build_target(target_config)
    topology = export_target_topology(target)
    pandora = PandoraCompiler()
    pandora_candidate = (
        pandora.python_path.exists()
        and topology["topology_type"] in pandora.supported_topologies
    )

    if pandora_candidate:
        selected = "pandora"
        selection_reason = "pandora_supported_ftarget_topology"
    else:
        selected = "qiskit_ftarget"
        if not pandora.python_path.exists():
            selection_reason = "pandora_environment_unavailable"
        else:
            selection_reason = "pandora_topology_unsupported"

    return selected, {
        "routing_mode": "auto",
        "routing_policy": {
            "auto_strategy": "ftarget_topology_first",
            "pandora_gate_threshold": PANDORA_GATE_THRESHOLD,
            "pandora_qubit_threshold": PANDORA_QUBIT_THRESHOLD,
            "pandora_supported_topologies": sorted(pandora.supported_topologies),
        },
        "routing_input": {
            "gate_count": circuit.size(),
            "num_qubits": circuit.num_qubits,
            "topology_type": topology["topology_type"],
            "pandora_candidate": pandora_candidate,
        },
        "selected_reason": selection_reason,
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
        selected_backend, routing_artifacts = select_compiler_backend(qasm, target_config, compiler_backend)
        compilation = _compile_with_fallback(
            qasm=qasm,
            target_config=target_config,
            compiler_backend=compiler_backend,
            selected_backend=selected_backend,
            routing_artifacts=routing_artifacts,
        )
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
        compilation.artifacts["reproducible_run_export"] = build_reproducible_run_export(
            qasm=qasm,
            target_config=target_config,
            requested_compiler_backend=compiler_backend,
            requested_resource_estimator=resource_estimator,
            estimation_profiles=estimation_profiles,
            compilation=compilation,
            resource_estimator_key=estimator.key,
            metrics=metrics,
            routing_artifacts=routing_artifacts,
        )
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


def _compile_with_fallback(
    *,
    qasm: str,
    target_config: dict[str, Any],
    compiler_backend: str,
    selected_backend: str,
    routing_artifacts: dict[str, Any],
):
    compiler = get_compiler_backend(selected_backend)
    if compiler_backend != "auto" or selected_backend != "pandora":
        return compiler.compile(qasm, target_config)

    try:
        return compiler.compile(qasm, target_config)
    except CompilerError as exc:
        fallback_compiler = get_compiler_backend("qiskit_ftarget")
        compilation = fallback_compiler.compile(qasm, target_config)
        compilation.artifacts["compiler_fallback"] = {
            "attempted": "pandora",
            "fallback": "qiskit_ftarget",
            "reason": str(exc),
        }
        routing_artifacts["selected_compiler"] = "qiskit_ftarget"
        routing_artifacts["selected_reason"] = "pandora_attempt_failed_fallback_to_qiskit"
        routing_artifacts["pandora_attempted"] = True
        routing_artifacts["pandora_failure_reason"] = str(exc)
        compilation.warnings.append(
            "Pandora compilation was attempted first for this FTarget but fell back to Qiskit because Pandora "
            f"could not compile the circuit cleanly: {exc}"
        )
        return compilation
