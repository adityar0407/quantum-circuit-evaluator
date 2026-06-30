from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
from uuid import uuid4

from backend.IR.qasm import export_circuit_to_qasm
from backend.services.circuit_service import circuit_summary
from backend.services.compilers.base import CompilationResult
from backend.services.compilers.pandora_topology import validate_pandora_comparison_ready


def build_reproducible_run_export(
    *,
    qasm: str,
    target_config: dict[str, Any],
    requested_compiler_backend: str,
    requested_resource_estimator: str,
    estimation_profiles: dict[str, Any] | None,
    compilation: CompilationResult,
    resource_estimator_key: str,
    metrics: dict[str, Any],
    routing_artifacts: dict[str, Any],
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    run_id = f"run_{uuid4().hex}"
    logical_ir = compilation.logical_ir.to_dict() if compilation.logical_ir is not None else None
    logical_analysis = logical_ir.get("metadata", {}).get("analysis") if logical_ir is not None else None
    qre_trace = metrics.get("native_qre_trace", {})
    qre_assumptions = metrics.get("qre_assumptions", {})
    comparison_readiness = _architecture_comparison_readiness(compilation)

    return {
        "schema_version": "reproducible_run_export.v1",
        "run_id": run_id,
        "timestamp": timestamp,
        "input": {
            "original_qasm": qasm,
            "requested_compiler_backend": requested_compiler_backend,
            "requested_resource_estimator": requested_resource_estimator,
            "requested_estimation_profiles": estimation_profiles or {},
        },
        "compilation": {
            "selected_compiler": compilation.compiler,
            "compiler_version": _compiler_version(compilation.compiler),
            "compiler_configuration": _compiler_configuration(compilation, routing_artifacts),
            "ftarget_configuration": target_config,
            "original_summary": circuit_summary(compilation.original_circuit),
            "compiled_summary": circuit_summary(compilation.compiled_circuit),
            "compiled_qasm": export_circuit_to_qasm(compilation.compiled_circuit),
            "compiler_warnings": compilation.warnings,
            "placement_routing": _placement_routing(compilation, routing_artifacts),
            "architecture_comparison": comparison_readiness,
        },
        "logical_ir": {
            "serialized": logical_ir,
            "operation_counts": logical_ir.get("operation_counts") if logical_ir else None,
            "logical_depth": _logical_depth(logical_analysis),
            "local_operations": _operations_by_kind(logical_ir, remote=False),
            "remote_operations": _operations_by_kind(logical_ir, remote=True),
            "unsupported_operations": _unsupported_operations(metrics),
            "skipped_operations": qre_trace.get("skipped_operations", []),
            "analysis": logical_analysis,
        },
        "qre_input": {
            "input_representation": qre_assumptions.get("input_representation"),
            "trace_operation_summary": {
                "compute_qubits": qre_trace.get("compute_qubits"),
                "mapped_operation_count": qre_trace.get("mapped_operation_count"),
                "skipped_operation_count": qre_trace.get("skipped_operation_count"),
                "mapped_operations": qre_trace.get("mapped_operations", []),
            },
            "logical_ir_to_qre_mapping": qre_trace.get("mapped_operations", []),
            "angle_parameters": _angle_parameters(qre_trace),
            "skipped_operations": qre_trace.get("skipped_operations", []),
            "mapping_warnings": qre_trace.get("mapping_notes", []),
            "trace_json": qre_trace.get("trace_json"),
            "lattice_surgery_trace": metrics.get("native_qre_lattice_surgery"),
        },
        "estimation_assumptions": {
            "physical_hardware_profile": qre_assumptions.get("physical_hardware_profile"),
            "physical_hardware": qre_assumptions.get("physical_hardware"),
            "normalized_qdk_hardware_parameters": (
                qre_assumptions.get("physical_hardware", {}).get("normalized_qdk_parameters")
                if isinstance(qre_assumptions.get("physical_hardware"), dict)
                else None
            ),
            "qec_model": qre_assumptions.get("qec_model"),
            "error_budget": qre_assumptions.get("max_error"),
            "qdk_version": qre_assumptions.get("qdk_version") or metrics.get("qdk_version"),
            "estimator_mode": qre_assumptions.get("estimator_mode") or metrics.get("qre_mode"),
            "qre_transform": qre_assumptions.get("qre_transform"),
        },
        "results": {
            "physical_qubits": metrics.get("physical_qubits"),
            "runtime": metrics.get("runtime"),
            "runtime_unit": metrics.get("runtime_unit"),
            "estimated_error": metrics.get("logical_error"),
            "qre_metrics": metrics,
        },
        "limitations": [
            "Remote operations are unsupported by native QRE and fail rather than being localized or silently priced.",
            "Network profile metadata is carried for traceability but is not priced in native QRE estimates.",
            "Factory configuration and PSSPC settings are not separately exposed by the current qdk.qre.Trace estimate path.",
            "For QDK GateBased, separate 1Q, 2Q, and measurement errors are reduced to one aggregate error_rate using max(...).",
        ],
        "reproduction": {
            "pipeline": "input QASM -> Qiskit/Pandora -> LogicalIR -> qdk.qre.Trace -> LatticeSurgery -> Trace.estimate",
            "instructions": [
                "Use original_qasm and ftarget_configuration as inputs.",
                "Use the selected compiler and compiler_configuration to recreate the compiled circuit.",
                "Use serialized LogicalIR and qre_input.logical_ir_to_qre_mapping to recreate the QDK Trace.",
                "Use estimation_assumptions to instantiate the same QDK physical model and QEC model.",
                "Run LatticeSurgery().transform(trace), then Trace.estimate(...) with the recorded error budget.",
            ],
        },
    }


def _compiler_version(compiler: str) -> str:
    if compiler == "pandora":
        return "pandora-installed-package"
    if compiler == "qiskit_ftarget":
        try:
            import qiskit

            return getattr(qiskit, "__version__", "unknown")
        except Exception:
            return "unknown"
    return "unknown"


def _compiler_configuration(compilation: CompilationResult, routing_artifacts: dict[str, Any]) -> dict[str, Any]:
    logical_ir = compilation.logical_ir.to_dict() if compilation.logical_ir is not None else {}
    compiler_metadata = logical_ir.get("metadata", {}).get("compiler_metadata", {})
    return {
        "compiler_metadata": compiler_metadata,
        "routing_artifacts": routing_artifacts,
    }


def _placement_routing(compilation: CompilationResult, routing_artifacts: dict[str, Any]) -> dict[str, Any]:
    logical_ir = compilation.logical_ir.to_dict() if compilation.logical_ir is not None else {}
    compiler_metadata = logical_ir.get("metadata", {}).get("compiler_metadata", {})
    return {
        "placements": logical_ir.get("placements", []),
        "original_layout": compiler_metadata.get("original_layout"),
        "final_layout": compiler_metadata.get("final_layout"),
        "routing_swaps": compiler_metadata.get("routing_swaps"),
        "routing_artifacts": routing_artifacts,
    }


def _architecture_comparison_readiness(compilation: CompilationResult) -> dict[str, Any]:
    if compilation.compiler != "pandora":
        return {"accepted": True, "reason": "non_pandora_compiler"}

    try:
        validate_pandora_comparison_ready(compilation.artifacts)
        return {"accepted": True, "reason": "pandora_topology_validated"}
    except Exception as exc:
        return {"accepted": False, "reason": str(exc)}


def _logical_depth(logical_analysis: dict[str, Any] | None) -> int | None:
    if not logical_analysis:
        return None
    dag = logical_analysis.get("dag", {})
    return dag.get("critical_path_length")


def _operations_by_kind(logical_ir: dict[str, Any] | None, *, remote: bool) -> list[dict[str, Any]]:
    if logical_ir is None:
        return []
    operations = logical_ir.get("operations", [])
    return [
        operation
        for operation in operations
        if bool(operation.get("metadata", {}).get("remote")) is remote
    ]


def _unsupported_operations(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    qre_trace = metrics.get("native_qre_trace", {})
    mapped_ids = {
        operation.get("op_id")
        for operation in qre_trace.get("mapped_operations", [])
        if isinstance(operation, dict)
    }
    skipped_ids = {
        operation.get("op_id")
        for operation in qre_trace.get("skipped_operations", [])
        if isinstance(operation, dict)
    }
    unsupported = []
    for operation in qre_trace.get("source_operations", []):
        if operation.get("op_id") not in mapped_ids and operation.get("op_id") not in skipped_ids:
            unsupported.append(operation)
    return unsupported


def _angle_parameters(qre_trace: dict[str, Any]) -> list[dict[str, Any]]:
    angles = []
    for operation in qre_trace.get("mapped_operations", []):
        if operation.get("operation") in {"RX", "RY", "RZ"}:
            angles.append(
                {
                    "op_id": operation.get("op_id"),
                    "operation": operation.get("operation"),
                    "logical_ir_parameters": operation.get("parameters", []),
                    "qre_trace_parameters": operation.get("qre_parameters", []),
                }
            )
    return angles
